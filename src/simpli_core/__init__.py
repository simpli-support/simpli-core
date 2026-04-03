"""Simpli Core — shared SDK for the Simpli Support product family."""

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
from simpli_core.connectors.ingest import IngestResult, create_ingest_router
from simpli_core.auth import add_api_key_middleware
from simpli_core.errors import (
    AuthenticationError,
    ExternalServiceError,
    ForbiddenError,
    NotFoundError,
    RateLimitedError,
    SimpliError,
    ValidationError,
)
from simpli_core.webhooks import create_webhook_router, verify_signature
from simpli_core.fastapi import (
    ChatMessage,
    add_request_id_middleware,
    create_app,
    create_ops_router,
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
from simpli_core.settings import SimpliSettings
from simpli_core.usage import (
    DEFAULT_PRICING,
    CostTracker,
    LLMCost,
    ModelPricing,
    TokenUsage,
)

__all__ = [
    "AuthenticationError",
    "BaseConnector",
    "ChatMessage",
    "ConnectorError",
    "ExternalServiceError",
    "ForbiddenError",
    "IngestResult",
    "DEFAULT_PRICING",
    "Agent",
    "AuthorType",
    "Channel",
    "Conversation",
    "CostTracker",
    "Customer",
    "CustomerTier",
    "FieldMapping",
    "FileConnector",
    "LLMCost",
    "Message",
    "ModelPricing",
    "NotFoundError",
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
    "create_app",
    "create_ingest_router",
    "create_ops_router",
    "create_webhook_router",
    "get_connector",
    "list_platforms",
    "load_config",
    "setup_logging",
    "verify_signature",
]
