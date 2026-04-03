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
from simpli_core.connectors.salesforce import SalesforceConnector
from simpli_core.connectors.settings import SalesforceSettings

__all__ = [
    "AuthenticationError",
    "BaseConnector",
    "ConfigurationError",
    "ConnectorError",
    "FieldMapping",
    "FileConnector",
    "PlatformAPIError",
    "RateLimitError",
    "SalesforceConnector",
    "SalesforceSettings",
    "apply_mappings",
    "get_connector",
    "list_platforms",
    "register",
]
