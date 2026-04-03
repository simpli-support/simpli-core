"""Shared ingest router factory for all services.

Provides file upload and multi-platform data pull endpoints via a
single ``create_ingest_router()`` call. Eliminates ~50 lines of
duplicated ingest boilerplate per service.
"""

from __future__ import annotations

import json as json_module
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from simpli_core.connectors.file_parser import FileConnector
from simpli_core.connectors.mapping import (
    DEFAULT_ARTICLE_MAPPINGS,
    DEFAULT_TICKET_MAPPINGS,
    FieldMapping,
    apply_mappings,
)
from simpli_core.connectors.registry import get_connector, list_platforms

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# File upload security constants
# ---------------------------------------------------------------------------

MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".csv", ".json", ".jsonl"})


def _validate_upload(filename: str | None, size: int) -> str | None:
    """Validate an uploaded file. Returns error message or None if valid."""
    if size > MAX_UPLOAD_SIZE:
        return (
            f"File too large: {size:,} bytes "
            f"(max {MAX_UPLOAD_SIZE // (1024 * 1024)} MB)"
        )
    if filename:
        ext = Path(filename).suffix.lower()
        if ext and ext not in ALLOWED_EXTENSIONS:
            allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
            return f"Unsupported file type: {ext}. Allowed: {allowed}"
    return None


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class PlatformIngestRequest(BaseModel):
    """Request to ingest data from any supported platform."""

    credentials: dict[str, str] = Field(
        default_factory=dict,
        description="Platform-specific credentials (falls back to server settings)",
    )
    query_filter: str = Field(
        default="",
        description="Platform-specific query filter (SOQL WHERE, JQL, etc.)",
    )
    limit: int = Field(
        default=100, ge=1, le=10000, description="Max records to fetch"
    )
    mappings: list[FieldMapping] | None = Field(
        default=None,
        description="Custom field mappings (uses platform defaults if not provided)",
    )


class IngestResult(BaseModel):
    """Result of an ingest operation."""

    source: str = Field(description="Data source (filename or platform name)")
    total: int = Field(description="Total records received")
    processed: int = Field(description="Records successfully processed")
    results: list[dict[str, Any]] = Field(description="Processing results")
    errors: list[dict[str, Any]] = Field(
        default_factory=list, description="Records that failed processing"
    )


# ---------------------------------------------------------------------------
# Router factory
# ---------------------------------------------------------------------------


