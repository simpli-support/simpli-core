"""Tests for simpli-core models."""

from datetime import UTC

import pytest
from pydantic import ValidationError

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


class TestTicket:
    def test_create_with_defaults(self, ticket: Ticket) -> None:
        assert ticket.status == TicketStatus.NEW
        assert ticket.priority == Priority.MEDIUM
        assert ticket.channel == Channel.EMAIL
        assert ticket.assignee_id is None
        assert ticket.tags == []
        assert ticket.metadata == {}

    def test_timestamps_are_utc(self, ticket: Ticket) -> None:
        assert ticket.created_at.tzinfo is not None
        assert ticket.created_at.tzinfo == UTC
        assert ticket.updated_at.tzinfo == UTC

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            Ticket(
                id="T-001",
                subject="Test",
                description="Test",
                customer_id="C-001",
                bogus="value",
            )

    def test_empty_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Ticket(
                id="",
                subject="Test",
                description="Test",
                customer_id="C-001",
            )

    def test_empty_subject_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Ticket(
                id="T-001",
                subject="",
                description="Test",
                customer_id="C-001",
            )

    def test_serialization_roundtrip(self, ticket: Ticket) -> None:
        data = ticket.model_dump()
        restored = Ticket.model_validate(data)
        assert restored == ticket

    def test_json_roundtrip(self, ticket: Ticket) -> None:
        json_str = ticket.model_dump_json()
        restored = Ticket.model_validate_json(json_str)
        assert restored == ticket


class TestCustomer:
    def test_create_with_defaults(self, customer: Customer) -> None:
        assert customer.tier is None
        assert customer.metadata == {}

    def test_invalid_email_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Customer(id="C-001", name="Jane", email="not-an-email")

    def test_none_email_allowed(self) -> None:
        customer = Customer(id="C-001", name="Jane")
        assert customer.email is None

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Customer(id="C-001", name="")

    def test_tier_enum(self) -> None:
        customer = Customer(id="C-001", name="Jane", tier=CustomerTier.PREMIUM)
        assert customer.tier == CustomerTier.PREMIUM
        assert customer.tier == "premium"

    def test_invalid_tier_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Customer(id="C-001", name="Jane", tier="invalid")

    def test_whitespace_stripping(self) -> None:
        customer = Customer(id="C-001", name="  Jane Doe  ")
        assert customer.name == "Jane Doe"

    def test_serialization_roundtrip(self, customer: Customer) -> None:
        data = customer.model_dump()
        restored = Customer.model_validate(data)
        assert restored == customer


class TestAgent:
    def test_create(self, agent: Agent) -> None:
        assert agent.active is True
        assert len(agent.skills) == 2

    def test_invalid_email_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Agent(id="A-001", name="John", email="bad")

    def test_empty_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Agent(id="", name="John", email="john@test.com")


class TestMessage:
    def test_create(self, message: Message) -> None:
        assert message.author_type == AuthorType.CUSTOMER
        assert message.author_type == "customer"  # StrEnum compat

    def test_author_type_from_string(self) -> None:
        msg = Message(
            id="M-001",
            author_type="agent",
            author_id="A-001",
            body="Hello",
        )
        assert msg.author_type == AuthorType.AGENT

    def test_invalid_author_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Message(
                id="M-001",
                author_type="invalid",
                author_id="C-001",
                body="Test",
            )

    def test_empty_body_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Message(
                id="M-001",
                author_type=AuthorType.CUSTOMER,
                author_id="C-001",
                body="",
            )


class TestConversation:
    def test_create_empty(self) -> None:
        conv = Conversation(id="CONV-001", ticket_id="T-001")
        assert conv.messages == []
        assert conv.created_at.tzinfo == UTC

    def test_create_with_messages(self, conversation: Conversation) -> None:
        assert len(conversation.messages) == 1

    def test_serialization_roundtrip(self, conversation: Conversation) -> None:
        data = conversation.model_dump()
        restored = Conversation.model_validate(data)
        assert restored == conversation


class TestEnums:
    def test_priority_values(self) -> None:
        assert set(Priority) == {"low", "medium", "high", "urgent"}

    def test_ticket_status_values(self) -> None:
        assert set(TicketStatus) == {
            "new",
            "open",
            "pending",
            "solved",
            "closed",
        }

    def test_channel_values(self) -> None:
        assert set(Channel) == {"email", "chat", "phone", "social", "web"}

    def test_author_type_values(self) -> None:
        assert set(AuthorType) == {"customer", "agent", "system"}

    def test_customer_tier_values(self) -> None:
        assert set(CustomerTier) == {
            "free",
            "basic",
            "premium",
            "enterprise",
        }
