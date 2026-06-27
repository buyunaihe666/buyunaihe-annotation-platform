from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_role
from ..models import (
    AnnotationResult,
    Dataset,
    ReviewOpinion,
    Task,
    TaskItem,
    TaskTransition,
    Template,
    User,
)
from ..response import ok

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/overview")
def overview(db: Session = Depends(get_db), _user: User = Depends(require_role("owner", "admin", "reviewer", "labeler"))):
    task_count = db.query(Task).count()
    dataset_count = db.query(Dataset).count()
    template_count = db.query(Template).count()
    user_count = db.query(User).count()
    pending_review = db.query(TaskItem).filter(TaskItem.status.in_(["submitted", "ai_reviewing", "reviewed"])).count()
    completed_items = db.query(TaskItem).filter(TaskItem.status.in_(["approved", "completed"])).count()
    return ok({
        "task_count": task_count,
        "dataset_count": dataset_count,
        "template_count": template_count,
        "user_count": user_count,
        "pending_review": pending_review,
        "completed_items": completed_items,
    })


@router.get("/task/{task_id}")
def task_stats(task_id: int, db: Session = Depends(get_db), _user: User = Depends(require_role("owner", "admin", "reviewer", "labeler"))):
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "task not found", "data": None})

    items = db.query(TaskItem).filter(TaskItem.task_id == task_id).all()
    status_counts = Counter(i.status for i in items)
    total = len(items)
    progress = {
        "total": total,
        "pending": status_counts.get("pending", 0),
        "annotating": status_counts.get("annotating", 0),
        "submitted": status_counts.get("submitted", 0),
        "ai_reviewing": status_counts.get("ai_reviewing", 0),
        "reviewed": status_counts.get("reviewed", 0),
        "approved": status_counts.get("approved", 0),
        "rejected": status_counts.get("rejected", 0),
        "completed": status_counts.get("completed", 0),
    }

    labeler_stats: list[dict] = []
    labeler_ids = {i.assigned_labeler_id for i in items if i.assigned_labeler_id}
    users = {u.id: u for u in db.query(User).filter(User.id.in_(labeler_ids)).all()} if labeler_ids else {}
    for lid in labeler_ids:
        litems = [i for i in items if i.assigned_labeler_id == lid]
        lc = Counter(i.status for i in litems)
        labeler_stats.append({
            "user_id": lid,
            "username": users.get(lid).username if users.get(lid) else None,
            "nickname": users.get(lid).nickname if users.get(lid) else None,
            "assigned": len(litems),
            "annotating": lc.get("annotating", 0),
            "submitted": lc.get("submitted", 0) + lc.get("ai_reviewing", 0) + lc.get("reviewed", 0),
            "approved": lc.get("approved", 0) + lc.get("completed", 0),
            "rejected": lc.get("rejected", 0),
        })

    transitions = (
        db.query(TaskTransition)
        .filter(TaskTransition.task_id == task_id)
        .order_by(TaskTransition.created_at)
        .all()
    )
    timeline_buckets: dict[str, Counter] = defaultdict(Counter)
    for t in transitions:
        if t.created_at is None:
            continue
        key = t.created_at.strftime("%Y-%m-%d")
        timeline_buckets[key][t.to_status] += 1
    timeline = [
        {"date": d, "events": dict(c)}
        for d, c in sorted(timeline_buckets.items())
    ]

    return ok({
        "progress": progress,
        "labeler_stats": labeler_stats,
        "timeline": timeline,
    })