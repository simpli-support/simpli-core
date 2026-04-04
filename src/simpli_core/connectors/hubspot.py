"""HubSpot connector using Private App access token."""

from __future__ import annotations

from typing import Any

from simpli_core.connectors.base import BaseConnector
from simpli_core.connectors.field_config import load_field_config
from simpli_core.connectors.mapping import (
    FieldCategory,
    FieldDescriptor,
    ObjectSchema,
    ObjectType,
)
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
        base_properties = (
            "subject,content,hs_pipeline_stage,hs_ticket_priority,"
            "createdate,hs_lastmodifieddate"
        )
        config = load_field_config("hubspot", "ticket")
        if config:
            extra = ",".join(
                f for f in config.selected_fields if f not in base_properties
            )
            properties = f"{base_properties},{extra}" if extra else base_properties
        else:
            properties = base_properties

        params: dict[str, Any] = {
            "limit": min(limit, 100),
            "properties": properties,
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
        data = self._get(f"/crm/v3/objects/tickets/{ticket_id}/associations/notes")
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

    def describe_fields(
        self,
        object_type: str = "ticket",
    ) -> ObjectSchema:
        """Discover ticket properties from HubSpot."""
        data = self._get("/crm/v3/properties/tickets")
        raw_fields = data.get("results", [])

        descriptors: list[FieldDescriptor] = []
        for field in raw_fields:
            if field.get("hidden", False):
                continue
            picklist_vals = None
            options = field.get("options") or []
            if options:
                picklist_vals = [o.get("value", "") for o in options]

            descriptors.append(
                FieldDescriptor(
                    name=field.get("name", ""),
                    label=field.get("label", field.get("name", "")),
                    field_type="picklist"
                    if picklist_vals
                    else field.get("type", "string"),
                    category=(
                        FieldCategory.STANDARD
                        if field.get("hubspotDefined", False)
                        else FieldCategory.CUSTOM
                    ),
                    required=field.get("required", False)
                    if not field.get("hubspotDefined")
                    else False,
                    picklist_values=picklist_vals,
                    description=field.get("description", ""),
                )
            )

        return ObjectSchema(
            object_type=ObjectType.TICKET,
            platform="hubspot",
            fields=descriptors,
        )


register("hubspot", HubSpotConnector)
