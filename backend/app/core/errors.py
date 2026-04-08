"""
Standard error response contract for the Umay API.

All errors follow the same shape:
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable message",
    "detail": [...],   # optional
    "request_id": "..."
  }
}
"""
import uuid
import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("umay.errors")


def _error_body(code: str, message: str, detail=None, request_id: str = "") -> dict:
    body: dict = {"error": {"code": code, "message": message, "request_id": request_id}}
    if detail is not None:
        body["error"]["detail"] = detail
    return body


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    request_id = str(request.state.request_id) if hasattr(request.state, "request_id") else str(uuid.uuid4())
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        413: "PAYLOAD_TOO_LARGE",
        415: "UNSUPPORTED_MEDIA_TYPE",
        422: "UNPROCESSABLE_ENTITY",
        429: "RATE_LIMITED",
        500: "INTERNAL_SERVER_ERROR",
        501: "NOT_IMPLEMENTED",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT",
    }
    code = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
    logger.warning("HTTP %s %s — %s", exc.status_code, request.url.path, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(code, str(exc.detail), request_id=request_id),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = str(request.state.request_id) if hasattr(request.state, "request_id") else str(uuid.uuid4())
    errors = [
        {"field": ".".join(str(loc) for loc in e["loc"]), "msg": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_body("VALIDATION_ERROR", "Request validation failed.", detail=errors, request_id=request_id),
    )


async def generic_exception_handler(request: Request, exc: Exception):
    request_id = str(request.state.request_id) if hasattr(request.state, "request_id") else str(uuid.uuid4())
    logger.exception("Unhandled exception on %s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body("INTERNAL_SERVER_ERROR", "An unexpected error occurred.", request_id=request_id),
    )
