"""Tests for platform connectors.

Covers Zendesk, Freshdesk, Intercom, HubSpot, Jira, ServiceNow.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from simpli_core.connectors.freshdesk import FreshdeskConnector
from simpli_core.connectors.hubspot import HubSpotConnector
from simpli_core.connectors.intercom import IntercomConnector
from simpli_core.connectors.jira import JiraConnector
from simpli_core.connectors.mapping import (
    DEFAULT_ARTICLE_MAPPINGS,
    DEFAULT_TICKET_MAPPINGS,
    FRESHDESK_TICKET_TO_TICKET,
    HUBSPOT_TICKET_TO_TICKET,
    INTERCOM_CONVERSATION_TO_TICKET,
    JIRA_ISSUE_TO_TICKET,
    SERVICENOW_INCIDENT_TO_TICKET,
    ZENDESK_TICKET_TO_TICKET,
    apply_mappings,
)
from simpli_core.connectors.registry import get_connector, list_platforms
from simpli_core.connectors.servicenow import ServiceNowConnector
from simpli_core.connectors.settings import (
    FreshdeskSettings,
    HubSpotSettings,
    IntercomSettings,
    JiraSettings,
    ServiceNowSettings,
    ZendeskSettings,
)
from simpli_core.connectors.zendesk import ZendeskConnector

# -- Registry tests --


class TestPlatformRegistration:
    def test_all_platforms_registered(self) -> None:
        platforms = list_platforms()
        expected = [
            "freshdesk",
            "hubspot",
            "intercom",
            "jira",
            "salesforce",
            "servicenow",
            "zendesk",
        ]
        assert platforms == expected

    def test_get_zendesk(self) -> None:
        assert get_connector("zendesk") is ZendeskConnector

    def test_get_freshdesk(self) -> None:
        assert get_connector("freshdesk") is FreshdeskConnector

    def test_get_intercom(self) -> None:
        assert get_connector("intercom") is IntercomConnector

    def test_get_hubspot(self) -> None:
        assert get_connector("hubspot") is HubSpotConnector

    def test_get_jira(self) -> None:
        assert get_connector("jira") is JiraConnector

    def test_get_servicenow(self) -> None:
        assert get_connector("servicenow") is ServiceNowConnector


# -- Settings mixin tests --


class TestSettingsMixins:
    def test_zendesk_settings(self) -> None:
        s = ZendeskSettings()
        assert s.zendesk_subdomain == ""
        assert s.zendesk_email == ""
        assert s.zendesk_api_token == ""

    def test_freshdesk_settings(self) -> None:
        s = FreshdeskSettings()
        assert s.freshdesk_domain == ""
        assert s.freshdesk_api_key == ""

    def test_intercom_settings(self) -> None:
        s = IntercomSettings()
        assert s.intercom_access_token == ""

    def test_hubspot_settings(self) -> None:
        s = HubSpotSettings()
        assert s.hubspot_access_token == ""

    def test_jira_settings(self) -> None:
        s = JiraSettings()
        assert s.jira_domain == ""
        assert s.jira_email == ""
        assert s.jira_api_token == ""
        assert s.jira_project_key == ""

    def test_servicenow_settings(self) -> None:
        s = ServiceNowSettings()
        assert s.servicenow_instance == ""
        assert s.servicenow_username == ""
        assert s.servicenow_password == ""


# -- Connector initialization tests --


class TestConnectorInit:
    def test_zendesk_sets_platform(self) -> None:
        conn = ZendeskConnector("test", "user@test.com", "token123")
        assert conn.platform == "zendesk"
        assert "test.zendesk.com" in str(conn._client.base_url)
        conn.close()

    def test_freshdesk_sets_platform(self) -> None:
        conn = FreshdeskConnector("test", "apikey123")
        assert conn.platform == "freshdesk"
        assert "test.freshdesk.com" in str(conn._client.base_url)
        conn.close()

    def test_intercom_sets_platform(self) -> None:
        conn = IntercomConnector("token123")
        assert conn.platform == "intercom"
        assert "api.intercom.io" in str(conn._client.base_url)
        conn.close()

    def test_hubspot_sets_platform(self) -> None:
        conn = HubSpotConnector("token123")
        assert conn.platform == "hubspot"
        assert "api.hubapi.com" in str(conn._client.base_url)
        conn.close()

    def test_jira_sets_platform(self) -> None:
        conn = JiraConnector("test", "user@test.com", "token123", "SUP")
        assert conn.platform == "jira"
        assert conn.project_key == "SUP"
        assert "test.atlassian.net" in str(conn._client.base_url)
        conn.close()

    def test_servicenow_sets_platform(self) -> None:
        conn = ServiceNowConnector("test", "admin", "pass123")
        assert conn.platform == "servicenow"
        assert "test.service-now.com" in str(conn._client.base_url)
        conn.close()


# -- Zendesk connector method tests --


class TestZendeskConnector:
    def _make_connector(self) -> ZendeskConnector:
        conn = object.__new__(ZendeskConnector)
        conn.platform = "zendesk"
        conn._client = MagicMock()
        return conn

    def test_get_messages(self) -> None:
        conn = self._make_connector()
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.json.return_value = {
            "comments": [
                {"id": 1, "body": "Hello"},
                {"id": 2, "body": "Thanks"},
            ]
        }
        conn._client.request.return_value = mock_resp
        comments = conn.get_messages("123")
        assert len(comments) == 2
        assert comments[0]["body"] == "Hello"


# -- Jira ADF parsing tests --


class TestJiraADFParsing:
    def test_adf_to_text_simple(self) -> None:
        adf = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Hello "},
                        {"type": "text", "text": "world"},
                    ],
                }
            ],
        }
        assert JiraConnector._adf_to_text(adf) == "Hello  world"

    def test_adf_to_text_empty(self) -> None:
        assert JiraConnector._adf_to_text(None) == ""
        assert JiraConnector._adf_to_text({}) == ""

    def test_flatten_issue(self) -> None:
        issue = {
            "key": "SUP-42",
            "id": "10042",
            "fields": {
                "summary": "Login broken",
                "description": {"type": "doc", "version": 1, "content": []},
                "status": {"name": "Open"},
                "priority": {"name": "High"},
                "issuetype": {"name": "Bug"},
                "assignee": {"accountId": "abc"},
                "reporter": {"accountId": "def"},
                "created": "2026-01-01",
                "updated": "2026-01-02",
            },
        }
        flat = JiraConnector._flatten_issue(issue)
        assert flat["key"] == "SUP-42"
        assert flat["summary"] == "Login broken"
        assert flat["status"] == "Open"
        assert flat["priority"] == "High"
        assert flat["assignee_id"] == "abc"


# -- HubSpot flatten tests --


class TestHubSpotFlatten:
    def test_flatten_properties(self) -> None:
        record = {
            "id": "123",
            "properties": {
                "subject": "Test ticket",
                "content": "Details here",
            },
        }
        flat = HubSpotConnector._flatten_properties(record)
        assert flat["id"] == "123"
        assert flat["subject"] == "Test ticket"
        assert "properties" not in flat


# -- Field mapping tests for all platforms --


class TestPlatformMappings:
    def test_zendesk_ticket_mapping(self) -> None:
        records = [
            {
                "id": 42,
                "subject": "Help needed",
                "description": "Cannot login",
                "status": "open",
                "priority": "high",
                "via": {"channel": "email"},
                "requester_id": 12345,
            }
        ]
        result = apply_mappings(records, ZENDESK_TICKET_TO_TICKET)
        assert result[0]["id"] == 42
        assert result[0]["subject"] == "Help needed"
        assert result[0]["status"] == "open"
        assert result[0]["priority"] == "high"
        assert result[0]["channel"] == "email"

    def test_freshdesk_ticket_mapping(self) -> None:
        records = [
            {
                "id": 100,
                "subject": "Billing issue",
                "description_text": "Overcharged",
                "status": 2,
                "priority": 3,
                "source": "email",
                "requester_id": 999,
            }
        ]
        result = apply_mappings(records, FRESHDESK_TICKET_TO_TICKET)
        assert result[0]["status"] == "open"
        assert result[0]["priority"] == "high"

    def test_intercom_conversation_mapping(self) -> None:
        records = [
            {
                "id": "conv-1",
                "title": "Help please",
                "source": {"body": "I need assistance"},
                "state": "open",
                "priority": "high",
                "contacts": {"contacts": [{"id": "c-1"}]},
            }
        ]
        result = apply_mappings(records, INTERCOM_CONVERSATION_TO_TICKET)
        assert result[0]["subject"] == "Help please"
        assert result[0]["description"] == "I need assistance"

    def test_hubspot_ticket_mapping(self) -> None:
        records = [
            {
                "id": "h-1",
                "subject": "Support request",
                "content": "Details",
                "hs_pipeline_stage": "OPEN",
                "hs_ticket_priority": "High",
            }
        ]
        result = apply_mappings(records, HUBSPOT_TICKET_TO_TICKET)
        assert result[0]["status"] == "open"
        assert result[0]["priority"] == "high"

    def test_jira_issue_mapping(self) -> None:
        records = [
            {
                "key": "SUP-1",
                "summary": "Bug report",
                "description": "Steps to reproduce",
                "status": "Open",
                "priority": "Medium",
                "reporter_id": "user-1",
            }
        ]
        result = apply_mappings(records, JIRA_ISSUE_TO_TICKET)
        assert result[0]["id"] == "SUP-1"
        assert result[0]["subject"] == "Bug report"

    def test_servicenow_incident_mapping(self) -> None:
        records = [
            {
                "number": "INC001",
                "short_description": "Server down",
                "description": "Production server unresponsive",
                "state": 2,
                "priority": 1,
                "caller_id": "user-sys-id",
            }
        ]
        result = apply_mappings(records, SERVICENOW_INCIDENT_TO_TICKET)
        assert result[0]["id"] == "INC001"
        assert result[0]["status"] == "open"
        assert result[0]["priority"] == "urgent"

    def test_default_ticket_mappings_has_all_platforms(self) -> None:
        assert set(DEFAULT_TICKET_MAPPINGS.keys()) == {
            "salesforce",
            "zendesk",
            "freshdesk",
            "intercom",
            "hubspot",
            "jira",
            "servicenow",
        }

    def test_default_article_mappings(self) -> None:
        assert "salesforce" in DEFAULT_ARTICLE_MAPPINGS
        assert "zendesk" in DEFAULT_ARTICLE_MAPPINGS
        assert "servicenow" in DEFAULT_ARTICLE_MAPPINGS
