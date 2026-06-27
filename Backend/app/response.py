from __future__ import annotations

from typing import Any, Optional

from fastapi.responses import JSONResponse


def ok(data: Any = None, message: str = "ok") -> dict:
    return {"code": 0, "message": message, "data": data}


def err(code: int, message: str, data: Optional[Any] = None, status: int = 400) -> dict:
    return {"code": code, "message": message, "data": data, "_status": status}


def error_response(code: int, message: str, status: int = 400, data: Optional[Any] = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"code": code, "message": message, "data": data},
    )