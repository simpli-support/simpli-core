"""Tests for data connectors: mapping, file parser, and Salesforce."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from simpli_core.connectors.file_parser import FileConnector
from simpli_core.connectors.mapping import (
    CASE_TO_TICKET,
    COMMENT_TO_MESSAGE,
    CONTACT_TO_CUSTOMER,
    KB_TO_ARTICLE,
    FieldMapping,
    apply_mappings,
)
from simpli_core.connectors.settings import SalesforceSettings


# -- FieldMapping tests --


class TestFieldMapping:
    def test_basic_mapping(self) -> None:
        mappings = [
            FieldMapping(source="Name", target="name"),
            FieldMapping(source="Email", target="email"),
        ]
        records = [{"Name": "Alice", "Email": "alice@example.com", "Extra": "ignored"}]
        result = apply_mappings(records, mappings)
        assert result == [{"name": "Alice", "email": "alice@example.com"}]

    def test_default_value(self) -> None:
        mappings = [
            FieldMapping(source="Missing", target="field", default="fallback"),
        ]
        result = apply_mappings([{"Other": "value"}], mappings)
        assert result == [{"field": "fallback"}]

    def test_transform_lower(self) -> None:
        mappings = [
            FieldMapping(source="Status", target="status", transform="lower"),
        ]
        result = apply_mappings([{"Status": "OPEN"}], mappings)
        assert result == [{"status": "open"}]

    def test_transform_upper(self) -> None:
        mappings = [
            FieldMapping(source="Code", target="code", transform="upper"),
        ]
        result = apply_mappings([{"Code": "abc"}], mappings)
        assert result == [{"code": "ABC"}]

    def test_transform_strip(self) -> None:
        mappings = [
            FieldMapping(source="Name", target="name", transform="strip"),
        ]
        result = apply_mappings([{"Name": "  Alice  "}], mappings)
        assert result == [{"name": "Alice"}]

    def test_transform_enum_priority(self) -> None:
        mappings = [
            FieldMapping(
                source="Priority", target="priority", transform="enum:Priority"
            ),
        ]
        result = apply_mappings([{"Priority": "High"}], mappings)
        assert result == [{"priority": "high"}]

    def test_transform_enum_ticket_status(self) -> None:
        mappings = [
            FieldMapping(
                source="Status", target="status", transform="enum:TicketStatus"
            ),
        ]
        result = apply_mappings([{"Status": "Open"}], mappings)
        assert result == [{"status": "open"}]

    def test_transform_enum_unknown_value_passthrough(self) -> None:
        mappings = [
            FieldMapping(
                source="Status", target="status", transform="enum:TicketStatus"
            ),
        ]
        result = apply_mappings([{"Status": "CustomStatus"}], mappings)
        assert result == [{"status": "CustomStatus"}]

    def test_transform_enum_unknown_class_passthrough(self) -> None:
        mappings = [
            FieldMapping(
                source="Val", target="val", transform="enum:NonExistentEnum"
            ),
        ]
        result = apply_mappings([{"Val": "test"}], mappings)
        assert result == [{"val": "test"}]

    def test_none_value_skips_transform(self) -> None:
        mappings = [
            FieldMapping(source="X", target="x", transform="lower"),
        ]
        result = apply_mappings([{"X": None}], mappings)
        assert result == [{"x": None}]

    def test_multiple_records(self) -> None:
        mappings = [FieldMapping(source="Id", target="id")]
        records = [{"Id": "1"}, {"Id": "2"}, {"Id": "3"}]
        result = apply_mappings(records, mappings)
        assert len(result) == 3
        assert result[2] == {"id": "3"}

    def test_empty_records(self) -> None:
        mappings = [FieldMapping(source="Id", target="id")]
        assert apply_mappings([], mappings) == []


class TestDefaultMappings:
    def test_case_to_ticket_fields(self) -> None:
        assert len(CASE_TO_TICKET) == 10
        targets = {m.target for m in CASE_TO_TICKET}
        assert "id" in targets
        assert "subject" in targets
        assert "priority" in targets
        assert "created_at" in targets
        assert "closed_at" in targets
        assert "assigned_to" in targets

    def test_contact_to_customer_fields(self) -> None:
        assert len(CONTACT_TO_CUSTOMER) == 6
        targets = {m.target for m in CONTACT_TO_CUSTOMER}
        assert "name" in targets
        assert "email" in targets
        assert "phone" in targets
        assert "company" in targets
        assert "account_type" in targets

    def test_comment_to_message_fields(self) -> None:
        assert len(COMMENT_TO_MESSAGE) == 3

    def test_kb_to_article_fields(self) -> None:
        assert len(KB_TO_ARTICLE) == 6
        targets = {m.target for m in KB_TO_ARTICLE}
        assert "published_at" in targets

    def test_case_to_ticket_applies_correctly(self) -> None:
        record = {
            "CaseNumber": "00001",
            "Subject": "Help",
            "Description": "Need help",
            "Status": "Open",
            "Priority": "High",
            "Origin": "Email",
            "ContactId": "003xx",
            "CreatedDate": "2025-01-01T00:00:00Z",
            "ClosedDate": None,
            "OwnerId": "005xx",
        }
        result = apply_mappings([record], CASE_TO_TICKET)
        assert result[0]["id"] == "00001"
        assert result[0]["created_at"] == "2025-01-01T00:00:00Z"
        assert result[0]["assigned_to"] == "005xx"

    def test_contact_to_customer_nested_account(self) -> None:
        record = {
            "Id": "003xx",
            "Name": "Alice",
            "Email": "alice@co.com",
            "Phone": "+1234567890",
            "Account": {"Name": "Acme Corp", "Type": "Customer"},
        }
        result = apply_mappings([record], CONTACT_TO_CUSTOMER)
        assert result[0]["phone"] == "+1234567890"
        assert result[0]["company"] == "Acme Corp"
        assert result[0]["account_type"] == "Customer"


# -- FileConnector tests --


class TestFileConnectorCSV:
    def test_parse_csv_from_path(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("name,email\nAlice,alice@test.com\nBob,bob@test.com\n")
        records = FileConnector.parse(csv_file)
        assert len(records) == 2
        assert records[0]["name"] == "Alice"
        assert records[1]["email"] == "bob@test.com"

    def test_parse_csv_from_string_path(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("id,value\n1,hello\n")
        records = FileConnector.parse(str(csv_file))
        assert records == [{"id": "1", "value": "hello"}]


class TestFileConnectorJSON:
    def test_parse_json_array(self, tmp_path: Path) -> None:
        json_file = tmp_path / "data.json"
        json_file.write_text(json.dumps([{"id": "1"}, {"id": "2"}]))
        records = FileConnector.parse(json_file)
        assert len(records) == 2

    def test_parse_json_with_data_wrapper(self, tmp_path: Path) -> None:
        json_file = tmp_path / "data.json"
        json_file.write_text(json.dumps({"data": [{"id": "1"}]}))
        records = FileConnector.parse(json_file)
        assert records == [{"id": "1"}]

    def test_parse_json_with_records_wrapper(self, tmp_path: Path) -> None:
        json_file = tmp_path / "data.json"
        json_file.write_text(json.dumps({"records": [{"id": "1"}]}))
        records = FileConnector.parse(json_file)
        assert records == [{"id": "1"}]

    def test_parse_json_invalid_structure(self, tmp_path: Path) -> None:
        json_file = tmp_path / "data.json"
        json_file.write_text(json.dumps({"foo": "bar"}))
        with pytest.raises(ValueError, match="JSON must be a list"):
            FileConnector.parse(json_file)


class TestFileConnectorJSONL:
    def test_parse_jsonl(self, tmp_path: Path) -> None:
        jsonl_file = tmp_path / "data.jsonl"
        jsonl_file.write_text('{"id": "1"}\n{"id": "2"}\n')
        records = FileConnector.parse(jsonl_file)
        assert len(records) == 2
        assert records[0]["id"] == "1"

    def test_parse_jsonl_with_blank_lines(self, tmp_path: Path) -> None:
        jsonl_file = tmp_path / "data.jsonl"
        jsonl_file.write_text('{"id": "1"}\n\n{"id": "2"}\n\n')
        records = FileConnector.parse(jsonl_file)
        assert len(records) == 2


class TestFileConnectorFormatDetection:
    def test_detect_from_path(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b\n1,2\n")
        records = FileConnector.parse(csv_file)
        assert len(records) == 1

    def test_unknown_extension_raises(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "data.xyz"
        bad_file.write_text("stuff")
        with pytest.raises(ValueError, match="Cannot detect format"):
            FileConnector.parse(bad_file)

    def test_explicit_format_override(self, tmp_path: Path) -> None:
        # File has .txt extension but we tell it to parse as CSV
        txt_file = tmp_path / "data.txt"
        txt_file.write_text("x,y\n1,2\n")
        records = FileConnector.parse(txt_file, format="csv")
        assert records == [{"x": "1", "y": "2"}]

    def test_unsupported_format_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Unsupported format"):
            FileConnector.parse(tmp_path / "x.csv", format="xml")


class TestFileConnectorExcel:
    def test_excel_import_error(self, tmp_path: Path) -> None:
        xlsx_file = tmp_path / "data.xlsx"
        xlsx_file.write_bytes(b"fake")
        with pytest.raises(ImportError, match="openpyxl"):
            # Mock openpyxl as unavailable
            with patch.dict("sys.modules", {"openpyxl": None}):
                FileConnector.parse(xlsx_file)


class TestFileConnectorParquet:
    def test_parquet_import_error(self, tmp_path: Path) -> None:
        pq_file = tmp_path / "data.parquet"
        pq_file.write_bytes(b"fake")
        with pytest.raises(ImportError, match="pyarrow"):
            with patch.dict("sys.modules", {"pyarrow": None, "pyarrow.parquet": None}):
                FileConnector.parse(pq_file)


# -- SalesforceConnector tests --


class TestSalesforceConnector:
    """Tests for the hardened SalesforceConnector."""

    def _make_connector(self) -> "SalesforceConnector":
        """Create a SalesforceConnector without calling __init__."""
        from simpli_core.connectors.salesforce import SalesforceConnector

        connector = object.__new__(SalesforceConnector)
        connector.instance_url = "https://test.salesforce.com"
        connector.sf = MagicMock()
        connector._client = MagicMock()  # Mock the inherited httpx client
        return connector

    def test_salesforce_import_error(self) -> None:
        with patch.dict(
            "sys.modules", {"simple_salesforce": None}
        ), pytest.raises(ImportError, match="simple-salesforce"):
            from simpli_core.connectors.salesforce import SalesforceConnector

            SalesforceConnector(
                instance_url="https://test.salesforce.com",
                client_id="id",
                client_secret="secret",
            )

    def test_configuration_error_empty_url(self) -> None:
        from simpli_core.connectors.errors import ConfigurationError
        from simpli_core.connectors.salesforce import SalesforceConnector

        with pytest.raises(ConfigurationError, match="instance_url"):
            SalesforceConnector(
                instance_url="",
                client_id="id",
                client_secret="secret",
            )

    def test_configuration_error_empty_client_id(self) -> None:
        from simpli_core.connectors.errors import ConfigurationError
        from simpli_core.connectors.salesforce import SalesforceConnector

        with pytest.raises(ConfigurationError, match="client_id"):
            SalesforceConnector(
                instance_url="https://test.salesforce.com",
                client_id="",
                client_secret="secret",
            )

    def test_configuration_error_empty_secret(self) -> None:
        from simpli_core.connectors.errors import ConfigurationError
        from simpli_core.connectors.salesforce import SalesforceConnector

        with pytest.raises(ConfigurationError, match="client_secret"):
            SalesforceConnector(
                instance_url="https://test.salesforce.com",
                client_id="id",
                client_secret="",
            )

    def test_query_strips_attributes(self) -> None:
        connector = self._make_connector()
        connector.sf.query_all.return_value = {
            "records": [
                {"Id": "1", "Name": "Test", "attributes": {"type": "Case"}},
                {"Id": "2", "Name": "Test2", "attributes": {"type": "Case"}},
            ]
        }

        results = connector.query("SELECT Id, Name FROM Case")
        assert len(results) == 2
        assert "attributes" not in results[0]
        assert results[0]["Id"] == "1"

    def test_query_wraps_exceptions(self) -> None:
        from simpli_core.connectors.errors import PlatformAPIError

        connector = self._make_connector()
        connector.sf.query_all.side_effect = Exception("SOQL syntax error")

        with pytest.raises(PlatformAPIError, match="SOQL query failed"):
            connector.query("SELECT Bad FROM Nothing")

    def test_query_empty_results(self) -> None:
        connector = self._make_connector()
        connector.sf.query_all.return_value = {"records": []}

        results = connector.query("SELECT Id FROM Case")
        assert results == []

    def test_get_cases_builds_soql(self) -> None:
        connector = self._make_connector()
        connector.sf.query_all.return_value = {"records": []}

        connector.get_cases(where="Status = 'Open'", limit=50)
        soql = connector.sf.query_all.call_args[0][0]
        assert "FROM Case" in soql
        assert "WHERE Status = 'Open'" in soql
        assert "LIMIT 50" in soql

    def test_get_cases_no_where(self) -> None:
        connector = self._make_connector()
        connector.sf.query_all.return_value = {"records": []}

        connector.get_cases()
        soql = connector.sf.query_all.call_args[0][0]
        assert "WHERE" not in soql
        assert "LIMIT 100" in soql

    def test_get_cases_includes_timestamps_and_owner(self) -> None:
        connector = self._make_connector()
        connector.sf.query_all.return_value = {"records": []}

        connector.get_cases()
        soql = connector.sf.query_all.call_args[0][0]
        assert "CreatedDate" in soql
        assert "ClosedDate" in soql
        assert "OwnerId" in soql

    def test_get_tickets_is_alias(self) -> None:
        connector = self._make_connector()
        connector.sf.query_all.return_value = {"records": []}

        connector.get_tickets(where="Status = 'New'", limit=5)
        soql = connector.sf.query_all.call_args[0][0]
        assert "FROM Case" in soql
        assert "LIMIT 5" in soql

    def test_get_customers_is_alias(self) -> None:
        connector = self._make_connector()
        connector.sf.query_all.return_value = {"records": []}

        connector.get_customers(limit=25)
        soql = connector.sf.query_all.call_args[0][0]
        assert "FROM Contact" in soql
        assert "LIMIT 25" in soql

    def test_get_contacts_includes_phone_and_account(self) -> None:
        connector = self._make_connector()
        connector.sf.query_all.return_value = {"records": []}

        connector.get_contacts()
        soql = connector.sf.query_all.call_args[0][0]
        assert "Phone" in soql
        assert "Account.Name" in soql
        assert "Account.Type" in soql

    def test_get_messages_is_alias(self) -> None:
        connector = self._make_connector()
        connector.sf.query_all.return_value = {"records": []}

        connector.get_messages("001xx")
        soql = connector.sf.query_all.call_args[0][0]
        assert "CaseComment" in soql
        assert "001xx" in soql

    def test_get_articles_is_alias(self) -> None:
        connector = self._make_connector()
        connector.sf.query_all.return_value = {"records": []}

        connector.get_articles(limit=10)
        soql = connector.sf.query_all.call_args[0][0]
        assert "Knowledge__kav" in soql
        assert "LIMIT 10" in soql

    def test_get_kb_articles_builds_soql(self) -> None:
        connector = self._make_connector()
        connector.sf.query_all.return_value = {"records": []}

        connector.get_kb_articles(limit=10)
        soql = connector.sf.query_all.call_args[0][0]
        assert "Knowledge__kav" in soql
        assert "LIMIT 10" in soql

    def test_close_calls_super(self) -> None:
        connector = self._make_connector()
        connector.close()
        connector._client.close.assert_called_once()

    # -- SOQL injection tests --

    def test_sanitize_soql_escapes_quotes(self) -> None:
        from simpli_core.connectors.salesforce import _sanitize_soql_value

        assert _sanitize_soql_value("test'value") == "test\\'value"
        assert _sanitize_soql_value("normal") == "normal"
        assert _sanitize_soql_value("a'b'c") == "a\\'b\\'c"

    def test_sanitize_soql_strips_control_chars(self) -> None:
        from simpli_core.connectors.salesforce import _sanitize_soql_value

        assert _sanitize_soql_value("test\x00value") == "testvalue"
        assert _sanitize_soql_value("test\nvalue") == "testvalue"

    def test_get_case_comments_sanitizes_id(self) -> None:
        connector = self._make_connector()
        connector.sf.query_all.return_value = {"records": []}

        # Attempt injection via case_id
        connector.get_case_comments("001xx' OR Id != '")
        soql = connector.sf.query_all.call_args[0][0]
        # The single quotes should be escaped
        assert "001xx\\' OR Id != \\'" in soql

    def test_get_feed_items_sanitizes_id(self) -> None:
        connector = self._make_connector()
        connector.sf.query_all.return_value = {"records": []}

        connector.get_feed_items("001xx' OR Id != '")
        soql = connector.sf.query_all.call_args[0][0]
        assert "001xx\\' OR Id != \\'" in soql

    # -- Write method tests --

    def test_update_case(self) -> None:
        connector = self._make_connector()
        connector.sf.Case.update.return_value = None
        connector.sf.Case.get.return_value = {
            "Id": "500xx",
            "Status": "Closed",
        }

        result = connector.update_case("500xx", {"Status": "Closed"})
        connector.sf.Case.update.assert_called_once_with(
            "500xx", {"Status": "Closed"}
        )
        assert result["Status"] == "Closed"

    def test_update_ticket_is_alias(self) -> None:
        connector = self._make_connector()
        connector.sf.Case.update.return_value = None
        connector.sf.Case.get.return_value = {"Id": "500xx"}

        connector.update_ticket("500xx", {"Priority": "High"})
        connector.sf.Case.update.assert_called_once_with(
            "500xx", {"Priority": "High"}
        )

    def test_update_case_wraps_errors(self) -> None:
        from simpli_core.connectors.errors import PlatformAPIError

        connector = self._make_connector()
        connector.sf.Case.update.side_effect = Exception("Not found")

        with pytest.raises(PlatformAPIError, match="Failed to update case"):
            connector.update_case("bad_id", {"Status": "Closed"})

    def test_add_case_comment(self) -> None:
        connector = self._make_connector()
        connector.sf.CaseComment.create.return_value = {
            "id": "comment-1",
            "success": True,
        }

        result = connector.add_case_comment(
            "500xx", "Fixed the issue", is_published=True
        )
        connector.sf.CaseComment.create.assert_called_once_with(
            {
                "ParentId": "500xx",
                "CommentBody": "Fixed the issue",
                "IsPublished": True,
            }
        )
        assert result["success"] is True

    def test_add_case_comment_wraps_errors(self) -> None:
        from simpli_core.connectors.errors import PlatformAPIError

        connector = self._make_connector()
        connector.sf.CaseComment.create.side_effect = Exception("API error")

        with pytest.raises(PlatformAPIError, match="Failed to add comment"):
            connector.add_case_comment("500xx", "text")


# -- SalesforceSettings tests --


class TestSalesforceSettings:
    def test_defaults_are_empty(self) -> None:
        settings = SalesforceSettings()
        assert settings.salesforce_instance_url == ""
        assert settings.salesforce_client_id == ""
        assert settings.salesforce_client_secret == ""

    def test_values_set(self) -> None:
        settings = SalesforceSettings(
            salesforce_instance_url="https://myorg.salesforce.com",
            salesforce_client_id="client-123",
            salesforce_client_secret="secret-456",
        )
        assert settings.salesforce_instance_url == "https://myorg.salesforce.com"
        assert settings.salesforce_client_id == "client-123"
