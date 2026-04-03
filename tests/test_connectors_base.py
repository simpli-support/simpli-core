"""Tests for connector base class, errors, registry, and dot-notation mapping."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest

from simpli_core.connectors.base import BaseConnector
from simpli_core.connectors.errors import (
    AuthenticationError,
    ConfigurationError,
    ConnectorError,
    PlatformAPIError,
    RateLimitError,
)
from simpli_core.connectors.mapping import (
    FieldMapping,
    _get_nested,
    apply_mappings,
)
from simpli_core.connectors.registry import (
    _CONNECTORS,
    get_connector,
    list_platforms,
    register,
)


# -- Error hierarchy tests --


class TestErrors:
    def test_connector_error_includes_platform(self) -> None:
        err = ConnectorError("something broke", platform="zendesk")
        assert "zendesk" in str(err)
        assert err.platform == "zendesk"

    def test_authentication_error(self) -> None:
        err = AuthenticationError("bad creds", platform="salesforce")
        assert isinstance(err, ConnectorError)
        assert "salesforce" in str(err)

    def test_rate_limit_error_with_retry_after(self) -> None:
        err = RateLimitError("slow down", platform="freshdesk", retry_after=60)
        assert err.retry_after == 60
        assert isinstance(err, ConnectorError)

    def test_platform_api_error(self) -> None:
        err = PlatformAPIError(
            "not found",
            platform="hubspot",
            status_code=404,
            response_body='{"error": "not found"}',
        )
        assert err.status_code == 404
        assert err.response_body == '{"error": "not found"}'

    def test_configuration_error(self) -> None:
        err = ConfigurationError("missing API key", platform="jira")
        assert isinstance(err, ConnectorError)


# -- Base connector tests --


class TestBaseConnector:
    def test_init_with_auth_headers(self) -> None:
        connector = BaseConnector(
            "https://api.example.com",
            auth_headers={"Authorization": "Bearer test-token"},
        )
        assert connector._client.headers["Authorization"] == "Bearer test-token"
        connector.close()

    def test_init_with_basic_auth(self) -> None:
        connector = BaseConnector(
            "https://api.example.com",
            basic_auth=("user", "pass"),
        )
        assert "Basic" in connector._client.headers["Authorization"]
        connector.close()

    def test_context_manager(self) -> None:
        with BaseConnector("https://api.example.com") as conn:
            assert conn is not None

    def test_handle_errors_401(self) -> None:
        connector = BaseConnector("https://api.example.com")
        resp = MagicMock(spec=httpx.Response)
        resp.is_success = False
        resp.status_code = 401
        resp.text = "Unauthorized"

        with pytest.raises(AuthenticationError):
            connector._handle_errors(resp)
        connector.close()

    def test_handle_errors_403(self) -> None:
        connector = BaseConnector("https://api.example.com")
        resp = MagicMock(spec=httpx.Response)
        resp.is_success = False
        resp.status_code = 403
        resp.text = "Forbidden"

        with pytest.raises(AuthenticationError):
            connector._handle_errors(resp)
        connector.close()

    def test_handle_errors_429(self) -> None:
        connector = BaseConnector("https://api.example.com")
        resp = MagicMock(spec=httpx.Response)
        resp.is_success = False
        resp.status_code = 429
        resp.text = "Too Many Requests"
        resp.headers = {"Retry-After": "30"}

        with pytest.raises(RateLimitError) as exc_info:
            connector._handle_errors(resp)
        assert exc_info.value.retry_after == 30
        connector.close()

    def test_handle_errors_500(self) -> None:
        connector = BaseConnector("https://api.example.com")
        resp = MagicMock(spec=httpx.Response)
        resp.is_success = False
        resp.status_code = 500
        resp.text = "Internal Server Error"

        with pytest.raises(PlatformAPIError) as exc_info:
            connector._handle_errors(resp)
        assert exc_info.value.status_code == 500
        connector.close()

    def test_handle_errors_success(self) -> None:
        connector = BaseConnector("https://api.example.com")
        resp = MagicMock(spec=httpx.Response)
        resp.is_success = True

        # Should not raise
        connector._handle_errors(resp)
        connector.close()

    def test_abstract_methods_raise(self) -> None:
        connector = BaseConnector("https://api.example.com")
        with pytest.raises(NotImplementedError):
            connector.get_tickets()
        with pytest.raises(NotImplementedError):
            connector.get_customers()
        with pytest.raises(NotImplementedError):
            connector.get_messages("123")
        with pytest.raises(NotImplementedError):
            connector.get_articles()
        connector.close()


# -- Registry tests --


class TestRegistry:
    def test_register_and_get(self) -> None:
        class FakeConnector(BaseConnector):
            platform = "fake"

        register("fake", FakeConnector)
        assert get_connector("fake") is FakeConnector
        # Cleanup
        _CONNECTORS.pop("fake", None)

    def test_get_unknown_raises(self) -> None:
        with pytest.raises(KeyError, match="Unknown platform"):
            get_connector("nonexistent_platform_xyz")

    def test_list_platforms(self) -> None:
        platforms = list_platforms()
        assert isinstance(platforms, list)
        # Salesforce should be registered (imported via connectors/__init__.py)
        assert "salesforce" in platforms

    def test_salesforce_registered(self) -> None:
        from simpli_core.connectors.salesforce import SalesforceConnector

        cls = get_connector("salesforce")
        assert cls is SalesforceConnector


# -- Dot-notation mapping tests --


class TestDotNotation:
    def test_flat_key(self) -> None:
        record = {"name": "Alice"}
        assert _get_nested(record, "name") == "Alice"

    def test_nested_key(self) -> None:
        record = {"via": {"channel": "email"}}
        assert _get_nested(record, "via.channel") == "email"

    def test_deeply_nested(self) -> None:
        record = {"a": {"b": {"c": "deep"}}}
        assert _get_nested(record, "a.b.c") == "deep"

    def test_missing_nested_returns_default(self) -> None:
        record = {"via": {"channel": "email"}}
        assert _get_nested(record, "via.missing", "fallback") == "fallback"

    def test_missing_intermediate_returns_default(self) -> None:
        record = {"via": "not_a_dict"}
        assert _get_nested(record, "via.channel", "fallback") == "fallback"

    def test_empty_record_returns_default(self) -> None:
        assert _get_nested({}, "any.key", "default") == "default"

    def test_flat_key_takes_precedence(self) -> None:
        # If the flat key exists, use it even if it has a dot
        record = {"via.channel": "flat_value", "via": {"channel": "nested_value"}}
        assert _get_nested(record, "via.channel") == "flat_value"

    def test_apply_mappings_with_dot_notation(self) -> None:
        mappings = [
            FieldMapping(source="via.channel", target="channel"),
            FieldMapping(source="name", target="name"),
        ]
        records = [{"via": {"channel": "email"}, "name": "Test"}]
        result = apply_mappings(records, mappings)
        assert result == [{"channel": "email", "name": "Test"}]


# -- Freshdesk / ServiceNow transform tests --


class TestPlatformTransforms:
    def test_freshdesk_status(self) -> None:
        mappings = [
            FieldMapping(source="status", target="status", transform="freshdesk_status"),
        ]
        records = [{"status": 2}, {"status": 3}, {"status": 4}, {"status": 5}]
        result = apply_mappings(records, mappings)
        assert result[0]["status"] == "open"
        assert result[1]["status"] == "pending"
        assert result[2]["status"] == "solved"
        assert result[3]["status"] == "closed"

    def test_freshdesk_priority(self) -> None:
        mappings = [
            FieldMapping(
                source="priority", target="priority", transform="freshdesk_priority"
            ),
        ]
        records = [{"priority": 1}, {"priority": 2}, {"priority": 3}, {"priority": 4}]
        result = apply_mappings(records, mappings)
        assert result[0]["priority"] == "low"
        assert result[1]["priority"] == "medium"
        assert result[2]["priority"] == "high"
        assert result[3]["priority"] == "urgent"

    def test_servicenow_state(self) -> None:
        mappings = [
            FieldMapping(
                source="state", target="status", transform="servicenow_state"
            ),
        ]
        records = [{"state": 1}, {"state": 2}, {"state": 6}, {"state": 7}]
        result = apply_mappings(records, mappings)
        assert result[0]["status"] == "new"
        assert result[1]["status"] == "open"
        assert result[2]["status"] == "solved"
        assert result[3]["status"] == "closed"

    def test_servicenow_priority(self) -> None:
        mappings = [
            FieldMapping(
                source="priority",
                target="priority",
                transform="servicenow_priority",
            ),
        ]
        records = [{"priority": 1}, {"priority": 2}, {"priority": 3}, {"priority": 4}]
        result = apply_mappings(records, mappings)
        assert result[0]["priority"] == "urgent"
        assert result[1]["priority"] == "high"
        assert result[2]["priority"] == "medium"
        assert result[3]["priority"] == "low"

    def test_unknown_freshdesk_value_passthrough(self) -> None:
        mappings = [
            FieldMapping(source="status", target="status", transform="freshdesk_status"),
        ]
        result = apply_mappings([{"status": 99}], mappings)
        assert result[0]["status"] == "99"  # Passes through as string
