"""Tests for webhook receiver: signatures, router, and payload normalization."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from simpli_core.webhooks.router import (
    _detect_event_type,
    _normalize_payload,
    create_webhook_router,
)
from simpli_core.webhooks.signatures import verify_signature

# -- Signature verification tests --


class TestSignatures:
    def _sign(self, payload: bytes, secret: str) -> str:
        return hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

    def test_zendesk_valid(self) -> None:
        payload = b'{"ticket": {"id": 1}}'
        secret = "test-secret"
        sig = self._sign(payload, secret)
        assert verify_signature("zendesk", payload, sig, secret)

    def test_zendesk_invalid(self) -> None:
        payload = b'{"ticket": {"id": 1}}'
        assert not verify_signature("zendesk", payload, "bad-sig", "secret")

    def test_freshdesk_valid(self) -> None:
        payload = b'{"data": "test"}'
        secret = "fd-secret"
        sig = self._sign(payload, secret)
        assert verify_signature("freshdesk", payload, sig, secret)

    def test_intercom_with_prefix(self) -> None:
        payload = b'{"type": "notification"}'
        secret = "ic-secret"
        sig = "sha256=" + self._sign(payload, secret)
        assert verify_signature("intercom", payload, sig, secret)

    def test_hubspot_v3(self) -> None:
        payload = b'{"event": "ticket.creation"}'
        secret = "hs-secret"
        expected = hashlib.sha256(secret.encode("utf-8") + payload).hexdigest()
        assert verify_signature("hubspot", payload, expected, secret)

    def test_jira_valid(self) -> None:
        payload = b'{"issue": {"key": "SUP-1"}}'
        secret = "jira-secret"
        sig = self._sign(payload, secret)
        assert verify_signature("jira", payload, sig, secret)

    def test_unknown_platform(self) -> None:
        assert not verify_signature("unknown", b"data", "sig", "secret")


# -- Payload normalization tests --


class TestNormalizePayload:
    def test_list_passthrough(self) -> None:
        result = _normalize_payload("any", [{"id": 1}, {"id": 2}])
        assert len(result) == 2

    def test_zendesk_ticket(self) -> None:
        result = _normalize_payload(
            "zendesk",
            {"ticket": {"id": 42, "subject": "Help"}},
        )
        assert len(result) == 1
        assert result[0]["id"] == 42

    def test_freshdesk_webhook(self) -> None:
        result = _normalize_payload(
            "freshdesk",
            {"freshdesk_webhook": {"ticket_data": {"id": 100}}},
        )
        assert result[0]["id"] == 100

    def test_intercom_data_item(self) -> None:
        result = _normalize_payload(
            "intercom",
            {"data": {"item": {"id": "conv-1", "type": "conversation"}}},
        )
        assert result[0]["id"] == "conv-1"

    def test_jira_issue(self) -> None:
        result = _normalize_payload(
            "jira",
            {"issue": {"key": "SUP-1", "fields": {"summary": "Bug"}}},
        )
        assert result[0]["key"] == "SUP-1"

    def test_servicenow_result(self) -> None:
        result = _normalize_payload(
            "servicenow",
            {"result": {"number": "INC001"}},
        )
        assert result[0]["number"] == "INC001"

    def test_salesforce_sobjects(self) -> None:
        result = _normalize_payload(
            "salesforce",
            {"sobjects": [{"CaseNumber": "1"}, {"CaseNumber": "2"}]},
        )
        assert len(result) == 2

    def test_unknown_platform(self) -> None:
        result = _normalize_payload("xyz", {"data": "test"})
        assert result == [{"data": "test"}]


# -- Event type detection --


class TestDetectEventType:
    def test_event_field(self) -> None:
        assert (
            _detect_event_type("any", {"event": "ticket.created"}) == "ticket.created"
        )

    def test_type_field(self) -> None:
        assert _detect_event_type("any", {"type": "notification"}) == "notification"

    def test_intercom_topic(self) -> None:
        assert (
            _detect_event_type("intercom", {"topic": "conversation.user.replied"})
            == "conversation.user.replied"
        )

    def test_jira_webhook_event(self) -> None:
        assert (
            _detect_event_type("jira", {"webhookEvent": "jira:issue_updated"})
            == "jira:issue_updated"
        )

    def test_unknown(self) -> None:
        assert _detect_event_type("any", {"data": 123}) == "unknown"


# -- Router integration tests --


class TestWebhookRouter:
    @pytest.fixture
    def received_events(self) -> list[tuple[str, list[dict[str, Any]]]]:
        return []

    @pytest.fixture
    def client(
        self, received_events: list[tuple[str, list[dict[str, Any]]]]
    ) -> TestClient:
        events = received_events

        async def on_event(event_type: str, records: list[dict[str, Any]]) -> None:
            events.append((event_type, records))

        app = FastAPI()
        router = create_webhook_router(
            on_event=on_event,
            secrets={"zendesk": "test-secret"},
            require_signature=False,  # Disable for testing
        )
        app.include_router(router)
        return TestClient(app)

    def test_receive_zendesk_webhook(
        self,
        client: TestClient,
        received_events: list[tuple[str, list[dict[str, Any]]]],
    ) -> None:
        resp = client.post(
            "/api/v1/webhook/zendesk",
            json={
                "event": "ticket.created",
                "ticket": {
                    "id": 42,
                    "subject": "Help needed",
                    "description": "Details",
                    "status": "new",
                    "priority": "high",
                    "via": {"channel": "email"},
                    "requester_id": 123,
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["event_type"] == "ticket.created"
        assert data["records"] == 1
        assert len(received_events) == 1

    def test_receive_jira_webhook(
        self,
        client: TestClient,
        received_events: list[tuple[str, list[dict[str, Any]]]],
    ) -> None:
        resp = client.post(
            "/api/v1/webhook/jira",
            json={
                "webhookEvent": "jira:issue_created",
                "issue": {
                    "key": "SUP-1",
                    "fields": {"summary": "Bug report"},
                },
            },
        )
        assert resp.status_code == 200
        assert len(received_events) == 1

    def test_invalid_json(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/webhook/zendesk",
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400

    def test_signature_required(self) -> None:
        events: list[tuple[str, list[dict[str, Any]]]] = []

        async def on_event(et: str, recs: list[dict[str, Any]]) -> None:
            events.append((et, recs))

        app = FastAPI()
        router = create_webhook_router(
            on_event=on_event,
            secrets={"zendesk": "my-secret"},
            require_signature=True,
        )
        app.include_router(router)
        client = TestClient(app)

        # No signature → rejected
        resp = client.post(
            "/api/v1/webhook/zendesk",
            json={"ticket": {"id": 1}},
        )
        assert resp.status_code == 401

    def test_valid_signature_accepted(self) -> None:
        events: list[tuple[str, list[dict[str, Any]]]] = []

        async def on_event(et: str, recs: list[dict[str, Any]]) -> None:
            events.append((et, recs))

        secret = "my-webhook-secret"
        app = FastAPI()
        router = create_webhook_router(
            on_event=on_event,
            secrets={"zendesk": secret},
            require_signature=True,
        )
        app.include_router(router)
        client = TestClient(app)

        payload = json.dumps({"ticket": {"id": 1}}).encode()
        sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

        resp = client.post(
            "/api/v1/webhook/zendesk",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Zendesk-Webhook-Signature": sig,
            },
        )
        assert resp.status_code == 200
        assert len(events) == 1
