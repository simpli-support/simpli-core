"""Salesforce connector using OAuth2 Client Credentials Flow."""

from __future__ import annotations

import logging
import re
from typing import Any, ClassVar

import httpx

from simpli_core.connectors.base import BaseConnector
from simpli_core.connectors.errors import (
    AuthenticationError,
    ConfigurationError,
    PlatformAPIError,
)
from simpli_core.connectors.field_config import load_field_config
from simpli_core.connectors.mapping import (
    FieldCategory,
    FieldDescriptor,
    ObjectSchema,
    ObjectType,
)
from simpli_core.connectors.registry import register

logger = logging.getLogger(__name__)


def _sanitize_soql_value(value: str) -> str:
    """Escape a value for safe interpolation into a SOQL query.

    Escapes single quotes and strips characters that could break SOQL syntax.
    """
    # Remove any control characters
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", value)
    # Escape single quotes for SOQL
    return cleaned.replace("'", "\\'")


class SalesforceConnector(BaseConnector):
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
        # Validate required credentials
        if not instance_url:
            raise ConfigurationError("instance_url is required", platform="salesforce")
        if not client_id:
            raise ConfigurationError("client_id is required", platform="salesforce")
        if not client_secret:
            raise ConfigurationError("client_secret is required", platform="salesforce")

        try:
            from simple_salesforce import Salesforce
        except ImportError:
            msg = (
                "Salesforce support requires simple-salesforce. "
                "Install with: pip install simpli-core[salesforce]"
            )
            raise ImportError(msg) from None

        # Initialize BaseConnector (httpx client for consistency/context manager)
        clean_url = instance_url.rstrip("/")
        super().__init__(base_url=clean_url)
        self.instance_url = clean_url

        # Authenticate via OAuth2 Client Credentials Flow
        token_url = f"{self.instance_url}/services/oauth2/token"
        try:
            resp = httpx.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                timeout=30,
            )
        except httpx.HTTPError as exc:
            logger.warning(
                "salesforce_auth_failed",
                extra={"instance_url": self.instance_url, "error": str(exc)},
            )
            raise PlatformAPIError(
                f"Failed to connect to Salesforce: {exc}",
                platform="salesforce",
            ) from exc

        if resp.status_code in (401, 403):
            logger.warning(
                "salesforce_auth_rejected",
                extra={"status_code": resp.status_code},
            )
            raise AuthenticationError(
                f"Salesforce authentication failed: {resp.status_code} {resp.text}",
                platform="salesforce",
            )
        if not resp.is_success:
            raise PlatformAPIError(
                f"Salesforce OAuth error: {resp.status_code} {resp.text}",
                platform="salesforce",
                status_code=resp.status_code,
                response_body=resp.text,
            )

        token_data = resp.json()
        access_token = token_data["access_token"]

        # The instance URL from the token response may differ
        resolved_instance = token_data.get("instance_url", self.instance_url)
        if resolved_instance != self.instance_url:
            logger.info(
                "salesforce_url_resolved",
                extra={
                    "provided": self.instance_url,
                    "resolved": resolved_instance,
                },
            )

        self.sf = Salesforce(
            instance_url=resolved_instance,
            session_id=access_token,
        )
        logger.info("Connected to Salesforce at %s", resolved_instance)

    def query(self, soql: str) -> list[dict[str, Any]]:
        """Execute a raw SOQL query and return records."""
        logger.debug("salesforce_query", extra={"soql": soql[:200]})
        try:
            result = self.sf.query_all(soql)
        except Exception as exc:
            raise PlatformAPIError(
                f"SOQL query failed: {exc}",
                platform="salesforce",
            ) from exc
        records: list[dict[str, Any]] = result.get("records", [])
        # Remove Salesforce metadata from each record
        for rec in records:
            rec.pop("attributes", None)
        logger.info(
            "salesforce_query_result",
            extra={"record_count": len(records)},
        )
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
        """Fetch Case records.

        Includes any extra fields saved via ``simpli-core setup``.
        """
        base_fields = [
            "Id",
            "CaseNumber",
            "Subject",
            "Description",
            "Status",
            "Priority",
            "Origin",
            "CreatedDate",
            "ClosedDate",
            "ContactId",
            "OwnerId",
        ]
        config = load_field_config("salesforce", "ticket")
        if config:
            extra = [f for f in config.selected_fields if f not in base_fields]
            all_fields = base_fields + extra
        else:
            all_fields = base_fields

        field_list = ", ".join(all_fields)
        soql = f"SELECT {field_list} FROM Case"
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
        soql = "SELECT Id, Name, Email, Phone, Account.Name, Account.Type FROM Contact"
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
        safe_id = _sanitize_soql_value(case_id)
        soql = (
            "SELECT Id, ParentId, CommentBody, CreatedDate, CreatedById, "
            "IsPublished "
            f"FROM CaseComment WHERE ParentId = '{safe_id}' "
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
        safe_id = _sanitize_soql_value(parent_id)
        soql = (
            "SELECT Id, ParentId, Body, CreatedDate, CreatedById, Type "
            f"FROM FeedItem WHERE ParentId = '{safe_id}' "
            "ORDER BY CreatedDate ASC"
        )
        return self.query(soql)

    def update_case(
        self,
        case_id: str,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a Case record and return the updated fields."""
        try:
            self.sf.Case.update(case_id, fields)
            return self.sf.Case.get(case_id)
        except Exception as exc:
            raise PlatformAPIError(
                f"Failed to update case {case_id}: {exc}",
                platform="salesforce",
            ) from exc

    def update_ticket(
        self,
        ticket_id: str,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a case (alias for update_case)."""
        return self.update_case(ticket_id, fields)

    def add_case_comment(
        self,
        case_id: str,
        body: str,
        *,
        is_published: bool = True,
    ) -> dict[str, Any]:
        """Add a CaseComment to a case."""
        try:
            result = self.sf.CaseComment.create(
                {
                    "ParentId": case_id,
                    "CommentBody": body,
                    "IsPublished": is_published,
                }
            )
            return result  # type: ignore[no-any-return]
        except Exception as exc:
            raise PlatformAPIError(
                f"Failed to add comment to case {case_id}: {exc}",
                platform="salesforce",
            ) from exc

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

    # -- Field type mapping for Salesforce describe results --

    _SF_TYPE_MAP: ClassVar[dict[str, str]] = {
        "string": "string",
        "textarea": "string",
        "email": "string",
        "url": "string",
        "phone": "string",
        "id": "string",
        "reference": "string",
        "picklist": "picklist",
        "multipicklist": "picklist",
        "boolean": "boolean",
        "int": "number",
        "double": "number",
        "currency": "number",
        "percent": "number",
        "date": "datetime",
        "datetime": "datetime",
    }

    def describe_fields(
        self,
        object_type: str = "ticket",
    ) -> ObjectSchema:
        """Discover fields on a Salesforce object.

        Uses the Salesforce ``describe()`` API for Case (tickets) or
        Knowledge__kav (articles).
        """
        sf_object = "Knowledge__kav" if object_type == "article" else "Case"
        try:
            desc = getattr(self.sf, sf_object).describe()
        except Exception as exc:
            raise PlatformAPIError(
                f"Failed to describe {sf_object}: {exc}",
                platform="salesforce",
            ) from exc

        descriptors: list[FieldDescriptor] = []
        for field in desc.get("fields", []):
            picklist_vals = None
            if field.get("type") in ("picklist", "multipicklist"):
                picklist_vals = [
                    pv["value"]
                    for pv in field.get("picklistValues", [])
                    if pv.get("active")
                ]

            descriptors.append(
                FieldDescriptor(
                    name=field["name"],
                    label=field.get("label", field["name"]),
                    field_type=self._SF_TYPE_MAP.get(
                        field.get("type", "string"), "string"
                    ),
                    category=(
                        FieldCategory.CUSTOM
                        if field.get("custom")
                        else FieldCategory.STANDARD
                    ),
                    required=not field.get("nillable", True)
                    and not field.get("defaultedOnCreate", False),
                    picklist_values=picklist_vals,
                    description=field.get("inlineHelpText", "") or "",
                )
            )

        ot = ObjectType.ARTICLE if object_type == "article" else ObjectType.TICKET
        return ObjectSchema(
            object_type=ot,
            platform="salesforce",
            fields=descriptors,
        )

    def close(self) -> None:
        """Close the HTTP client (inherited) and clean up."""
        super().close()


# Register with the connector registry
register("salesforce", SalesforceConnector)  # type: ignore[arg-type]
