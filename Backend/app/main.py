from __future__ import annotations

import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import config, minio_client, rabbitmq
from .database import Base, SessionLocal, engine
from .models import User
from .security import hash_password
from .routers import (
    annotation,
    auth,
    datasets,
    export,
    review,
    stats,
    tasks,
    templates,
    upload,
    users,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("buyunaihe")


def _seed_defaults():
    db = SessionLocal()
    try:
        admin_pw = config.APP_ADMIN_PASSWORD or secrets.token_urlsafe(12)
        defaults = [
            ("admin", "管理员", "owner", admin_pw),
            ("labeler1", "标注员甲", "labeler", config.APP_ADMIN_PASSWORD or "labeler123"),
            ("reviewer1", "审核员甲", "reviewer", config.APP_ADMIN_PASSWORD or "reviewer123"),
        ]
        for username, nickname, role, password in defaults:
            u = db.query(User).filter(User.username == username).first()
            if u is None:
                db.add(User(
                    username=username,
                    password_hash=hash_password(password),
                    nickname=nickname,
                    role_code=role,
                    status="active",
                ))
            elif not u.password_hash or u.password_hash == "":
                u.password_hash = hash_password(password)
        db.commit()
        if not config.APP_ADMIN_PASSWORD:
            logger.warning(
                "APP_ADMIN_PASSWORD not set. Generated initial passwords — "
                "login and change them immediately: admin=%s labeler1=labeler123 reviewer1=reviewer123",
                admin_pw,
            )
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Buyunaihe backend starting up")
    if not config.JWT_SECRET:
        logger.error("JWT_SECRET is not set. Configure it in deploy/docker.env and restart.")
        raise RuntimeError("JWT_SECRET is required")
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        logger.warning(f"[db] create_all failed: {e}")
    try:
        minio_client.ensure_buckets()
    except Exception as e:
        logger.warning(f"[minio] ensure_buckets failed: {e}")
    try:
        _seed_defaults()
    except Exception as e:
        logger.warning(f"[seed] failed: {e}")
    if not rabbitmq.verify_connection():
        logger.warning("[rabbitmq] connection not available at startup; publishing will retry")
    yield
    logger.info("Buyunaihe backend shutting down")


app = FastAPI(title="Buyunaihe Backend", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exc_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        code = detail.get("code", exc.status_code)
        message = detail.get("message", "error")
        data = detail.get("data")
    else:
        code = exc.status_code
        message = str(detail)
        data = None
    return JSONResponse(status_code=exc.status_code, content={"code": code, "message": message, "data": data})


@app.exception_handler(RequestValidationError)
async def validation_exc_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"code": 422, "message": "validation error", "data": exc.errors()},
    )


@app.exception_handler(Exception)
async def unhandled_exc_handler(request: Request, exc: Exception):
    logger.exception("unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": f"internal error: {exc}", "data": None},
    )


@app.get("/health")
def health():
    return {"code": 0, "message": "ok", "data": {"status": "ok"}}


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(templates.router)
app.include_router(datasets.router)
app.include_router(tasks.router)
app.include_router(annotation.router)
app.include_router(review.router)
app.include_router(export.router)
app.include_router(stats.router)
app.include_router(upload.router)
