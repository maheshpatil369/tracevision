"""Consistent API error format (spec section 71) and shared exception types."""
from __future__ import annotations

from fastapi import HTTPException
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base application error. Every service-layer error raises one of these
    (or a subclass) so the API layer can map it to a consistent JSON shape
    without ever leaking a raw stack trace to the client."""

    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)

    def to_http_exception(self) -> HTTPException:
        return HTTPException(status_code=self.status_code, detail={"code": self.code, "message": self.message})


class NotFoundError(AppError):
    def __init__(self, resource: str, resource_id: str):
        super().__init__("NOT_FOUND", f"{resource} '{resource_id}' was not found.", status_code=404)


class ValidationAppError(AppError):
    def __init__(self, code: str, message: str):
        super().__init__(code, message, status_code=422)


def error_response(code: str, message: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={
        "success": False, "error": {"code": code, "message": message},
    })


def success_response(data, status_code: int = 200) -> dict:
    return {"success": True, "data": data}
