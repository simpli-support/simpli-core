"""Freshdesk connector using API key authentication."""

from __future__ import annotations

from typing import Any

from simpli_core.connectors.base import BaseConnector
from simpli_core.connectors.mapping import (
    FieldCategory,
    FieldDescriptor,
    ObjectSchema,
    ObjectType,
)
from simpli_core.connectors.registry import register


class FreshdeskConnector(BaseConnector):
    """Connect to Freshdesk via REST API v2.

    Uses API key as Basic auth username with ``X`` as password.

    Args:
        domain: Freshdesk domain (e.g. ``mycompany`` for mycompany.freshdesk.com).
        api_key: Freshdesk API key (Profile Settings > API Key).
    """

    platform = "freshdesk"

    def __init__(self, domain: str, api_key: str) -> None:
        super().__init__(
            f"https://{domain}.freshdesk.com",
            basic_auth=(api_key, "X"),
        )

    def get_tickets(
        self,
        where: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch tickets. ``where`` is a Freshdesk filter query."""
        params: dict[str, Any] = {"per_page": min(limit, 100)}
        if where:
            params["filter"] = where
        return self._paginate(
            "/api/v2/tickets",
            params=params,
            records_key="results" if where else "",
            limit=limit,
        )

    def get_customers(
        self,
        where: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch contacts."""
        params: dict[str, Any] = {"per_page": min(limit, 100)}
        return self._paginate(
            "/api/v2/contacts",
            params=params,
            records_key="results",
            limit=limit,
        )

    def get_messages(
        self,
        ticket_id: str,
    ) -> list[dict[str, Any]]:
        """Fetch conversations (replies/notes) for a ticket."""
        data = self._get(f"/api/v2/tickets/{ticket_id}/conversations")
        if isinstance(data, list):
            return data
        return data.get("results", [])

    def get_articles(
        self,
        where: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch Solution articles."""
        return self._paginate(
            "/api/v2/solutions/articles",
            records_key="results",
            limit=limit,
        )

    def update_ticket(
        self,
        ticket_id: str,
        note: str | None = None,
        private: bool = True,
        **fields: Any,
    ) -> dict[str, Any]:
        """Update a ticket. Optionally add a note."""
        if note:
            self._post(
                f"/api/v2/tickets/{ticket_id}/notes",
                json={"body": note, "private": private},
            )
        if fields:
            return self._put(f"/api/v2/tickets/{ticket_id}", json=fields)
        return {}


    def describe_fields(
        self,
        object_type: str = "ticket",
    ) -> ObjectSchema:
        """Discover ticket fields from Freshdesk."""
        raw_fields = self._get("/api/v2/ticket_fields")
        if not isinstance(raw_fields, list):
            raw_fields = raw_fields.get("ticket_fields", [])

        descriptors: list[FieldDescriptor] = []
        for field in raw_fields:
            picklist_vals = None
            choices = field.get("choices")
            if choices and isinstance(choices, (list, dict)):
                if isinstance(choices, dict):
                    picklist_vals = list(choices.keys())
                else:
                    picklist_vals = [str(c) for c in choices]

            descriptors.append(
                FieldDescriptor(
                    name=field.get("name", ""),
                    label=field.get("label", field.get("name", "")),
                    field_type="picklist" if picklist_vals else "string",
                    category=(
                        FieldCategory.STANDARD
                        if field.get("default", False)
                        else FieldCategory.CUSTOM
                    ),
                    required=field.get("required_for_agents", False),
                    picklist_values=picklist_vals,
                    description=field.get("description", "") or "",
                )
            )

        return ObjectSchema(
            object_type=ObjectType.TICKET,
            platform="freshdesk",
            fields=descriptors,
        )


register("freshdesk", FreshdeskConnector)
