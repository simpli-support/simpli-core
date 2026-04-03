"""Tests for the generic ingest router factory."""

from __future__ import annotations

import io
import json
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from simpli_core.connectors.ingest import (
    IngestResult,
    PlatformIngestRequest,
    _detect_format,
    _merge_settings_credentials,
    create_ingest_router,
)


async def _mock_process(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Simple processing function that echoes records."""
    return [{"processed": True, **r} for r in records]


def _create_test_app() -> FastAPI:
    app = FastAPI()
    router = create_ingest_router(process_fn=_mock_process)
    app.include_router(router)
    return app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(_create_test_app())


class TestFileIngest:
    def test_csv_upload(self, client: TestClient) -> None:
        csv = "name,email\nAlice,alice@test.com\nBob,bob@test.com\n"
        file = io.BytesIO(csv.encode())
        resp = client.post(
            "/api/v1/ingest",
            files={"file": ("data.csv", file, "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert data["processed"] == 2
        assert data["source"] == "data.csv"

    def test_json_upload(self, client: TestClient) -> None:
        records = [{"id": "1", "name": "Test"}]
        file = io.BytesIO(json.dumps(records).encode())
        resp = client.post(
            "/api/v1/ingest",
            files={"file": ("data.json", file, "application/json")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1

    def test_csv_with_custom_mappings(self, client: TestClient) -> None:
        csv = "title,body\nHelp,Details\n"
        mappings = json.dumps([
            {"source": "title", "target": "subject"},
            {"source": "body", "target": "description"},
        ])
        file = io.BytesIO(csv.encode())
        resp = client.post(
            "/api/v1/ingest",
            files={"file": ("data.csv", file, "text/csv")},
            data={"mappings": mappings},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["processed"] == 1
        assert data["results"][0]["subject"] == "Help"


class TestPlatformIngest:
    def test_unknown_platform(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/ingest/nonexistent",
            json={"limit": 10},
        )
        assert resp.status_code == 400
        assert "Unknown platform" in resp.json()["detail"]

    def test_no_credentials(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/ingest/zendesk",
            json={"limit": 10},
        )
        assert resp.status_code == 400
        assert "credentials" in resp.json()["detail"].lower()

    def test_available_platforms(self, client: TestClient) -> None:
        resp = client.get("/api/v1/ingest/platforms")
        assert resp.status_code == 200
        platforms = resp.json()["platforms"]
        assert "salesforce" in platforms
        assert "zendesk" in platforms
        assert "freshdesk" in platforms


class TestHelpers:
    def test_detect_format_csv(self) -> None:
        assert _detect_format("data.csv") == "csv"

    def test_detect_format_json(self) -> None:
        assert _detect_format("data.json") == "json"

    def test_detect_format_jsonl(self) -> None:
        assert _detect_format("data.jsonl") == "jsonl"

    def test_detect_format_none(self) -> None:
        assert _detect_format(None) == "csv"

    def test_detect_format_unknown(self) -> None:
        assert _detect_format("data.xyz") == "csv"

    def test_merge_settings_salesforce(self) -> None:
        class FakeSettings:
            salesforce_instance_url = "https://test.salesforce.com"
            salesforce_client_id = "id123"
            salesforce_client_secret = "secret456"

        merged = _merge_settings_credentials(
            "salesforce", {}, FakeSettings()
        )
        assert merged["instance_url"] == "https://test.salesforce.com"
        assert merged["client_id"] == "id123"

    def test_merge_settings_request_takes_precedence(self) -> None:
        class FakeSettings:
            zendesk_subdomain = "default"
            zendesk_email = "default@test.com"
            zendesk_api_token = "default-token"

        merged = _merge_settings_credentials(
            "zendesk",
            {"subdomain": "override"},
            FakeSettings(),
        )
        assert merged["subdomain"] == "override"
        assert merged["email"] == "default@test.com"

    def test_merge_settings_unknown_platform(self) -> None:
        merged = _merge_settings_credentials(
            "unknown_platform", {"key": "val"}, object()
        )
        assert merged == {"key": "val"}


class TestModels:
    def test_platform_ingest_request_defaults(self) -> None:
        req = PlatformIngestRequest()
        assert req.credentials == {}
        assert req.query_filter == ""
        assert req.limit == 100

    def test_ingest_result(self) -> None:
        result = IngestResult(
            source="test.csv",
            total=10,
            processed=8,
            results=[{"ok": True}],
            errors=[{"error": "bad record"}],
        )
        assert result.total == 10
        assert result.processed == 8
