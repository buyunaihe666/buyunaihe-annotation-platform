from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_role
from ..models import (
    Task,
    TaskAssignment,
    TaskItem,
    TaskProgress,
    TaskTransition,
    DatasetItem,
    AnnotationResult,
    Template,
    User,
)
from ..response import ok
from ..schemas import TaskCreate, TaskUpdate, AssignRequest

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

PROGRESS_STATUSES = [
    "pending",
    "annotating",
    "submitted",
    "ai_reviewing",
    "reviewed",
    "approved",
    "rejected",
    "completed",
]


def _out(t: Task) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "template_id": t.template_id,
        "dataset_id": t.dataset_id,
        "status": t.status,
        "enable_ai_audit": t.enable_ai_audit,
        "enable_ai_suggestion": t.enable_ai_suggestion,
        "quota": t.quota,
        "max_item_count": t.max_item_count,
        "deadline": t.deadline.isoformat() if t.deadline else None,
        "reward_rules": t.reward_rules,
        "tags": t.tags,
        "distribution_type": t.distribution_type,
        "ai_audit_config": t.ai_audit_config,
        "created_by": t.created_by,
        "created_at": t.created_at,
    }


def recompute_progress(db: Session, task_id: int) -> dict:
    rows = db.query(TaskItem.status).filter(TaskItem.task_id == task_id).all()
    counts = {s: 0 for s in PROGRESS_STATUSES}
    for (st,) in rows:
        counts[st] = counts.get(st, 0) + 1
    total = len(rows)
    progress = db.query(TaskProgress).filter(TaskProgress.task_id == task_id).first()
    if progress is None:
        progress = TaskProgress(task_id=task_id)
        db.add(progress)
    progress.total = total
    for s in PROGRESS_STATUSES:
        setattr(progress, s, counts.get(s, 0))
    db.commit()
    return {
        "total": total,
        "pending": counts.get("pending", 0),
        "annotating": counts.get("annotating", 0),
        "submitted": counts.get("submitted", 0),
        "ai_reviewing": counts.get("ai_reviewing", 0),
        "reviewed": counts.get("reviewed", 0),
        "approved": counts.get("approved", 0),
        "rejected": counts.get("rejected", 0),
        "completed": counts.get("completed", 0),
    }


@router.get("")
def list_tasks(
    status_filter: str | None = Query(default=None, alias="status"),
    keyword: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("owner", "admin", "labeler", "reviewer")),
):
    q = db.query(Task)
    if status_filter:
        q = q.filter(Task.status == status_filter)
    if keyword:
        q = q.filter(Task.name.like(f"%{keyword}%"))
    rows = q.order_by(Task.id.desc()).all()
    return ok([_out(t) for t in rows])


@router.post("")
def create_task(body: TaskCreate, db: Session = Depends(get_db), user: User = Depends(require_role("owner", "admin"))):
    # 确定数据集总量
    max_count = 0
    if body.dataset_id:
        ds = db.query(DatasetItem).filter(DatasetItem.dataset_id == body.dataset_id).count()
        max_count = ds

    t = Task(
        name=body.name,
        description=body.description,
        template_id=body.template_id,
        dataset_id=body.dataset_id,
        enable_ai_audit=1 if body.enable_ai_audit else 0,
        enable_ai_suggestion=1 if body.enable_ai_suggestion else 0,
        quota=body.quota if body.quota is not None else max_count,
        max_item_count=max_count,
        deadline=body.deadline,
        reward_rules=body.reward_rules,
        tags=body.tags,
        distribution_type=body.distribution_type or "first_come_first_serve",
        ai_audit_config=body.ai_audit_config,
        created_by=user.id,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return ok(_out(t))


@router.get("/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db), _user: User = Depends(require_role("owner", "admin", "labeler", "reviewer"))):
    t = db.query(Task).filter(Task.id == task_id).first()
    if t is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "task not found", "data": None})
    progress = recompute_progress(db, task_id)
    return ok({**_out(t), "progress": progress})


