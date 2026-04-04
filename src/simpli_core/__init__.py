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

# FastAPI-dependent imports — optional so consumers that only need
# models/settings (e.g. simpli-data) don't require fastapi.
try:
    from simpli_core.auth import add_api_key_middleware
    from simpli_core.connectors.ingest import IngestResult, create_ingest_router
    from simpli_core.connectors.setup_router import create_setup_router
    from simpli_core.fastapi import (
        ChatMessage,
        add_request_id_middleware,
        create_app,
        create_ops_router,
    )
    from simpli_core.webhooks import create_webhook_router, verify_signature
except ImportError:  # pragma: no cover
    pass

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
