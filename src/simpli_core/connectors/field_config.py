"""Persistent field configuration for platform custom field mappings.

Stores user-selected custom fields and their mapping rules in a JSON file
at ``~/.simpli/field_config.json`` (overridable via ``SIMPLI_CONFIG_DIR``).
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from simpli_core.connectors.mapping import FieldMapping

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_DIR = Path.home() / ".simpli"


def _config_dir() -> Path:
    """Return the configuration directory, creating it if needed."""
    path = Path(os.environ.get("SIMPLI_CONFIG_DIR", str(_DEFAULT_CONFIG_DIR)))
    path.mkdir(parents=True, exist_ok=True)
    return path


def _config_path() -> Path:
    return _config_dir() / "field_config.json"


class FieldConfig(BaseModel):
    """Configuration for a single platform + object type combination."""

    model_config = ConfigDict(extra="forbid")

    platform: str
    object_type: str = "ticket"
    selected_fields: list[str] = Field(default_factory=list)
    custom_mappings: list[FieldMapping] = Field(default_factory=list)
    discovered_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
    )


class FieldConfigStore(BaseModel):
    """Root structure for the field config JSON file."""

    model_config = ConfigDict(extra="forbid")

    version: int = 1
    configs: dict[str, FieldConfig] = Field(default_factory=dict)


def _store_key(platform: str, object_type: str) -> str:
    return f"{platform}:{object_type}"


def _load_store() -> FieldConfigStore:
    path = _config_path()
    if not path.exists():
        return FieldConfigStore()
    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return FieldConfigStore.model_validate(data)
    except Exception:
        logger.warning("Failed to load field config from %s, using defaults", path)
        return FieldConfigStore()


def _save_store(store: FieldConfigStore) -> None:
    path = _config_path()
    path.write_text(
        store.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    logger.info("Saved field config to %s", path)


def load_field_config(
    platform: str,
    object_type: str = "ticket",
) -> FieldConfig | None:
    """Load the field configuration for a platform and object type.

    Returns ``None`` if no configuration has been saved.
    """
    store = _load_store()
    return store.configs.get(_store_key(platform, object_type))


def save_field_config(config: FieldConfig) -> None:
    """Save a field configuration, merging into the existing store."""
    store = _load_store()
    store.configs[_store_key(config.platform, config.object_type)] = config
    _save_store(store)


def delete_field_config(platform: str, object_type: str = "ticket") -> bool:
    """Remove a field configuration. Returns True if it existed."""
    store = _load_store()
    key = _store_key(platform, object_type)
    if key in store.configs:
        del store.configs[key]
        _save_store(store)
        return True
    return False
