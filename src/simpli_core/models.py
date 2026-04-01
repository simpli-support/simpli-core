"""Shared data models for the Simpli Support product family."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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


class AuthorType(StrEnum):
    CUSTOMER = "customer"
    AGENT = "agent"
    SYSTEM = "system"


class SimpliBase(BaseModel):
    """Base model with shared configuration for all Simpli models."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class _TimestampBase(SimpliBase):
    """Base model that adds a created_at timestamp."""

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )


class Customer(_TimestampBase):
    """A customer who submits support requests."""

    id: str
    name: str
    email: EmailStr | None = None
    tier: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class Agent(SimpliBase):
    """A support agent who handles tickets."""

    id: str
    name: str
    email: EmailStr
    teams: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    active: bool = True


class Message(_TimestampBase):
    """A single message in a conversation."""

    id: str
    author_type: AuthorType
    author_id: str
    body: str
    channel: Channel = Channel.EMAIL


class Ticket(_TimestampBase):
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
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )


class Conversation(_TimestampBase):
    """A conversation thread associated with a ticket."""

    id: str
    ticket_id: str
    messages: list[Message] = Field(default_factory=list)
