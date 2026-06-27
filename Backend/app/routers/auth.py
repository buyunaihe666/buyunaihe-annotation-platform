from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..response import ok
from ..schemas import LoginRequest, UserCreate, UserOut
from .. import security

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_out(u: User) -> dict:
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


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if user is None or not security.verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 401, "message": "invalid username or password", "data": None},
        )
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 403, "message": "user inactive", "data": None},
        )
    token = security.create_access_token(user.id, user.username, user.role_code)
    return ok({"token": token, "user": _user_out(user)})


@router.post("/logout")
def logout(user: User = Depends(get_current_user)):
    return ok({})


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return ok(_user_out(user))