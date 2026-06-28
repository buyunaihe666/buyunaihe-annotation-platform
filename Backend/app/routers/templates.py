from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_role
from ..models import Template, User
from ..response import ok
from ..schemas import TemplateCreate, TemplateUpdate

router = APIRouter(prefix="/api/templates", tags=["templates"])


def _out(t: Template) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "status": t.status,
        "schema": t.schema_json,
        "created_by": t.created_by,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }


@router.get("")
def list_templates(
    status_filter: str | None = Query(default=None, alias="status"),
    keyword: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("owner", "admin", "labeler", "reviewer")),
):
    q = db.query(Template)
    if status_filter:
        q = q.filter(Template.status == status_filter)
    if keyword:
        kw = f"%{keyword}%"
        q = q.filter(Template.name.like(kw))
    rows = q.order_by(Template.id.desc()).all()
    return ok([_out(t) for t in rows])


@router.post("")
def create_template(
    body: TemplateCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("owner", "admin")),
):
    t = Template(
        name=body.name,
        description=body.description,
        schema_json=body.schema,
        created_by=user.id,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return ok(_out(t))


@router.get("/{template_id}")
def get_template(template_id: int, db: Session = Depends(get_db), _user: User = Depends(require_role("owner", "admin", "labeler", "reviewer"))):
    t = db.query(Template).filter(Template.id == template_id).first()
    if t is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "template not found", "data": None})
    return ok(_out(t))


@router.put("/{template_id}")
def update_template(
    template_id: int,
    body: TemplateUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("owner", "admin")),
):
    t = db.query(Template).filter(Template.id == template_id).first()
    if t is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "template not found", "data": None})
    if body.name is not None:
        t.name = body.name
    if body.description is not None:
        t.description = body.description
    if body.schema is not None:
        t.schema_json = body.schema
    db.commit()
    db.refresh(t)
    return ok(_out(t))


@router.delete("/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db), _user: User = Depends(require_role("owner", "admin"))):
    t = db.query(Template).filter(Template.id == template_id).first()
    if t is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "template not found", "data": None})
    db.delete(t)
    db.commit()
    return ok({})


@router.post("/{template_id}/publish")
def publish_template(template_id: int, db: Session = Depends(get_db), _user: User = Depends(require_role("owner", "admin"))):
    t = db.query(Template).filter(Template.id == template_id).first()
    if t is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "template not found", "data": None})
    t.status = "published"
    db.commit()
    db.refresh(t)
    return ok(_out(t))


@router.post("/{template_id}/archive")
def archive_template(template_id: int, db: Session = Depends(get_db), _user: User = Depends(require_role("owner", "admin"))):
    t = db.query(Template).filter(Template.id == template_id).first()
    if t is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "template not found", "data": None})
    t.status = "archived"
    db.commit()
    db.refresh(t)
    return ok(_out(t))


class BatchDeleteRequest(BaseModel):
    ids: list[int]


@router.post("/batch-delete")
def batch_delete_templates(body: BatchDeleteRequest, db: Session = Depends(get_db), _user: User = Depends(require_role("owner", "admin"))):
    deleted = 0
    for template_id in body.ids:
        t = db.query(Template).filter(Template.id == template_id).first()
        if t is None:
            continue
        db.delete(t)
        deleted += 1
    db.commit()
    return ok({"deleted": deleted})