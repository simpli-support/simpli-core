"""Centralized error model for all Simpli services.

Provides a consistent exception hierarchy and error response format.
Exception handlers are registered automatically by ``create_app()``.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SimpliError(Exception):
    """Base exception for all Simpli service errors.

    Subclass this to create domain-specific errors that automatically
    produce the correct HTTP status code and error response format.
    """

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, detail: str = "An internal error occurred") -> None:
        self.detail = detail
        super().__init__(detail)


class ValidationError(SimpliError):
    """Input validation failed (422)."""

    status_code = 422
    error_code = "VALIDATION_ERROR"


class NotFoundError(SimpliError):
    """Requested resource not found (404)."""

    status_code = 404
    error_code = "NOT_FOUND"


class AuthenticationError(SimpliError):
    """Authentication failed (401)."""

    status_code = 401
    error_code = "AUTHENTICATION_ERROR"


class ForbiddenError(SimpliError):
    """Authorization failed (403)."""

    status_code = 403
    error_code = "FORBIDDEN"


class RateLimitedError(SimpliError):
    """Rate limit exceeded (429)."""

    status_code = 429
    error_code = "RATE_LIMITED"


class ExternalServiceError(SimpliError):
    """Upstream/external service error (502)."""

    status_code = 502
    error_code = "EXTERNAL_SERVICE_ERROR"


class ErrorResponse(BaseModel):
    """Consistent error response format across all services."""

    error_code: str = Field(description="Machine-readable error code")
    detail: str = Field(description="Human-readable error message")
    request_id: str | None = Field(
        default=None, description="Request ID for tracing"
    )
