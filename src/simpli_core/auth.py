"""API key authentication middleware for Simpli services.

When ``api_key`` is set in service settings, all requests (except excluded
paths like ``/health``) must include a valid ``X-API-Key`` header.
Disabled when ``api_key`` is empty (default for development).
"""

from __future__ import annotations

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)

DEFAULT_EXCLUDE_PATHS = frozenset(
    {
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
)


def add_api_key_middleware(
    app: FastAPI,
    api_key: str,
    *,
    exclude_paths: frozenset[str] = DEFAULT_EXCLUDE_PATHS,
) -> None:
    """Add API key validation middleware to a FastAPI app.

    Does nothing if ``api_key`` is empty (dev mode).

    Validated via the ``X-API-Key`` header.
    """
    if not api_key:
        return

    @app.middleware("http")
    async def api_key_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        # Skip excluded paths
        if request.url.path in exclude_paths:
            return await call_next(request)

        # Validate
        provided = request.headers.get("X-API-Key", "")
        if provided != api_key:
            logger.warning(
                "api_key_rejected",
                path=request.url.path,
                provided_key_prefix=provided[:4] + "..." if provided else "(none)",
            )
            return JSONResponse(
                status_code=401,
                content={
                    "error_code": "AUTHENTICATION_ERROR",
                    "detail": "Invalid or missing API key",
                },
            )
        return await call_next(request)
