from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from . import security
from .database import get_db
from .models import User
from .response import error_response


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth = request.headers.get("Authorization") or ""
    if not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 401, "message": "missing or invalid Authorization header", "data": None},
        )
    token = auth.split(" ", 1)[1]
    payload = security.decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 401, "message": "invalid or expired token", "data": None},
        )
    user_id = int(payload.get("sub", 0))
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 401, "message": "user not found or inactive", "data": None},
        )
    return user


def require_role(*roles: str):
    def _dep(user: User = Depends(get_current_user)) -> User:
        if roles and user.role_code not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": 403, "message": f"role '{user.role_code}' not allowed", "data": None},
            )
        return user

    return _dep


def optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    auth = request.headers.get("Authorization") or ""
    if not auth.startswith("Bearer "):
        return None
    token = auth.split(" ", 1)[1]
    payload = security.decode_access_token(token)
    if payload is None:
        return None
    user_id = int(payload.get("sub", 0))
    return db.query(User).filter(User.id == user_id).first()