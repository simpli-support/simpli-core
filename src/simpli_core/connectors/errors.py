"""Connector-specific exception hierarchy."""

from __future__ import annotations


class ConnectorError(Exception):
    """Base exception for all connector errors."""

    def __init__(self, message: str, platform: str = "unknown") -> None:
        self.platform = platform
        super().__init__(f"[{platform}] {message}")


class AuthenticationError(ConnectorError):
    """Raised when authentication fails (401/403)."""


class RateLimitError(ConnectorError):
    """Raised when rate limit is exceeded (429) and retries are exhausted."""

    def __init__(
        self,
        message: str,
        platform: str = "unknown",
        retry_after: int | None = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(message, platform)


class PlatformAPIError(ConnectorError):
    """Raised for non-2xx responses from a platform API."""

    def __init__(
        self,
        message: str,
        platform: str = "unknown",
        status_code: int = 0,
        response_body: str = "",
    ) -> None:
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message, platform)


class ConfigurationError(ConnectorError):
    """Raised when required credentials or configuration are missing."""
