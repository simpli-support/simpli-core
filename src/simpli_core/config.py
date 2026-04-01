"""Configuration loader supporting .env and YAML files."""

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


def load_config(
    env_file: str | Path | None = None,
    yaml_file: str | Path | None = None,
) -> dict[str, Any]:
    """Load configuration from environment variables, .env file, and optional YAML.

    Priority (highest to lowest): env vars > .env file > YAML file.
    """
    config: dict[str, Any] = {}

    if yaml_file and Path(yaml_file).exists():
        import yaml

        with open(yaml_file) as f:
            yaml_config = yaml.safe_load(f)
            if isinstance(yaml_config, dict):
                config.update(yaml_config)

    if env_file:
        load_dotenv(env_file, override=True)
    else:
        load_dotenv(override=True)

    for key, value in os.environ.items():
        if key.startswith("SIMPLI_"):
            config[key] = value

    return config
