"""Simpli Core — shared SDK for the Simpli Support product family."""

__version__ = "0.4.0"

from simpli_core.config import SimpliConfig, load_config
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
    "ChatMessage",
    "DEFAULT_PRICING",
    "Agent",
    "AuthorType",
    "Channel",
    "Conversation",
    "CostTracker",
    "Customer",
    "CustomerTier",
    "LLMCost",
    "Message",
    "ModelPricing",
    "Priority",
    "SimpliConfig",
    "SimpliSettings",
    "Ticket",
    "TicketStatus",
    "TokenUsage",
    "add_request_id_middleware",
    "create_app",
    "create_ops_router",
    "load_config",
    "setup_logging",
]
