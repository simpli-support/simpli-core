"""Simpli Core — shared SDK for the Simpli Support product family."""

__version__ = "0.2.0"

from simpli_core.config import SimpliConfig, load_config
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
    "SimpliSettings",
    "Ticket",
    "TicketStatus",
    "load_config",
    "setup_logging",
]
