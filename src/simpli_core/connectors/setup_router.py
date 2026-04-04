"""Setup router factory for field discovery and configuration via API.

Provides endpoints for the frontend to discover platform fields and
save custom field mapping configurations.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from simpli_core.connectors.field_config import (
    FieldConfig,
    delete_field_config,
    load_field_config,
    save_field_config,
)
from simpli_core.connectors.ingest import _merge_settings_credentials
from simpli_core.connectors.mapping import FieldMapping, ObjectSchema
from simpli_core.connectors.registry import get_connector, list_platforms

logger = logging.getLogger(__name__)


class DiscoverRequest(BaseModel):
    """Request to discover fields from a platform."""

    credentials: dict[str, str] = Field(
        default_factory=dict,
        description="Platform-specific credentials (falls back to server settings)",
    )
    object_type: str = Field(
        default="ticket", description="Object type: ticket or article"
    )


class ConfigureRequest(BaseModel):
    """Request to save a field configuration."""

    object_type: str = Field(default="ticket")
    selected_fields: list[str] = Field(
        description="API field names to include in queries",
    )
    custom_mappings: list[FieldMapping] = Field(
        description="Field mapping rules for custom fields",
    )


def create_setup_router(*, settings: Any = None) -> APIRouter:
    """Create a FastAPI router with field discovery and configuration endpoints.

    Args:
        settings: Service settings object for credential fallback.

    Returns:
        APIRouter with setup endpoints under ``/api/v1/setup``.
    """
    router = APIRouter(prefix="/api/v1/setup", tags=["setup"])

    @router.get("/platforms")
    async def available_platforms() -> dict[str, list[str]]:
        """List available platform connectors."""
        return {"platforms": list_platforms()}

    @router.post("/{platform}/discover", response_model=ObjectSchema)
    async def discover_fields(
        platform: str,
        request: DiscoverRequest,
    ) -> ObjectSchema | JSONResponse:
        """Discover available fields from a platform."""
        try:
            connector_cls = get_connector(platform)
        except KeyError:
            available = ", ".join(list_platforms())
            return JSONResponse(
                status_code=400,
                content={
                    "detail": f"Unknown platform: {platform!r}. Available: {available}"
                },
            )

        creds = dict(request.credentials)
        if settings:
            creds = _merge_settings_credentials(platform, creds, settings)

        if not creds:
            return JSONResponse(
                status_code=400,
                content={"detail": f"No credentials for {platform}."},
            )

        try:
            connector = connector_cls(**creds)
            schema = connector.describe_fields(request.object_type)
            if hasattr(connector, "close"):
                connector.close()
        except NotImplementedError:
            return JSONResponse(
                status_code=501,
                content={
                    "detail": f"{platform} does not support field discovery."
                },
            )
        except Exception as exc:
            return JSONResponse(
                status_code=502,
                content={"detail": f"Field discovery failed: {exc}"},
            )

        return schema

    @router.post("/{platform}/configure")
    async def configure_fields(
        platform: str,
        request: ConfigureRequest,
    ) -> dict[str, Any]:
        """Save a field configuration for a platform."""
        config = FieldConfig(
            platform=platform,
            object_type=request.object_type,
            selected_fields=request.selected_fields,
            custom_mappings=request.custom_mappings,
        )
        save_field_config(config)
        return {
            "status": "saved",
            "platform": platform,
            "object_type": request.object_type,
            "total_fields": len(request.selected_fields),
            "custom_mappings": len(request.custom_mappings),
        }

    @router.get("/{platform}/config")
    async def get_config(
        platform: str,
        object_type: str = "ticket",
    ) -> FieldConfig | JSONResponse:
        """Get the current field configuration for a platform."""
        config = load_field_config(platform, object_type)
        if config is None:
            return JSONResponse(
                status_code=404,
                content={
                    "detail": f"No config for {platform}:{object_type}"
                },
            )
        return config

    @router.delete("/{platform}/config")
    async def remove_config(
        platform: str,
        object_type: str = "ticket",
    ) -> dict[str, str]:
        """Remove a field configuration."""
        deleted = delete_field_config(platform, object_type)
        if not deleted:
            return JSONResponse(
                status_code=404,
                content={
                    "detail": f"No config for {platform}:{object_type}"
                },
            )
        return {"status": "deleted", "platform": platform}

    return router
