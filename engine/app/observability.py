"""Request ID correlation + structured JSON logging.

- `request_id_ctx`: a ContextVar that carries the current request's UUID so
  downstream services can include it in log lines without threading it
  through every function.
- `RequestIDMiddleware`: generates a UUID per request (or accepts an
  inbound X-Request-ID header), stores it in the context var, and echoes
  it back as the response's X-Request-ID header.
- `StructuredFormatter`: a stdlib logging formatter that emits each record
  as a single-line JSON object with timestamp, level, logger, message,
  request_id, and any extra fields the caller added via `extra={...}`.
- `configure_logging`: call once at app startup to install the formatter.
"""

from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def current_request_id() -> str:
    """Return the current request's ID, or '' outside a request context."""
    return request_id_ctx.get()


class StructuredFormatter(logging.Formatter):
    """Emit each log record as a single-line JSON document.

    Standard fields: ts (ISO8601), level, logger, msg, request_id. Any keys
    the caller added via ``logger.info("...", extra={"key": value})`` are
    merged in at the top level (as long as they don't collide with the
    standards above). Exception info is included as ``exc``.
    """

    _RESERVED = {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "message", "asctime", "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003 — stdlib name
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": current_request_id(),
        }
        # Caller-supplied extras
        for key, value in record.__dict__.items():
            if key in self._RESERVED or key == "request_id":
                continue
            try:
                json.dumps(value)  # skip anything non-serializable
            except (TypeError, ValueError):
                value = repr(value)
            payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    """Install the structured formatter on the root logger.

    Safe to call multiple times — existing handlers are replaced so tests
    and dev reloaders don't stack handlers.
    """
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(StructuredFormatter())
    root.addHandler(handler)
    root.setLevel(level)
    # Quiet a couple of noisy third-party loggers at INFO
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Generate or propagate X-Request-ID; log each request as JSON."""

    logger = logging.getLogger("kestrel.access")

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        inbound = request.headers.get("x-request-id", "").strip()
        request_id = inbound or uuid.uuid4().hex
        token = request_id_ctx.set(request_id)
        start = time.perf_counter()
        status_code = 500
        try:
            response: Response = await call_next(request)
            status_code = response.status_code
        except Exception:
            # Log and re-raise so FastAPI's exception handlers still run
            duration_ms = (time.perf_counter() - start) * 1000
            self.logger.exception(
                "request.unhandled",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                },
            )
            request_id_ctx.reset(token)
            raise
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["x-request-id"] = request_id
        # Only log non-health traffic to keep Render logs readable
        if request.url.path not in {"/health", "/ready"}:
            self.logger.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": status_code,
                    "duration_ms": round(duration_ms, 2),
                },
            )
        request_id_ctx.reset(token)
        return response
