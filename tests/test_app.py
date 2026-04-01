"""Tests for simpli-core models and config."""

from simpli_core.models import (
    Agent,
    Customer,
    Message,
    Priority,
    Ticket,
    TicketStatus,
)


def test_create_ticket() -> None:
    ticket = Ticket(
        id="T-001",
        subject="Cannot login",
        description="Getting 403 error when trying to login",
        customer_id="C-001",
    )
    assert ticket.status == TicketStatus.NEW
    assert ticket.priority == Priority.MEDIUM


def test_create_customer() -> None:
    customer = Customer(id="C-001", name="Jane Doe", email="jane@example.com")
    assert customer.tier is None
    assert customer.metadata == {}


def test_create_agent() -> None:
    agent = Agent(
        id="A-001",
        name="John Smith",
        email="john@support.com",
        teams=["billing"],
        skills=["payments", "refunds"],
    )
    assert agent.active is True
    assert len(agent.skills) == 2


def test_create_message() -> None:
    msg = Message(
        id="M-001",
        author_type="customer",
        author_id="C-001",
        body="I need help with my account",
    )
    assert msg.author_type == "customer"
