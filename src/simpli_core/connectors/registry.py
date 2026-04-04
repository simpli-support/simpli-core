"""Connector registry for looking up connectors by platform name."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from simpli_core.connectors.base import BaseConnector

# Registry maps platform name → connector class
_CONNECTORS: dict[str, type[BaseConnector]] = {}


def register(name: str, cls: type[BaseConnector]) -> None:
    """Register a connector class for a platform name."""
    _CONNECTORS[name] = cls


def get_connector(name: str) -> type[BaseConnector]:
    """Look up a connector class by platform name.

    Raises:
        KeyError: If the platform is not registered.
    """
    if name not in _CONNECTORS:
        available = ", ".join(sorted(_CONNECTORS.keys())) or "(none)"
        msg = f"Unknown platform: {name!r}. Available connectors: {available}"
        raise KeyError(msg)
    return _CONNECTORS[name]


def list_platforms() -> list[str]:
    """Return sorted list of registered platform names."""
    return sorted(_CONNECTORS.keys())
