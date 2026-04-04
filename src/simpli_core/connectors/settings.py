"""Optional platform settings mixins for services."""

from pydantic import BaseModel


class SalesforceSettings(BaseModel):
    """Mixin providing Salesforce connection fields.

    Example::

        class Settings(SimpliSettings, SalesforceSettings):
            litellm_model: str = "openrouter/google/gemini-2.5-flash-lite"
    """

    salesforce_instance_url: str = ""
    salesforce_client_id: str = ""
    salesforce_client_secret: str = ""


class ZendeskSettings(BaseModel):
    """Mixin providing Zendesk connection fields."""

    zendesk_subdomain: str = ""
    zendesk_email: str = ""
    zendesk_api_token: str = ""


class FreshdeskSettings(BaseModel):
    """Mixin providing Freshdesk connection fields."""

    freshdesk_domain: str = ""
    freshdesk_api_key: str = ""


class IntercomSettings(BaseModel):
    """Mixin providing Intercom connection fields."""

    intercom_access_token: str = ""


class HubSpotSettings(BaseModel):
    """Mixin providing HubSpot connection fields."""

    hubspot_access_token: str = ""


class JiraSettings(BaseModel):
    """Mixin providing Jira connection fields."""

    jira_domain: str = ""
    jira_email: str = ""
    jira_api_token: str = ""
    jira_project_key: str = ""


class ServiceNowSettings(BaseModel):
    """Mixin providing ServiceNow connection fields."""

    servicenow_instance: str = ""
    servicenow_username: str = ""
    servicenow_password: str = ""
