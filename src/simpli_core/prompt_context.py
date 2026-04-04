"""Utilities for building LLM prompt context from records with custom fields."""

from __future__ import annotations

from typing import Any

_DEFAULT_PRIMARY_FIELDS = ["subject", "description", "body", "content", "text"]


def build_record_context(
    record: dict[str, Any],
    *,
    primary_fields: list[str] | None = None,
    include_custom: bool = True,
    max_custom_fields: int = 20,
) -> str:
    """Build a text block from a record dict for inclusion in LLM prompts.

    *primary_fields* are rendered first with their values. Remaining
    top-level keys (excluding ``custom_fields``) are appended as extra
    context. If *include_custom* is ``True``, the ``custom_fields`` dict
    is formatted as an "Additional Context" section.

    Returns a plain-text string suitable for embedding in a user message.
    """
    fields = primary_fields or _DEFAULT_PRIMARY_FIELDS
    lines: list[str] = []

    # Primary fields
    for field in fields:
        value = record.get(field)
        if value:
            label = field.replace("_", " ").title()
            lines.append(f"{label}: {value}")

    # Other standard fields (skip primary, custom_fields, and None values)
    skip = set(fields) | {"custom_fields"}
    for key, value in record.items():
        if key in skip or value is None:
            continue
        label = key.replace("_", " ").title()
        lines.append(f"{label}: {value}")

    # Custom fields
    if include_custom:
        custom = record.get("custom_fields")
        if custom and isinstance(custom, dict):
            cf_items = list(custom.items())[:max_custom_fields]
            if cf_items:
                lines.append("")
                lines.append("Additional Context:")
                for key, value in cf_items:
                    label = key.replace("__c", "").replace("_", " ").strip().title()
                    lines.append(f"  {label}: {value}")

    return "\n".join(lines)
