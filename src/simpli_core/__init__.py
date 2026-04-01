"""Simpli Core — shared SDK for the Simpli Support product family."""

__version__ = "0.1.0"

from simpli_core.config import SimpliConfig, load_config
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

__all__ = [
    "Agent",
    "AuthorType",
    "Channel",
    "Conversation",
    "Customer",
    "CustomerTier",
    "Message",
    "Priority",
    "SimpliConfig",
    "Ticket",
    "TicketStatus",
    "load_config",
]
