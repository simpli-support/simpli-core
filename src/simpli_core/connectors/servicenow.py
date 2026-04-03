"""ServiceNow connector using Basic auth."""

from __future__ import annotations

from typing import Any

from simpli_core.connectors.base import BaseConnector
from simpli_core.connectors.registry import register


class ServiceNowConnector(BaseConnector):
    """Connect to ServiceNow via Table API.

    Uses Basic auth (username/password).

    Args:
        instance: ServiceNow instance name (e.g. ``mycompany``
                  for mycompany.service-now.com).
        username: ServiceNow username.
        password: ServiceNow password.
    """

    platform = "servicenow"

    def __init__(
        self,
        instance: str,
        username: str,
        password: str,
    ) -> None:
        super().__init__(
            f"https://{instance}.service-now.com",
            basic_auth=(username, password),
        )

    def get_tickets(
        self,
        where: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch Incident records.

        ``where`` is a ServiceNow encoded query string
        (e.g. ``state=2^priority=1``).
        """
        params: dict[str, Any] = {
            "sysparm_limit": limit,
            "sysparm_fields": (
                "sys_id,number,short_description,description,"
                "state,priority,urgency,category,opened_at,"
                "closed_at,caller_id,assigned_to"
            ),
            "sysparm_display_value": "false",
        }
        if where:
            params["sysparm_query"] = where
        else:
            params["sysparm_query"] = "ORDERBYDESCopened_at"

        data = self._get("/api/now/table/incident", params=params)
        return data.get("result", [])

    def get_customers(
        self,
        where: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch User records."""
        params: dict[str, Any] = {
            "sysparm_limit": limit,
            "sysparm_fields": "sys_id,name,email,phone,company,department",
        }
        if where:
            params["sysparm_query"] = where
        data = self._get("/api/now/table/sys_user", params=params)
        return data.get("result", [])

    def get_messages(
        self,
        ticket_id: str,
    ) -> list[dict[str, Any]]:
        """Fetch work notes and comments for an incident.

        ``ticket_id`` should be the incident's sys_id.
        """
        params: dict[str, Any] = {
            "sysparm_query": f"element_id={ticket_id}",
            "sysparm_fields": (
                "sys_id,value,element,sys_created_on,sys_created_by"
            ),
            "sysparm_limit": 200,
        }
        data = self._get(
            "/api/now/table/sys_journal_field", params=params
        )
        return data.get("result", [])

    def get_articles(
        self,
        where: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch Knowledge Base articles."""
        params: dict[str, Any] = {
            "sysparm_limit": limit,
            "sysparm_fields": (
                "sys_id,number,short_description,text,"
                "kb_knowledge_base,sys_created_on,active"
            ),
        }
        if where:
            params["sysparm_query"] = where
        else:
            params["sysparm_query"] = "active=true^ORDERBYDESCsys_created_on"

        data = self._get("/api/now/table/kb_knowledge", params=params)
        return data.get("result", [])

    def update_ticket(
        self,
        sys_id: str,
        work_note: str | None = None,
        **fields: Any,
    ) -> dict[str, Any]:
        """Update an incident. Optionally add a work note."""
        payload: dict[str, Any] = {**fields}
        if work_note:
            payload["work_notes"] = work_note
        return self._patch(
            f"/api/now/table/incident/{sys_id}",
            json=payload,
        )


register("servicenow", ServiceNowConnector)
