"""Data connectors for ingesting from external platforms and file uploads."""

from simpli_core.connectors.base import BaseConnector
from simpli_core.connectors.errors import (
    AuthenticationError,
    ConfigurationError,
    ConnectorError,
    PlatformAPIError,
    RateLimitError,
)
from simpli_core.connectors.file_parser import FileConnector
from simpli_core.connectors.mapping import FieldMapping, apply_mappings
from simpli_core.connectors.registry import get_connector, list_platforms, register

# Import connectors to trigger registration with the registry
from simpli_core.connectors.salesforce import SalesforceConnector
from simpli_core.connectors.settings import (
    FreshdeskSettings,
    HubSpotSettings,
    IntercomSettings,
    JiraSettings,
    SalesforceSettings,
    ServiceNowSettings,
    ZendeskSettings,
)

# Lazy imports — these register themselves on import
# Import them here so they're available and registered
from simpli_core.connectors.freshdesk import FreshdeskConnector
from simpli_core.connectors.hubspot import HubSpotConnector
from simpli_core.connectors.intercom import IntercomConnector
from simpli_core.connectors.jira import JiraConnector
from simpli_core.connectors.servicenow import ServiceNowConnector
from simpli_core.connectors.zendesk import ZendeskConnector

__all__ = [
    "AuthenticationError",
    "BaseConnector",
    "ConfigurationError",
    "ConnectorError",
    "FieldMapping",
    "FileConnector",
    "FreshdeskConnector",
    "FreshdeskSettings",
    "HubSpotConnector",
    "HubSpotSettings",
    "IntercomConnector",
    "IntercomSettings",
    "JiraConnector",
    "JiraSettings",
    "PlatformAPIError",
    "RateLimitError",
    "SalesforceConnector",
    "SalesforceSettings",
    "ServiceNowConnector",
    "ServiceNowSettings",
    "ZendeskConnector",
    "ZendeskSettings",
    "apply_mappings",
    "get_connector",
    "list_platforms",
    "register",
]
