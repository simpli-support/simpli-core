"""Jira Service Management connector using API token authentication."""

from __future__ import annotations

import re
from typing import Any

from simpli_core.connectors.base import BaseConnector
from simpli_core.connectors.registry import register


class JiraConnector(BaseConnector):
    """Connect to Jira / Jira Service Management via REST API v3.

    Uses Basic auth with email and API token.

    Args:
        domain: Atlassian domain (e.g. ``mycompany`` for mycompany.atlassian.net).
        email: User email address.
        api_token: Atlassian API token (https://id.atlassian.net/manage-profile/security/api-tokens).
        project_key: Default Jira project key (e.g. ``SUP``).
    """

    platform = "jira"

    def __init__(
        self,
        domain: str,
        email: str,
        api_token: str,
        project_key: str = "",
    ) -> None:
        super().__init__(
            f"https://{domain}.atlassian.net",
            basic_auth=(email, api_token),
        )
        self.project_key = project_key

    def get_tickets(
        self,
        where: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch issues using JQL.

        ``where`` is a JQL clause. If empty and ``project_key`` is set,
        fetches all issues in that project.
        """
        jql = where
        if not jql and self.project_key:
            jql = f"project = {self.project_key} ORDER BY created DESC"

        data = self._get(
            "/rest/api/3/search",
            params={
                "jql": jql,
                "maxResults": min(limit, 100),
                "fields": "summary,description,status,priority,issuetype,assignee,reporter,created,updated,comment",
            },
        )
        issues = data.get("issues", [])
        return [self._flatten_issue(issue) for issue in issues[:limit]]

    def get_customers(
        self,
        where: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Search for users (reporters/requesters)."""
        params: dict[str, Any] = {"maxResults": min(limit, 50)}
        if where:
            params["query"] = where
        data = self._get("/rest/api/3/users/search", params=params)
        if isinstance(data, list):
            return data[:limit]
        return data.get("values", [])[:limit]

    def get_messages(
        self,
        ticket_id: str,
    ) -> list[dict[str, Any]]:
        """Fetch comments for an issue."""
        data = self._get(f"/rest/api/3/issue/{ticket_id}/comment")
        comments = data.get("comments", [])
        return [
            {
                "id": c.get("id", ""),
                "body": self._adf_to_text(c.get("body", {})),
                "author_id": c.get("author", {}).get("accountId", ""),
                "author_name": c.get("author", {}).get("displayName", ""),
                "created": c.get("created", ""),
            }
            for c in comments
        ]

    def get_articles(
        self,
        where: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch issues of type 'Article' or search Confluence (if accessible)."""
        jql = where or "type = Article"
        if self.project_key and "project" not in jql.lower():
            jql = f"project = {self.project_key} AND {jql}"
        return self.get_tickets(where=jql, limit=limit)

    def add_comment(
        self,
        issue_key: str,
        body: str,
        internal: bool = True,
    ) -> dict[str, Any]:
        """Add a comment to an issue."""
        payload: dict[str, Any] = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": body}],
                    }
                ],
            }
        }
        if internal:
            payload["visibility"] = {
                "type": "role",
                "value": "Service Desk Team",
            }
        return self._post(
            f"/rest/api/3/issue/{issue_key}/comment",
            json=payload,
        )

    @staticmethod
    def _flatten_issue(issue: dict[str, Any]) -> dict[str, Any]:
        """Flatten Jira's nested issue structure for easier mapping."""
        fields = issue.get("fields", {})
        return {
            "key": issue.get("key", ""),
            "id": issue.get("id", ""),
            "summary": fields.get("summary", ""),
            "description": JiraConnector._adf_to_text(
                fields.get("description", {})
            ),
            "status": (fields.get("status") or {}).get("name", ""),
            "priority": (fields.get("priority") or {}).get("name", ""),
            "issuetype": (fields.get("issuetype") or {}).get("name", ""),
            "assignee_id": (fields.get("assignee") or {}).get(
                "accountId", ""
            ),
            "reporter_id": (fields.get("reporter") or {}).get(
                "accountId", ""
            ),
            "created": fields.get("created", ""),
            "updated": fields.get("updated", ""),
        }

    @staticmethod
    def _adf_to_text(adf: dict[str, Any] | None) -> str:
        """Convert Atlassian Document Format (ADF) to plain text."""
        if not adf or not isinstance(adf, dict):
            return ""

        texts: list[str] = []

        def _extract(node: dict[str, Any] | list[Any]) -> None:
            if isinstance(node, list):
                for item in node:
                    _extract(item)
                return
            if isinstance(node, dict):
                if node.get("type") == "text":
                    texts.append(node.get("text", ""))
                for child in node.get("content", []):
                    _extract(child)

        _extract(adf)
        return " ".join(texts)


register("jira", JiraConnector)
