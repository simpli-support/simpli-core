# Simpli Core

Shared Python SDK for the [Simpli Support](https://simpli.support) product family. Provides domain models, base settings, structured logging, LLM cost tracking, and a FastAPI app factory used by all services.

## Installation

```bash
pip install "simpli-core @ git+https://github.com/simpli-support/simpli-core.git"
```

For development:

```bash
pip install -e ".[dev]"
```

## Modules

### Domain Models (`simpli_core.models`)

| Model | Description |
|-------|-------------|
| `Ticket` | Support ticket with status, priority, channel, tags, and metadata |
| `Customer` | Customer profile with tier and metadata |
| `Agent` | Support agent with teams and skills |
| `Message` | Full conversation message with author, channel, and timestamp |
| `Conversation` | Thread of messages linked to a ticket |

**Enums:** `Priority`, `TicketStatus`, `Channel`, `AuthorType`, `CustomerTier`

### Settings (`simpli_core.settings`)

Base settings class that all services subclass:

```python
from simpli_core import SimpliSettings

class Settings(SimpliSettings):
    litellm_model: str = "openai/gpt-5-mini"

settings = Settings()  # reads from env vars and .env files
```

Built-in fields: `app_env`, `app_host`, `app_port`, `app_log_level`, `app_debug`, `cost_tracking_enabled`

### Logging (`simpli_core.logging`)

```python
from simpli_core import setup_logging

setup_logging(log_level="INFO", json_output=False)
```

Configures [structlog](https://www.structlog.org/) with sensible defaults, context vars, and optional JSON output.

### Cost Tracking (`simpli_core.usage`)

Track LLM token usage and costs across any provider:

```python
from simpli_core import CostTracker

tracker = CostTracker()
cost = tracker.record_from_response("openai/gpt-5-mini", litellm_response)
print(tracker.summary())  # per-model breakdown with costs
```

Includes pricing for 50+ models (OpenAI, Anthropic, Google, xAI, DeepSeek, Mistral, Ollama).

### FastAPI Utilities (`simpli_core.fastapi`)

App factory that eliminates boilerplate across all services:

```python
from simpli_core import CostTracker, create_app
from my_service.settings import settings

cost_tracker = CostTracker()
app = create_app(
    title="My Service",
    version="0.1.0",
    description="Service description",
    settings=settings,
    cors_origins=settings.cors_origins,
    cost_tracker=cost_tracker,
)
```

This sets up CORS, request ID middleware, structured logging, and `/health` + `/usage` endpoints automatically.

**Also provides:**

| Export | Description |
|--------|-------------|
| `ChatMessage` | Lightweight `role + content` model for LLM chat input |
| `add_request_id_middleware()` | Standalone request ID middleware for custom setups |
| `create_ops_router()` | `/health` + `/usage` router for custom app instances |

### Data Connectors (`simpli_core.connectors`)

Ingest data from Salesforce or file uploads with automatic field mapping:

```python
from simpli_core import FileConnector, FieldMapping, apply_mappings

# Parse files (CSV, JSON, JSONL — Excel/Parquet with optional extras)
records = FileConnector.parse("tickets.csv")
records = FileConnector.parse(uploaded_file, format="json")

# Map fields from source to domain model
mappings = [
    FieldMapping(source="CaseNumber", target="id"),
    FieldMapping(source="Subject", target="subject"),
    FieldMapping(source="Priority", target="priority", transform="enum:Priority"),
]
mapped = apply_mappings(records, mappings)
```

**Salesforce connector** (requires `pip install simpli-core[salesforce]`):

```python
from simpli_core import SalesforceConnector

sf = SalesforceConnector(
    instance_url="https://myorg.salesforce.com",
    client_id="...",
    client_secret="...",
)
cases = sf.get_cases(where="Status = 'Open'", limit=50)
articles = sf.get_kb_articles(limit=20)
comments = sf.get_case_comments(case_id="5001234")
```

**Default field mappings** included: `CASE_TO_TICKET`, `CONTACT_TO_CUSTOMER`, `COMMENT_TO_MESSAGE`, `KB_TO_ARTICLE`.

**Optional extras:** `simpli-core[excel]` (openpyxl), `simpli-core[parquet]` (pyarrow).

### Configuration (`simpli_core.config`)

```python
from simpli_core import load_config

config = load_config(env_file=".env", yaml_file="config.yml")
```

Priority: environment variables > `.env` file > YAML. Reads all `SIMPLI_*` prefixed keys.

## Development

```bash
ruff check .
ruff format --check .
mypy src/
pytest tests/ -q
```

## License

MIT
