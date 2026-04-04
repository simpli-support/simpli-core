"""Intercom connector using Access Token authentication."""

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


class IntercomConnector(BaseConnector):
    """Connect to Intercom via REST API.

    Uses Bearer token authentication (Access Token from Developer Hub).

    Args:
        access_token: Intercom access token.
    """

    platform = "intercom"

    def __init__(self, access_token: str) -> None:
        super().__init__(
            "https://api.intercom.io",
            auth_headers={
                "Authorization": f"Bearer {access_token}",
                "Intercom-Version": "2.11",
            },
        )

    def get_tickets(
        self,
        where: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch conversations (Intercom's equivalent of tickets)."""
        return self._paginate(
            "/conversations",
            records_key="conversations",
            limit=limit,
        )

    def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        """Fetch a single conversation with all parts."""
        return self._get(f"/conversations/{conversation_id}")

    def get_customers(
        self,
        where: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch contacts."""
        return self._paginate(
            "/contacts",
            params={"per_page": min(limit, 150)},
            records_key="data",
            limit=limit,
        )

    def get_messages(
        self,
        ticket_id: str,
    ) -> list[dict[str, Any]]:
        """Fetch conversation parts (messages) for a conversation."""
        data = self._get(f"/conversations/{ticket_id}")
        parts = data.get("conversation_parts", {})
        return parts.get("conversation_parts", [])

    def get_articles(
        self,
        where: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch Help Center articles."""
        return self._paginate(
            "/articles",
            records_key="data",
            limit=limit,
        )

    def reply_to_conversation(
        self,
        conversation_id: str,
        body: str,
        message_type: str = "note",
        admin_id: str = "",
    ) -> dict[str, Any]:
        """Reply to or add a note to a conversation."""
        payload: dict[str, Any] = {
            "message_type": message_type,
            "type": "admin",
            "body": body,
        }
        if admin_id:
            payload["admin_id"] = admin_id
        return self._post(
            f"/conversations/{conversation_id}/reply",
            json=payload,
        )


    def describe_fields(
        self,
        object_type: str = "ticket",
    ) -> ObjectSchema:
        """Discover data attributes from Intercom."""
        data = self._get(
            "/data_attributes",
            params={"model": "conversation"},
        )
        raw_fields = data.get("data_attributes", data.get("data", []))
        if not isinstance(raw_fields, list):
            raw_fields = []

        descriptors: list[FieldDescriptor] = []
        for field in raw_fields:
            if field.get("archived", False):
                continue
            descriptors.append(
                FieldDescriptor(
                    name=field.get("name", ""),
                    label=field.get("label", field.get("name", "")),
                    field_type=field.get("data_type", "string"),
                    category=(
                        FieldCategory.CUSTOM
                        if field.get("custom", False)
                        else FieldCategory.STANDARD
                    ),
                    description=field.get("description", ""),
                )
            )

        return ObjectSchema(
            object_type=ObjectType.TICKET,
            platform="intercom",
            fields=descriptors,
        )


register("intercom", IntercomConnector)
