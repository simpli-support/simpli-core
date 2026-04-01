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
    Message,
    Priority,
    Ticket,
    TicketStatus,
)


class TestTicket:
    def test_create_with_defaults(self) -> None:
        ticket = Ticket(
            id="T-001",
            subject="Cannot login",
            description="Getting 403 error when trying to login",
            customer_id="C-001",
        )
        assert ticket.status == TicketStatus.NEW
        assert ticket.priority == Priority.MEDIUM
        assert ticket.channel == Channel.EMAIL
        assert ticket.assignee_id is None
        assert ticket.tags == []
        assert ticket.metadata == {}

    def test_timestamps_are_utc(self) -> None:
        ticket = Ticket(
            id="T-001",
            subject="Test",
            description="Test",
            customer_id="C-001",
        )
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


class TestCustomer:
    def test_create_with_defaults(self) -> None:
        customer = Customer(id="C-001", name="Jane Doe", email="jane@example.com")
        assert customer.tier is None
        assert customer.metadata == {}

    def test_invalid_email_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Customer(id="C-001", name="Jane", email="not-an-email")

    def test_none_email_allowed(self) -> None:
        customer = Customer(id="C-001", name="Jane")
        assert customer.email is None


class TestAgent:
    def test_create(self) -> None:
        agent = Agent(
            id="A-001",
            name="John Smith",
            email="john@support.com",
            teams=["billing"],
            skills=["payments", "refunds"],
        )
        assert agent.active is True
        assert len(agent.skills) == 2

    def test_invalid_email_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Agent(id="A-001", name="John", email="bad")


class TestMessage:
    def test_create(self) -> None:
        msg = Message(
            id="M-001",
            author_type=AuthorType.CUSTOMER,
            author_id="C-001",
            body="I need help with my account",
        )
        assert msg.author_type == AuthorType.CUSTOMER
        assert msg.author_type == "customer"  # StrEnum compat

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


class TestConversation:
    def test_create_empty(self) -> None:
        conv = Conversation(id="CONV-001", ticket_id="T-001")
        assert conv.messages == []
        assert conv.created_at.tzinfo == UTC

    def test_create_with_messages(self) -> None:
        msg = Message(
            id="M-001",
            author_type=AuthorType.CUSTOMER,
            author_id="C-001",
            body="Help",
        )
        conv = Conversation(id="CONV-001", ticket_id="T-001", messages=[msg])
        assert len(conv.messages) == 1


class TestEnums:
    def test_priority_values(self) -> None:
        assert set(Priority) == {"low", "medium", "high", "urgent"}

    def test_ticket_status_values(self) -> None:
        assert set(TicketStatus) == {"new", "open", "pending", "solved", "closed"}

    def test_channel_values(self) -> None:
        assert set(Channel) == {"email", "chat", "phone", "social", "web"}

    def test_author_type_values(self) -> None:
        assert set(AuthorType) == {"customer", "agent", "system"}
