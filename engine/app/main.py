import logging
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.observability import RequestIDMiddleware, configure_logging, current_request_id
from app.routers import (
    admin,
    ai,
    alerts,
    cases,
    ctr,
    diagrams,
    disseminations,
    intelligence,
    investigate,
    match_definitions,
    network,
    overview,
    reports,
    saved_queries,
    scan,
    str_reports,
    system,
)

settings = get_settings()
configure_logging()
logger = logging.getLogger("kestrel.error")

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Kestrel intelligence engine",
)


def _error_envelope(status_code: int, detail: object) -> JSONResponse:
    body = {
        "detail": detail,
        "request_id": current_request_id() or None,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    return JSONResponse(body, status_code=status_code)


@app.exception_handler(HTTPException)
async def handle_http_exception(_: Request, exc: HTTPException) -> JSONResponse:
    return _error_envelope(exc.status_code, exc.detail)


@app.exception_handler(StarletteHTTPException)
async def handle_starlette_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    # Catches 404 from unknown paths and a handful of other Starlette-raised errors.
    return _error_envelope(exc.status_code, exc.detail)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    return _error_envelope(422, exc.errors())


@app.exception_handler(Exception)
async def handle_unhandled(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", extra={"exc_type": type(exc).__name__})
    return _error_envelope(500, "Internal server error.")

# Request ID middleware runs first so every log line + response carries the ID.
app.add_middleware(RequestIDMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router, tags=["system"])
app.include_router(ai.router, prefix="/ai", tags=["ai"])
app.include_router(overview.router, prefix="/overview", tags=["overview"])
app.include_router(investigate.router, prefix="/investigate", tags=["investigate"])
app.include_router(network.router, prefix="/network", tags=["network"])
app.include_router(scan.router, prefix="/scan", tags=["scan"])
app.include_router(str_reports.router, prefix="/str-reports", tags=["str-reports"])
app.include_router(ctr.router, prefix="/ctr", tags=["ctr"])
app.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
app.include_router(cases.router, prefix="/cases", tags=["cases"])
app.include_router(disseminations.router, prefix="/disseminations", tags=["disseminations"])
app.include_router(intelligence.router, prefix="/intelligence", tags=["intelligence"])
app.include_router(saved_queries.router, prefix="/saved-queries", tags=["saved-queries"])
app.include_router(diagrams.router, prefix="/diagrams", tags=["diagrams"])
app.include_router(match_definitions.router, prefix="/match-definitions", tags=["match-definitions"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
