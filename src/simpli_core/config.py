"""Configuration loader supporting .env and YAML files."""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict


class SimpliConfig(BaseModel):
    """Typed configuration with known keys and extensibility for unknown ones."""

    model_config = ConfigDict(extra="allow")

    simpli_env: str = "development"
    simpli_debug: bool = False
    simpli_log_level: str = "INFO"


def load_config(
    env_file: str | Path | None = None,
    yaml_file: str | Path | None = None,
) -> SimpliConfig:
    """Load configuration from environment variables, .env file, and optional YAML.

    Priority (highest to lowest): env vars > .env file > YAML file.

    Raises:
        ValueError: If the YAML file exists but cannot be parsed or read.
    """
    config: dict[str, str] = {}

    if yaml_file and Path(yaml_file).exists():
        try:
            with open(yaml_file) as f:
                yaml_config = yaml.safe_load(f)
                if isinstance(yaml_config, dict):
                    config.update(yaml_config)
        except yaml.YAMLError as exc:
            raise ValueError(f"Failed to parse YAML config {yaml_file}: {exc}") from exc
        except OSError as exc:
            raise ValueError(f"Failed to read config file {yaml_file}: {exc}") from exc

    if env_file:
        load_dotenv(env_file, override=True)
    else:
        load_dotenv(override=True)

    for key, value in os.environ.items():
        if key.startswith("SIMPLI_"):
            config[key.lower()] = value

    return SimpliConfig.model_validate(config)
