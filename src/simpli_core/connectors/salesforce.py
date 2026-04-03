"""Salesforce connector using OAuth2 Client Credentials Flow."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class SalesforceConnector:
    """Connect to Salesforce via OAuth2 Client Credentials and query data.

    Requires the ``simple-salesforce`` package. Install with::

        pip install simpli-core[salesforce]
    """

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

        # Authenticate via OAuth2 Client Credentials Flow
        import requests

        token_url = f"{self.instance_url}/services/oauth2/token"
        resp = requests.post(
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
