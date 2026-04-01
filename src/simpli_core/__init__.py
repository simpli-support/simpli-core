"""Simpli Core — shared SDK for the Simpli Support product family."""

__version__ = "0.1.0"

from simpli_core.config import SimpliConfig, load_config
from simpli_core.models import (
    Agent,
    AuthorType,
    Conversation,
    Customer,
    Message,
    Ticket,
)

__all__ = [
    "Agent",
    "AuthorType",
    "Conversation",
    "Customer",
    "Message",
    "SimpliConfig",
    "Ticket",
    "load_config",
]
