from __future__ import annotations

import uuid
import logging
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import config, rabbitmq
from ..database import get_db
from ..deps import get_current_user, require_role
from ..models import (
    AnnotationResult,
    Dataset,
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

logger = logging.getLogger("buyunaihe.annotation")

router = APIRouter(prefix="/api/annotation", tags=["annotation"])

# In-memory store for heuristic suggestions when the AI agent is unavailable.
_fallback_suggestions: dict[str, dict] = {}


def _heuristic_suggestion(schema_json: dict | None, raw_data: dict | None) -> dict:
    """Generate a simple heuristic suggestion based on template component types."""
    suggestion: dict[str, object] = {}
    components = []
    if isinstance(schema_json, dict):
        components = schema_json.get("components") or schema_json.get("fields") or []
    if isinstance(components, list):
        for comp in components:
            if not isinstance(comp, dict):
                continue
            key = comp.get("key") or comp.get("name") or comp.get("id")
            if not key:
                continue
            ctype = (comp.get("type") or "").lower()
            if ctype in ("radio", "select", "single_choice"):
                opts = comp.get("options") or []
                suggestion[key] = opts[0] if opts else ""
            elif ctype in ("checkbox", "multi_choice", "multiple_choice"):
                suggestion[key] = []
            elif ctype in ("number", "rating", "score"):
                suggestion[key] = comp.get("default", 3 if ctype == "rating" else 0)
            elif ctype in ("json", "json_editor"):
                suggestion[key] = {}
            elif ctype in ("file", "image", "upload"):
                suggestion[key] = ""
            else:
                suggestion[key] = ""
    return suggestion


def _task_out(t: Task, db: Session | None = None) -> dict:
    out = {
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
    if db is not None:
        # 关联模板和数据集名称
        tpl = db.query(Template).filter(Template.id == t.template_id).first() if t.template_id else None
        ds = db.query(Dataset).filter(Dataset.id == t.dataset_id).first() if t.dataset_id else None
        out["template"] = {"id": tpl.id, "name": tpl.name} if tpl else None
        out["dataset"] = {"id": ds.id, "name": ds.name} if ds else None
        # 剩余可领取数量
        available = db.query(TaskItem).filter(
            TaskItem.task_id == t.id, TaskItem.status == "pending"
        ).count()
        total = db.query(TaskItem).filter(TaskItem.task_id == t.id).count()
        out["available_count"] = available
        out["total_count"] = total
        out["reward_rules"] = t.reward_rules or {}
    return out


def _item_out(i: TaskItem) -> dict:
    return {
        "id": i.id,
        "task_id": i.task_id,
        "dataset_item_id": i.dataset_item_id,
        "index": i.index,
        "status": i.status,
        "assigned_labeler_id": i.assigned_labeler_id,
        "assigned_reviewer_id": i.assigned_reviewer_id,
        "current_reviewer_id": i.current_reviewer_id,
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
    tab: str = Query(default="available"),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("labeler", "reviewer", "owner", "admin")),
):
    if tab in ("mine_active", "mine_done"):
        if tab == "mine_active":
            item_statuses = ["annotating", "submitted", "ai_reviewing", "reviewed"]
        else:
            item_statuses = ["approved", "rejected", "completed"]

        items = db.query(TaskItem).filter(
            TaskItem.assigned_labeler_id == user.id,
            TaskItem.status.in_(item_statuses),
        ).all()
        task_ids = list({i.task_id for i in items})
        q = db.query(Task).filter(Task.id.in_(task_ids))
        if keyword:
            q = q.filter(Task.name.like(f"%{keyword}%"))
        rows = q.order_by(Task.id.desc()).all()
        result = []
        for t in rows:
            out = _task_out(t, db)
            task_items = [i for i in items if i.task_id == t.id]
            # 计算奖励
            rules = t.reward_rules or {}
            per_item = float(rules.get("per_item", 0))
            bonus_approved = float(rules.get("bonus_approved", 0))
            total_reward = 0.0
            my_items = []
            for i in task_items:
                reward = per_item
                if i.status == "approved":
                    reward += bonus_approved
                total_reward += reward
                my_items.append({
                    "id": i.id,
                    "status": i.status,
                    "index": i.index,
                    "reward": round(reward, 2),
                })
            out["my_items"] = my_items
            out["total_reward"] = round(total_reward, 2)
            out["reward_rules"] = rules
            result.append(out)
        return ok(result)

    # default: available (published tasks)
    q = db.query(Task).filter(Task.status == "published")
    if keyword:
        q = q.filter(Task.name.like(f"%{keyword}%"))
    rows = q.order_by(Task.id.desc()).all()
    return ok([_task_out(t, db) for t in rows])


@router.post("/tasks/{task_id}/claim")
def claim_item(
    task_id: int,
    count: int = Query(default=1, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("labeler", "owner", "admin")),
):
    task = db.query(Task).filter(Task.id == task_id, Task.status == "published").first()
    if task is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "published task not found", "data": None})
    items = (
        db.query(TaskItem)
        .filter(TaskItem.task_id == task_id, TaskItem.status == "pending")
        .order_by(TaskItem.index)
        .limit(count)
        .all()
    )
    if not items:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "no available items", "data": None})
    claimed_ids = []
    for item in items:
        item.assigned_labeler_id = user.id
        item.status = "annotating"
        _log_transition(db, task_id, item.id, "pending", "annotating", user.id)
        claimed_ids.append(item.id)
    db.commit()
    return ok({"task_item_ids": claimed_ids, "task_item_id": claimed_ids[0], "claimed_count": len(claimed_ids)})


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
    # Auto-transition: if ai_reviewing, check if audit is done
    if item.status == "ai_reviewing" and result_row and result_row.ai_report_id:
        try:
            r = httpx.get(f"{config.AGENT_WEB_URL}/audit/{result_row.ai_report_id}", timeout=5)
            if r.status_code == 200:
                audit_data = r.json()
                if audit_data.get("status") in ("done", "failed"):
                    item.status = "reviewed"
                    _log_transition(db, item.task_id, item_id, "ai_reviewing", "reviewed", 0, "AI audit completed")
                    db.commit()
        except Exception:
            pass
    return ok({
        "item": _item_out(item),
        "template_schema": schema_json,
        "raw_data": raw_data,
        "result": result_row.result if result_row else None,
        "suggestion": suggestion,
        "my_items": [
            {"id": mi.id, "status": mi.status, "index": mi.index}
            for mi in db.query(TaskItem)
            .filter(TaskItem.task_id == item.task_id, TaskItem.assigned_labeler_id == user.id)
            .order_by(TaskItem.index).all()
        ],
        "transitions": [
            {"id": tr.id, "from_status": tr.from_status, "to_status": tr.to_status,
             "created_at": tr.created_at.isoformat() if tr.created_at else None,
             "comment": tr.comment}
            for tr in db.query(TaskTransition)
            .filter(TaskTransition.task_item_id == item_id)
            .order_by(TaskTransition.id).all()
        ],
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
            raise httpx.HTTPError(f"agent-web status {r.status_code}")
        data = r.json()
        return ok({"suggestion_id": suggestion_id, "status": data.get("status", "generating")})
    except httpx.HTTPError as e:
        # Agent unreachable — generate heuristic fallback suggestion
        logger.warning(f"[ai-suggestion] agent unreachable ({e}), using heuristic fallback")
        heuristic = _heuristic_suggestion(schema_json, raw_data)
        _fallback_suggestions[suggestion_id] = {
            "status": "done",
            "suggestion": heuristic,
            "model": "heuristic",
        }
        return ok({"suggestion_id": suggestion_id, "status": "done"})


@router.get("/suggestions/{suggestion_id}")
def poll_suggestion(suggestion_id: str, _user: User = Depends(get_current_user)):
    # Check fallback store first (heuristic suggestions generated when agent was down)
    if suggestion_id in _fallback_suggestions:
        entry = _fallback_suggestions[suggestion_id]
        return ok({"status": entry.get("status"), "suggestion": entry.get("suggestion"), "model": entry.get("model")})
    try:
        r = httpx.get(f"{config.AGENT_WEB_URL}/suggestion/{suggestion_id}", timeout=5)
        if r.status_code != 200:
            raise httpx.HTTPError(f"agent-web status {r.status_code}")
        data = r.json()
    except httpx.HTTPError as e:
        # Agent unreachable and no fallback available
        return ok({"status": "error", "suggestion": None, "message": f"AI 服务暂不可用: {e}"})
    return ok({"status": data.get("status"), "suggestion": data.get("suggestion")})