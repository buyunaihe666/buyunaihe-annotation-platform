from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import config
from ..database import get_db
from ..deps import require_role, get_current_user
from ..models import (
    AnnotationResult,
    DatasetItem,
    ReviewOpinion,
    Task,
    TaskItem,
    TaskTransition,
    Template,
    User,
)
from ..response import ok
from ..schemas import DecisionRequest

router = APIRouter(prefix="/api/review", tags=["review"])


def _task_out(t: Task) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "status": t.status,
        "template_id": t.template_id,
        "dataset_id": t.dataset_id,
        "enable_ai_audit": t.enable_ai_audit,
        "created_at": t.created_at,
    }


@router.get("/tasks")
def review_tasks(
    keyword: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("reviewer", "owner", "admin")),
):
    q = (
        db.query(Task)
        .join(TaskItem, TaskItem.task_id == Task.id)
        .filter(TaskItem.status.in_(["submitted", "ai_reviewing", "reviewed"]))
    )
    if user.role_code == "reviewer":
        q = q.filter(TaskItem.assigned_reviewer_id == user.id)
    if keyword:
        q = q.filter(Task.name.like(f"%{keyword}%"))
    rows = q.distinct().order_by(Task.id.desc()).all()
    return ok([_task_out(t) for t in rows])


@router.get("/tasks/{task_id}/items")
def review_items(
    task_id: int,
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("reviewer", "owner", "admin")),
):
    q = db.query(TaskItem).filter(TaskItem.task_id == task_id)
    if user.role_code == "reviewer":
        q = q.filter(TaskItem.assigned_reviewer_id == user.id)
    if status_filter:
        q = q.filter(TaskItem.status == status_filter)
    else:
        q = q.filter(TaskItem.status.in_(["submitted", "ai_reviewing", "reviewed"]))
    total = q.count()
    rows = q.order_by(TaskItem.index).offset((page - 1) * size).limit(size).all()
    return ok({
        "items": [
            {
                "id": r.id,
                "task_id": r.task_id,
                "dataset_item_id": r.dataset_item_id,
                "index": r.index,
                "status": r.status,
                "assigned_labeler_id": r.assigned_labeler_id,
                "assigned_reviewer_id": r.assigned_reviewer_id,
            }
            for r in rows
        ],
        "total": total,
    })


@router.get("/items/{item_id}")
def review_item(item_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("reviewer", "owner", "admin"))):
    data = _item_detail(db, item_id)
    return ok(data)


def _item_detail(db: Session, item_id: int) -> dict:
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
    ai_report = None
    opinion = db.query(ReviewOpinion).filter(ReviewOpinion.task_item_id == item_id).order_by(ReviewOpinion.id.desc()).first()
    ai_report_id = None
    if opinion and opinion.ai_report_id:
        ai_report_id = opinion.ai_report_id
    elif result_row and result_row.ai_report_id:
        ai_report_id = result_row.ai_report_id
    if ai_report_id:
        try:
            r = httpx.get(f"{config.AGENT_WEB_URL}/audit/{ai_report_id}", timeout=5)
            if r.status_code == 200:
                ai_report = r.json()
        except Exception:
            ai_report = None
    return {
        "item": {
            "id": item.id,
            "task_id": item.task_id,
            "dataset_item_id": item.dataset_item_id,
            "index": item.index,
            "status": item.status,
            "assigned_labeler_id": item.assigned_labeler_id,
            "assigned_reviewer_id": item.assigned_reviewer_id,
        },
        "template_schema": schema_json,
        "raw_data": raw_data,
        "result": result_row.result if result_row else None,
        "ai_report": ai_report,
    }


@router.get("/items/{item_id}/ai-report")
def review_ai_report(item_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("reviewer", "owner", "admin"))):
    item = db.query(TaskItem).filter(TaskItem.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "item not found", "data": None})
    opinion = (
        db.query(ReviewOpinion)
        .filter(ReviewOpinion.task_item_id == item_id, ReviewOpinion.ai_report_id.isnot(None))
        .order_by(ReviewOpinion.id.desc())
        .first()
    )
    audit_id = opinion.ai_report_id if opinion else None
    if not audit_id:
        result = db.query(AnnotationResult).filter(AnnotationResult.task_item_id == item_id).first()
        if result and result.ai_report_id:
            audit_id = result.ai_report_id
    if not audit_id:
        return ok({"status": "none", "score": None, "issues": [], "reasoning": None, "suggestion": None})
    try:
        r = httpx.get(f"{config.AGENT_WEB_URL}/audit/{audit_id}", timeout=5)
        if r.status_code != 200:
            return ok({"status": "error", "score": None, "issues": [], "reasoning": None, "suggestion": None})
        data = r.json()
    except Exception:
        return ok({"status": "unavailable", "score": None, "issues": [], "reasoning": None, "suggestion": None})
    return ok({
        "status": data.get("status"),
        "score": data.get("score"),
        "issues": data.get("issues"),
        "reasoning": data.get("reasoning"),
        "suggestion": data.get("suggestion"),
    })


@router.post("/items/{item_id}/decision")
def review_decision(
    item_id: int,
    body: DecisionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("reviewer", "owner", "admin")),
):
    item = db.query(TaskItem).filter(TaskItem.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "item not found", "data": None})
    task = db.query(Task).filter(Task.id == item.task_id).first()

    decision_map = {
        "approved": "approved",
        "rejected": "rejected",
        "modify_approve": "completed",
    }
    new_status = decision_map.get(body.decision)
    if new_status is None:
        raise HTTPException(status_code=400, detail={"code": 400, "message": "invalid decision", "data": None})

    opinion = ReviewOpinion(
        task_id=item.task_id,
        task_item_id=item_id,
        reviewer_id=user.id,
        decision=body.decision,
        comment=body.comment,
    )
    result = db.query(AnnotationResult).filter(AnnotationResult.task_item_id == item_id).first()
    if result and result.ai_report_id:
        opinion.ai_report_id = result.ai_report_id
    db.add(opinion)

    from_status = item.status
    item.status = new_status
    item.assigned_reviewer_id = user.id
    db.add(TaskTransition(
        task_id=item.task_id, task_item_id=item_id, from_status=from_status, to_status=new_status,
        operator_id=user.id, operator_type="reviewer", comment=body.comment,
    ))
    db.commit()
    db.refresh(item)
    return ok({"task_item": {
        "id": item.id,
        "task_id": item.task_id,
        "dataset_item_id": item.dataset_item_id,
        "index": item.index,
        "status": item.status,
        "assigned_labeler_id": item.assigned_labeler_id,
        "assigned_reviewer_id": item.assigned_reviewer_id,
    }})