def create_ingest_router(
    process_fn: Callable[[list[dict[str, Any]]], Awaitable[list[dict[str, Any]]]],
    *,
    default_object: str = "tickets",
    settings: Any = None,
) -> APIRouter:
    """Create a FastAPI router with file upload and platform ingest endpoints.

    Args:
        process_fn: Async function that takes a list of mapped records and
            returns a list of result dicts. Each service implements this
            to feed records into its core processing logic.
        default_object: What to fetch from platforms — ``"tickets"`` calls
            ``get_tickets()``, ``"articles"`` calls ``get_articles()``.
        settings: Service settings object. Used to look up platform
            credentials as fallback when not provided in the request.

    Returns:
        APIRouter with ``POST /api/v1/ingest`` and
        ``POST /api/v1/ingest/{platform}`` endpoints.
    """
    router = APIRouter(prefix="/api/v1", tags=["ingest"])

    @router.post("/ingest", response_model=IngestResult)
    async def ingest_file(
        file: UploadFile = File(
            ..., description="File to ingest (CSV, JSON, JSONL)"
        ),
        mappings: str | None = Form(
            default=None, description="JSON array of field mappings"
        ),
    ) -> IngestResult:
        """Ingest records from a file upload."""
        # Read file content for size validation
        content = await file.read()
        await file.seek(0)  # Reset for parsing

        validation_error = _validate_upload(file.filename, len(content))
        if validation_error:
            status = 413 if "too large" in validation_error else 415
            return JSONResponse(  # type: ignore[return-value]
                status_code=status,
                content={"detail": validation_error},
            )

        logger.info(
            "ingest_file",
            extra={"filename": file.filename, "size": len(content)},
        )

        records = FileConnector.parse(
            file.file, format=_detect_format(file.filename)
        )

        field_mappings: list[FieldMapping] | None = None
        if mappings:
            field_mappings = [
                FieldMapping(**m) for m in json_module.loads(mappings)
            ]

        if field_mappings:
            mapped = apply_mappings(records, field_mappings)
        else:
            mapped = records

        return await _run_processing(
            source=file.filename or "upload",
            records=records,
            mapped=mapped,
            process_fn=process_fn,
        )

    @router.post("/ingest/{platform}", response_model=IngestResult)
    async def ingest_platform(
        platform: str,
        request: PlatformIngestRequest,
    ) -> IngestResult:
        """Pull data from a platform and process it."""
        try:
            connector_cls = get_connector(platform)
        except KeyError:
            available = ", ".join(list_platforms())
            return JSONResponse(  # type: ignore[return-value]
                status_code=400,
                content={
                    "detail": f"Unknown platform: {platform!r}. Available: {available}"
                },
            )

        # Resolve credentials: request > server settings
        creds = dict(request.credentials)
        if settings:
            creds = _merge_settings_credentials(platform, creds, settings)

        if not creds:
            return JSONResponse(  # type: ignore[return-value]
                status_code=400,
                content={
                    "detail": f"No credentials provided for {platform}. "
                    f"Supply them in the request or configure server settings."
                },
            )

        try:
            connector = connector_cls(**creds)
        except Exception as exc:
            return JSONResponse(  # type: ignore[return-value]
                status_code=400,
                content={"detail": f"Failed to connect to {platform}: {exc}"},
            )

        logger.info(
            "ingest_platform",
            extra={"platform": platform, "limit": request.limit},
        )

        # Fetch records
        fetch_method = (
            "get_articles" if default_object == "articles" else "get_tickets"
        )
        records = getattr(connector, fetch_method)(
            where=request.query_filter, limit=request.limit
        )

        # Apply mappings
        if request.mappings:
            mapped = apply_mappings(records, request.mappings)
        else:
            mapping_lookup = (
                DEFAULT_ARTICLE_MAPPINGS
                if default_object == "articles"
                else DEFAULT_TICKET_MAPPINGS
            )
            default_mappings = mapping_lookup.get(platform)
            if default_mappings:
                mapped = apply_mappings(records, default_mappings)
            else:
                mapped = records

        if hasattr(connector, "close"):
            connector.close()

        return await _run_processing(
            source=platform,
            records=records,
            mapped=mapped,
            process_fn=process_fn,
        )

    @router.get("/ingest/platforms")
    async def available_platforms() -> dict[str, list[str]]:
        """List available platform connectors."""
        return {"platforms": list_platforms()}

    return router


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _detect_format(filename: str | None) -> str:
    """Detect file format from filename."""
    if not filename:
        return "csv"
    suffix = (
        filename.rsplit(".", 1)[-1].lower() if "." in filename else "csv"
    )
    return suffix if suffix in FileConnector.SUPPORTED_FORMATS else "csv"


async def _run_processing(
    *,
    source: str,
    records: list[dict[str, Any]],
    mapped: list[dict[str, Any]],
    process_fn: Callable[
        [list[dict[str, Any]]], Awaitable[list[dict[str, Any]]]
    ],
) -> IngestResult:
    """Run the service's processing function and build the result."""
    try:
        results = await process_fn(mapped)
    except Exception as exc:
        logger.exception("ingest_processing_error")
        return IngestResult(
            source=source,
            total=len(records),
            processed=0,
            results=[],
            errors=[{"error": str(exc)}],
        )

    return IngestResult(
        source=source,
        total=len(records),
        processed=len(results),
        results=results,
        errors=[],
    )


def _merge_settings_credentials(
    platform: str,
    request_creds: dict[str, str],
    settings: Any,
) -> dict[str, str]:
    """Merge server settings into request credentials as fallback."""
    platform_fields: dict[str, dict[str, str]] = {
        "salesforce": {
            "instance_url": "salesforce_instance_url",
            "client_id": "salesforce_client_id",
            "client_secret": "salesforce_client_secret",
        },
        "zendesk": {
            "subdomain": "zendesk_subdomain",
            "email": "zendesk_email",
            "api_token": "zendesk_api_token",
        },
        "freshdesk": {
            "domain": "freshdesk_domain",
            "api_key": "freshdesk_api_key",
        },
        "intercom": {
            "access_token": "intercom_access_token",
        },
        "hubspot": {
            "access_token": "hubspot_access_token",
        },
        "jira": {
            "domain": "jira_domain",
            "email": "jira_email",
            "api_token": "jira_api_token",
            "project_key": "jira_project_key",
        },
        "servicenow": {
            "instance": "servicenow_instance",
            "username": "servicenow_username",
            "password": "servicenow_password",
        },
    }

    field_map = platform_fields.get(platform, {})
    merged = dict(request_creds)

    for param, setting_name in field_map.items():
        if param not in merged or not merged[param]:
            val = getattr(settings, setting_name, "")
            if val:
                merged[param] = val

    # Remove empty values
    return {k: v for k, v in merged.items() if v}
