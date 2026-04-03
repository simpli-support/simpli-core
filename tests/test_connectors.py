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
        assert len(CASE_TO_TICKET) == 7
        targets = {m.target for m in CASE_TO_TICKET}
        assert "id" in targets
        assert "subject" in targets
        assert "priority" in targets

    def test_contact_to_customer_fields(self) -> None:
        assert len(CONTACT_TO_CUSTOMER) == 3
        targets = {m.target for m in CONTACT_TO_CUSTOMER}
        assert "name" in targets
        assert "email" in targets

    def test_comment_to_message_fields(self) -> None:
        assert len(COMMENT_TO_MESSAGE) == 3

    def test_kb_to_article_fields(self) -> None:
        assert len(KB_TO_ARTICLE) == 5


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

    def test_connector_strips_trailing_slash(self) -> None:
        from simpli_core.connectors.salesforce import SalesforceConnector

        connector = object.__new__(SalesforceConnector)
        connector.instance_url = "https://test.salesforce.com/"
        connector.instance_url = connector.instance_url.rstrip("/")
        assert connector.instance_url == "https://test.salesforce.com"

    def test_query_strips_attributes(self) -> None:
        from simpli_core.connectors.salesforce import SalesforceConnector

        connector = object.__new__(SalesforceConnector)
        connector.sf = MagicMock()
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

    def test_get_cases_builds_soql(self) -> None:
        from simpli_core.connectors.salesforce import SalesforceConnector

        connector = object.__new__(SalesforceConnector)
        connector.sf = MagicMock()
        connector.sf.query_all.return_value = {"records": []}

        connector.get_cases(where="Status = 'Open'", limit=50)
        soql = connector.sf.query_all.call_args[0][0]
        assert "FROM Case" in soql
        assert "WHERE Status = 'Open'" in soql
        assert "LIMIT 50" in soql

    def test_get_cases_no_where(self) -> None:
        from simpli_core.connectors.salesforce import SalesforceConnector

        connector = object.__new__(SalesforceConnector)
        connector.sf = MagicMock()
        connector.sf.query_all.return_value = {"records": []}

        connector.get_cases()
        soql = connector.sf.query_all.call_args[0][0]
        assert "WHERE" not in soql
        assert "LIMIT 100" in soql

    def test_get_kb_articles_builds_soql(self) -> None:
        from simpli_core.connectors.salesforce import SalesforceConnector

        connector = object.__new__(SalesforceConnector)
        connector.sf = MagicMock()
        connector.sf.query_all.return_value = {"records": []}

        connector.get_kb_articles(limit=10)
        soql = connector.sf.query_all.call_args[0][0]
        assert "Knowledge__kav" in soql
        assert "LIMIT 10" in soql


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
