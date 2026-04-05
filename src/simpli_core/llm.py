"""Shared LLM utilities for consistent JSON parsing and call patterns."""

from __future__ import annotations

import json
from typing import Any


def parse_llm_json(raw: str) -> dict[str, Any]:
    """Extract and parse JSON from LLM output.

    Handles common LLM output quirks:
    - Markdown code fences (```json ... ```)
    - Leading/trailing text around JSON
    - Nested brace matching

    Raises ``ValueError`` if no valid JSON is found.
    """
    text = raw.strip()

    # Strip markdown fences
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3].strip()

    # Try direct parse first
    try:
        return json.loads(text)  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        pass

    # Find JSON object within text
    start = text.find("{")
    if start == -1:
        msg = "No JSON object found in LLM output"
        raise ValueError(msg)

    # Find matching closing brace
    depth = 0
    end = start
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    candidate = text[start:end]
    try:
        return json.loads(candidate)  # type: ignore[no-any-return]
    except json.JSONDecodeError as exc:
        msg = f"Failed to parse JSON from LLM output: {exc}"
        raise ValueError(msg) from exc


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert LLM output to int."""
    if isinstance(value, int):
        return value
    try:
        return int(float(str(value)))
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert LLM output to float."""
    if isinstance(value, float):
        return value
    try:
        return float(str(value))
    except (ValueError, TypeError):
        return default
