"""Lightweight async HTTP client for inter-service communication."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class ServiceRegistry:
    """Reads service URLs from a settings object or env-derived defaults.

    Each service URL is expected as ``simpli_{name}_url`` on the settings,
    falling back to ``http://localhost:{port}``.
    """

    _urls: dict[str, str] = field(default_factory=dict)

    # Default ports per service (matches Dockerfile EXPOSE values)
    DEFAULT_PORTS: dict[str, int] = field(
        default_factory=lambda: {
            "triage": 8001,
            "reply": 8005,
            "qa": 8006,
            "sentiment": 8007,
            "pulse": 8008,
            "kb": 8009,
            "assist": 8010,
            "summary": 8011,
            "translate": 8012,
            "redact": 8013,
            "tag": 8014,
            "insights": 8015,
            "assess": 8016,
            "simulate": 8017,
            "benchmark": 8018,
            "catalog": 8019,
            "macro": 8020,
            "kbaudit": 8021,
            "pipeline": 8030,
        },
        init=False,
    )

    @classmethod
    def from_settings(cls, settings: Any) -> ServiceRegistry:
        """Build registry from a settings object's ``simpli_*_url`` fields."""
        registry = cls()
        for name, port in registry.DEFAULT_PORTS.items():
            attr = f"simpli_{name}_url"
            url = getattr(settings, attr, "") or ""
            registry._urls[name] = url or f"http://localhost:{port}"
        return registry

    def url_for(self, service: str) -> str:
        """Get the base URL for a service."""
        if service in self._urls:
            return self._urls[service]
        port = self.DEFAULT_PORTS.get(service, 8000)
        return f"http://localhost:{port}"


@dataclass
class StepResult:
    """Result of a single pipeline step."""

    service: str
    endpoint: str
    status: str  # "success" | "error" | "skipped"
    duration_ms: int
    result: dict[str, Any] | None = None
    error: str | None = None


class ServiceClient:
    """Async HTTP client for calling Simpli services."""

    def __init__(
        self,
        registry: ServiceRegistry,
        timeout: float = 30.0,
        retries: int = 2,
    ) -> None:
        self.registry = registry
        self.timeout = timeout
        self.retries = retries
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(max_connections=50, max_keepalive_connections=10),
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def call(
        self,
        service: str,
        endpoint: str,
        payload: dict[str, Any],
        *,
        request_id: str | None = None,
        pipeline_id: str | None = None,
    ) -> StepResult:
        """Call a service endpoint with retry and timing."""
        url = f"{self.registry.url_for(service)}{endpoint}"
        headers: dict[str, str] = {}
        if request_id:
            headers["X-Request-ID"] = request_id
        if pipeline_id:
            headers["X-Pipeline-ID"] = pipeline_id

        client = await self._get_client()
        last_error: str | None = None

        for attempt in range(self.retries + 1):
            start = time.monotonic()
            try:
                resp = await client.post(url, json=payload, headers=headers)
                duration_ms = int((time.monotonic() - start) * 1000)

                if resp.status_code < 400:
                    return StepResult(
                        service=service,
                        endpoint=endpoint,
                        status="success",
                        duration_ms=duration_ms,
                        result=resp.json(),
                    )
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
            except httpx.HTTPError as exc:
                duration_ms = int((time.monotonic() - start) * 1000)
                last_error = f"{type(exc).__name__}: {exc}"

            # Don't retry on last attempt
            if attempt < self.retries:
                continue

        return StepResult(
            service=service,
            endpoint=endpoint,
            status="error",
            duration_ms=duration_ms,
            error=last_error,
        )

    # ── Convenience methods for common service calls ──

    async def triage(self, subject: str, body: str, **kwargs: Any) -> StepResult:
        """Classify a ticket via simpli-triage."""
        return await self.call(
            "triage",
            "/api/v1/classify",
            {"subject": subject, "body": body, **kwargs},
        )

    async def redact(self, text: str, **kwargs: Any) -> StepResult:
        """Redact PII via simpli-redact."""
        return await self.call("redact", "/api/v1/redact", {"text": text, **kwargs})

    async def search_kb(self, query: str, top_k: int = 5) -> StepResult:
        """Search knowledge base via simpli-kb."""
        return await self.call("kb", "/api/v1/search", {"query": query, "top_k": top_k})

    async def draft_reply(
        self,
        messages: list[dict[str, Any]],
        context: str = "",
        **kwargs: Any,
    ) -> StepResult:
        """Generate a draft reply via simpli-reply."""
        return await self.call(
            "reply",
            "/api/v1/draft",
            {"messages": messages, "context": context, **kwargs},
        )

    async def evaluate(
        self, messages: list[dict[str, Any]], **kwargs: Any
    ) -> StepResult:
        """Score a conversation via simpli-qa."""
        return await self.call(
            "qa", "/api/v1/evaluate", {"messages": messages, **kwargs}
        )

    async def summarize(
        self, messages: list[dict[str, Any]], **kwargs: Any
    ) -> StepResult:
        """Summarize a conversation via simpli-summary."""
        return await self.call(
            "summary",
            "/api/v1/summarize",
            {"messages": messages, **kwargs},
        )
