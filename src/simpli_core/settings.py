"""Base application settings using pydantic-settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SimpliSettings(BaseSettings):
    """Base settings shared by all Simpli services.

    Subclass this in each service and add service-specific fields.
    Reads from environment variables and .env files automatically.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: str = Field(default="development")
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    app_log_level: str = Field(default="info")
    app_debug: bool = Field(default=False)
    cost_tracking_enabled: bool = Field(default=False)
    api_key: str = Field(
        default="",
        description="API key for authenticating requests. Empty = disabled.",
    )
