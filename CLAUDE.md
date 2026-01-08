# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Perpee is an AI-powered price monitoring agent for Canadian online retailers. Users add products via URL or natural language chat, and Perpee tracks prices, detects changes, and sends email alerts.

## 🚨 CRITICAL RULES
- Every start of the session, check the docs folder to update me with the status of the project.
- **NEVER deviate from the IMPLEMENTATION_PLAN.md** - Follow every task exactly as specified. Do not skip files, use alternative implementations, or reuse existing code instead of creating specified files. Only deviate if the user explicitly requests it.
- When implementing a phase, cross-check each task item against what you've built before marking it complete.
- **ALWAYS follow the Phase Execution Workflow** from global CLAUDE.md:
  1. **BEFORE any implementation**: Create feature branch (`feature/phase-X-name`) and verify you're on it
  2. Implement with incremental commits
  3. Run tests, ensure coverage
  4. Self-review, then create PR
  5. **Use `/update-docs` skill** to update changelog and status (do NOT manually edit docs)
  6. Merge to main after approval
- **PRE-IMPLEMENTATION CHECKLIST**: Before writing ANY code for a phase, run `git branch` to confirm you're on the correct feature branch. If on `main`, STOP and create the feature branch first.
- **DOCUMENTATION UPDATES**: Always use the `/update-docs` skill for updating `docs/change_logs.md` and `docs/project_status.md`. Never manually edit these files.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI, Pydantic AI |
| Database | SQLite + SQLModel, ChromaDB (vector) |
| Scraping | Crawl4AI (Playwright) |
| LLM | OpenRouter (Gemini 2.0 Flash free, Llama 3.3 70B free fallback) |
| Frontend | Vite + React, shadcn/ui, Tailwind CSS, TanStack Query |
| Email | Resend |
| Scheduler | APScheduler |

## Project Structure

```
perpee/
├── backend/
│   ├── src/
│   │   ├── core/           # Exceptions, constants, security
│   │   ├── agent/          # Pydantic AI agent & tools
│   │   ├── scraper/        # Crawl4AI extraction strategies
│   │   ├── rag/            # ChromaDB embeddings
│   │   ├── scheduler/      # APScheduler jobs
│   │   ├── notifications/  # Email via Resend
│   │   ├── api/            # FastAPI endpoints
│   │   ├── database/       # SQLModel models
│   │   └── utils/
│   ├── config/
│   │   ├── settings.py     # Pydantic Settings
│   │   ├── stores_seed.py  # Initial store data
│   │   └── prompts/        # LLM prompt templates
│   ├── alembic/            # DB migrations
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── lib/            # API client, utils
│   └── ...
├── docker/
└── data/                   # Persisted: perpee.db, chromadb/, logs/
```

## Common Commands

### Backend
```bash
cd backend

# Install dependencies
uv sync

# Run development server
uv run uvicorn src.api.main:app --reload --port 8000

# Run tests
uv run pytest
uv run pytest tests/test_scraper.py -v  # Single file
uv run pytest -k "test_name"             # By name

# Lint & format
uv run ruff check .
uv run ruff format .

# Database migrations
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "description"
```

### Frontend
```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Lint
npm run lint
```

### Docker
```bash
cd docker
docker-compose up --build
```

## Architecture Notes

### Data Flow
```
User Input (Chat/URL) → Agent Core → [Scrape|Query|Schedule|Alert] → SQLite → Price Change Detection → Email Alert
```

### LLM Model Fallback Chain
1. **Primary**: `google/gemini-2.0-flash-exp:free` - Fast, 1M context
2. **Fallback 1**: `meta-llama/llama-3.3-70b-instruct:free` - Stable backup
3. **Fallback 2**: `anthropic/claude-3.5-haiku` - Paid, last resort

### Conversation Memory
- Window-based: last 15 messages
- Session-only: chat history NOT persisted to DB
- Products, alerts, and schedules ARE persisted

### Self-Healing
When site selectors break, the system automatically attempts recovery using LLM extraction. Target: 80%+ auto-recovery rate.

### Agent Tools
The Pydantic AI agent exposes these tools:
- `scrape_product` - Extract product data from URL
- `scan_website` - Analyze unknown website before whitelisting
- `search_products` - Search tracked products (local DB)
- `web_search` - DuckDuckGo for product URLs
- `get_price_history` - Query price history
- `create_schedule` - Set monitoring schedule
- `set_alert` - Configure price alert (target_price, percent_drop, any_change, back_in_stock)
- `compare_prices` - Cross-store comparison
- `list_products` / `remove_product`

### Scraper Extraction Priority
1. JSON-LD (free) - Structured data in `<script type="application/ld+json">`
2. CSS Selectors (free) - Pre-configured for known stores
3. XPath (free) - Edge cases
4. LLM Extraction (costs tokens) - Unknown stores, last resort

### Store Tiers
- **Known** (`is_whitelisted=TRUE`): Use CSS/XPath, fast & free
- **Scanned** (`is_whitelisted=FALSE`): Must use `scan_website` tool first, then LLM

### Alert Types
| Type | Trigger |
|------|---------|
| `target_price` | Price ≤ target AND in stock |
| `percent_drop` | Price dropped X% AND in stock |
| `any_change` | Price changed AND in stock |
| `back_in_stock` | `in_stock` changed false → true |

### API Structure
- REST: `/api/products`, `/api/alerts`, `/api/schedules`, `/api/stores`
- WebSocket: `/api/chat/ws` - Real-time agent conversation
- Static: `/` serves React build

### Rate Limits & Guardrails
- Max 10 scrapes/minute
- Max 30 LLM requests/minute
- 100,000 tokens/day limit
- 30s request timeout, 2min operation timeout

## Key Configuration

Environment variables (`.env`):
```
OPENROUTER_API_KEY=sk-or-...
OPENAI_API_KEY=sk-...          # For embeddings
RESEND_API_KEY=re_...
USER_EMAIL=user@example.com
PRIMARY_MODEL=google/gemini-2.0-flash-exp:free
FALLBACK_MODEL_1=meta-llama/llama-3.3-70b-instruct:free
FALLBACK_MODEL_2=anthropic/claude-3.5-haiku
DAILY_TOKEN_LIMIT=100000
```
Copy `.env.example` to `env.local` for local development

## Documentation

Consult these documents for detailed context when implementing features:

| Document | Purpose |
|----------|---------|
| `referrence/PRD PERPEE.md` | Product requirements, user stories, feature scope |
| `referrence/TECHNICAL_SPEC PERPEE.md` | Detailed technical specification, API contracts, data models |
| `IMPLEMENTATION_PLAN.md` | Step-by-step implementation phases and task breakdown |


## Security Notes

- URL whitelist enforced; unknown URLs require `scan_website` validation
- Block private IPs (SSRF protection)
- 4-layer XSS sanitization: Crawl4AI → extraction → storage → frontend
- Scraped content stored as sanitized text, never raw HTML
