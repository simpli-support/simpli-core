"""Shared test fixtures for simpli-core."""

import pytest

from simpli_core.models import (
    Agent,
    AuthorType,
    Conversation,
    Customer,
    Message,
    Ticket,
)


@pytest.fixture
def customer() -> Customer:
    return Customer(id="C-001", name="Jane Doe", email="jane@example.com")


@pytest.fixture
def agent() -> Agent:
    return Agent(
        id="A-001",
        name="John Smith",
        email="john@support.com",
        teams=["billing"],
        skills=["payments", "refunds"],
    )


@pytest.fixture
def message() -> Message:
    return Message(
        id="M-001",
        author_type=AuthorType.CUSTOMER,
        author_id="C-001",
        body="I need help with my account",
    )


@pytest.fixture
def ticket(customer: Customer) -> Ticket:
    return Ticket(
        id="T-001",
        subject="Cannot login",
        description="Getting 403 error when trying to login",
        customer_id=customer.id,
    )


@pytest.fixture
def conversation(ticket: Ticket, message: Message) -> Conversation:
    return Conversation(
        id="CONV-001",
        ticket_id=ticket.id,
        messages=[message],
    )
