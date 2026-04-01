# Simpli Core

Shared Python SDK for the Simpli Support product family. Provides common data models, configuration loading, and integration utilities.

## Installation

```bash
pip install -e ".[dev]"
```

## Models

- `Ticket` — Support ticket with status, priority, and metadata
- `Customer` — Customer profile with tier and metadata
- `Agent` — Support agent with teams and skills
- `Message` — Individual message in a conversation
- `Conversation` — Thread of messages linked to a ticket

## Configuration

```python
from simpli_core.config import load_config

config = load_config(env_file=".env", yaml_file="config.yml")
```

## Development

```bash
ruff check .
mypy src/
pytest
```
