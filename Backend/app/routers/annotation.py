from __future__ import annotations

import uuid
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import config, rabbitmq
from ..database import get_db
from ..deps import get_current_user, require_role
from ..models import (
    AnnotationResult,
    DatasetItem,
    Task,
    TaskItem,
    TaskProgress,
    TaskTransition,
    Template,
    User,
)
from ..response import ok
from ..schemas import DraftRequest

router = APIRouter(prefix="/api/annotation", tags=["annotation"])


def _task_out(t: Task) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "template_id": t.template_id,
        "dataset_id": t.dataset_id,
        "status": t.status,
        "enable_ai_audit": t.enable_ai_audit,
        "enable_ai_suggestion": t.enable_ai_suggestion,
        "created_at": t.created_at,
    }


def _item_out(i: TaskItem) -> dict:
    return {
        "id": i.id,
        "task_id": i.task_id,
        "dataset_item_id": i.dataset_item_id,
        "index": i.index,
        "status": i.status,
        "assigned_labeler_id": i.assigned_labeler_id,
        "assigned_reviewer_id": i.assigned_reviewer_id,
    }


def _log_transition(db: Session, task_id: int, item_id: int, frm: str | None, to: str, operator_id: int, comment: str | None = None):
    db.add(TaskTransition(
        task_id=task_id, task_item_id=item_id, from_status=frm, to_status=to,
        operator_id=operator_id, operator_type="user", comment=comment,
    ))


@router.get("/square")
def square(
    status_filter: str | None = Query(default=None, alias="status"),
    keyword: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("labeler", "reviewer", "owner", "admin")),
):
    q = db.query(Task).filter(Task.status == "published")
    if keyword:
        q = q.filter(Task.name.like(f"%{keyword}%"))
    rows = q.order_by(Task.id.desc()).all()
    return ok([_task_out(t) for t in rows])


@router.post("/tasks/{task_id}/claim")
def claim_item(task_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("labeler", "owner", "admin"))):
    task = db.query(Task).filter(Task.id == task_id, Task.status == "published").first()
    if task is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "published task not found", "data": None})
    item = (
        db.query(TaskItem)
        .filter(TaskItem.task_id == task_id, TaskItem.status == "pending")
        .order_by(TaskItem.index)
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "no available items", "data": None})
    item.assigned_labeler_id = user.id
    item.status = "annotating"
    _log_transition(db, task_id, item.id, "pending", "annotating", user.id)
    db.commit()
    return ok({"task_item_id": item.id})


@router.get("/items/{item_id}")
def get_item(item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.query(TaskItem).filter(TaskItem.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "item not found", "data": None})
    task = db.query(Task).filter(Task.id == item.task_id).first()
    schema_json = None
    if task and task.template_id:
        tpl = db.query(Template).filter(Template.id == task.template_id).first()
        if tpl:
            schema_json = tpl.schema_json
    raw_data = None
    if item.dataset_item_id:
        di = db.query(DatasetItem).filter(DatasetItem.id == item.dataset_item_id).first()
        if di:
            raw_data = di.raw_data
    result_row = db.query(AnnotationResult).filter(AnnotationResult.task_item_id == item_id).first()
    suggestion = None
    if result_row and result_row.ai_suggestion_id:
        try:
            r = httpx.get(f"{config.AGENT_WEB_URL}/suggestion/{result_row.ai_suggestion_id}", timeout=5)
            if r.status_code == 200:
                suggestion = r.json()
        except Exception:
            suggestion = None
    return ok({
        "item": _item_out(item),
        "template_schema": schema_json,
        "raw_data": raw_data,
        "result": result_row.result if result_row else None,
        "suggestion": suggestion,
    })


@router.put("/items/{item_id}/draft")
def save_draft(item_id: int, body: DraftRequest, db: Session = Depends(get_db), user: User = Depends(require_role("labeler", "owner", "admin"))):
    item = db.query(TaskItem).filter(TaskItem.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "item not found", "data": None})
    if item.assigned_labeler_id and item.assigned_labeler_id != user.id and user.role_code not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail={"code": 403, "message": "item assigned to another labeler", "data": None})
    result = db.query(AnnotationResult).filter(AnnotationResult.task_item_id == item_id).first()
    if result is None:
        result = AnnotationResult(task_id=item.task_id, task_item_id=item_id, labeler_id=user.id, result=body.result, status="draft")
        db.add(result)
    else:
        result.result = body.result
        result.labeler_id = user.id
        result.status = "draft"
    if item.status == "pending":
        item.status = "annotating"
        _log_transition(db, item.task_id, item_id, "pending", "annotating", user.id)
    db.commit()
    return ok({"result": result.result})


