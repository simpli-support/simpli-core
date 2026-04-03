"""Shared FastAPI utilities for all Simpli services.

Provides common middleware, endpoint factories, and the ChatMessage model
so that services can avoid duplicating boilerplate.
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from simpli_core.logging import setup_logging
from simpli_core.models import AuthorType
from simpli_core.settings import SimpliSettings
from simpli_core.usage import CostTracker


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

    # Health + usage
    app.include_router(create_ops_router(cost_tracker))

    return app
