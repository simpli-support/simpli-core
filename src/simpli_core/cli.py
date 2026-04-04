"""CLI interface for simpli-core."""

from pathlib import Path

import typer

app = typer.Typer(help="Simpli Core CLI — shared utilities")


@app.command()
def version() -> None:
    """Show the SDK version."""
    from simpli_core import __version__

    typer.echo(f"simpli-core {__version__}")


@app.command()
def config(
    env_file: str | None = typer.Option(None, help="Path to .env file"),
    yaml_file: str | None = typer.Option(None, help="Path to YAML config file"),
) -> None:
    """Show the resolved configuration."""
    from simpli_core.config import load_config

    env_path = Path(env_file) if env_file else None
    yaml_path = Path(yaml_file) if yaml_file else None
    try:
        cfg = load_config(env_file=env_path, yaml_file=yaml_path)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    for key, value in sorted(cfg.model_dump().items()):
        typer.echo(f"{key}={value}")
    for key, value in sorted((cfg.model_extra or {}).items()):
        typer.echo(f"{key}={value}")


@app.command()
def setup(
    platform: str = typer.Argument(
        ..., help="Platform to configure (salesforce, zendesk, freshdesk, hubspot, jira, servicenow, intercom)"
    ),
    object_type: str = typer.Option(
        "ticket", help="Object type: ticket or article"
    ),
) -> None:
    """Discover fields from a connected platform and configure field mappings.

    Connects to the platform, retrieves all available fields (including
    custom fields), and lets you choose which ones to include in data
    ingestion. Selected fields are saved to ~/.simpli/field_config.json.
    """
    from simpli_core.connectors.field_config import (
        FieldConfig,
        load_field_config,
        save_field_config,
    )
    from simpli_core.connectors.mapping import (
        DEFAULT_ARTICLE_MAPPINGS,
        DEFAULT_TICKET_MAPPINGS,
        FieldCategory,
        FieldMapping,
    )
    from simpli_core.connectors.registry import get_connector, list_platforms

    # Validate platform
    available = list_platforms()
    if platform not in available:
        typer.echo(
            f"Unknown platform: {platform!r}. Available: {', '.join(available)}",
            err=True,
        )
        raise typer.Exit(code=1)

    # Resolve credentials
    creds = _prompt_credentials(platform)

    # Connect
    typer.echo(f"\nConnecting to {platform}...")
    try:
        connector_cls = get_connector(platform)
        connector = connector_cls(**creds)
    except Exception as exc:
        typer.echo(f"Failed to connect: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    # Discover fields
    typer.echo("Discovering fields...")
    try:
        schema = connector.describe_fields(object_type)
    except NotImplementedError:
        typer.echo(
            f"{platform} connector does not support field discovery yet.",
            err=True,
        )
        raise typer.Exit(code=1)
    except Exception as exc:
        typer.echo(f"Field discovery failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if hasattr(connector, "close"):
        connector.close()

    # Determine which fields are already in default mappings
    mapping_lookup = (
        DEFAULT_ARTICLE_MAPPINGS
        if object_type == "article"
        else DEFAULT_TICKET_MAPPINGS
    )
    default_mappings = mapping_lookup.get(platform, [])
    default_sources = {m.source for m in default_mappings}

    # Split into standard (already mapped) and custom (available)
    standard_fields = []
    custom_fields = []
    for fd in schema.fields:
        if fd.name in default_sources:
            standard_fields.append(fd)
        elif fd.category == FieldCategory.CUSTOM:
            custom_fields.append(fd)

    # Display standard fields
    typer.echo(f"\n{'─' * 60}")
    typer.echo(f"Standard fields (already mapped by default): {len(standard_fields)}")
    typer.echo(f"{'─' * 60}")
    for fd in standard_fields:
        typer.echo(f"  ✓ {fd.name:<30} {fd.label}")

    # Display custom fields
    if not custom_fields:
        typer.echo("\nNo custom fields found on this object.")
        raise typer.Exit()

    typer.echo(f"\n{'─' * 60}")
    typer.echo(f"Custom fields available: {len(custom_fields)}")
    typer.echo(f"{'─' * 60}")
    for i, fd in enumerate(custom_fields, 1):
        extra = ""
        if fd.picklist_values:
            vals = ", ".join(fd.picklist_values[:5])
            if len(fd.picklist_values) > 5:
                vals += f", ... (+{len(fd.picklist_values) - 5} more)"
            extra = f"  [{vals}]"
        typer.echo(f"  {i:3}. {fd.name:<30} {fd.label} ({fd.field_type}){extra}")

    # Check for existing config
    existing = load_field_config(platform, object_type)
    if existing:
        typer.echo(
            f"\nExisting config found with {len(existing.selected_fields)} "
            f"custom fields. This will be replaced."
        )

    # Select fields
    typer.echo("")
    selection = typer.prompt(
        "Enter field numbers to include (e.g. 1,3,5), 'all', or 'none'",
        default="none",
    )

    if selection.strip().lower() == "none":
        typer.echo("No custom fields selected.")
        raise typer.Exit()

    if selection.strip().lower() == "all":
        selected = custom_fields
    else:
        indices = []
        for part in selection.split(","):
            part = part.strip()
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(custom_fields):
                    indices.append(idx)
        selected = [custom_fields[i] for i in indices]

    if not selected:
        typer.echo("No valid fields selected.")
        raise typer.Exit()

    # Build mappings for selected fields
    typer.echo(f"\nConfiguring {len(selected)} custom field(s):")
    custom_mappings: list[FieldMapping] = []
    selected_names: list[str] = []
    for fd in selected:
        default_target = fd.name.lower().replace("__c", "").rstrip("_")
        target = typer.prompt(
            f"  Target name for '{fd.name}'",
            default=default_target,
        )
        custom_mappings.append(
            FieldMapping(source=fd.name, target=target)
        )
        selected_names.append(fd.name)

    # Save config
    field_config = FieldConfig(
        platform=platform,
        object_type=object_type,
        selected_fields=selected_names,
        custom_mappings=custom_mappings,
    )
    save_field_config(field_config)

    typer.echo(f"\n✓ Saved configuration for {platform}:{object_type}")
    typer.echo(f"  {len(custom_mappings)} custom field mapping(s)")
    typer.echo(f"  Config: ~/.simpli/field_config.json")

    # Offer test
    if typer.confirm("\nTest the configuration by fetching 1 record?", default=False):
        try:
            connector = connector_cls(**creds)
            fetch = "get_articles" if object_type == "article" else "get_tickets"
            records = getattr(connector, fetch)(limit=1)
            if hasattr(connector, "close"):
                connector.close()
            if records:
                typer.echo(f"  Fetched 1 record with {len(records[0])} fields")
                for name in selected_names:
                    val = records[0].get(name, "(not present)")
                    typer.echo(f"    {name}: {val}")
            else:
                typer.echo("  No records returned.")
        except Exception as exc:
            typer.echo(f"  Test failed: {exc}", err=True)


# -- Credential prompting helpers --

_PLATFORM_CRED_FIELDS: dict[str, list[tuple[str, str, bool]]] = {
    "salesforce": [
        ("instance_url", "Salesforce instance URL", False),
        ("client_id", "Client ID", False),
        ("client_secret", "Client Secret", True),
    ],
    "zendesk": [
        ("subdomain", "Zendesk subdomain", False),
        ("email", "Agent email", False),
        ("api_token", "API token", True),
    ],
    "freshdesk": [
        ("domain", "Freshdesk domain", False),
        ("api_key", "API key", True),
    ],
    "hubspot": [
        ("access_token", "Access token", True),
    ],
    "intercom": [
        ("access_token", "Access token", True),
    ],
    "jira": [
        ("domain", "Atlassian domain", False),
        ("email", "Email", False),
        ("api_token", "API token", True),
        ("project_key", "Project key (optional)", False),
    ],
    "servicenow": [
        ("instance", "Instance name", False),
        ("username", "Username", False),
        ("password", "Password", True),
    ],
}

# Env var prefix mapping (matches connector settings.py)
_SETTINGS_PREFIX: dict[str, str] = {
    "salesforce": "SALESFORCE_",
    "zendesk": "ZENDESK_",
    "freshdesk": "FRESHDESK_",
    "hubspot": "HUBSPOT_",
    "intercom": "INTERCOM_",
    "jira": "JIRA_",
    "servicenow": "SERVICENOW_",
}


def _prompt_credentials(platform: str) -> dict[str, str]:
    """Resolve credentials from env vars or prompt the user."""
    import os

    fields = _PLATFORM_CRED_FIELDS.get(platform, [])
    prefix = _SETTINGS_PREFIX.get(platform, "")
    creds: dict[str, str] = {}

    for param, label, is_secret in fields:
        env_key = f"{prefix}{param.upper()}"
        env_val = os.environ.get(env_key, "")
        if env_val:
            creds[param] = env_val
            masked = "***" if is_secret else env_val
            typer.echo(f"  {label}: {masked} (from {env_key})")
        else:
            value = typer.prompt(f"  {label}", hide_input=is_secret)
            if value:
                creds[param] = value

    return {k: v for k, v in creds.items() if v}
