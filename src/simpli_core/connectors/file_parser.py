"""Multi-format file parser for data ingestion."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any, BinaryIO, ClassVar


class FileConnector:
    """Parse uploaded files into lists of dictionaries.

    Supports CSV, JSON, and JSONL out of the box. Excel (.xlsx) and
    Parquet require optional extras (openpyxl and pyarrow respectively).
    """

    SUPPORTED_FORMATS: ClassVar[set[str]] = {
        "csv",
        "json",
        "jsonl",
        "xlsx",
        "parquet",
    }

    @staticmethod
    def parse(
        file: BinaryIO | Path | str,
        fmt: str | None = None,
    ) -> list[dict[str, Any]]:
        """Parse a file into a list of dictionaries.

        Args:
            file: A file-like object (binary mode) or a path to a file.
            fmt: File format. Auto-detected from extension if not given.
                 One of: csv, json, jsonl, xlsx, parquet.

        Returns:
            List of dictionaries, one per record.
        """
        if fmt is None:
            fmt = FileConnector._detect_format(file)

        if fmt == "csv":
            return FileConnector._parse_csv(file)
        if fmt == "json":
            return FileConnector._parse_json(file)
        if fmt == "jsonl":
            return FileConnector._parse_jsonl(file)
        if fmt == "xlsx":
            return FileConnector._parse_excel(file)
        if fmt == "parquet":
            return FileConnector._parse_parquet(file)

        msg = f"Unsupported format: {fmt}"
        raise ValueError(msg)

    @staticmethod
    def _detect_format(file: BinaryIO | Path | str) -> str:
        """Detect file format from filename/path."""
        if isinstance(file, str | Path):
            suffix = Path(file).suffix.lower().lstrip(".")
            if suffix in FileConnector.SUPPORTED_FORMATS:
                return suffix
            msg = f"Cannot detect format from extension: .{suffix}"
            raise ValueError(msg)

        name = getattr(file, "name", "") or getattr(file, "filename", "")
        if name:
            suffix = Path(name).suffix.lower().lstrip(".")
            if suffix in FileConnector.SUPPORTED_FORMATS:
                return suffix

        msg = "Cannot detect format — please specify format explicitly"
        raise ValueError(msg)

    @staticmethod
    def _read_text(file: BinaryIO | Path | str) -> str:
        """Read file content as text."""
        if isinstance(file, str | Path):
            return Path(file).read_text(encoding="utf-8")
        data = file.read()
        if isinstance(data, bytes):
            return data.decode("utf-8")
        return data  # pragma: no cover

    @staticmethod
    def _read_bytes(file: BinaryIO | Path | str) -> bytes:
        """Read file content as bytes."""
        if isinstance(file, str | Path):
            return Path(file).read_bytes()
        data = file.read()
        if isinstance(data, str):
            return data.encode("utf-8")
        return data  # pragma: no cover

    @staticmethod
    def _parse_csv(file: BinaryIO | Path | str) -> list[dict[str, Any]]:
        text = FileConnector._read_text(file)
        reader = csv.DictReader(io.StringIO(text))
        return list(reader)

    @staticmethod
    def _parse_json(file: BinaryIO | Path | str) -> list[dict[str, Any]]:
        text = FileConnector._read_text(file)
        data = json.loads(text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # Support {"data": [...]} or {"records": [...]} wrappers
            for key in ("data", "records", "items", "results"):
                if key in data and isinstance(data[key], list):
                    return data[key]  # type: ignore[no-any-return]
        msg = "JSON must be a list of objects or contain a data/records array"
        raise ValueError(msg)

    @staticmethod
    def _parse_jsonl(file: BinaryIO | Path | str) -> list[dict[str, Any]]:
        text = FileConnector._read_text(file)
        records: list[dict[str, Any]] = []
        for line in text.strip().splitlines():
            line = line.strip()
            if line:
                records.append(json.loads(line))
        return records

    @staticmethod
    def _parse_excel(file: BinaryIO | Path | str) -> list[dict[str, Any]]:
        try:
            import openpyxl  # type: ignore[import-untyped,unused-ignore]
        except ImportError:
            msg = (
                "Excel support requires openpyxl. "
                "Install with: pip install simpli-core[excel]"
            )
            raise ImportError(msg) from None

        data = FileConnector._read_bytes(file)
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True)
        ws = wb.active
        if ws is None:
            return []

        rows = list(ws.iter_rows(values_only=True))
        if len(rows) < 2:
            return []

        headers = [
            str(h) if h is not None else f"col_{i}" for i, h in enumerate(rows[0])
        ]
        records: list[dict[str, Any]] = []
        for row in rows[1:]:
            record = dict(zip(headers, row, strict=False))
            records.append(record)
        wb.close()
        return records

    @staticmethod
    def _parse_parquet(file: BinaryIO | Path | str) -> list[dict[str, Any]]:
        try:
            import pyarrow.parquet as pq  # type: ignore[import-untyped,unused-ignore]
        except ImportError:
            msg = (
                "Parquet support requires pyarrow. "
                "Install with: pip install simpli-core[parquet]"
            )
            raise ImportError(msg) from None

        if isinstance(file, str | Path):
            table = pq.read_table(str(file))
        else:
            data = file.read()
            table = pq.read_table(io.BytesIO(data))
        return table.to_pydict()  # type: ignore[no-any-return]
