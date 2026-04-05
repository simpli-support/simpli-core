"""Base application settings using pydantic-settings."""

from pydantic import BaseModel, Field
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
    cors_origins: str = Field(
        default="*",
        description="Comma-separated CORS allowed origins. '*' allows all.",
    )
    api_key: str = Field(
        default="",
        description="API key for authenticating requests. Empty = disabled.",
    )
    supabase_url: str = Field(
        default="",
        description="Supabase project URL for persistent storage.",
    )
    supabase_key: str = Field(
        default="",
        description="Supabase service-role key for server-side access.",
    )
    llm_mock_mode: bool = Field(
        default=False,
        description=(
            "When true, services return deterministic mock"
            " responses instead of calling LLM APIs."
        ),
    )


class CustomFieldSettings(BaseModel):
    """Mixin for custom field preservation in data ingestion.

    Add to a service's ``Settings`` class to enable custom field support::

        class Settings(SimpliSettings, SalesforceSettings, CustomFieldSettings):
            ...

    Fields are configured via the ``simpli-core setup`` CLI command or the
    setup API, and persisted in ``~/.simpli/field_config.json``.
    """

    preserve_unmapped_fields: bool = Field(
        default=False,
        description=(
            "When true, unmapped source fields are preserved in a "
            "custom_fields dict during ingestion."
        ),
    )
    custom_fields_in_prompts: bool = Field(
        default=True,
        description="Include custom field data in LLM prompt context.",
    )
