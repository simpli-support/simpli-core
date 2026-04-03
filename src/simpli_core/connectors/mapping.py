"""Field mapping and transformation engine for data ingestion."""

from __future__ import annotations

import importlib
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class FieldMapping(BaseModel):
    """Maps a source field to a target field with optional transformation."""

    model_config = ConfigDict(extra="forbid")

    source: str
    target: str
    transform: str | None = None
    default: Any = None


def _resolve_enum(enum_path: str, value: str) -> str:
    """Resolve a value through a StrEnum.

    enum_path is like "Priority" or "TicketStatus" — looked up in simpli_core.models.
    Salesforce values like "High" are lowercased to match enum values.
    """
    mod = importlib.import_module("simpli_core.models")
    enum_cls = getattr(mod, enum_path, None)
    if enum_cls is None or not issubclass(enum_cls, StrEnum):
        return value

    lowered = value.strip().lower()
    for member in enum_cls:
        if member.value == lowered:
            return member.value
    return value


def _get_nested(record: dict[str, Any], key: str, default: Any = None) -> Any:
    """Get a value from a nested dict using dot notation.

    ``_get_nested({"via": {"channel": "email"}}, "via.channel")`` → ``"email"``
    Falls back to flat key lookup first for backwards compatibility.
    """
    # Try flat key first (handles keys that literally contain dots)
    if key in record:
        return record[key]

    parts = key.split(".")
    current: Any = record
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
            if current is None:
                return default
        else:
            return default
    return current


# -- Freshdesk integer status/priority mappings --

_FRESHDESK_STATUS_MAP: dict[str, str] = {
    "2": "open",
    "3": "pending",
    "4": "solved",
    "5": "closed",
}

_FRESHDESK_PRIORITY_MAP: dict[str, str] = {
    "1": "low",
    "2": "medium",
    "3": "high",
    "4": "urgent",
}

# -- ServiceNow integer state mapping --

_SERVICENOW_STATE_MAP: dict[str, str] = {
    "1": "new",
    "2": "open",
    "3": "pending",
    "6": "solved",
    "7": "closed",
}

_SERVICENOW_PRIORITY_MAP: dict[str, str] = {
    "1": "urgent",
    "2": "high",
    "3": "medium",
    "4": "low",
}


def _apply_transform(value: Any, transform: str) -> Any:
    """Apply a single transform to a value."""
    if value is None:
        return value

    str_val = str(value)

    if transform == "lower":
        return str_val.lower()
    if transform == "upper":
        return str_val.upper()
    if transform == "strip":
        return str_val.strip()
    if transform.startswith("enum:"):
        enum_name = transform[5:]
        return _resolve_enum(enum_name, str_val)
    if transform == "freshdesk_status":
        return _FRESHDESK_STATUS_MAP.get(str_val, str_val)
    if transform == "freshdesk_priority":
        return _FRESHDESK_PRIORITY_MAP.get(str_val, str_val)
    if transform == "servicenow_state":
        return _SERVICENOW_STATE_MAP.get(str_val, str_val)
    if transform == "servicenow_priority":
        return _SERVICENOW_PRIORITY_MAP.get(str_val, str_val)

    return value


def apply_mappings(
    records: list[dict[str, Any]],
    mappings: list[FieldMapping],
) -> list[dict[str, Any]]:
    """Transform a list of raw records using field mappings.

    Each record is transformed by extracting source fields, applying
    transforms, and writing to target fields. Fields not covered by
    mappings are dropped.
    """
    results: list[dict[str, Any]] = []
    for record in records:
        mapped: dict[str, Any] = {}
        for m in mappings:
            value = _get_nested(record, m.source, m.default)
            if m.transform and value is not None:
                value = _apply_transform(value, m.transform)
            mapped[m.target] = value
        results.append(mapped)
    return results


# -- Default Salesforce → Simpli field mappings --

CASE_TO_TICKET: list[FieldMapping] = [
    FieldMapping(source="CaseNumber", target="id"),
    FieldMapping(source="Subject", target="subject"),
    FieldMapping(source="Description", target="description", default=""),
    FieldMapping(
        source="Status", target="status", transform="enum:TicketStatus"
    ),
    FieldMapping(
        source="Priority", target="priority", transform="enum:Priority"
    ),
    FieldMapping(
        source="Origin", target="channel", transform="enum:Channel"
    ),
    FieldMapping(source="ContactId", target="customer_id", default="unknown"),
    FieldMapping(source="CreatedDate", target="created_at"),
    FieldMapping(source="ClosedDate", target="closed_at"),
    FieldMapping(source="OwnerId", target="assigned_to"),
]

CONTACT_TO_CUSTOMER: list[FieldMapping] = [
    FieldMapping(source="Id", target="id"),
    FieldMapping(source="Name", target="name"),
    FieldMapping(source="Email", target="email"),
    FieldMapping(source="Phone", target="phone"),
    FieldMapping(source="Account.Name", target="company"),
    FieldMapping(source="Account.Type", target="account_type"),
]

COMMENT_TO_MESSAGE: list[FieldMapping] = [
    FieldMapping(source="Id", target="id"),
    FieldMapping(source="CommentBody", target="body"),
    FieldMapping(source="CreatedById", target="author_id"),
]

