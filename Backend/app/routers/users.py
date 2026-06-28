from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_role
from ..models import User
from ..response import ok
from ..schemas import UserCreate, UserUpdate
from .. import security

router = APIRouter(prefix="/api/users", tags=["users"])

VALID_ROLES = {"owner", "admin", "labeler", "reviewer", "agent"}


def _out(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "nickname": u.nickname,
        "email": u.email,
        "phone": u.phone,
        "role_code": u.role_code,
        "avatar_url": u.avatar_url,
        "status": u.status,
    }


@router.get("")
def list_users(db: Session = Depends(get_db), _user: User = Depends(require_role("owner", "admin"))):
    users = db.query(User).order_by(User.id).all()
    return ok([_out(u) for u in users])


@router.post("")
def create_user(body: UserCreate, db: Session = Depends(get_db), cur: User = Depends(require_role("owner", "admin"))):
    if body.role_code not in VALID_ROLES:
        raise HTTPException(status_code=400, detail={"code": 400, "message": "invalid role_code", "data": None})
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail={"code": 400, "message": "username exists", "data": None})
    u = User(
        username=body.username,
        password_hash=security.hash_password(body.password),
        nickname=body.nickname,
        email=body.email,
        phone=body.phone,
        role_code=body.role_code,
        status="active",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return ok(_out(u))


@router.put("/{user_id}")
def update_user(user_id: int, body: UserUpdate, db: Session = Depends(get_db), _user: User = Depends(require_role("owner", "admin"))):
    u = db.query(User).filter(User.id == user_id).first()
    if u is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "user not found", "data": None})
    if body.nickname is not None:
        u.nickname = body.nickname
    if body.email is not None:
        u.email = body.email
    if body.phone is not None:
        u.phone = body.phone
    if body.avatar_url is not None:
        u.avatar_url = body.avatar_url
    if body.status is not None:
        u.status = body.status
    if body.role_code is not None:
        if body.role_code not in VALID_ROLES:
            raise HTTPException(status_code=400, detail={"code": 400, "message": "invalid role_code", "data": None})
        u.role_code = body.role_code
    if body.password:
        u.password_hash = security.hash_password(body.password)
    db.commit()
    db.refresh(u)
    return ok(_out(u))


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), cur: User = Depends(require_role("owner", "admin"))):
    if cur.id == user_id:
        raise HTTPException(status_code=400, detail={"code": 400, "message": "cannot delete self", "data": None})
    u = db.query(User).filter(User.id == user_id).first()
    if u is None:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "user not found", "data": None})
    db.delete(u)
    db.commit()
    return ok({})


class BatchDeleteRequest(BaseModel):
    ids: list[int]


@router.post("/batch-delete")
def batch_delete_users(body: BatchDeleteRequest, db: Session = Depends(get_db), cur: User = Depends(require_role("owner", "admin"))):
    deleted = 0
    for user_id in body.ids:
        if cur.id == user_id:
            continue
        u = db.query(User).filter(User.id == user_id).first()
        if u is None:
            continue
        db.delete(u)
        deleted += 1
    db.commit()
    return ok({"deleted": deleted})