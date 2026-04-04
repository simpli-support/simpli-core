"""Zendesk connector using API token authentication."""

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

_ZENDESK_STANDARD_TYPES = {
    "subject",
    "description",
    "status",
    "priority",
    "group",
    "assignee",
    "tickettype",
    "organization",
}


class ZendeskConnector(BaseConnector):
    """Connect to Zendesk Support via REST API.

    Uses API token authentication (email/token + API token as Basic auth).

    Args:
        subdomain: Zendesk subdomain (e.g. ``mycompany`` for mycompany.zendesk.com).
        email: Admin or agent email address.
        api_token: Zendesk API token (Admin > Channels > API).
    """

    platform = "zendesk"

    def __init__(
        self,
        subdomain: str,
        email: str,
        api_token: str,
    ) -> None:
        super().__init__(
            f"https://{subdomain}.zendesk.com",
            basic_auth=(f"{email}/token", api_token),
        )

    def get_tickets(
        self,
        where: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch tickets. ``where`` is a Zendesk search query string."""
        if where:
            params: dict[str, Any] = {"query": f"type:ticket {where}"}
            data = self._get("/api/v2/search.json", params=params)
            results: list[dict[str, Any]] = data.get("results", [])
            return results[:limit]

        return self._paginate(
            "/api/v2/tickets.json",
            records_key="tickets",
            limit=limit,
        )

    def get_customers(
        self,
        where: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch end-users (customers)."""
        params: dict[str, Any] = {"role": "end-user"}
        return self._paginate(
            "/api/v2/users.json",
            params=params,
            records_key="users",
            limit=limit,
        )

    def get_messages(
        self,
        ticket_id: str,
    ) -> list[dict[str, Any]]:
        """Fetch comments for a ticket."""
        data = self._get(f"/api/v2/tickets/{ticket_id}/comments.json")
        result: list[dict[str, Any]] = data.get("comments", [])
        return result

    def get_articles(
        self,
        where: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch Help Center articles."""
        return self._paginate(
            "/api/v2/help_center/articles.json",
            records_key="articles",
            limit=limit,
        )

    def get_user(self, user_id: str) -> dict[str, Any]:
        """Fetch a single user by ID."""
        data = self._get(f"/api/v2/users/{user_id}.json")
        result: dict[str, Any] = data.get("user", {})
        return result

    def update_ticket(
        self,
        ticket_id: str,
        comment: str | None = None,
        internal: bool = True,
        **fields: Any,
    ) -> dict[str, Any]:
        """Update a ticket (add comment, change fields)."""
        payload: dict[str, Any] = {"ticket": {**fields}}
        if comment:
            payload["ticket"]["comment"] = {
                "body": comment,
                "public": not internal,
            }
        return self._put(f"/api/v2/tickets/{ticket_id}.json", json=payload)

    def describe_fields(
        self,
        object_type: str = "ticket",
    ) -> ObjectSchema:
        """Discover ticket fields from Zendesk."""
        data = self._get("/api/v2/ticket_fields.json")
        raw_fields = data.get("ticket_fields", [])

        descriptors: list[FieldDescriptor] = []
        for field in raw_fields:
            if not field.get("active", True):
                continue
            ftype = field.get("type", "text")
            is_standard = ftype in _ZENDESK_STANDARD_TYPES
            picklist_vals = None
            options = field.get("custom_field_options") or []
            if options:
                picklist_vals = [o.get("value", "") for o in options]

            descriptors.append(
                FieldDescriptor(
                    name=str(field.get("id", "")),
                    label=field.get("title", ""),
                    field_type="picklist" if picklist_vals else "string",
                    category=(
                        FieldCategory.STANDARD if is_standard else FieldCategory.CUSTOM
                    ),
                    required=field.get("required", False),
                    picklist_values=picklist_vals,
                    description=field.get("description", ""),
                )
            )

        return ObjectSchema(
            object_type=ObjectType.TICKET,
            platform="zendesk",
            fields=descriptors,
        )


register("zendesk", ZendeskConnector)