@router.put("/{task_id}")
def update_task(task_id: int, body: TaskUpdate, db: Session = Depends(get_db), _user: User = Depends(require_role("owner", "admin"))):
    t = db.query(Task).filter(Task.id == task_id).first()
    if t is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "task not found", "data": None})
    if body.name is not None:
        t.name = body.name
    if body.description is not None:
        t.description = body.description
    if body.template_id is not None:
        t.template_id = body.template_id
    if body.dataset_id is not None:
        t.dataset_id = body.dataset_id
    if body.enable_ai_audit is not None:
        t.enable_ai_audit = 1 if body.enable_ai_audit else 0
    if body.enable_ai_suggestion is not None:
        t.enable_ai_suggestion = 1 if body.enable_ai_suggestion else 0
    if body.quota is not None:
        t.quota = body.quota
    if body.deadline is not None:
        t.deadline = body.deadline
    if body.reward_rules is not None:
        t.reward_rules = body.reward_rules
    if body.tags is not None:
        t.tags = body.tags
    if body.distribution_type is not None:
        t.distribution_type = body.distribution_type
    if body.ai_audit_config is not None:
        t.ai_audit_config = body.ai_audit_config
    db.commit()
    db.refresh(t)
    return ok(_out(t))


class BatchDeleteRequest(BaseModel):
    ids: list[int]


@router.post("/batch-delete")
def batch_delete_tasks(body: BatchDeleteRequest, db: Session = Depends(get_db), _user: User = Depends(require_role("owner", "admin"))):
    deleted = 0
    for tid in body.ids:
        t = db.query(Task).filter(Task.id == tid).first()
        if t is None:
            continue
        db.query(TaskItem).filter(TaskItem.task_id == tid).delete()
        db.query(TaskAssignment).filter(TaskAssignment.task_id == tid).delete()
        db.query(TaskTransition).filter(TaskTransition.task_id == tid).delete()
        db.query(TaskProgress).filter(TaskProgress.task_id == tid).delete()
        db.delete(t)
        deleted += 1
    db.commit()
    return ok({"deleted": deleted})


@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), _user: User = Depends(require_role("owner", "admin"))):
    t = db.query(Task).filter(Task.id == task_id).first()
    if t is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "task not found", "data": None})
    db.query(TaskItem).filter(TaskItem.task_id == task_id).delete()
    db.query(TaskAssignment).filter(TaskAssignment.task_id == task_id).delete()
    db.query(TaskTransition).filter(TaskTransition.task_id == task_id).delete()
    db.query(TaskProgress).filter(TaskProgress.task_id == task_id).delete()
    db.delete(t)
    db.commit()
    return ok({})


@router.post("/{task_id}/publish")
def publish_task(task_id: int, db: Session = Depends(get_db), _user: User = Depends(require_role("owner", "admin"))):
    t = db.query(Task).filter(Task.id == task_id).first()
    if t is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "task not found", "data": None})
    if t.dataset_id is None:
        raise HTTPException(status_code=400, detail={"code": 400, "message": "dataset not bound", "data": None})
    existing = db.query(TaskItem).filter(TaskItem.task_id == task_id).count()
    if existing == 0:
        items = (
            db.query(DatasetItem)
            .filter(DatasetItem.dataset_id == t.dataset_id)
            .order_by(DatasetItem.index)
            .all()
        )
        for i, it in enumerate(items):
            db.add(TaskItem(task_id=task_id, dataset_item_id=it.id, index=i, status="pending"))
        db.flush()  # ensure new items have IDs
        # Apply existing reviewer assignments to the newly created items
        reviewer_assignments = (
            db.query(TaskAssignment)
            .filter(TaskAssignment.task_id == task_id, TaskAssignment.role == "reviewer")
            .all()
        )
        if reviewer_assignments:
            new_items = db.query(TaskItem).filter(TaskItem.task_id == task_id).all()
            for it in new_items:
                if it.assigned_reviewer_id is None:
                    it.assigned_reviewer_id = reviewer_assignments[0].user_id
    t.status = "published"
    db.commit()
    recompute_progress(db, task_id)
    db.refresh(t)
    return ok(_out(t))


