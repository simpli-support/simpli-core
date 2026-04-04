"""Simpli Core — shared SDK for the Simpli Support product family."""

from __future__ import annotations

__version__ = "0.7.0"

from simpli_core.config import SimpliConfig, load_config
from simpli_core.connectors import (
    BaseConnector,
    ConnectorError,
    FieldMapping,
    FileConnector,
    SalesforceConnector,
    SalesforceSettings,
    apply_mappings,
    get_connector,
    list_platforms,
)
from simpli_core.connectors.field_config import (
    FieldConfig,
    FieldConfigStore,
    delete_field_config,
    load_field_config,
    save_field_config,
)
from simpli_core.connectors.mapping import (
    FieldCategory,
    FieldDescriptor,
    ObjectSchema,
    ObjectType,
)
from simpli_core.errors import (
    AuthenticationError,
    ExternalServiceError,
    ForbiddenError,
    NotFoundError,
    RateLimitedError,
    SimpliError,
    ValidationError,
)
from simpli_core.logging import setup_logging
from simpli_core.models import (
    Agent,
    AuthorType,
    Channel,
    Conversation,
    Customer,
    CustomerTier,
    Message,
    Priority,
    Ticket,
    TicketStatus,
)
from simpli_core.prompt_context import build_record_context
from simpli_core.settings import CustomFieldSettings, SimpliSettings
from simpli_core.usage import (
    DEFAULT_PRICING,
    CostTracker,
    LLMCost,
    ModelPricing,
    TokenUsage,
)

# FastAPI-dependent imports are lazy to avoid requiring fastapi for
# consumers that only need models/settings (e.g. simpli-data).
_FASTAPI_IMPORTS = {
    "add_api_key_middleware": ("simpli_core.auth", "add_api_key_middleware"),
    "ChatMessage": ("simpli_core.fastapi", "ChatMessage"),
    "add_request_id_middleware": ("simpli_core.fastapi", "add_request_id_middleware"),
    "create_app": ("simpli_core.fastapi", "create_app"),
    "create_ops_router": ("simpli_core.fastapi", "create_ops_router"),
    "IngestResult": ("simpli_core.connectors.ingest", "IngestResult"),
    "create_ingest_router": ("simpli_core.connectors.ingest", "create_ingest_router"),
    "create_setup_router": (
        "simpli_core.connectors.setup_router",
        "create_setup_router",
    ),
    "create_webhook_router": ("simpli_core.webhooks", "create_webhook_router"),
    "verify_signature": ("simpli_core.webhooks", "verify_signature"),
}


def __getattr__(name: str) -> object:
    if name in _FASTAPI_IMPORTS:
        module_path, attr_name = _FASTAPI_IMPORTS[name]
        import importlib

        module = importlib.import_module(module_path)
        return getattr(module, attr_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "DEFAULT_PRICING",
    "Agent",
    "AuthenticationError",
    "AuthorType",
    "BaseConnector",
    "Channel",
    "ChatMessage",
    "ConnectorError",
    "Conversation",
    "CostTracker",
    "CustomFieldSettings",
    "Customer",
    "CustomerTier",
    "ExternalServiceError",
    "FieldCategory",
    "FieldConfig",
    "FieldConfigStore",
    "FieldDescriptor",
    "FieldMapping",
    "FileConnector",
    "ForbiddenError",
    "IngestResult",
    "LLMCost",
    "Message",
    "ModelPricing",
    "NotFoundError",
    "ObjectSchema",
    "ObjectType",
    "Priority",
    "RateLimitedError",
    "SalesforceConnector",
    "SalesforceSettings",
    "SimpliConfig",
    "SimpliError",
    "SimpliSettings",
    "Ticket",
    "TicketStatus",
    "TokenUsage",
    "ValidationError",
    "add_api_key_middleware",
    "add_request_id_middleware",
    "apply_mappings",
    "build_record_context",
    "create_app",
    "create_ingest_router",
    "create_ops_router",
    "create_setup_router",
    "create_webhook_router",
    "delete_field_config",
    "get_connector",
    "list_platforms",
    "load_config",
    "load_field_config",
    "save_field_config",
    "setup_logging",
    "verify_signature",
]
