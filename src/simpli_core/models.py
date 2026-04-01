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


class CustomerTier(StrEnum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


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

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    email: EmailStr | None = None
    tier: CustomerTier | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class Agent(SimpliBase):
    """A support agent who handles tickets."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    email: EmailStr
    teams: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    active: bool = True


class Message(_TimestampBase):
    """A single message in a conversation."""

    id: str = Field(min_length=1)
    author_type: AuthorType
    author_id: str = Field(min_length=1)
    body: str = Field(min_length=1)
    channel: Channel = Channel.EMAIL


class Ticket(_TimestampBase):
    """A support ticket."""

    id: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    description: str = Field(min_length=1)
    status: TicketStatus = TicketStatus.NEW
    priority: Priority = Priority.MEDIUM
    channel: Channel = Channel.EMAIL
    customer_id: str = Field(min_length=1)
    assignee_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )


class Conversation(_TimestampBase):
    """A conversation thread associated with a ticket."""

    id: str = Field(min_length=1)
    ticket_id: str = Field(min_length=1)
    messages: list[Message] = Field(default_factory=list)