@router.post("/{task_id}/pause")
def pause_task(task_id: int, db: Session = Depends(get_db), _user: User = Depends(require_role("owner", "admin"))):
    t = db.query(Task).filter(Task.id == task_id).first()
    if t is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "task not found", "data": None})
    t.status = "paused"
    db.commit()
    db.refresh(t)
    return ok(_out(t))


@router.post("/{task_id}/complete")
def complete_task(task_id: int, db: Session = Depends(get_db), _user: User = Depends(require_role("owner", "admin"))):
    t = db.query(Task).filter(Task.id == task_id).first()
    if t is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "task not found", "data": None})
    t.status = "completed"
    db.commit()
    recompute_progress(db, task_id)
    db.refresh(t)
    return ok(_out(t))


@router.get("/{task_id}/progress")
def task_progress(task_id: int, db: Session = Depends(get_db), _user: User = Depends(require_role("owner", "admin", "labeler", "reviewer"))):
    t = db.query(Task).filter(Task.id == task_id).first()
    if t is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "task not found", "data": None})
    return ok(recompute_progress(db, task_id))


@router.post("/{task_id}/assign")
def assign_task(
    task_id: int,
    body: AssignRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("owner", "admin")),
):
    t = db.query(Task).filter(Task.id == task_id).first()
    if t is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "task not found", "data": None})
    for a in body.assignments:
        existing = (
            db.query(TaskAssignment)
            .filter(TaskAssignment.task_id == task_id, TaskAssignment.user_id == a.user_id, TaskAssignment.role == a.role)
            .first()
        )
        if existing:
            continue
        db.add(TaskAssignment(task_id=task_id, user_id=a.user_id, role=a.role, review_order=a.review_order))
        if a.role == "reviewer":
            # 审核链路：设置首个审核员为当前审核员
            items = db.query(TaskItem).filter(
                TaskItem.task_id == task_id, TaskItem.assigned_reviewer_id.is_(None)
            ).all()
            for it in items:
                it.assigned_reviewer_id = a.user_id
                if it.current_reviewer_id is None:
                    it.current_reviewer_id = a.user_id
    db.commit()
    return ok({})


@router.get("/{task_id}/assignees")
def list_assignees(task_id: int, db: Session = Depends(get_db), _user: User = Depends(require_role("owner", "admin", "labeler", "reviewer"))):
    rows = db.query(TaskAssignment).filter(TaskAssignment.task_id == task_id).all()
    users = {u.id: u for u in db.query(User).all()}
    return ok([
        {
            "id": a.id,
            "task_id": a.task_id,
            "user_id": a.user_id,
            "username": users[a.user_id].username if a.user_id in users else None,
            "nickname": users[a.user_id].nickname if a.user_id in users else None,
            "role": a.role,
            "assigned_at": a.assigned_at,
        }
        for a in rows
    ])


@router.get("/{task_id}/items")
def list_task_items(
    task_id: int,
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=500),
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("owner", "admin", "labeler", "reviewer")),
):
    q = db.query(TaskItem).filter(TaskItem.task_id == task_id)
    if status_filter:
        q = q.filter(TaskItem.status == status_filter)
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
                "updated_at": r.updated_at,
            }
            for r in rows
        ],
        "total": total,
    })


@router.get("/{task_id}/items/{item_id}")
def get_task_item(task_id: int, item_id: int, db: Session = Depends(get_db), _user: User = Depends(require_role("owner", "admin", "labeler", "reviewer"))):
    return ok(_task_item_detail(db, task_id, item_id))


def _task_item_detail(db: Session, task_id: int, item_id: int) -> dict:
    item = db.query(TaskItem).filter(TaskItem.id == item_id, TaskItem.task_id == task_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "task item not found", "data": None})
    task = db.query(Task).filter(Task.id == task_id).first()
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
    result_row = (
        db.query(AnnotationResult)
        .filter(AnnotationResult.task_item_id == item_id)
        .first()
    )
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
    }