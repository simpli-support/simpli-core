"""Simpli Core — shared SDK for the Simpli Support product family."""

__version__ = "0.5.0"

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
    "BaseConnector",
    "ChatMessage",
    "ConnectorError",
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
    "Priority",
    "SalesforceConnector",
    "SalesforceSettings",
    "SimpliConfig",
    "SimpliSettings",
    "Ticket",
    "TicketStatus",
    "TokenUsage",
    "add_request_id_middleware",
    "apply_mappings",
    "create_app",
    "create_ops_router",
    "get_connector",
    "list_platforms",
    "load_config",
    "setup_logging",
]
