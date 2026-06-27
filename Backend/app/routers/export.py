from __future__ import annotations

import csv
import io
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .. import config
from ..database import get_db
from ..deps import require_role
from ..minio_client import public_url, upload_bytes
from ..models import (
    AnnotationResult,
    DatasetItem,
    ExportFile,
    ExportRecord,
    Task,
    TaskItem,
    User,
)
from ..response import ok
from ..schemas import ExportRequest

router = APIRouter(prefix="/api/export", tags=["export"])

EXPORT_STATUSES = ("approved", "completed")


def _record_out(r: ExportRecord, with_files: bool = False) -> dict:
    out = {
        "id": r.id,
        "task_id": r.task_id,
        "format": r.format,
        "status": r.status,
        "total": r.total,
        "created_by": r.created_by,
        "created_at": r.created_at,
        "completed_at": r.completed_at,
    }
    if with_files:
        out["files"] = [
            {
                "id": f.id,
                "minio_object": f.minio_object,
                "filename": f.filename,
                "size": f.size,
                "url": f.url,
            }
            for f in r.files
        ] if hasattr(r, "files") else []
    return out


def _collect_rows(db: Session, task_id: int) -> list[dict]:
    items = (
        db.query(TaskItem, AnnotationResult, DatasetItem)
        .join(AnnotationResult, AnnotationResult.task_item_id == TaskItem.id)
        .outerjoin(DatasetItem, DatasetItem.id == TaskItem.dataset_item_id)
        .filter(TaskItem.task_id == task_id, TaskItem.status.in_(EXPORT_STATUSES))
        .order_by(TaskItem.index)
        .all()
    )
    rows = []
    for ti, ar, di in items:
        raw = di.raw_data if di else None
        row = {
            "task_item_id": ti.id,
            "index": ti.index,
            "status": ti.status,
            "raw_data": raw if isinstance(raw, dict) else ({"value": raw} if raw is not None else {}),
            "annotation_result": ar.result,
            "labeler_id": ar.labeler_id,
            "submitted_at": ar.submitted_at.isoformat() if ar.submitted_at else None,
        }
        rows.append(row)
    return rows


def _build_content(rows: list[dict], fmt: str) -> tuple[bytes, str]:
    if fmt == "json":
        return json.dumps(rows, ensure_ascii=False, indent=2).encode("utf-8"), "application/json"
    if fmt == "jsonl":
        text = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows)
        return (text + "\n").encode("utf-8"), "application/x-ndjson"
    if fmt == "csv":
        if not rows:
            return b"", "text/csv"
        flat = []
        all_keys: list[str] = []
        for r in rows:
            f = {"task_item_id": r["task_item_id"], "index": r["index"], "status": r["status"]}
            raw = r.get("raw_data") or {}
            res = r.get("annotation_result") or {}
            for k, v in raw.items():
                f[f"raw_{k}"] = v
            for k, v in res.items():
                f[f"result_{k}"] = v
            flat.append(f)
            for k in f.keys():
                if k not in all_keys:
                    all_keys.append(k)
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=all_keys)
        writer.writeheader()
        for f in flat:
            writer.writerow({k: f.get(k, "") for k in all_keys})
        return buf.getvalue().encode("utf-8"), "text/csv"
    if fmt == "xlsx":
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = "export"
        if rows:
            flat = []
            all_keys: list[str] = []
            for r in rows:
                f = {"task_item_id": r["task_item_id"], "index": r["index"], "status": r["status"]}
                raw = r.get("raw_data") or {}
                res = r.get("annotation_result") or {}
                for k, v in raw.items():
                    f[f"raw_{k}"] = v
                for k, v in res.items():
                    f[f"result_{k}"] = v
                flat.append(f)
                for k in f.keys():
                    if k not in all_keys:
                        all_keys.append(k)
            ws.append(all_keys)
            for f in flat:
                ws.append([f.get(k) for k in all_keys])
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    raise ValueError(f"unsupported format {fmt}")


@router.post("")
def create_export(body: ExportRequest, db: Session = Depends(get_db), user: User = Depends(require_role("owner", "admin", "reviewer"))):
    task = db.query(Task).filter(Task.id == body.task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "task not found", "data": None})
    if body.format not in ("json", "jsonl", "csv", "xlsx"):
        raise HTTPException(status_code=400, detail={"code": 400, "message": "unsupported format", "data": None})

    rec = ExportRecord(task_id=body.task_id, format=body.format, status="pending", created_by=user.id)
    db.add(rec)
    db.commit()
    db.refresh(rec)

    rows = _collect_rows(db, task.id)
    rec.total = len(rows)
    try:
        content, content_type = _build_content(rows, body.format)
        ext = {"json": "json", "jsonl": "jsonl", "csv": "csv", "xlsx": "xlsx"}[body.format]
        filename = f"export_task{task.id}_{rec.id}.{ext}"
        object_name = upload_bytes("export", content, filename, content_type)
        url = public_url("export", object_name)
        ef = ExportFile(
            export_record_id=rec.id,
            minio_object=object_name,
            filename=filename,
            size=len(content),
            url=url,
        )
        db.add(ef)
        rec.status = "completed"
        rec.completed_at = datetime.now()
    except Exception as e:
        rec.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail={"code": 500, "message": f"export failed: {e}", "data": None})
    db.commit()
    db.refresh(rec)
    files = db.query(ExportFile).filter(ExportFile.export_record_id == rec.id).all()
    out = _record_out(rec)
    out["files"] = [
        {"id": f.id, "minio_object": f.minio_object, "filename": f.filename, "size": f.size, "url": f.url}
        for f in files
    ]
    return ok(out)


@router.get("")
def list_exports(task_id: int | None = Query(default=None), db: Session = Depends(get_db), _user: User = Depends(require_role("owner", "admin", "reviewer"))):
    q = db.query(ExportRecord)
    if task_id is not None:
        q = q.filter(ExportRecord.task_id == task_id)
    rows = q.order_by(ExportRecord.id.desc()).all()
    return ok([_record_out(r) for r in rows])


@router.get("/{export_id}")
def get_export(export_id: int, db: Session = Depends(get_db), _user: User = Depends(require_role("owner", "admin", "reviewer"))):
    r = db.query(ExportRecord).filter(ExportRecord.id == export_id).first()
    if r is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "export not found", "data": None})
    files = db.query(ExportFile).filter(ExportFile.export_record_id == r.id).all()
    out = _record_out(r)
    out["files"] = [
        {"id": f.id, "minio_object": f.minio_object, "filename": f.filename, "size": f.size, "url": f.url}
        for f in files
    ]
    return ok(out)


@router.get("/{export_id}/download")
def download_export(export_id: int, db: Session = Depends(get_db), _user: User = Depends(require_role("owner", "admin", "reviewer"))):
    r = db.query(ExportRecord).filter(ExportRecord.id == export_id).first()
    if r is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "export not found", "data": None})
    f = db.query(ExportFile).filter(ExportFile.export_record_id == r.id).order_by(ExportFile.id.desc()).first()
    if f is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "no file", "data": None})
    return RedirectResponse(url=f.url or public_url("export", f.minio_object))