KB_TO_ARTICLE: list[FieldMapping] = [
    FieldMapping(source="Id", target="id"),
    FieldMapping(source="Title", target="title"),
    FieldMapping(source="Summary", target="summary"),
    FieldMapping(source="ArticleBody", target="body"),
    FieldMapping(source="UrlName", target="slug"),
    FieldMapping(source="LastPublishedDate", target="published_at"),
]


# -- Default Zendesk → Simpli field mappings --

ZENDESK_TICKET_TO_TICKET: list[FieldMapping] = [
    FieldMapping(source="id", target="id"),
    FieldMapping(source="subject", target="subject"),
    FieldMapping(source="description", target="description", default=""),
    FieldMapping(
        source="status", target="status", transform="enum:TicketStatus"
    ),
    FieldMapping(
        source="priority", target="priority", transform="enum:Priority"
    ),
    FieldMapping(
        source="via.channel", target="channel", transform="enum:Channel"
    ),
    FieldMapping(source="requester_id", target="customer_id"),
]

ZENDESK_COMMENT_TO_MESSAGE: list[FieldMapping] = [
    FieldMapping(source="id", target="id"),
    FieldMapping(source="body", target="body"),
    FieldMapping(source="author_id", target="author_id"),
]

ZENDESK_ARTICLE_TO_ARTICLE: list[FieldMapping] = [
    FieldMapping(source="id", target="id"),
    FieldMapping(source="title", target="title"),
    FieldMapping(source="body", target="body"),
    FieldMapping(source="name", target="slug"),
]


# -- Default Freshdesk → Simpli field mappings --

FRESHDESK_TICKET_TO_TICKET: list[FieldMapping] = [
    FieldMapping(source="id", target="id"),
    FieldMapping(source="subject", target="subject"),
    FieldMapping(
        source="description_text", target="description", default=""
    ),
    FieldMapping(
        source="status", target="status", transform="freshdesk_status"
    ),
    FieldMapping(
        source="priority", target="priority", transform="freshdesk_priority"
    ),
    FieldMapping(source="source", target="channel", transform="enum:Channel"),
    FieldMapping(source="requester_id", target="customer_id"),
]


# -- Default Intercom → Simpli field mappings --

INTERCOM_CONVERSATION_TO_TICKET: list[FieldMapping] = [
    FieldMapping(source="id", target="id"),
    FieldMapping(source="title", target="subject", default="(no subject)"),
    FieldMapping(source="source.body", target="description", default=""),
    FieldMapping(source="state", target="status", transform="enum:TicketStatus"),
    FieldMapping(source="priority", target="priority", transform="enum:Priority"),
    FieldMapping(source="contacts.contacts.0.id", target="customer_id", default="unknown"),
]


# -- Default HubSpot → Simpli field mappings --

HUBSPOT_TICKET_TO_TICKET: list[FieldMapping] = [
    FieldMapping(source="id", target="id"),
    FieldMapping(source="subject", target="subject", default="(no subject)"),
    FieldMapping(source="content", target="description", default=""),
    FieldMapping(
        source="hs_pipeline_stage", target="status", transform="lower"
    ),
    FieldMapping(
        source="hs_ticket_priority", target="priority", transform="enum:Priority"
    ),
]


# -- Default Jira → Simpli field mappings --

JIRA_ISSUE_TO_TICKET: list[FieldMapping] = [
    FieldMapping(source="key", target="id"),
    FieldMapping(source="summary", target="subject"),
    FieldMapping(source="description", target="description", default=""),
    FieldMapping(
        source="status", target="status", transform="enum:TicketStatus"
    ),
    FieldMapping(
        source="priority", target="priority", transform="enum:Priority"
    ),
    FieldMapping(source="reporter_id", target="customer_id", default="unknown"),
]


# -- Default ServiceNow → Simpli field mappings --

SERVICENOW_INCIDENT_TO_TICKET: list[FieldMapping] = [
    FieldMapping(source="number", target="id"),
    FieldMapping(source="short_description", target="subject"),
    FieldMapping(source="description", target="description", default=""),
    FieldMapping(
        source="state", target="status", transform="servicenow_state"
    ),
    FieldMapping(
        source="priority", target="priority", transform="servicenow_priority"
    ),
    FieldMapping(source="caller_id", target="customer_id", default="unknown"),
]

SERVICENOW_KB_TO_ARTICLE: list[FieldMapping] = [
    FieldMapping(source="sys_id", target="id"),
    FieldMapping(source="short_description", target="title"),
    FieldMapping(source="text", target="body"),
    FieldMapping(source="number", target="slug"),
]


# -- Platform → default ticket mappings lookup --

DEFAULT_TICKET_MAPPINGS: dict[str, list[FieldMapping]] = {
    "salesforce": CASE_TO_TICKET,
    "zendesk": ZENDESK_TICKET_TO_TICKET,
    "freshdesk": FRESHDESK_TICKET_TO_TICKET,
    "intercom": INTERCOM_CONVERSATION_TO_TICKET,
    "hubspot": HUBSPOT_TICKET_TO_TICKET,
    "jira": JIRA_ISSUE_TO_TICKET,
    "servicenow": SERVICENOW_INCIDENT_TO_TICKET,
}

DEFAULT_ARTICLE_MAPPINGS: dict[str, list[FieldMapping]] = {
    "salesforce": KB_TO_ARTICLE,
    "zendesk": ZENDESK_ARTICLE_TO_ARTICLE,
    "servicenow": SERVICENOW_KB_TO_ARTICLE,
}
