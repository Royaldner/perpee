# Perpee Backend

AI-powered price monitoring agent for Canadian online retailers.

## Setup

```bash
# Install dependencies
uv sync

# Run development server
uv run uvicorn src.api.main:app --reload --port 8000

# Run tests
uv run pytest
```

## Environment Variables

Copy `.env.example` to `.env` and configure your API keys.
