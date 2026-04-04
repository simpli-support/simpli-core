"""Webhook router factory for receiving platform events.

Creates a FastAPI router with ``POST /api/v1/webhook/{platform}``
that verifies signatures and dispatches to service handlers.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from simpli_core.connectors.mapping import (
    DEFAULT_TICKET_MAPPINGS,
    apply_mappings,
)
from simpli_core.webhooks.signatures import SIGNATURE_HEADERS, verify_signature

logger = logging.getLogger(__name__)

WebhookHandler = Callable[[str, list[dict[str, Any]]], Awaitable[Any]]


def create_webhook_router(
    *,
    on_event: WebhookHandler,
    secrets: dict[str, str] | None = None,
    require_signature: bool = True,
) -> APIRouter:
    """Create a router that receives webhooks from external platforms.

    Args:
        on_event: Async function called with ``(event_type, records)``
            where records are mapped to Simpli domain fields.
        secrets: Dict mapping platform name to webhook signing secret.
            Can also be populated from settings at runtime.
        require_signature: If True, reject webhooks without valid signatures.
            Set to False for development/testing.

    Returns:
        APIRouter with ``POST /api/v1/webhook/{platform}`` endpoint.
    """
    router = APIRouter(prefix="/api/v1", tags=["webhooks"])
    _secrets = secrets or {}

    @router.post("/webhook/{platform}")
    async def receive_webhook(platform: str, request: Request) -> dict[str, Any]:
        """Receive a webhook from an external platform."""
        body = await request.body()

        # Verify signature if secret is configured
        secret = _secrets.get(platform, "")
        if secret and require_signature:
            header_name = SIGNATURE_HEADERS.get(platform, "")
            signature = request.headers.get(header_name, "")
            if not signature or not verify_signature(platform, body, signature, secret):
                logger.warning(
                    "webhook_signature_invalid",
                    extra={"platform": platform},
                )
                return JSONResponse(  # type: ignore[return-value]
                    status_code=401,
                    content={"detail": "Invalid webhook signature"},
                )
        elif require_signature and not secret:
            logger.debug(
                "webhook_no_secret_configured",
                extra={"platform": platform},
            )

        # Parse payload
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(  # type: ignore[return-value]
                status_code=400,
                content={"detail": "Invalid JSON payload"},
            )

        # Normalize to list of records
        records = _normalize_payload(platform, payload)

        # Apply default field mappings
        default_mappings = DEFAULT_TICKET_MAPPINGS.get(platform)
        if default_mappings:
            mapped = apply_mappings(records, default_mappings)
        else:
            mapped = records

        # Detect event type from payload
        event_type = _detect_event_type(platform, payload)

        logger.info(
            "webhook_received",
            extra={
                "platform": platform,
                "event_type": event_type,
                "record_count": len(mapped),
            },
        )

        # Dispatch to handler
        try:
            await on_event(event_type, mapped)
        except Exception:
            logger.exception("webhook_handler_error")
            return JSONResponse(  # type: ignore[return-value]
                status_code=500,
                content={"detail": "Webhook processing failed"},
            )

        return {"status": "ok", "event_type": event_type, "records": len(mapped)}

    return router


def _normalize_payload(
    platform: str,
    payload: dict[str, Any] | list[Any],
) -> list[dict[str, Any]]:
    """Normalize a webhook payload into a list of records."""
    if isinstance(payload, list):
        return payload

    # Platform-specific extraction
    if platform == "zendesk":
        # Zendesk sends ticket data in various formats
        if "ticket" in payload:
            return [payload["ticket"]]
        return [payload]

    if platform == "freshdesk":
        if "freshdesk_webhook" in payload:
            data = payload["freshdesk_webhook"]
            if "ticket_data" in data:
                return [data["ticket_data"]]
            return [data]
        return [payload]

    if platform == "intercom":
        if "data" in payload and "item" in payload["data"]:
            return [payload["data"]["item"]]
        return [payload]

    if platform == "hubspot":
        if "object" in payload:
            return [payload["object"]]
        return [payload]

    if platform == "jira":
        if "issue" in payload:
            return [payload["issue"]]
        return [payload]

    if platform == "servicenow":
        if "result" in payload:
            result = payload["result"]
            return result if isinstance(result, list) else [result]
        return [payload]

    if platform == "salesforce":
        if "sobjects" in payload:
            sobjects: list[dict[str, Any]] = payload["sobjects"]
            return sobjects
        return [payload]

    return [payload]


def _detect_event_type(platform: str, payload: dict[str, Any]) -> str:
    """Detect the event type from a webhook payload."""
    # Common patterns across platforms
    event_fields = [
        "event",
        "event_type",
        "type",
        "action",
        "webhookEvent",
        "topic",
    ]
    for field in event_fields:
        val = payload.get(field)
        if isinstance(val, str):
            return val

    # Platform-specific
    if platform == "intercom":
        topic = payload.get("topic")
        if isinstance(topic, str):
            return topic
    if platform == "jira":
        webhook_event = payload.get("webhookEvent")
        if isinstance(webhook_event, str):
            return webhook_event

    return "unknown"
