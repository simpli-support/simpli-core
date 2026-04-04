"""Base connector class for all platform integrations."""

from __future__ import annotations

import base64
import contextlib
import logging
from typing import Any

import httpx

from simpli_core.connectors.errors import (
    AuthenticationError,
    PlatformAPIError,
    RateLimitError,
)
from simpli_core.connectors.mapping import ObjectSchema

logger = logging.getLogger(__name__)


class BaseConnector:
    """Base class providing HTTP client, error handling, and pagination.

    Subclasses must set ``platform`` and implement the ``get_*`` methods
    relevant to their platform.
    """

    platform: str = "unknown"

    def __init__(
        self,
        base_url: str,
        *,
        auth_headers: dict[str, str] | None = None,
        basic_auth: tuple[str, str] | None = None,
        timeout: int = 30,
    ) -> None:
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if auth_headers:
            headers.update(auth_headers)
        if basic_auth:
            creds = base64.b64encode(
                f"{basic_auth[0]}:{basic_auth[1]}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {creds}"

        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
        )
        logger.info("Connector initialized: %s → %s", self.platform, base_url)

    # -- HTTP helpers --

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an HTTP request with error handling."""
        resp = self._client.request(method, path, params=params, json=json)
        self._handle_errors(resp)
        return resp.json()  # type: ignore[no-any-return]

    def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request("GET", path, params=params)

    def _post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request("POST", path, json=json)

    def _put(
        self,
        path: str,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request("PUT", path, json=json)

    def _patch(
        self,
        path: str,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request("PATCH", path, json=json)

    def _handle_errors(self, resp: httpx.Response) -> None:
        """Raise appropriate ConnectorError for non-2xx responses."""
        if resp.is_success:
            return

        body = resp.text
        if resp.status_code in (401, 403):
            raise AuthenticationError(
                f"Authentication failed: {resp.status_code} {body}",
                platform=self.platform,
            )
        if resp.status_code == 429:
            retry_after = None
            if ra := resp.headers.get("Retry-After"):
                with contextlib.suppress(ValueError):
                    retry_after = int(ra)
            raise RateLimitError(
                f"Rate limited: {body}",
                platform=self.platform,
                retry_after=retry_after,
            )
        raise PlatformAPIError(
            f"API error {resp.status_code}: {body}",
            platform=self.platform,
            status_code=resp.status_code,
            response_body=body,
        )

    def _paginate(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        records_key: str = "results",
        next_key: str = "next",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Generic cursor/link-based pagination.

        Keeps fetching until there's no ``next_key`` in the response
        or ``limit`` records are collected.
        """
        params = dict(params or {})
        all_records: list[dict[str, Any]] = []

        while True:
            data = self._get(path, params=params)
            records = data.get(records_key, [])
            all_records.extend(records)

            if len(all_records) >= limit:
                all_records = all_records[:limit]
                break

            next_cursor = data.get(next_key)
            if not next_cursor:
                # Try links/meta patterns
                links = data.get("links", {})
                meta = data.get("meta", {})
                next_cursor = (
                    links.get("next")
                    or meta.get("after_cursor")
                    or meta.get("next_cursor")
                )

            if not next_cursor:
                break

            # Handle both full URL and cursor value
            if isinstance(next_cursor, str) and next_cursor.startswith("http"):
                # Full URL — extract path
                from urllib.parse import urlparse

                parsed = urlparse(next_cursor)
                path = parsed.path
                if parsed.query:
                    from urllib.parse import parse_qs

                    params.update({k: v[0] for k, v in parse_qs(parsed.query).items()})
            else:
                params["page[after]"] = str(next_cursor)

        return all_records

    # -- Abstract interface (subclasses implement as needed) --

    def get_tickets(
        self,
        where: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch ticket/case/issue records."""
        msg = f"{self.platform} connector does not support get_tickets()"
        raise NotImplementedError(msg)

    def get_customers(
        self,
        where: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch customer/contact records."""
        msg = f"{self.platform} connector does not support get_customers()"
        raise NotImplementedError(msg)

    def get_messages(
        self,
        ticket_id: str,
    ) -> list[dict[str, Any]]:
        """Fetch messages/comments for a specific ticket."""
        msg = f"{self.platform} connector does not support get_messages()"
        raise NotImplementedError(msg)

    def get_articles(
        self,
        where: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch knowledge base articles."""
        msg = f"{self.platform} connector does not support get_articles()"
        raise NotImplementedError(msg)

    def describe_fields(
        self,
        object_type: str = "ticket",
    ) -> ObjectSchema:
        """Discover available fields for a platform object type.

        Returns an :class:`~simpli_core.connectors.mapping.ObjectSchema`.
        Subclasses should import and return the Pydantic model directly;
        the base implementation raises ``NotImplementedError``.
        """
        msg = f"{self.platform} connector does not support describe_fields()"
        raise NotImplementedError(msg)

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> BaseConnector:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
