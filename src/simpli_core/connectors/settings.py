"""Optional Salesforce settings mixin for services."""

from pydantic import BaseModel


class SalesforceSettings(BaseModel):
    """Mixin providing Salesforce connection fields.

    Add to a service's Settings class to enable server-configured
    Salesforce credentials as defaults (can be overridden per-request).

    Example::

        class Settings(SimpliSettings, SalesforceSettings):
            litellm_model: str = "openai/gpt-5-mini"
    """

    salesforce_instance_url: str = ""
    salesforce_client_id: str = ""
    salesforce_client_secret: str = ""
