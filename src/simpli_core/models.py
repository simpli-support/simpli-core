"""Shared data models for the Simpli Support product family."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketStatus(StrEnum):
    NEW = "new"
    OPEN = "open"
    PENDING = "pending"
    SOLVED = "solved"
    CLOSED = "closed"


class Channel(StrEnum):
    EMAIL = "email"
    CHAT = "chat"
    PHONE = "phone"
    SOCIAL = "social"
    WEB = "web"


class Customer(BaseModel):
    """A customer who submits support requests."""

    id: str
    name: str
    email: str | None = None
    tier: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


class Agent(BaseModel):
    """A support agent who handles tickets."""

    id: str
    name: str
    email: str
    teams: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    active: bool = True


class Message(BaseModel):
    """A single message in a conversation."""

    id: str
    author_type: str  # "customer", "agent", "system"
    author_id: str
    body: str
    channel: Channel = Channel.EMAIL
    created_at: datetime = Field(default_factory=datetime.now)


class Ticket(BaseModel):
    """A support ticket."""

    id: str
    subject: str
    description: str
    status: TicketStatus = TicketStatus.NEW
    priority: Priority = Priority.MEDIUM
    channel: Channel = Channel.EMAIL
    customer_id: str
    assignee_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Conversation(BaseModel):
    """A conversation thread associated with a ticket."""

    id: str
    ticket_id: str
    messages: list[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
