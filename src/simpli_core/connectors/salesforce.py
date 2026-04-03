"""Salesforce connector using OAuth2 Client Credentials Flow."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from simpli_core.connectors.registry import register

logger = logging.getLogger(__name__)


class SalesforceConnector:
    """Connect to Salesforce via OAuth2 Client Credentials and query data.

    Requires the ``simple-salesforce`` package for SOQL queries.
    Install with::

        pip install simpli-core[salesforce]
    """

    platform: str = "salesforce"

    def __init__(
        self,
        instance_url: str,
        client_id: str,
        client_secret: str,
    ) -> None:
        try:
            from simple_salesforce import Salesforce
        except ImportError:
            msg = (
                "Salesforce support requires simple-salesforce. "
                "Install with: pip install simpli-core[salesforce]"
            )
            raise ImportError(msg) from None

        # Strip trailing slash
        self.instance_url = instance_url.rstrip("/")

        # Authenticate via OAuth2 Client Credentials Flow (httpx)
        token_url = f"{self.instance_url}/services/oauth2/token"
        resp = httpx.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=30,
        )
        resp.raise_for_status()
        token_data = resp.json()
        access_token = token_data["access_token"]

        # The instance URL from the token response may differ
        resolved_instance = token_data.get("instance_url", self.instance_url)

        self.sf = Salesforce(
            instance_url=resolved_instance,
            session_id=access_token,
        )
        logger.info("Connected to Salesforce at %s", resolved_instance)

    def query(self, soql: str) -> list[dict[str, Any]]:
        """Execute a raw SOQL query and return records."""
        result = self.sf.query_all(soql)
        records: list[dict[str, Any]] = result.get("records", [])
        # Remove Salesforce metadata from each record
        for rec in records:
            rec.pop("attributes", None)
        return records

    def get_tickets(
        self,
        where: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch Case records (alias for get_cases)."""
        return self.get_cases(where=where, limit=limit)

    def get_cases(
        self,
        where: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch Case records."""
        soql = (
            "SELECT Id, CaseNumber, Subject, Description, Status, Priority, "
            "Origin, CreatedDate, ClosedDate, ContactId "
            "FROM Case"
        )
        if where:
            soql += f" WHERE {where}"
        soql += f" ORDER BY CreatedDate DESC LIMIT {limit}"
        return self.query(soql)

    def get_contacts(
        self,
        where: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch Contact records with Account info."""
        soql = (
            "SELECT Id, Name, Email, Phone, "
            "Account.Name, Account.Type "
            "FROM Contact"
        )
        if where:
            soql += f" WHERE {where}"
        soql += f" LIMIT {limit}"
        return self.query(soql)

    def get_customers(
        self,
        where: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch Contact records (alias for get_contacts)."""
        return self.get_contacts(where=where, limit=limit)

    def get_case_comments(
        self,
        case_id: str,
    ) -> list[dict[str, Any]]:
        """Fetch CaseComment records for a specific case."""
        soql = (
            "SELECT Id, ParentId, CommentBody, CreatedDate, CreatedById, "
            "IsPublished "
            f"FROM CaseComment WHERE ParentId = '{case_id}' "
            "ORDER BY CreatedDate ASC"
        )
        return self.query(soql)

    def get_messages(
        self,
        ticket_id: str,
    ) -> list[dict[str, Any]]:
        """Fetch messages for a case (alias for get_case_comments)."""
        return self.get_case_comments(ticket_id)

    def get_feed_items(
        self,
        parent_id: str,
    ) -> list[dict[str, Any]]:
        """Fetch FeedItem records (Chatter) for a case."""
        soql = (
            "SELECT Id, ParentId, Body, CreatedDate, CreatedById, Type "
            f"FROM FeedItem WHERE ParentId = '{parent_id}' "
            "ORDER BY CreatedDate ASC"
        )
        return self.query(soql)

    def get_kb_articles(
        self,
        where: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch Knowledge articles (Knowledge__kav)."""
        soql = (
            "SELECT Id, Title, Summary, ArticleBody, UrlName, "
            "LastPublishedDate, IsVisibleInPkb "
            "FROM Knowledge__kav WHERE PublishStatus = 'Online' "
            "AND Language = 'en_US'"
        )
        if where:
            soql += f" AND {where}"
        soql += f" LIMIT {limit}"
        return self.query(soql)

    def get_articles(
        self,
        where: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch KB articles (alias for get_kb_articles)."""
        return self.get_kb_articles(where=where, limit=limit)

    def close(self) -> None:
        """No-op — Salesforce uses simple-salesforce session."""


# Register with the connector registry
register("salesforce", SalesforceConnector)  # type: ignore[arg-type]
