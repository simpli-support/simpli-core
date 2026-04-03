"""Shared FastAPI utilities for all Simpli services.

Provides common middleware, endpoint factories, and the ChatMessage model
so that services can avoid duplicating boilerplate.
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from simpli_core.auth import add_api_key_middleware
from simpli_core.errors import SimpliError
from simpli_core.logging import setup_logging
from simpli_core.models import AuthorType
from simpli_core.settings import SimpliSettings
from simpli_core.usage import CostTracker

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Shared lightweight chat message (role + content only)
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    """A single chat-style message used as LLM input.

    Different from ``simpli_core.Message`` which represents a full
    conversation message with id, author_id, channel, timestamps, etc.
    """

    role: AuthorType
    content: str = Field(min_length=1)


# ---------------------------------------------------------------------------
# Request-ID middleware
# ---------------------------------------------------------------------------


def add_request_id_middleware(app: FastAPI) -> None:
    """Register middleware that attaches a unique request ID to every request."""

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        structlog.contextvars.unbind_contextvars("request_id")
        return response


# ---------------------------------------------------------------------------
# Ops endpoints (health + usage)
# ---------------------------------------------------------------------------


def create_ops_router(cost_tracker: CostTracker | None = None) -> APIRouter:
    """Return a router with ``/health`` and optionally ``/usage`` endpoints."""

    router = APIRouter(tags=["ops"])

    @router.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    if cost_tracker is not None:

        @router.get("/usage")
        async def usage() -> dict:  # type: ignore[no-untyped-def]
            return cost_tracker.summary()

    return router


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app(
    *,
    title: str,
    version: str,
    description: str,
    settings: SimpliSettings,
    cors_origins: str | list[str] = "*",
    cost_tracker: CostTracker | None = None,
) -> FastAPI:
    """Create a fully-configured FastAPI app with standard middleware and ops endpoints.

    Parameters
    ----------
    title:
        OpenAPI title.
    version:
        App version string.
    description:
        OpenAPI description.
    settings:
        Service settings (used for logging config).
    cors_origins:
        Comma-separated string or list of allowed origins.
    cost_tracker:
        Optional CostTracker instance; if provided, ``/usage`` is registered.
    """
    setup_logging(log_level=settings.app_log_level.upper())

    app = FastAPI(title=title, version=version, description=description)

    # CORS
    if isinstance(cors_origins, str):
        origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
    else:
        origins = cors_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID middleware
    add_request_id_middleware(app)

    # API key auth (disabled when api_key is empty)
    api_key = getattr(settings, "api_key", "")
    if api_key:
        add_api_key_middleware(app, api_key)

    # Centralized error handlers
    _register_error_handlers(app)

    # Health + usage
    app.include_router(create_ops_router(cost_tracker))

    return app


def _register_error_handlers(app: FastAPI) -> None:
    """Register shared exception handlers on the app."""

    @app.exception_handler(SimpliError)
    async def simpli_error_handler(
        request: Request, exc: SimpliError
    ) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": exc.error_code,
                "detail": exc.detail,
                "request_id": request_id,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID")
        logger.warning("validation_error", errors=exc.errors())
        return JSONResponse(
            status_code=422,
            content={
                "error_code": "VALIDATION_ERROR",
                "detail": "Request validation failed",
                "request_id": request_id,
                "errors": [
                    {
                        "field": " -> ".join(str(loc) for loc in err["loc"]),
                        "message": err["msg"],
                    }
                    for err in exc.errors()
                ],
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID")
        logger.exception("unhandled_error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "INTERNAL_ERROR",
                "detail": "An internal error occurred",
                "request_id": request_id,
            },
        )
