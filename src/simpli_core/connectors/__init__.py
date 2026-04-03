"""Data connectors for ingesting from Salesforce and file uploads."""

from simpli_core.connectors.file_parser import FileConnector
from simpli_core.connectors.mapping import FieldMapping, apply_mappings
from simpli_core.connectors.salesforce import SalesforceConnector
from simpli_core.connectors.settings import SalesforceSettings

__all__ = [
    "FieldMapping",
    "FileConnector",
    "SalesforceConnector",
    "SalesforceSettings",
    "apply_mappings",
]
