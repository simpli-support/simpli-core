"""HubSpot connector using Private App access token."""

from __future__ import annotations

from typing import Any

from simpli_core.connectors.base import BaseConnector
from simpli_core.connectors.registry import register


class HubSpotConnector(BaseConnector):
    """Connect to HubSpot CRM via REST API v3.

    Uses Private App access token (Bearer auth).

    Args:
        access_token: HubSpot Private App access token.
    """

    platform = "hubspot"

    def __init__(self, access_token: str) -> None:
        super().__init__(
            "https://api.hubapi.com",
            auth_headers={"Authorization": f"Bearer {access_token}"},
        )

    def get_tickets(
        self,
        where: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch tickets from HubSpot CRM.

        Tickets are returned with their properties flattened.
        """
        params: dict[str, Any] = {
            "limit": min(limit, 100),
            "properties": "subject,content,hs_pipeline_stage,hs_ticket_priority,createdate,hs_lastmodifieddate",
        }
        records = self._paginate(
            "/crm/v3/objects/tickets",
            params=params,
            records_key="results",
            limit=limit,
        )
        # Flatten properties into top-level for easier mapping
        return [self._flatten_properties(r) for r in records]

    def get_customers(
        self,
        where: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch contacts from HubSpot CRM."""
        params: dict[str, Any] = {
            "limit": min(limit, 100),
            "properties": "firstname,lastname,email,phone,company",
        }
        records = self._paginate(
            "/crm/v3/objects/contacts",
            params=params,
            records_key="results",
            limit=limit,
        )
        return [self._flatten_properties(r) for r in records]

    def get_messages(
        self,
        ticket_id: str,
    ) -> list[dict[str, Any]]:
        """Fetch engagement notes associated with a ticket."""
        # Get associated notes via associations API
        data = self._get(
            f"/crm/v3/objects/tickets/{ticket_id}/associations/notes"
        )
        results = data.get("results", [])

        notes: list[dict[str, Any]] = []
        for assoc in results:
            note_id = assoc.get("id", "")
            if note_id:
                note_data = self._get(
                    f"/crm/v3/objects/notes/{note_id}",
                    params={"properties": "hs_note_body,hs_createdate"},
                )
                notes.append(self._flatten_properties(note_data))
        return notes

    def get_articles(
        self,
        where: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch blog posts (HubSpot's closest KB equivalent)."""
        params: dict[str, Any] = {"limit": min(limit, 100)}
        return self._paginate(
            "/cms/v3/blogs/posts",
            params=params,
            records_key="results",
            limit=limit,
        )

    def update_ticket(
        self,
        ticket_id: str,
        **properties: Any,
    ) -> dict[str, Any]:
        """Update ticket properties."""
        return self._patch(
            f"/crm/v3/objects/tickets/{ticket_id}",
            json={"properties": properties},
        )

    @staticmethod
    def _flatten_properties(record: dict[str, Any]) -> dict[str, Any]:
        """Flatten HubSpot's nested ``properties`` dict to top-level."""
        flat = dict(record)
        props = flat.pop("properties", {})
        if isinstance(props, dict):
            flat.update(props)
        return flat


register("hubspot", HubSpotConnector)
