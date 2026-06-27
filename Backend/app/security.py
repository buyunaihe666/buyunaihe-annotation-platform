from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt, JWTError

from . import config


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: int, username: str, role_code: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=config.JWT_TTL_HOURS)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role_code": role_code,
        "exp": expire,
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALG)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALG])
    except JWTError:
        return None