@router.post("/items/{item_id}/submit")
def submit_item(item_id: int, body: DraftRequest, db: Session = Depends(get_db), user: User = Depends(require_role("labeler", "owner", "admin"))):
    item = db.query(TaskItem).filter(TaskItem.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "item not found", "data": None})
    task = db.query(Task).filter(Task.id == item.task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "task not found", "data": None})

    result = db.query(AnnotationResult).filter(AnnotationResult.task_item_id == item_id).first()
    if result is None:
        result = AnnotationResult(task_id=item.task_id, task_item_id=item_id, labeler_id=user.id, result=body.result, status="draft")
        db.add(result)
    else:
        result.result = body.result
        result.labeler_id = user.id
    result.submitted_at = datetime.now()

    if task.enable_ai_audit:
        audit_id = uuid.uuid4().hex
        result.ai_report_id = audit_id
        result.status = "submitted"
        item.status = "ai_reviewing"
        from_status = item.status
        _log_transition(db, item.task_id, item_id, "annotating", "ai_reviewing", user.id)
        db.commit()

        raw_data = None
        if item.dataset_item_id:
            di = db.query(DatasetItem).filter(DatasetItem.id == item.dataset_item_id).first()
            if di:
                raw_data = di.raw_data
        schema_json = None
        if task.template_id:
            tpl = db.query(Template).filter(Template.id == task.template_id).first()
            if tpl:
                schema_json = tpl.schema_json
        message = {
            "audit_id": audit_id,
            "task_id": task.id,
            "task_item_id": item.id,
            "template_schema": schema_json or {},
            "annotation_result": result.result or {},
            "raw_data": raw_data or {},
            "context": {"task_name": task.name, "dataset_name": None},
        }
        sent = rabbitmq.publish_audit(message)
        result.status = "submitted"
        item.status = "ai_reviewing" if sent else "submitted"
        db.commit()
        return ok({"result": result.result, "audit_id": audit_id if sent else None, "audit_dispatched": sent})
    else:
        result.status = "submitted"
        item.status = "reviewed"
        _log_transition(db, item.task_id, item_id, "annotating", "reviewed", user.id)
        db.commit()
        return ok({"result": result.result})


@router.post("/items/{item_id}/ai-suggestion")
def ai_suggestion(item_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("labeler", "owner", "admin"))):
    item = db.query(TaskItem).filter(TaskItem.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "item not found", "data": None})
    task = db.query(Task).filter(Task.id == item.task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "task not found", "data": None})
    if not task.enable_ai_suggestion:
        raise HTTPException(status_code=400, detail={"code": 400, "message": "ai suggestion disabled for task", "data": None})

    suggestion_id = uuid.uuid4().hex
    result = db.query(AnnotationResult).filter(AnnotationResult.task_item_id == item_id).first()
    if result is None:
        result = AnnotationResult(task_id=task.id, task_item_id=item_id, labeler_id=user.id, status="draft")
        db.add(result)
    result.ai_suggestion_id = suggestion_id
    db.commit()

    raw_data = None
    if item.dataset_item_id:
        di = db.query(DatasetItem).filter(DatasetItem.id == item.dataset_item_id).first()
        if di:
            raw_data = di.raw_data
    schema_json = None
    if task.template_id:
        tpl = db.query(Template).filter(Template.id == task.template_id).first()
        if tpl:
            schema_json = tpl.schema_json
    payload = {
        "suggestion_id": suggestion_id,
        "task_id": task.id,
        "task_item_id": item.id,
        "template_schema": schema_json or {},
        "raw_data": raw_data or {},
        "context": {"labeler_id": user.id},
    }
    try:
        r = httpx.post(f"{config.AGENT_WEB_URL}/suggestion", json=payload, timeout=10)
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail={"code": 502, "message": f"agent-web error: {r.text}", "data": None})
        data = r.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail={"code": 502, "message": f"agent-web unreachable: {e}", "data": None})
    return ok({"suggestion_id": suggestion_id, "status": data.get("status", "generating")})


@router.get("/suggestions/{suggestion_id}")
def poll_suggestion(suggestion_id: str, _user: User = Depends(get_current_user)):
    try:
        r = httpx.get(f"{config.AGENT_WEB_URL}/suggestion/{suggestion_id}", timeout=5)
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail={"code": 502, "message": f"agent-web error: {r.text}", "data": None})
        data = r.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail={"code": 502, "message": f"agent-web unreachable: {e}", "data": None})
    return ok({"status": data.get("status"), "suggestion": data.get("suggestion")})