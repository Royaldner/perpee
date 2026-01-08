# Perpee - Technical Specification

**Version:** 1.0  
**Last Updated:** January 6, 2025  
**Status:** Ready for Implementation  
**Related Document:** PRD.md

---

## Overview

This document contains the complete technical specification for implementing Perpee, an AI-powered price monitoring agent. It is designed for use with Claude Code for AI-assisted implementation.

### Document Structure

| Section | Description |
|---------|-------------|
| Architecture | System diagram, tech stack, data flow |
| Component 1 | Project Structure & Agent Core |
| Component 2 | Database Schema & Models |
| Component 3 | Scraper Engine |
| Component 4 | RAG System |
| Component 5 | Self-Healing Module |
| Component 6 | Scheduler |
| Component 7 | Notifications |
| Component 8 | API Endpoints |
| Component 9 | Web UI |
| Appendices | Store list, costs, dependencies |

---

## Technical Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Container                          │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                      FastAPI Server                       │   │
│  │                                                          │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │   │
│  │  │   Agent     │  │   Scraper   │  │    Scheduler    │  │   │
│  │  │  (Pydantic  │  │  (Crawl4AI) │  │  (APScheduler)  │  │   │
│  │  │    AI)      │  │             │  │                 │  │   │
│  │  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘  │   │
│  │         │                │                  │           │   │
│  │         └────────────────┼──────────────────┘           │   │
│  │                          │                              │   │
│  │                    ┌─────▼─────┐                        │   │
│  │                    │  SQLite   │                        │   │
│  │                    │ + ChromaDB│                        │   │
│  │                    └───────────┘                        │   │
│  │                                                          │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │   │
│  │  │    RAG      │  │ Self-Heal   │  │  Notifications  │  │   │
│  │  │  (ChromaDB) │  │   Module    │  │    (Resend)     │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  │   │
│  │                                                          │   │
│  │  ┌──────────────────────────────────────────────────┐   │   │
│  │  │              Static Frontend (React)              │   │   │
│  │  └──────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
    ┌─────────┐         ┌─────────┐         ┌─────────┐
    │OpenRouter│        │Retailer │         │ Resend  │
    │  (LLM)  │         │ Sites   │         │ (Email) │
    └─────────┘         └─────────┘         └─────────┘
```

### Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Backend** | Python 3.11+, FastAPI | API server, async support |
| **Agent** | Pydantic AI | LLM agent framework |
| **Database** | SQLite + SQLModel | Relational data, ORM |
| **Vector DB** | ChromaDB | Semantic product search |
| **Scraping** | Crawl4AI (Playwright) | Web scraping with stealth |
| **LLM** | OpenRouter | Model routing, fallbacks |
| **Frontend** | Vite + React | SPA, fast builds |
| **UI Components** | shadcn/ui + Tailwind | Accessible, customizable |
| **Email** | Resend | Transactional email |
| **Scheduler** | APScheduler | Cron jobs, persistence |
| **Infrastructure** | Docker | Single container deployment |
| **Hosting** | Oracle Cloud Free Tier | Free VM (1GB RAM) |

### Data Flow

```
User Input (Chat/URL)
       │
       ▼
┌─────────────────┐
│   Agent Core    │ ──── Decides action via LLM
└────────┬────────┘
         │
    ┌────┴────┬─────────────┬──────────────┐
    ▼         ▼             ▼              ▼
┌───────┐ ┌───────┐   ┌──────────┐   ┌──────────┐
│Scrape │ │ Query │   │ Schedule │   │  Alert   │
│Product│ │  RAG  │   │   Job    │   │  Setup   │
└───┬───┘ └───┬───┘   └────┬─────┘   └────┬─────┘
    │         │            │              │
    └─────────┴────────────┴──────────────┘
                    │
                    ▼
             ┌────────────┐
             │   SQLite   │
             │  Database  │
             └──────┬─────┘
                    │
                    ▼
          ┌─────────────────┐
          │ Price Change?   │
          │ Alert Trigger?  │
          └────────┬────────┘
                   │ Yes
                   ▼
          ┌─────────────────┐
          │  Email Alert    │
          │    (Resend)     │
          └─────────────────┘
```

---

## Component Specifications

## Component 1: Project Structure & Agent Core

### 1.1 Project Structure

  

```

perpee/

├── docker/

│   ├── Dockerfile

│   └── docker-compose.yml

│

├── data/                        # Mounted volume (persisted)

│   ├── perpee.db               # SQLite database

│   ├── chromadb/               # Vector embeddings

│   └── logs/                   # Application logs

│

├── backend/

│   ├── src/

│   │   ├── core/               # Shared domain logic

│   │   │   ├── __init__.py

│   │   │   ├── exceptions.py   # Custom exceptions

│   │   │   ├── constants.py    # App-wide constants

│   │   │   └── security.py     # URL validation, sanitization

│   │   ├── agent/              # Pydantic AI agent

│   │   ├── scraper/            # Crawl4AI & extraction

│   │   ├── rag/                # ChromaDB & embeddings

│   │   ├── scheduler/          # APScheduler jobs

│   │   ├── notifications/      # Email notifications

│   │   ├── api/                # FastAPI endpoints

│   │   ├── database/           # SQLModel models

│   │   └── utils/              # Generic helpers

│   ├── config/

│   │   ├── settings.py         # Pydantic Settings

│   │   ├── stores_seed.py      # Initial store data for DB seeding

│   │   └── prompts/            # LLM prompt templates

│   ├── alembic/

│   │   ├── versions/           # Migration files

│   │   └── env.py

│   ├── alembic.ini

│   ├── tests/

│   ├── pyproject.toml      # Dependencies (uv)

│   └── uv.lock             # Lockfile (auto-generated)

│

├── frontend/

│   ├── src/

│   │   ├── components/

│   │   ├── pages/

│   │   ├── hooks/

│   │   ├── lib/                # API client, utils

│   │   └── App.tsx

│   ├── public/

│   ├── index.html

│   ├── package.json

│   ├── vite.config.ts

│   └── tailwind.config.js

│

├── .env.example

├── .gitignore

└── README.md

```

  

### 1.2 Infrastructure Decisions

  

| Decision | Choice | Rationale |

|----------|--------|-----------|

| Package manager | `uv` | 10-100x faster installs, automatic lockfile |

| Backend framework | FastAPI | Async, fast, great OpenAPI docs |

| Frontend framework | Vite + React (SPA) | Fast dev, simple deployment |

| Hosting model | Single Docker container | FastAPI serves static build |

| Configuration | `.env` + Pydantic Settings | Type-safe, validation built-in |

| Authentication | None (MVP) | Single user |

| Repository | Monorepo | Simpler for solo dev |

  

### 1.3 Agent Core Configuration

  

| Setting | Value | Notes |

|---------|-------|-------|

| Agent framework | Pydantic AI | Type-safe, FastAPI-native |

| Agent pattern | Hybrid (Router + ReAct) | Router for simple tasks, ReAct for complex |

| LLM provider | OpenRouter | Model switching, unified API |

| Primary model | `google/gemini-2.0-flash-exp:free` | Free, fast, 1M context |

| Fallback model 1 | `meta-llama/llama-3.3-70b-instruct:free` | Free, stable, battle-tested |

| Fallback model 2 | `anthropic/claude-3.5-haiku` | Paid, high reliability last resort |

| Conversation memory | Window-based, last 15 messages | Session-only (not persisted to DB) |

| Welcome message | Shown at chat start | Informs user that chat is session-only |

  

#### Chat Welcome Message

  

When a chat session begins, display this message (or similar):

  

```

👋 Hi! I'm Perpee, your price monitoring assistant.

  

I can help you:

• Track product prices from Canadian retailers

• Set alerts when prices drop

• Compare prices across stores

  

ℹ️ Note: Chat history is not saved between sessions.

   Your tracked products, alerts, and schedules are always saved.

  

Paste a product URL or ask me anything!
```

  

### 1.4 Agent Tools

| Tool | Purpose | Input | Output |
|------|---------|-------|--------|
| `scrape_product` | Extract product data from URL | `url: str` | `Product` object |
| `scan_website` | Analyze a website's structure for safe extraction before whitelisting | `url: str` | `ScanResult` (feasible, selectors, risks) |
| `search_products` | Search tracked products in local DB (not store websites) | `query: str, store?: str` | `list[Product]` |
| `web_search` | DuckDuckGo search for product URLs (shopping queries only) | `query: str` | `list[SearchResult]` |
| `get_price_history` | Query price history | `product_id: UUID, days?: int` | `list[PricePoint]` |
| `create_schedule` | Set up monitoring schedule | `product_id: UUID, cron: str` | `Schedule` |
| `set_alert` | Configure price alert | `product_id: UUID, target_price?: float, percent_drop?: int` | `Alert` |
| `compare_prices` | Cross-store comparison | `canonical_id: UUID` | `list[StorePrice]` |
| `list_products` | List tracked products | `store?: str, limit?: int` | `list[Product]` |
| `remove_product` | Stop tracking a product | `product_id: UUID` | `bool` |

  

### 1.5 Agent Guardrails

  

| Category | Guardrail | Rule | Implementation |

|----------|-----------|------|----------------|

| **Rate Limiting** | Scrape rate | Max 10 scrapes per minute | In-memory counter + queue |

| **Rate Limiting** | LLM requests | Max 30 requests per minute | Token bucket |

| **Security** | URL whitelist | Pre-configured popular Canadian stores | Domain extraction + lookup |
| **Security** | Unknown URLs | Require `scan_website` tool before adding new stores | Block until scanned |
| **Security** | SSRF protection | Block private IPs, metadata endpoints | IP validation after DNS resolution |

| **Security** | Input sanitization | Separate user content from prompts | Structured prompt templates |

| **Cost Control** | Input tokens | Max 4,000 per request | Truncation |

| **Cost Control** | Output tokens | Max 1,000 per request | Model parameter |

| **Cost Control** | Daily limit | Max 100,000 tokens/day | Hard stop with user notification |

| **Timeouts** | Request timeout | 30 seconds per HTTP request | `httpx` timeout |

| **Timeouts** | Operation timeout | 2 minutes per agent action | Asyncio timeout |

| **Behavior** | Scope limits | Product/price queries only | System prompt + output validation |

| **Behavior** | Hallucination prevention | Only report data from DB/scrape | Grounding in retrieved data |
| **Behavior** | Action confirmation | Confirm destructive actions | User confirmation for delete/bulk ops |
| **Behavior** | Web search filter | Shopping-related queries only | Query classification |
| **Behavior** | Scan website validation | Validate site safety before whitelisting | Security checks + structure analysis |

### 1.6 Configuration Files

  

#### `.env.example`

  

```env

# LLM

OPENROUTER_API_KEY=sk-or-...

PRIMARY_MODEL=google/gemini-2.0-flash-exp:free

FALLBACK_MODEL_1=meta-llama/llama-3.3-70b-instruct:free

FALLBACK_MODEL_2=anthropic/claude-3.5-haiku

  

# Embeddings

OPENAI_API_KEY=sk-...

  

# Notifications
RESEND_API_KEY=re_...
USER_EMAIL=user@example.com

# App

LOG_LEVEL=INFO

DEBUG=false

DAILY_TOKEN_LIMIT=100000

```

  

#### `pyproject.toml`

  

```toml

[project]

name = "perpee"

version = "0.1.0"

description = "AI-powered price monitoring agent for Canadian retailers"

requires-python = ">=3.11"

dependencies = [

    "fastapi>=0.109.0",

    "uvicorn[standard]>=0.27.0",

    "sqlmodel>=0.0.14",

    "alembic>=1.13.0",

    "pydantic-settings>=2.1.0",

    "pydantic-ai>=0.1.0",

    "crawl4ai>=0.2.0",

    "chromadb>=0.4.0",

    "apscheduler>=3.10.0",

    "httpx>=0.26.0",

    "openai>=1.10.0",

    "resend>=0.8.0",

    "duckduckgo-search>=4.1.0",

    "pyyaml>=6.0.0",

]

  

[tool.uv]

dev-dependencies = [

    "pytest>=7.4.0",

    "pytest-asyncio>=0.23.0",

    "ruff>=0.1.0",

]

```

  

#### `config/settings.py` (Structure)

  

```python

from pydantic_settings import BaseSettings

  

class Settings(BaseSettings):

    # LLM

    openrouter_api_key: str

    primary_model: str = "google/gemini-2.0-flash-exp:free"

    fallback_model_1: str = "meta-llama/llama-3.3-70b-instruct:free"

    fallback_model_2: str = "anthropic/claude-3.5-haiku"

    # Cost controls

    max_input_tokens: int = 4000

    max_output_tokens: int = 1000

    daily_token_limit: int = 100000

    # Rate limits

    max_scrapes_per_minute: int = 10

    request_timeout_seconds: int = 30

    operation_timeout_seconds: int = 120

    # Paths

    data_dir: str = "/app/data"

    db_path: str = "/app/data/perpee.db"

    class Config:

        env_file = ".env"

```

  

### 1.7 Agent Personality & System Prompt

  

#### Identity

  

| Attribute | Value |

|-----------|-------|

| **Name** | Perpee |

| **Role** | AI price monitoring assistant |

| **Scope** | Canadian retail price tracking only |

| **Creator** | (Your name/brand) |

  

#### Personality Traits

  

| Trait | Description |

|-------|-------------|

| **Tone** | Friendly, helpful, and concise |

| **Style** | Conversational but efficient - gets to the point |

| **Emoji Use** | Sparingly - for price drops 📉, alerts 🔔, success ✅, errors ⚠️ |

| **Verbosity** | Brief responses unless user asks for details |

| **Proactivity** | Suggests related actions (e.g., "Want me to set an alert?") |

| **Honesty** | Admits limitations, doesn't make up data |

  

#### Behavioral Guidelines

  

| Scenario | Behavior |

|----------|----------|

| **On-topic request** | Execute immediately, confirm completion |

| **Off-topic request** | Politely redirect to price tracking |

| **Ambiguous request** | Ask one clarifying question |

| **Error/failure** | Explain what went wrong, suggest alternatives |

| **Destructive action** | Confirm before deleting (from C1 guardrails) |

| **Unknown store** | Warn but proceed, explain auto-whitelist |

| **No results** | Acknowledge, suggest alternatives |

  

#### Scope Boundaries

  

**Will Do:**

- Track product prices from Canadian retailers

- Set price alerts and schedules

- Show price history and comparisons

- Search tracked products

- Explain how Perpee works

  

**Won't Do:**

- General knowledge questions (not a general assistant)

- Purchase products or process payments

- Access non-retail websites

- Provide financial/investment advice

- Track products outside Canada (MVP)

- Anything unrelated to price monitoring

  

#### System Prompt Template

  

```

You are Perpee, a friendly AI assistant specialized in monitoring product prices from Canadian online retailers.

  

## Your Capabilities

- Track product prices by URL

- Search products you're already tracking

- Set price alerts (target price, percent drop, any change, back in stock)

- Configure check schedules

- Show price history and comparisons across stores

- Web search for product URLs (shopping queries only)

  

## Your Personality

- Be friendly, helpful, and concise

- Use emojis sparingly: 📉 price drops, 🔔 alerts, ✅ success, ⚠️ issues

- Get to the point - users want quick answers

- Proactively suggest helpful follow-ups

  

## Important Rules

1. ONLY help with price tracking for Canadian retailers

2. If asked about something unrelated, politely redirect: "I'm focused on price tracking. Is there a product you'd like me to monitor?"

3. NEVER make up prices or data - only report what's in the database or freshly scraped

4. When a scrape fails, explain clearly and offer to retry or check later

5. Confirm before deleting products or alerts

6. For unknown stores, warn the user but proceed with the attempt

7. Keep responses brief unless the user asks for more detail

  

## Response Format

- Use short paragraphs, not long blocks

- For multiple products, use a brief list format

- Always include the current price when discussing a product

- Format prices as CAD (e.g., $149.99)

  

## Current Context

- User's tracked products and alerts are available via tools

- Price checks run daily at approximately 6 AM

- Chat history is session-only (not saved between visits)

```

  

#### Example Conversations

  

**Example 1: Adding a product**

```

User: Track this https://walmart.ca/product/nike-air-max

  

Perpee: ✅ Now tracking Nike Air Max 90 from Walmart!

  

Current price: $149.99

Last checked: Just now

  

Want me to set a price alert for this?

```

  

**Example 2: Off-topic request**

```

User: What's the weather like today?

  

Perpee: I'm focused on tracking product prices, so I can't help with weather. 🙂

  

Is there a product you'd like me to find or monitor?

```

  

**Example 3: Price drop notification context**

```

User: Show me the biggest drops

  

Perpee: 📉 Here are your biggest price drops today:

  

1. **Sony WH-1000XM5** (Best Buy) - $279.99 → $249.99 (-11%)

2. **Nike Air Max 90** (Walmart) - $159.99 → $149.99 (-6%)

3. **Instant Pot Duo** (Amazon) - $129.99 → $119.99 (-8%)

  

Want details on any of these?

```

  

**Example 4: Scrape failure**

```

User: Add https://unknownstore.ca/product/123

  

Perpee: ⚠️ I wasn't able to extract product details from that page.

  

This could be because:

- The store layout isn't recognized yet

- The page requires login

- The product is no longer available

  

Want me to try again, or would you like to try a different URL?

```

  

**Example 5: Destructive action confirmation**

```

User: Delete all my Walmart products

  

Perpee: You have 12 products from Walmart. Are you sure you want to remove all of them?

  

This will also delete associated alerts and schedules.

  

Reply "yes" to confirm, or "no" to cancel.

```

  

**Example 6: Ambiguous request**

```

User: Set an alert

  

Perpee: Sure! Which product would you like to set an alert for?

  

You can say the product name, or paste a URL to add a new one.

```
#### Prompt Variables
| Variable | Source | Description |

|----------|--------|-------------|

| `{product_count}` | Database | Number of tracked products |

| `{store_count}` | Database | Number of active stores |

| `{recent_drops}` | Database | Count of price drops (24h) |

| `{user_name}` | Settings | Optional personalization (SaaS) |

  
---

## Component 2: Database Schema & Models

  

> ✅ **Status:** Complete

  

### 2.1 Data Retention Policy

  

| Table | Retention | Method |

|-------|-----------|--------|

| `products` | Forever | Soft delete |

| `alerts` | Forever | Soft delete |

| `schedules` | Forever | Soft delete |

| `canonical_products` | Forever | Soft delete |

| `price_history` | Forever | None |

| `scrape_logs` | 30 days | Daily cron hard delete |

| `notifications` | 90 days | Daily cron hard delete |

| `stores` | Forever | `is_active` flag |

  

### 2.2 Tables

  

#### `products`

  

| Column | Type | Notes |

|--------|------|-------|

| `id` | UUID | PK |

| `url` | TEXT | Full product URL |

| `store_domain` | TEXT | FK to stores |

| `name` | TEXT | Product title |

| `brand` | TEXT | Nullable |

| `upc` | TEXT | Nullable, for canonical matching |

| `current_price` | DECIMAL | Latest price |

| `original_price` | DECIMAL | Nullable (strikethrough price) |

| `currency` | TEXT | Default "CAD" |

| `in_stock` | BOOL | Nullable |

| `image_url` | TEXT | Nullable |

| `status` | TEXT | active, paused, error, archived |

| `canonical_id` | UUID | Nullable, FK to canonical_products |

| `last_checked_at` | DATETIME | |

| `last_successful_at` | DATETIME | |

| `consecutive_failures` | INT | Default 0 |

| `deleted_at` | DATETIME | Nullable, soft delete |

| `created_at` | DATETIME | |

| `updated_at` | DATETIME | |

  

#### `price_history`

  

| Column | Type | Notes |

|--------|------|-------|

| `id` | INT | PK, auto-increment |

| `product_id` | UUID | FK to products |

| `price` | DECIMAL | |

| `original_price` | DECIMAL | Nullable |

| `in_stock` | BOOL | Nullable |

| `scraped_at` | DATETIME | |

  

#### `alerts`

  

| Column | Type | Notes |

|--------|------|-------|

| `id` | UUID | PK |

| `product_id` | UUID | FK to products |

| `alert_type` | TEXT | target_price, percent_drop, any_change, back_in_stock |

| `target_value` | DECIMAL | Nullable (not needed for back_in_stock) |

| `is_active` | BOOL | Default true |

| `is_triggered` | BOOL | Default false |

| `triggered_at` | DATETIME | Nullable |

| `deleted_at` | DATETIME | Nullable, soft delete |

| `created_at` | DATETIME | |

  

#### `schedules`

  

| Column | Type | Notes |

|--------|------|-------|

| `id` | UUID | PK |

| `product_id` | UUID | Nullable, FK to products |

| `store_domain` | TEXT | Nullable (store-wide schedule) |

| `cron_expression` | TEXT | e.g., "0 6 * * *" |

| `is_active` | BOOL | Default true |

| `last_run_at` | DATETIME | Nullable |

| `next_run_at` | DATETIME | Nullable |

| `deleted_at` | DATETIME | Nullable, soft delete |

| `created_at` | DATETIME | |

  

#### `stores`

  

| Column | Type | Notes |

|--------|------|-------|

| `domain` | TEXT | PK, e.g., "walmart.ca" |

| `name` | TEXT | Display name |

| `is_whitelisted` | BOOL | P0/P1/P2 vs user-added |

| `is_active` | BOOL | Can disable problematic stores |

| `selectors` | JSON | CSS selectors for extraction |

| `rate_limit_rpm` | INT | Default 10 |

| `success_rate` | DECIMAL | Nullable, calculated |

| `last_success_at` | DATETIME | Nullable |

| `created_at` | DATETIME | |

| `updated_at` | DATETIME | |

  

#### `canonical_products`

  

| Column | Type | Notes |

|--------|------|-------|

| `id` | UUID | PK |

| `name` | TEXT | Normalized product name |

| `brand` | TEXT | Nullable |

| `upc` | TEXT | Nullable, for matching |

| `category` | TEXT | Nullable |

| `deleted_at` | DATETIME | Nullable, soft delete |

| `created_at` | DATETIME | |

  

#### `scrape_logs`

  

| Column | Type | Notes |

|--------|------|-------|

| `id` | INT | PK, auto-increment |

| `product_id` | UUID | FK to products |

| `success` | BOOL | |

| `strategy_used` | TEXT | json_ld, css, llm |

| `error_type` | TEXT | Nullable |

| `error_message` | TEXT | Nullable (sanitized, no secrets) |

| `response_time_ms` | INT | |

| `scraped_at` | DATETIME | |

  

#### `notifications`

  

| Column | Type | Notes |

|--------|------|-------|

| `id` | INT | PK, auto-increment |

| `alert_id` | UUID | Nullable, FK to alerts |

| `product_id` | UUID | FK to products |

| `channel` | TEXT | email, push |

| `status` | TEXT | pending, sent, failed |

| `payload` | JSON | What was sent |

| `sent_at` | DATETIME | Nullable |

| `error_message` | TEXT | Nullable |

| `created_at` | DATETIME | |

  

### 2.3 Indexes

  

| Table | Index Name | Columns | Purpose |

|-------|------------|---------|---------|

| `products` | idx_products_store | `store_domain` | Filter by store |

| `products` | idx_products_status | `status, deleted_at` | Active product queries |

| `products` | idx_products_canonical | `canonical_id` | Cross-store lookups |

| `products` | idx_products_upc | `upc` | Auto-matching |

| `price_history` | idx_price_product_date | `product_id, scraped_at DESC` | Time-series queries |

| `alerts` | idx_alerts_product | `product_id, is_active, deleted_at` | Check alerts on price change |

| `scrape_logs` | idx_scrape_product_date | `product_id, scraped_at DESC` | Recent failures |

| `notifications` | idx_notif_alert | `alert_id, created_at DESC` | Duplicate prevention |

  

### 2.4 Alert Logic

  

| Alert Type | Trigger Condition |

|------------|-------------------|

| `target_price` | Price ≤ target AND `in_stock` ≠ false |

| `percent_drop` | Price dropped X% AND `in_stock` ≠ false |

| `any_change` | Price changed AND `in_stock` ≠ false |

| `back_in_stock` | `in_stock` changed from false to true |

  

**Note:** `in_stock = NULL` (unknown) does not block alerts.

  

### 2.5 Canonical Product Matching

  

| Step | Action |

|------|--------|

| 1 | Extract UPC during scrape (if available) |

| 2 | Check for existing products with same UPC |

| 3 | If match found: auto-link + notify user |

| 4 | If no UPC: user can manually link via chat |

| 5 | On link: "Found same product at [store], linked for comparison!" |

  

### 2.6 Security Considerations

  

| Risk | Severity | Mitigation |

|------|----------|------------|

| URL injection | Medium | Validate URL format before storing |

| Scraped content XSS | High | Store only sanitized text, never raw HTML |

| JSON column injection | Low | SQLModel uses parameterized queries |

| Sensitive data in error_message | Low | Sanitize errors, never log tokens/keys |
### 2.7 Cross-Component Dependencies

  
| Component | Required Addition |

|-----------|-------------------|

| Component 3 (Scraper) | Extract `in_stock` and `upc` fields |

| Component 5 (Self-Healing) | Update `stores.selectors` in DB |

| Component 6 (Scheduler) | Daily pruning job for scrape_logs (30d) and notifications (90d) |

| Component 7 (Notifications) | Duplicate prevention via notifications table lookup |

| Component 1 (Agent) | Notify user on canonical product auto-linking |

  
---
## Component 3: Scraper Engine

### 3.1 Overview

The Scraper Engine handles all web scraping operations using Crawl4AI with Playwright. It implements a multi-strategy extraction approach prioritizing free methods before falling back to LLM-based extraction.

### Core Technologies

| Component | Technology |

|-----------|------------|

| Scraping Engine | Crawl4AI (Playwright underneath) |

| Extraction Strategies | JSON-LD, CSS, XPath, LLM (all native) |

| Rate Limiting | Crawl4AI `RateLimiter` |

| Concurrency | Crawl4AI `MemoryAdaptiveDispatcher` |

| Anti-Detection | Crawl4AI stealth mode + `UserAgentGenerator` |

| robots.txt | Crawl4AI native `check_robots_txt` |
## 3.2 Extraction Priority

Extraction attempts follow this waterfall to minimize LLM token costs:
| Priority | Strategy | Cost | Use Case |

|----------|----------|------|----------|

| 1st | JSON-LD | Free | Structured data in `<script type="application/ld+json">` |

| 2nd | CSS Selectors | Free | Known stores with pre-configured selectors |

| 3rd | XPath | Free | Edge cases CSS cannot handle (text content, sibling traversal) |

| 4th | LLM Extraction | Tokens | Unknown stores or when all else fails |

  

### Implementation

  

```python

from crawl4ai import JsonCssExtractionStrategy, JsonXPathExtractionStrategy, LLMExtractionStrategy

  

# Priority waterfall

strategies = [

    ("json_ld", JsonCssExtractionStrategy(schema=json_ld_schema)),

    ("css", JsonCssExtractionStrategy(schema=store_selectors)),

    ("xpath", JsonXPathExtractionStrategy(schema=xpath_schema)),

    ("llm", LLMExtractionStrategy(llm_config=llm_config, schema=product_schema))

]

```

  

## 3.3 Store Tiers

Simplified 2-tier system using existing database columns:

| Indicator | Tier | Behavior |
|-----------|------|----------|
| `is_whitelisted=TRUE` + `selectors` populated | **Known** | Use CSS/XPath extraction, fast & free |
| `is_whitelisted=FALSE` + `selectors` empty | **Scanned** | Must use `scan_website` tool first, then LLM extraction |

**Note:** Unknown URLs are no longer auto-allowed. Users must explicitly scan a new website before adding products from it. This prevents SSRF and ensures safe extraction.

## 3.4 Scan Website Tool

The `scan_website` tool analyzes a website's structure before adding it to the whitelist.

### Flow
```
User: "Can you scan bestdeals.ca so I can track products there?"
           │
           ▼
    ┌──────────────────┐
    │ Validate URL     │ → Block private IPs, check robots.txt
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │ Fetch Sample     │ → Load homepage + sample product page
    │ Pages            │    with stealth mode
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │ Structure        │ → Check for JSON-LD, product schema,
    │ Analysis         │    price elements, standard markup
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │ Security Check   │ → Validate no login required,
    │                  │    check for anti-bot measures
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │ Generate Report  │ → Return feasibility + suggested selectors
    └──────────────────┘
```

### ScanResult Response

```python
class ScanResult(BaseModel):
    domain: str
    feasible: bool                    # Can we extract products?
    confidence: float                 # 0.0-1.0 extraction confidence
    has_json_ld: bool                 # Structured data available?
    suggested_selectors: dict | None  # CSS selectors if found
    risks: list[str]                  # Potential issues
    recommendation: str               # Human-readable summary
```

### Example Output
```
✅ Scan complete for bestdeals.ca

Feasibility: HIGH (confidence: 0.85)
- Found JSON-LD product schema
- Standard price markup detected
- No login required

Risks:
- Aggressive rate limiting detected (recommend 5s delays)

Would you like me to add this store to your whitelist?
```

### Security Checks
| Check | Action if Failed |
|-------|-----------------|
| Private IP | Block immediately |
| robots.txt disallows | Warn user, proceed only if they confirm |
| Login required | Mark as unfeasible |
| Heavy anti-bot | Warn user of potential issues |
| No product structure found | Mark as unfeasible |

## 3.5 Retry Strategy

Hybrid approach: Crawl4AI native + custom wrapper for UX feedback.
### Retry Matrix

| Error Type | Retry? | Attempts | Behavior |

|------------|--------|----------|----------|

| Network errors/timeouts | Yes | 3 | Exponential backoff |

| 5xx server errors | Yes | 3 | Exponential backoff |

| 429 rate limited | Yes | 3 | Exponential backoff |

| 403 forbidden | Yes | 1 | Single retry, then fail |

| 404 not found | No | 0 | Mark `broken_link` |

| CAPTCHA detected | No | 0 | Mark for review |

| Parse failure | No | 0 | Increment `consecutive_failures` (self-healing after 3) |

  
### User Feedback

Real-time messages during retries:

- "Retrying (1/3)..."

- "Retrying (2/3)..."

- On final failure: "Offer to notify when next scheduled check succeeds"

  
## 3.5 Block Detection & Evasion 

### Detection Layers

1. `result.success` (Crawl4AI native)

2. `result.status_code` (429/403/503)

3. Keyword scan in `result.html` (CAPTCHA, "access denied", "blocked")

4. Data validation (price/title present?)

### Progressive Evasion Strategy
| Level | Configuration | When Used |

|-------|---------------|-----------|

| 1 | Regular browser + stealth mode | Default |

| 2 | `UndetectedAdapter` + headless=False | After block detection |
### Implementation

  

```python

from crawl4ai import BrowserConfig, UndetectedAdapter

from crawl4ai.user_agent_generator import UserAgentGenerator

  

ua_generator = UserAgentGenerator()

  

# Level 1: Default

browser_config = BrowserConfig(

    enable_stealth=True,

    headless=True,

    user_agent=ua_generator.generate(device_type="desktop", browser_type="chrome")

)

  

# Level 2: After block detected

adapter = UndetectedAdapter()

browser_config = BrowserConfig(

    enable_stealth=True,

    headless=False  # Better evasion

)

```

## 3.6 Rate Limiting

Per-domain rate limiting using Crawl4AI native `RateLimiter`:

  

```python

from crawl4ai import RateLimiter

  

rate_limiter = RateLimiter(

    base_delay=(2.0, 5.0),      # Random 2-5s between requests

    max_delay=60.0,             # Cap at 60s after backoff

    max_retries=3,              # Aligns with retry strategy

    rate_limit_codes=[429, 503, 403]

)

```

  
### Features

- **Per-domain tracking**: Automatic delay enforcement per domain

- **Exponential backoff**: On rate limit codes with jitter

- **Future enhancement**: Per-store overrides using `stores.rate_limit_rpm` column

  
## 3.7 Timeout Configuration

  
```python

from crawl4ai import CrawlerRunConfig

  

config = CrawlerRunConfig(

    page_timeout=30000,           # 30s page load (matches C1 guardrail)

    delay_before_return_html=1.0, # 1s extra wait for JS

    wait_for="css:[data-automation='buybox-price']"  # Per-store selector

)

```

  

| Setting | Value | Purpose |

|---------|-------|---------|

| `page_timeout` | 30000ms | Max page load time |

| `delay_before_return_html` | 1.0s | Wait for JS after load event |

| `wait_for` | Per-store | CSS selector to wait for (stored in `stores.selectors`) |

  

## 3.8 Concurrency Control

Memory-adaptive concurrency for Oracle Cloud free tier (1GB RAM):

  

```python

from crawl4ai import MemoryAdaptiveDispatcher

  

dispatcher = MemoryAdaptiveDispatcher(

    memory_threshold_percent=70.0,  # Auto-pause above 70%

    check_interval=1.0,             # Check every 1 second

    max_session_permit=3            # Max 3 concurrent browsers

)

```

### Resource Calculations

| Metric | Value |

|--------|-------|

| Browser memory | ~200MB each |

| Max instances | 3 |

| Total browser memory | ~600MB |

| Memory threshold | 70% of 1GB = 700MB |

| Batch performance | 50 products ÷ 3 concurrent × 3.5s = ~60 seconds |
## 3.9 robots.txt Compliance

Always respect robots.txt:

```python

config = CrawlerRunConfig(

    check_robots_txt=True

)

```

  

### Behavior
| Scenario | Action |

|----------|--------|

| URL allowed | Proceed with scrape |
| URL disallowed | Return 403, mark as `robots_blocked` |
| robots.txt unreachable | Proceed (assume allowed) |
| Cache | `/app/data/robots/` (mounted volume), 7-day TTL |

### User Notification

When blocked: "This product can't be monitored due to site restrictions."

## 3.10 Content Sanitization

Multi-layer defense against XSS and injection:

### Layer 1: Crawl4AI HTML Cleanup

  

```python

config = CrawlerRunConfig(

    excluded_tags=["script", "style", "iframe", "form", "object", "embed"],

    remove_forms=True

)

```

  

### Layer 2: Extraction Strategy

  

```python

schema = {

    "fields": [

        {"name": "title", "selector": "h1", "type": "text"},  # Returns text only

        {"name": "price", "selector": ".price", "type": "text"}

    ]

}

```

  

### Layer 3: Storage Sanitization (Python)

  

```python

import re

import html

  

def sanitize_scraped_content(value: str, max_length: int) -> str:

    # Strip HTML tags

    value = re.sub(r'<[^>]+>', '', value)

    # Escape HTML entities

    value = html.escape(value)

    # Enforce length limit

    return value[:max_length]

  

def validate_url(url: str) -> bool:

    # Only allow http/https schemes

    return url.startswith(('http://', 'https://'))

```

### Length Limits

| Field | Max Length |

|-------|------------|

| Product name | 500 chars |

| Description | 10,000 chars |

| URLs | 2,000 chars |

  

### Layer 4: Frontend (React)

  

- Default escaping (never use `dangerouslySetInnerHTML`)

- All scraped content displayed as text, not HTML
## 3.11 User-Agent Strategy

Crawl4AI native `UserAgentGenerator` with realistic browser signatures:

  

```python

from crawl4ai import BrowserConfig

from crawl4ai.user_agent_generator import UserAgentGenerator

  

ua_generator = UserAgentGenerator()

  

browser_config = BrowserConfig(

    enable_stealth=True,

    user_agent=ua_generator.generate(

        device_type="desktop",

        browser_type="chrome"  # Rotate: chrome, firefox, edge

    )

)

```

  

### Configuration

| Setting | Value |

|---------|-------|

| Device type | `desktop` (matches viewport) |

| Browser types | Rotate: `chrome`, `firefox`, `edge` |

| Rotation frequency | Per-request for batch scraping |

| Stealth mode | Always enabled |

  

### Ethical Consideration

  

Browser-like UAs are industry standard for price monitoring. We access public product pages, respect robots.txt, and rate-limit requests.

  

## 3.12 Security Risks & Mitigations

  

| Risk | Severity | Mitigation |

|------|----------|------------|

| SSRF (Server-Side Request Forgery) | HIGH | IP validation + redirect checks + 10MB limit + Content-Type validation |

| XSS from scraped content | HIGH | 4-layer sanitization (Crawl4AI + extraction + storage + frontend) |

| Bot detection/blocking | MEDIUM | Stealth mode + UserAgentGenerator + progressive evasion |

| Rate limiting/IP bans | MEDIUM | Native RateLimiter + exponential backoff + per-domain tracking |

| robots.txt violation | LOW | Always respect with `check_robots_txt=True` |

| Credential leakage in logs | MEDIUM | Never log full URLs with query params |

| Resource exhaustion | MEDIUM | MemoryAdaptiveDispatcher with 70% threshold |

| Malicious URL injection | MEDIUM | URL sanitization, private IP blocking |

  

## 3.13 Cross-Component Dependencies

  

| Component | Dependency |

|-----------|------------|

| Component 1 (Agent) | Calls `scrape_product` tool |

| Component 2 (Database) | Reads `stores.selectors`, writes `scrape_logs` |

| Component 5 (Self-Healing) | Updates `stores.selectors` when broken |

| Component 6 (Scheduler) | Triggers batch scrapes |

  

## 3.14 Module Structure

  

```

backend/src/scraper/

├── __init__.py

├── engine.py           # Main scraper orchestration

├── strategies.py       # Extraction strategy implementations

├── rate_limiter.py     # Rate limiting configuration

├── sanitization.py     # Content sanitization utilities

├── validators.py       # URL/IP validation (SSRF protection)

└── user_agent.py       # User-agent generation wrapper

```

---

## Component 4: RAG System

### 4.1 Purpose

  

The RAG (Retrieval-Augmented Generation) system enables semantic search over tracked products. Users can find products using natural language queries like "that Nike shoe I added last week" or "electronics from Best Buy" instead of requiring exact keyword matches.

### 4.2 Core Responsibilities

| Responsibility | Description |

|----------------|-------------|

| **Product Indexing** | Embed and store product metadata when products are added |

| **Semantic Search** | Power the `search_products` agent tool with vector similarity |

| **Hybrid Search** | Combine vector search with metadata filters (store, price range) |

| **Index Maintenance** | Update embeddings on name/description change, remove on delete |

  

### 4.3 Technology Stack

  

| Component | Choice | Rationale |

|-----------|--------|-----------|

| **Vector DB** | ChromaDB | Proven, good Python API, migrates to pgvector for SaaS |

| **Embedding Model** | OpenAI `text-embedding-3-small` | $0.02/1M tokens (~$0.02/year), excellent quality |

| **Dimensions** | 1536 | Model default |

| **Distance Metric** | Cosine similarity | Standard for text embeddings |

  

### 4.4 What Gets Embedded

  

| Field | Embedded | Rationale |

|-------|----------|-----------|

| `name` | ✅ | Primary search target |

| `description` | ✅ | Rich semantic content |

| `store.name` | ✅ | "Find my Walmart products" |

| `category` | ✅ | "Show me electronics" |

| `brand` | ✅ | "Nike products" |

| `current_price` | ❌ | Use metadata filter instead |

| `url` | ❌ | Not semantically meaningful |

  

**Combined text for embedding:**

```

{brand} {name} - {category} from {store_name}

{description}

```

  

### 4.5 ChromaDB Collection Schema

  

```python

collection = chroma_client.get_or_create_collection(

    name="products",

    metadata={"hnsw:space": "cosine"}

)

  

# Document structure

{

    "id": str(product.id),  # UUID as string

    "embedding": [...],      # 1536 dimensions

    "document": "Nike Air Max 90 - Footwear from Foot Locker\nClassic sneaker...",

    "metadata": {

        "store_domain": "footlocker.ca",

        "store_name": "Foot Locker",

        "brand": "Nike",

        "category": "Footwear",

        "current_price": 159.99,

        "in_stock": True,

        "created_at": "2024-12-17T10:00:00Z"

    }

}

```

  

### 4.6 Search Strategy

  

```

User Query: "Nike shoes under $150"

           │

           ▼

    ┌──────────────┐

    │ Embed Query  │  → Vector for "Nike shoes"

    └──────┬───────┘

           │

           ▼

    ┌──────────────────┐

    │ ChromaDB Search  │  → Top 10 by similarity

    │ with metadata    │     where current_price < 150

    │ filters          │

    └──────┬───────────┘

           │

           ▼

    ┌──────────────────┐

    │ SQLite Enrich    │  → Join with products table

    └──────┬───────────┘     for full product details

           │

           ▼

    Return results to agent

```

  

### 4.7 Similarity Threshold

  

| Setting | MVP | Future (Large DB) |

|---------|-----|-------------------|

| **Threshold** | None (return top N) | 0.3 minimum |

| **Rationale** | Agent filters contextually | Reduce noise at scale |

  

**MVP behavior:** Return top 10 results regardless of score. Agent decides relevance based on context.

  

**Future:** When database grows beyond ~1000 products, add configurable threshold to filter low-relevance results before returning to agent.

  

### 4.8 Fallback Strategy

  

When ChromaDB is unavailable (corrupt file, failed to load):

  

| Step | Action |

|------|--------|

| 1 | Catch ChromaDB exception |

| 2 | Log warning with error details |

| 3 | Fall back to SQLite `LIKE` query |

| 4 | Include note in response: "basic search mode" |

  

```python

async def search(self, query: str, ...) -> list[SearchResult]:

    try:

        return await self._vector_search(query, ...)

    except ChromaDBError as e:

        logger.warning(f"ChromaDB unavailable, falling back to SQLite: {e}")

        return await self._sqlite_fallback(query, ...)

```

  

### 4.9 Index Sync Strategy

  

| Event | Action |

|-------|--------|

| Product created | Embed and index immediately |

| Price/stock updated | Update metadata only (no re-embed) |

| Name/description changed | Re-embed and update |

| Product soft-deleted | Remove from ChromaDB |

| Product restored | Re-index |

  

```python

async def update_product(self, product: Product, old_product: Product):

    if (product.name != old_product.name or

        product.description != old_product.description):

        # Re-embed - semantic content changed

        await self.rag_service.index_product(product)

    else:

        # Metadata only - no re-embed needed

        await self.rag_service.update_metadata(product)

```

  

### 4.10 API Design

  

```python

class RAGService:

    async def index_product(self, product: Product) -> None:

        """Add or update product in vector store (generates embedding)"""

    async def update_metadata(self, product: Product) -> None:

        """Update metadata without re-embedding (price, stock)"""

    async def remove_product(self, product_id: UUID) -> None:

        """Remove product from vector store"""

    async def search(

        self,

        query: str,

        store_domain: str | None = None,

        min_price: float | None = None,

        max_price: float | None = None,

        in_stock: bool | None = None,

        limit: int = 10

    ) -> list[SearchResult]:

        """Semantic search with optional metadata filters"""

    async def reindex_all(self) -> int:

        """Full reindex - admin recovery operation"""

```

  

### 4.11 Configuration

  

```python

class RAGSettings(BaseSettings):

    # Embedding

    embedding_model: str = "text-embedding-3-small"

    embedding_dimensions: int = 1536

    # ChromaDB

    chromadb_path: str = "/app/data/chromadb"

    collection_name: str = "products"

    # Search

    search_limit_default: int = 10

    search_limit_max: int = 50

    # similarity_threshold: float = 0.3  # Future: enable for large DB

```

  

### 4.12 Error Handling

  

| Scenario | Handling |

|----------|----------|

| Embedding API fails | Retry 3x with exponential backoff, then skip (log error) |

| Embedding API rate limit | Queue and retry after delay |

| ChromaDB unavailable | Fall back to SQLite LIKE search |

| Product not in index | Return from SQLite only, flag for reindex |

| Corrupt ChromaDB | Log error, trigger `reindex_all()` on next startup |

  

### 4.13 Security Considerations

  
| Risk | Severity | Mitigation |

|------|----------|------------|

| Prompt injection via product name | Low | Embeddings are mathematical vectors, not executable |

| Sensitive data in embeddings | Low | Only index public product info (name, description) |

| ChromaDB file access | Low | Same filesystem permissions as SQLite |

  
### 4.14 Cross-Component Dependencies

| Component | Dependency |

|-----------|------------|

| Component 1 (Agent) | Calls `search_products` tool → RAGService.search() |

| Component 2 (Database) | RAG reads product data, syncs on CRUD operations |

| Component 5 (Self-Healing) | May trigger reindex if product data corrected |
### 4.15 Module Structure
```

backend/src/rag/

├── __init__.py

├── service.py          # RAGService class

├── embeddings.py       # OpenAI embedding wrapper

├── search.py           # Search logic with hybrid filtering

└── sync.py             # Index maintenance (sync, reindex_all)

```

---

## Component 5: Self-Healing Module

### 5.1 Purpose

The Self-Healing Module automatically detects and recovers from scraping failures without user intervention. When website structures change and CSS selectors break, the module regenerates selectors using LLM extraction and updates the store configuration.

### 5.2 Core Responsibilities

| Responsibility | Description |

|----------------|-------------|

| **Failure Detection** | Identify broken selectors vs temporary errors |

| **Selector Regeneration** | Re-run LLM extraction to discover new selectors |

| **Store Health Tracking** | Monitor success rates, flag problematic stores |

| **Escalation** | Notify user when automatic recovery fails |

  

### 5.3 Failure Classification

  

| Failure Type | Cause | Self-Healable? |

|--------------|-------|----------------|

| **Parse failure** | Selectors return null/empty | ✅ Yes |

| **Price validation fail** | Price extracted but invalid ($0, negative, impossibly high) | ✅ Yes |

| **Structure change** | HTML changed, selectors don't match | ✅ Yes |

| **404 Not Found** | Product removed/URL changed | ❌ No (broken link) |

| **403/Blocked** | IP banned, anti-bot triggered | ❌ No (evasion issue) |

| **Network timeout** | Temporary server issue | ❌ No (retry handles this) |

  

### 5.4 Trigger Conditions

  

| Trigger | Threshold | Action |

|---------|-----------|--------|

| Single parse failure | 1 failure | Log, increment `consecutive_failures` |

| **Consecutive failures** | **3 failures** | **Trigger self-healing** |

| Store-wide failures | >50% products OR 5+ products failing | Flag store for review |

  

**Note:** This overrides the C3 retry matrix implication. Parse failures increment the counter; self-healing triggers only after 3 consecutive failures to avoid wasting LLM tokens on transient issues.

  

### 5.5 Recovery Flow

  

```

Scrape Attempt Failed (Parse Failure)

              │

              ▼

   ┌─────────────────────┐

   │ Increment           │

   │ consecutive_failures│

   └──────────┬──────────┘

              │

              ▼

      ┌───────────────┐

      │ Failures ≥ 3? │───No──→ Wait for next scheduled scrape

      └───────┬───────┘

              │ Yes

              ▼

      ┌───────────────┐

      │ Healing       │

      │ attempts < 3? │───No──→ Mark status=error, notify user

      └───────┬───────┘

              │ Yes

              ▼

   ┌─────────────────────┐

   │ Trigger LLM         │

   │ Selector Regen      │

   │ (store-wide)        │

   └──────────┬──────────┘

              │

         ┌────┴────┐

         │ Success? │

         └────┬────┘

              │

        Yes ──┴── No

         │        │

         ▼        ▼

   ┌──────────┐  ┌──────────────────┐

   │ Update   │  │ Increment        │

   │ store    │  │ healing_attempts │

   │ selectors│  │ Wait for next    │

   │ Reset    │  │ scheduled scrape │

   │ failures │  └──────────────────┘

   └──────────┘

```

  

### 5.6 Healing Scope

  

When self-healing triggers, it operates at **store level**:

  

| Scope | Behavior |

|-------|----------|

| **Selector regeneration** | Store-wide - updates `stores.selectors` |

| **Failure reset** | Product-specific - only triggering product resets |

| **Other products** | Reset on their next successful scrape |

  

**Rationale:** Selectors are stored per-store. If one product fails due to selector breakage, likely all products from that store are affected.

  

### 5.7 Selector Regeneration

  

```python

async def regenerate_selectors(self, product: Product, html: str) -> bool:

    """

    Regenerate store selectors using LLM extraction.

    Called after 3 consecutive failures.

    """

    # 1. Run LLM extraction on current page HTML

    result = await llm_extractor.extract(html, product_schema)

    if not result.success:

        return False

    # 2. Ask LLM to generate CSS selectors for found elements

    selectors = await llm_extractor.generate_selectors(

        html=html,

        extracted_data=result.data

    )

    # 3. Validate selectors work on current page

    validated = await validate_selectors(html, selectors)

    if validated:

        # 4. Update store selectors in DB (affects all products)

        await store_repo.update_selectors(

            domain=product.store_domain,

            selectors=selectors

        )

        # 5. Reset failures for this product only

        await product_repo.reset_failures(product.id)

        return True

    return False

```

  

### 5.8 Healing Attempts Tracking

  

| Field | Location | Purpose |

|-------|----------|---------|

| `consecutive_failures` | `products` table | Tracks scrape failures (resets on success) |

| `healing_attempts` | In-memory or `products` table | Tracks healing tries (resets on healing success) |

  

**Flow across days:**

  

| Day | Event | `consecutive_failures` | `healing_attempts` | Action |

|-----|-------|------------------------|--------------------| -------|

| 1 | Scrape fails | 1 | 0 | Log |

| 1 | Scrape fails | 2 | 0 | Log |

| 1 | Scrape fails | 3 | 0 | Trigger healing → fails |

| 1 | (after healing) | 3 | 1 | Wait |

| 2 | Scrape fails | 4 | 1 | Trigger healing → fails |

| 2 | (after healing) | 4 | 2 | Wait |

| 3 | Scrape fails | 5 | 2 | Trigger healing → fails |

| 3 | (after healing) | 5 | 3 | **Mark error, notify user** |

  

### 5.9 Store Health Tracking

  

| Metric | Calculation | Storage |

|--------|-------------|---------|

| **Success rate** | Successful / Total scrapes (7-day window) | `stores.success_rate` |

| **Last success** | Timestamp of last successful scrape | `stores.last_success_at` |

| **Failing products** | Count where `status=error` | Calculated on demand |

  

**Store flagging triggers:**

- **50% failure rate** across products from that store, OR

- **5+ products** in `error` status from that store  

### 5.10 LLM Budget

Self-healing uses the **shared daily token budget** (100k tokens/day from C1).

| Operation | Estimated Tokens |

|-----------|------------------|

| LLM extraction | 500-1000 |

| Selector generation | 300-500 |

| **Per healing attempt** | **~1000-1500** |
**Rationale:**

- Simplicity - one budget to track

- Self-limiting - mass breakage stops before budget exhaustion

- Healing typically runs overnight during scheduled scrapes, not competing with daytime chat

### 5.11 User Notifications

| Event | Notify? | Message |

|-------|---------|---------|

| Healing succeeds | ❌ No | Silent (logged only) |

| Healing fails (final) | ✅ Yes | Product-level notification |

| Store flagged | ✅ Yes | Store-level warning |

  

**Product failure notification:**

```

Unable to track "Nike Air Max 90" from Walmart.

The website may have changed.

[Retry] [Remove]

```

  

**Store flagged notification:**

```

⚠️ Multiple products from Walmart are failing.

The site may be blocking us or has changed significantly.

[View affected products]

```
### 5.12 Error Handling

| Scenario | Handling |

|----------|----------|

| LLM extraction fails | Count as failed healing attempt |

| LLM rate limited | Queue, retry with backoff |

| Selector validation fails | Count as failed healing attempt |

| Daily token budget exhausted | Skip healing, retry tomorrow |

| Store selectors update fails | Log error, don't reset product failures |

### 5.13 API Design
```python

class SelfHealingService:

    async def handle_scrape_failure(

        self,

        product: Product,

        error_type: str,

        html: str | None

    ) -> HealingResult:

        """Called by scraper on failure. Decides whether to heal."""

    async def attempt_healing(

        self,

        product: Product,

        html: str

    ) -> bool:

        """Execute healing attempt. Returns success status."""

    async def check_store_health(

        self,

        store_domain: str

    ) -> StoreHealth:

        """Calculate and return store health metrics."""

    async def get_flagged_stores(self) -> list[StoreHealth]:

        """List stores exceeding failure thresholds."""

    async def get_failing_products(

        self,

        store_domain: str | None = None

    ) -> list[Product]:

        """List products with status=error."""

    async def retry_product(self, product_id: UUID) -> bool:

        """Manual retry triggered by user. Resets counters."""

```

  

### 5.14 Configuration

  

```python

class HealingSettings(BaseSettings):

    # Thresholds

    consecutive_failures_threshold: int = 3

    max_healing_attempts: int = 3

    store_failure_rate_threshold: float = 0.5  # 50%

    store_failure_count_threshold: int = 5

    # Health calculation

    health_window_days: int = 7

```

  

### 5.15 Security Considerations
| Risk | Severity | Mitigation |

|------|----------|------------|

| LLM token exhaustion via forced failures | Medium | Shared budget cap, healing attempt limit |

| Malicious selector injection | Low | Validate selectors before saving |

| Infinite healing loops | Low | Max 3 attempts, then stop |

  

### 5.16 Cross-Component Dependencies

  

| Component | Dependency |

|-----------|------------|

| Component 3 (Scraper) | Calls `handle_scrape_failure()` on parse errors |

| Component 3 (Scraper) | Uses regenerated `stores.selectors` |

| Component 6 (Scheduler) | Healing runs during scheduled scrapes |

| Component 7 (Notifications) | Sends failure/flagging alerts |

| Component 4 (RAG) | May re-index if product data corrected |
### 5.17 Module Structure
```

backend/src/healing/

├── __init__.py

├── service.py          # SelfHealingService class

├── detector.py         # Failure classification logic

├── regenerator.py      # Selector regeneration with LLM

└── health.py           # Store health calculations

```

---

## Component 6: Scheduler

### 6.1 Purpose
The Scheduler manages automated price checking jobs using APScheduler. It handles product-level and store-level schedules, batches scrapes efficiently, and runs maintenance tasks like data retention cleanup.

### 6.2 Core Responsibilities

| Responsibility | Description |

|----------------|-------------|

| **Price Check Scheduling** | Run daily scrapes for tracked products |

| **Batch Optimization** | Group products by store for efficient scraping |

| **Maintenance Jobs** | Prune old scrape_logs (30d) and notifications (90d) |

| **Job Persistence** | Survive container restarts via SQLite jobstore |

| **Missed Job Recovery** | Coalesce missed runs into single execution |

  
### 6.3 Technology

| Component | Choice | Rationale |

|-----------|--------|-----------|

| **Scheduler** | APScheduler (AsyncIOScheduler) | Async-native, CRON support, mature |

| **Job Store** | SQLAlchemyJobStore (SQLite) | Persists jobs, survives restarts |

| **Triggers** | CronTrigger | Standard CRON expressions |

### 6.4 Job Types

| Job Type | Schedule | Purpose |
|----------|----------|---------|
| **Default daily scrape** | 6:00 AM ± 30 min jitter | Check all active products |
| **Custom product schedule** | User-defined CRON | Per-product override |
| **Store-wide schedule** | User-defined CRON | All products from a store |
| **Data retention cleanup** | Weekly (Sunday 3 AM) | Prune scrape_logs (30d), notifications (90d) |
| **Store health calculation** | Daily (4 AM) | Calculate 7-day success rates |
### 6.5 Default Schedule

| Setting | Value | Rationale |

|---------|-------|-----------|

| **Time** | 6:00 AM EST | Fresh prices before user's day starts |
| **Jitter** | ± 30 minutes | Anti-detection, spread load |
| **Timezone** | UTC internally, EST display | Consistent storage, user-friendly display |

  

```python

scheduler.add_job(

    daily_scrape,

    CronTrigger(hour=6, minute=0, jitter=1800),  # 1800s = 30min

    id='daily_scrape'

)

```
### 6.6 Schedule Hierarchy

When determining when to scrape a product:

| Priority | Level | Source |

|----------|-------|--------|

| 1 (Highest) | Product-specific | `schedules` where `product_id` is set |

| 2 | Store-wide | `schedules` where `store_domain` is set |

| 3 (Lowest) | System default | 6 AM daily with jitter |

  

### 6.7 Minimum Schedule Interval

| Setting | MVP | Future SaaS |

|---------|-----|-------------|

| **Minimum** | 24 hours (daily) | Hourly+ for paid tiers |

| **Validation** | Reject CRON running more than once per day | Tier-based limits |

  

```python

def validate_cron(cron_expression: str) -> bool:

    if runs_more_than_once_per_day(cron_expression):

        raise ValueError("Minimum schedule interval is 24 hours")

    return True

```

### 6.8 Batch Strategy

Products are processed **store-by-store** for efficiency:

```

Daily Scrape Job Triggered

          │

          ▼

┌─────────────────────┐

│ Load active products│

│ GROUP BY store_domain│

└──────────┬──────────┘

          │

          ▼

┌─────────────────────┐

│ For each store:     │

│ 1. Load selectors   │

│ 2. Init browser     │

│ 3. Scrape products  │

│    (3 concurrent)   │

│ 4. Close browser    │

└──────────┬──────────┘

          │

          ▼

┌─────────────────────┐

│ For each result:    │

│ - Update prices     │

│ - Check alerts      │

│ - Handle failures   │

└─────────────────────┘

```

  

**Rationale:**

- Reuse browser session per store

- Same selectors loaded once

- RateLimiter handles intra-store delays

- Natural gap between stores

### 6.9 APScheduler Configuration

  

```python

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from apscheduler.triggers.cron import CronTrigger

  

scheduler = AsyncIOScheduler(

    jobstores={

        'default': SQLAlchemyJobStore(url='sqlite:///data/perpee.db')

    },

    job_defaults={

        'coalesce': True,           # Combine missed runs into one

        'max_instances': 1,         # Prevent overlapping runs

        'misfire_grace_time': 3600  # 1 hour grace period

    },

    timezone='UTC'

)

```

### 6.10 Missed Job Handling

  

| Setting | Value | Behavior |

|---------|-------|----------|

| `coalesce` | `True` | Multiple missed runs → single execution |

| `misfire_grace_time` | 3600 (1 hour) | Jobs missed by >1 hour are skipped |

| `max_instances` | 1 | Prevent overlapping job runs |

  

**Example scenario:**

- Container down from 5 AM to 10 AM

- 6 AM job was missed

- At 10 AM: Job runs once (catches up)
### 6.11 Schedule Limits

| Setting | MVP | Future SaaS |

|---------|-----|-------------|

| **Max schedules** | No limit | Tier-based (e.g., Free: 10, Pro: 100) |

### 6.12 Maintenance Jobs

#### Data Retention Cleanup (Weekly - Sunday 3 AM)
```python

async def cleanup_old_data():

    # Prune scrape_logs older than 30 days

    await db.execute(

        delete(ScrapeLog).where(

            ScrapeLog.scraped_at < datetime.now() - timedelta(days=30)

        )

    )

    # Prune notifications older than 90 days

    await db.execute(

        delete(Notification).where(

            Notification.created_at < datetime.now() - timedelta(days=90)

        )

    )

```

  

#### Store Health Calculation (Daily 4 AM)

  

```python

async def calculate_store_health():

    for store in await get_all_stores():

        # Calculate 7-day success rate

        success_rate = await calculate_success_rate(

            store.domain,

            window_days=7

        )

        await update_store(store.domain, success_rate=success_rate)

```

  

### 6.13 API Design

  

```python

class SchedulerService:

    async def start(self) -> None:

        """Start scheduler on app startup"""

    async def shutdown(self) -> None:

        """Graceful shutdown, wait for running jobs"""

    async def create_schedule(

        self,

        cron_expression: str,

        product_id: UUID | None = None,

        store_domain: str | None = None

    ) -> Schedule:

        """Create custom schedule (validates daily minimum)"""

    async def update_schedule(

        self,

        schedule_id: UUID,

        cron_expression: str | None = None,

        is_active: bool | None = None

    ) -> Schedule:

        """Modify existing schedule"""

    async def delete_schedule(self, schedule_id: UUID) -> bool:

        """Remove schedule (soft delete)"""

    async def run_now(self, product_id: UUID) -> ScrapeResult:

        """Manual immediate scrape (bypasses schedule)"""

    async def get_next_runs(self, limit: int = 10) -> list[ScheduledRun]:

        """Preview upcoming scheduled runs"""

    async def pause_schedule(self, schedule_id: UUID) -> Schedule:

        """Temporarily disable a schedule"""

    async def resume_schedule(self, schedule_id: UUID) -> Schedule:

        """Re-enable a paused schedule"""

```

  

### 6.14 Lifecycle Integration

  

```python

# In main.py

from contextlib import asynccontextmanager

  

@asynccontextmanager

async def lifespan(app: FastAPI):

    # Startup

    scheduler_service.start()

    yield

    # Shutdown

    await scheduler_service.shutdown()

  

app = FastAPI(lifespan=lifespan)

```

  

### 6.15 Configuration

  

```python

class SchedulerSettings(BaseSettings):

    # Default schedule

    default_scrape_hour: int = 6

    default_scrape_minute: int = 0

    default_jitter_seconds: int = 1800  # 30 min

    # Job behavior

    misfire_grace_time: int = 3600  # 1 hour

    max_instances: int = 1

    coalesce: bool = True

    # Maintenance

    cleanup_hour: int = 3

    health_calc_hour: int = 4

    # Limits

    min_schedule_interval_hours: int = 24

    # Timezone

    timezone: str = "UTC"

```

  

### 6.16 Error Handling

  

| Scenario | Handling |

|----------|----------|

| Job raises exception | Log error, job runs again next scheduled time |

| Database unavailable | Retry with backoff, alert if persistent |

| Scheduler fails to start | App startup fails (critical dependency) |

| Job runs too long | No timeout (batching handles via scraper timeouts) |

  

### 6.17 Security Considerations

  

| Risk | Severity | Mitigation |

|------|----------|------------|

| CRON injection | Low | Validate CRON syntax before storing |

| Job flooding | Low | `max_instances=1`, daily minimum interval |

| Resource exhaustion | Medium | MemoryAdaptiveDispatcher limits (from C3) |

  

### 6.18 Cross-Component Dependencies  

| Component | Dependency |

|-----------|------------|

| Component 1 (Agent) | `create_schedule` tool calls SchedulerService |

| Component 2 (Database) | Reads `schedules` table, jobstore uses SQLite |

| Component 3 (Scraper) | Scheduler triggers batch scrapes |

| Component 5 (Self-Healing) | Healing attempts run during scheduled scrapes |

| Component 7 (Notifications) | Scheduler triggers alert checks after scrapes |

  

### 6.19 Module Structure
```

backend/src/scheduler/

├── __init__.py

├── service.py          # SchedulerService class

├── jobs.py             # Job definitions (daily_scrape, cleanup, health)

├── batching.py         # Store-grouped batch logic

└── triggers.py         # CRON parsing and validation

```

---

## Component 7: Notifications

### 7.1 Purpose

The Notifications module sends alerts to users when price conditions are met or system events occur. MVP supports email only via Resend.

### 7.2 Core Responsibilities

| Responsibility | Description |
|----------------|-------------|
| **Alert Delivery** | Send email notifications when alerts trigger |
| **Duplicate Prevention** | Avoid re-notifying until price changes again |
| **Retry Handling** | Retry failed sends with backoff |
| **System Notifications** | Scraper failures, store issues |

### 7.3 Channel

| Channel | Provider | Status |
|---------|----------|--------|
| **Email** | Resend | ✅ MVP |
| Slack/Discord | - | 🔮 Post-MVP |

### 7.4 Notification Types

| Type | Trigger | Channel | Source |
|------|---------|---------|--------|
| **Price Alert** | Alert condition met (target_price, percent_drop, any_change) | Email | Scheduler |
| **Back in Stock** | Product `in_stock` changed from false to true | Email | Scheduler |
| **Product Error** | Self-healing failed after 3 attempts | Email | Self-Healing (C5) |
| **Store Flagged** | Store health threshold exceeded (50% OR 5+) | Email | Self-Healing (C5) |

  

### 7.5 Duplicate Prevention

Notifications are suppressed until the price changes again:

```python

async def should_notify(alert: Alert, product: Product) -> bool:

    last_notification = await get_last_notification(

        alert_id=alert.id,

        product_id=product.id

    )

    if not last_notification:

        return True  # Never notified before

    last_notified_price = last_notification.payload.get("price")

    return product.current_price != last_notified_price

```
  

### 7.6 Notification Timing

| Setting | MVP |

|---------|-----|

| **Timing** | Immediate |

| **Digest option** | Not implemented |

**MVP behavior:** Send notification immediately when alert triggers during scheduled scrape.

  
### 7.7 User Preferences

Stored in environment variables (MVP single user):

```env

# .env

USER_EMAIL=user@example.com
EMAIL_ENABLED=true
```

  
```python

class NotificationSettings(BaseSettings):

    user_email: str
    email_enabled: bool = True

```  

### 7.8 Email Implementation (Resend)
```python

import resend

  

async def send_email(to: str, subject: str, html: str) -> bool:

    resend.api_key = settings.resend_api_key

    response = await resend.Emails.send({

        "from": "Perpee <alerts@perpee.app>",

        "to": to,

        "subject": subject,

        "html": html

    })

    return response.get("id") is not None

```

  
### 7.9 Retry Strategy

Immediate retry with exponential backoff:

```python

async def send_with_retry(

    send_func: Callable,

    max_retries: int = 3

) -> str:

    for attempt in range(max_retries):

        try:

            success = await send_func()

            if success:

                return "sent"

        except TransientError:

            pass

        if attempt < max_retries - 1:

            await asyncio.sleep(2 ** attempt)  # 1s, 2s, 4s

    return "failed"

```

  

| Attempt | Delay | Total Elapsed |

|---------|-------|---------------|

| 1 | 0s | 0s |

| 2 | 1s | 1s |

| 3 | 2s | 3s |

| Fail | - | ~3-5s |

  

### 7.10 Message Templates

#### Price Alert Email
```

Subject: 🔔 Price Drop: {product_name}

  

{product_name} dropped to {new_price}!

  

Was: {old_price}

Now: {new_price}

Savings: {savings_amount} ({savings_percent}%)

  

{product_url}

  

Store: {store_name}

```

  

#### Product Error Email

```

Subject: ⚠️ Unable to track: {product_name}

  

We're having trouble tracking {product_name} from {store_name}.

  

The website may have changed or is blocking our access.

We'll keep trying, but you may want to check the product manually.

  

[View Product] [Remove from Tracking]

```

  

#### Store Flagged Email

  

```

Subject: ⚠️ Multiple products failing from {store_name}

  

{failing_count} products from {store_name} are having issues.

  

The site may be blocking us or has changed significantly.

  

[View Affected Products]

```

  

### 7.11 API Design

  

```python

class NotificationService:

    async def send_alert(

        self,

        alert: Alert,

        product: Product,

        old_price: float,

        new_price: float

    ) -> Notification:

        """Send notification for triggered alert"""

    async def send_product_error(

        self,

        product: Product

    ) -> Notification:

        """Notify about product tracking failure"""

    async def send_store_flagged(

        self,

        store: Store,

        failing_count: int

    ) -> Notification:

        """Notify about store-wide issues"""

    async def get_history(

        self,

        limit: int = 50,

        channel: str | None = None

    ) -> list[Notification]:

        """Get recent notification history"""

```

  

### 7.12 Configuration

  

```python

class NotificationSettings(BaseSettings):

    # Email (Resend)

    resend_api_key: str

    user_email: str

    email_enabled: bool = True

    email_from: str = "Perpee <alerts@perpee.app>"

    # Retry

    max_retry_attempts: int = 3

    # Templates

    templates_dir: str = "src/notifications/templates"

```

  

### 7.13 Error Handling

  

| Scenario | Handling |

|----------|----------|

| Resend API error | Retry 3x, then mark failed |


| Invalid email address | Mark failed, log error |

| Rate limited by provider | Retry with backoff |

| Template rendering error | Log error, send plain text fallback |

  

### 7.14 Security Considerations

  

| Risk | Severity | Mitigation |

|------|----------|------------|

| Email address exposure | Low | Stored in env, not DB |

| Notification content injection | Low | Escape all dynamic content in templates |

| API key exposure | Medium | Never log API keys, use env vars |

  

### 7.15 Cross-Component Dependencies

  

| Component | Dependency |

|-----------|------------|

| Component 2 (Database) | Writes to `notifications` table |

| Component 5 (Self-Healing) | Calls `send_product_error()`, `send_store_flagged()` |

| Component 6 (Scheduler) | Triggers alert checks after scrapes, prunes old notifications |

| Component 8 (API) | Exposes notification history endpoint |

  

### 7.16 Module Structure

  

```

backend/src/notifications/

├── __init__.py

├── service.py          # NotificationService class

├── channels/

│   ├── __init__.py

│   ├── email.py        # Resend integration


├── templates/

│   ├── price_alert.html

│   ├── product_error.html

│   └── store_flagged.html

└── formatters.py       # Message formatting utilities

```

---

## Component 8: API Endpoints

### 8.1 Purpose

The API layer exposes FastAPI endpoints for the frontend and handles real-time chat via WebSocket. It serves as the interface between the React UI and all backend services.

### 8.2 Core Responsibilities

| Responsibility | Description |

|----------------|-------------|

| **REST Endpoints** | CRUD operations for products, alerts, schedules |

| **WebSocket Chat** | Real-time agent conversation with streaming |

| **Static Files** | Serve React frontend build |

| **Error Handling** | Standardized error responses |

| **OpenAPI Docs** | Auto-generated API documentation |

  

### 8.3 Key Decisions

  

| Decision | Choice | Rationale |

|----------|--------|-----------|

| **Chat interface** | WebSocket only | Streaming responses, tool call visibility |

| **API versioning** | None for MVP | Single user, add `/v1/` for SaaS |

| **Pagination** | Offset-based | Simple, familiar, good enough for 500 products |

| **Rate limiting** | None for MVP | Agent guardrails handle expensive ops |

| **CORS** | Localhost whitelist | Dev only, same-origin in production |

| **Authentication** | None for MVP | Add Supabase Auth for SaaS |

  

### 8.4 Endpoint Groups

  

| Group | Base Path | Purpose |

|-------|-----------|---------|

| **Chat** | `/api/chat` | WebSocket for agent conversation |

| **Products** | `/api/products` | Product CRUD + price history |

| **Alerts** | `/api/alerts` | Alert CRUD |

| **Schedules** | `/api/schedules` | Schedule CRUD |

| **Stores** | `/api/stores` | Store list + health status |

| **System** | `/api/health`, `/api/stats` | Health check, dashboard stats |

| **Static** | `/` | React frontend |

  

### 8.5 REST Endpoints

  

#### Products

  

| Method | Path | Purpose | Response |

|--------|------|---------|----------|

| `GET` | `/api/products` | List tracked products | Paginated list |

| `GET` | `/api/products/{id}` | Get product details | Product |

| `POST` | `/api/products` | Add product (via URL) | Product |

| `DELETE` | `/api/products/{id}` | Remove product (soft delete) | Success |

| `GET` | `/api/products/{id}/history` | Price history | List of price points |

| `POST` | `/api/products/{id}/refresh` | Manual scrape now | Scrape result |

  

#### Alerts

  

| Method | Path | Purpose | Response |

|--------|------|---------|----------|

| `GET` | `/api/alerts` | List alerts | Paginated list |

| `GET` | `/api/alerts/{id}` | Get alert details | Alert |

| `POST` | `/api/alerts` | Create alert | Alert |

| `PATCH` | `/api/alerts/{id}` | Update alert | Alert |

| `DELETE` | `/api/alerts/{id}` | Remove alert (soft delete) | Success |

  

#### Schedules

  

| Method | Path | Purpose | Response |

|--------|------|---------|----------|

| `GET` | `/api/schedules` | List schedules | Paginated list |

| `POST` | `/api/schedules` | Create schedule | Schedule |

| `PATCH` | `/api/schedules/{id}` | Update schedule | Schedule |

| `DELETE` | `/api/schedules/{id}` | Remove schedule (soft delete) | Success |

  

#### Stores

  

| Method | Path | Purpose | Response |

|--------|------|---------|----------|

| `GET` | `/api/stores` | List supported stores | List of stores |

| `GET` | `/api/stores/{domain}/health` | Store health metrics | StoreHealth |

  

#### System

  

| Method | Path | Purpose | Response |

|--------|------|---------|----------|

| `GET` | `/api/health` | Health check | `{"status": "ok"}` |

| `GET` | `/api/stats` | Dashboard stats | Stats object |

  

### 8.6 WebSocket Chat

  

#### Connection

  

```

ws://localhost:8000/api/chat/ws

```

  

#### Message Flow

  

```

Client                                    Server

  │                                          │

  │──── Connect ────────────────────────────►│

  │                                          │

  │◄──── {"type": "welcome", ...} ───────────│

  │                                          │

  │──── {"message": "Track Nike..."} ───────►│

  │                                          │

  │◄──── {"type": "thinking"} ───────────────│

  │◄──── {"type": "tool_call", ...} ─────────│

  │◄──── {"type": "tool_result", ...} ───────│

  │◄──── {"type": "response", ...} ──────────│

  │                                          │

```

  

#### Message Types

  

| Type | Direction | Purpose |

|------|-----------|---------|

| `welcome` | Server → Client | Initial greeting with capabilities |

| `message` | Client → Server | User message |

| `thinking` | Server → Client | Agent is processing |

| `tool_call` | Server → Client | Agent calling a tool |

| `tool_result` | Server → Client | Tool execution result |

| `response` | Server → Client | Agent text response |

| `error` | Server → Client | Error occurred |

  

#### Implementation

  

```python

@app.websocket("/api/chat/ws")

async def chat_websocket(websocket: WebSocket):

    await websocket.accept()

    # Send welcome message

    await websocket.send_json({

        "type": "welcome",

        "content": WELCOME_MESSAGE

    })

    try:

        while True:

            data = await websocket.receive_json()

            message = data.get("message", "")

            async for chunk in agent.run_stream(message):

                await websocket.send_json({

                    "type": chunk.type,

                    "content": chunk.content

                })

    except WebSocketDisconnect:

        pass  # Client disconnected

```

  

### 8.7 Pagination

  

Offset-based pagination for list endpoints:

  

#### Request

  

```

GET /api/products?page=2&limit=20&store=walmart.ca&status=active

```

  

#### Response

  

```json

{

  "data": [

    {"id": "...", "name": "...", ...},

    ...

  ],

  "meta": {

    "page": 2,

    "limit": 20,

    "total": 150,

    "total_pages": 8

  }

}

```

  

#### Implementation

  

```python

@router.get("/api/products")

async def list_products(

    page: int = Query(1, ge=1),

    limit: int = Query(20, ge=1, le=100),

    store: str | None = None,

    status: str | None = None

) -> PaginatedResponse[ProductOut]:

    offset = (page - 1) * limit

    products, total = await product_repo.list(

        offset=offset,

        limit=limit,

        store=store,

        status=status

    )

    return {

        "data": products,

        "meta": {

            "page": page,

            "limit": limit,

            "total": total,

            "total_pages": ceil(total / limit)

        }

    }

```

### 8.8 Response Formats
#### Success Response

  

```json

{

  "data": { ... }

}

```

#### Success Response (List)

  

```json

{

  "data": [ ... ],

  "meta": {

    "page": 1,

    "limit": 20,

    "total": 100

  }

}

```
#### Error Response

```json

{

  "error": {

    "code": "PRODUCT_NOT_FOUND",

    "message": "Product with ID xyz not found",

    "details": null

  }

}

```

### 8.9 Error Codes

| Code | HTTP Status | Description |

|------|-------------|-------------|

| `VALIDATION_ERROR` | 422 | Request validation failed |

| `PRODUCT_NOT_FOUND` | 404 | Product ID doesn't exist |

| `ALERT_NOT_FOUND` | 404 | Alert ID doesn't exist |

| `SCHEDULE_NOT_FOUND` | 404 | Schedule ID doesn't exist |

| `STORE_NOT_FOUND` | 404 | Store domain doesn't exist |

| `SCRAPE_FAILED` | 500 | Failed to scrape product |

| `INVALID_URL` | 400 | URL format invalid |

| `RATE_LIMITED` | 429 | Too many requests (agent guardrail) |

| `INTERNAL_ERROR` | 500 | Unexpected server error |
### 8.10 CORS Configuration
```python

from fastapi.middleware.cors import CORSMiddleware

  

# Only needed for development (Vite dev server)

# Production serves frontend from same origin

app.add_middleware(

    CORSMiddleware,

    allow_origins=[

        "http://localhost:5173",  # Vite dev server

        "http://localhost:3000",  # Alternative dev port

    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],

)

```
### 8.11 Static File Serving

```python

from fastapi.staticfiles import StaticFiles

  

# Serve React build in production

app.mount("/", StaticFiles(directory="static", html=True), name="static")

```

  

**Build process:**

1. `cd frontend && npm run build`

2. Copy `frontend/dist/*` to `backend/static/`

3. FastAPI serves static files at `/`
### 8.12 App Lifecycle
```python

from contextlib import asynccontextmanager

  

@asynccontextmanager

async def lifespan(app: FastAPI):

    # Startup

    await database.connect()

    scheduler_service.start()

    yield

    # Shutdown

    await scheduler_service.shutdown()

    await database.disconnect()

  

app = FastAPI(

    title="Perpee API",

    description="AI-powered price monitoring agent",

    version="0.1.0",

    lifespan=lifespan,

    docs_url="/api/docs",

    redoc_url="/api/redoc",

    openapi_url="/api/openapi.json"

)

```
### 8.13 Configuration

```python

class APISettings(BaseSettings):

    # Server

    host: str = "0.0.0.0"

    port: int = 8000

    debug: bool = False

    # Pagination

    default_page_size: int = 20

    max_page_size: int = 100

    # CORS (dev only)

    cors_origins: list[str] = [

        "http://localhost:5173",

        "http://localhost:3000",

    ]

    # Docs

    docs_enabled: bool = True

```

  

### 8.14 Security Considerations

| Risk | Severity | Mitigation |

|------|----------|------------|

| API error leakage | Medium | `debug=False`, generic error messages in production |

| WebSocket abuse | Low | Connection limit, message size limit |

| Mass data exposure | Low | Pagination limits, no bulk export |

| CORS misconfiguration | Medium | Whitelist only localhost for dev |

### 8.15 Cross-Component Dependencies

  
| Component | Dependency |

|-----------|------------|

| Component 1 (Agent) | WebSocket chat invokes agent |

| Component 2 (Database) | All CRUD operations |

| Component 4 (RAG) | Product search via agent |

| Component 5 (Self-Healing) | Store health endpoint |

| Component 6 (Scheduler) | Lifecycle start/stop, manual refresh |

| Component 7 (Notifications) | Notification history endpoint |

  
### 8.16 Module Structure

```

backend/src/api/

├── __init__.py

├── main.py             # FastAPI app, lifespan, middleware

├── routes/

│   ├── __init__.py

│   ├── products.py     # Product endpoints

│   ├── alerts.py       # Alert endpoints

│   ├── schedules.py    # Schedule endpoints

│   ├── stores.py       # Store endpoints

│   ├── chat.py         # WebSocket handler

│   └── health.py       # Health + stats endpoints

├── schemas/

│   ├── __init__.py

│   ├── products.py     # Product request/response models

│   ├── alerts.py       # Alert models

│   ├── schedules.py    # Schedule models

│   ├── stores.py       # Store models

│   └── common.py       # Pagination, errors

├── dependencies.py     # Dependency injection

└── exceptions.py       # Custom exception handlers

```

---
## Component 9: Web UI (Frontend)

### 9.1 Purpose

The Web UI provides a React-based single-page application for interacting with Perpee. It features a 3-column layout with persistent chat access, allowing users to manage products, alerts, and schedules while conversing with the AI agent.
### 9.2 Core Responsibilities

| Responsibility | Description |

|----------------|-------------|

| **Product Management** | View, add, remove tracked products |

| **Alert Configuration** | Create and manage price alerts |

| **Schedule Management** | Configure custom check schedules |

| **Chat Interface** | Real-time conversation with AI agent |

| **Price Visualization** | Charts showing price history |

| **Store Health** | View store status and health metrics |

  

### 9.3 Technology Stack
| Component | Technology | Rationale |

|-----------|------------|-----------|

| **Framework** | Vite + React | Fast dev, simple deployment |

| **App Type** | Single Page Application (SPA) | Served by FastAPI |

| **UI Library** | shadcn/ui + Tailwind CSS | Customizable, accessible |

| **State (Server)** | React Query (TanStack) | Caching, background refresh |

| **State (Client)** | useState/useContext | Zustand deferred for MVP |

| **Forms** | React Hook Form + Zod | Validation, type-safe |

| **Routing** | React Router v6 | Standard SPA routing |

| **Charts** | Recharts | Price history visualization |

| **Toasts** | Sonner | Notifications, alerts |

| **Dates** | date-fns | Formatting, manipulation |

| **Icons** | Lucide React | Consistent icon set |

| **Sanitization** | DOMPurify | XSS prevention |

  

### 9.4 Layout Structure

  

```

┌──────────────────────────────────────────────────────────────────┐

│                         Header (optional)                         │

├────────────┬─────────────────────────────────┬───────────────────┤

│            │                                 │                   │

│  Sidebar   │         Main Content            │    Chat Panel     │

│   (Nav)    │                                 │   (Collapsible)   │

│            │   - Dashboard                   │                   │

│  - Logo    │   - Products list               │   - Messages      │

│  - Nav     │   - Product detail              │   - Input         │

│  - Links   │   - Alerts                      │   - Quick actions │

│            │   - Schedules                   │                   │

│            │   - Stores                      │                   │

│            │   - Settings                    │                   │

│            │                                 │                   │

├────────────┴─────────────────────────────────┴───────────────────┤

│                         Footer (optional)                         │

└──────────────────────────────────────────────────────────────────┘

```

  

### 9.5 Layout Decisions

  

| Element | Decision | Details |

|---------|----------|---------|

| **Structure** | 3-column | Sidebar + Main + Chat Panel |

| **Sidebar** | Left side, collapsible | Dark periwinkle background, collapses on mobile/tablet |

| **Chat Panel** | Right side, collapsible | Accessible from any page via toggle button |

| **Chat Default** | Expanded on desktop | Expanded ≥1280px, collapsed on smaller screens |

| **Responsive** | Mobile-first | Sidebar and chat collapse to overlays on mobile |

  

### 9.6 Theme

  

| Setting | Choice |

|---------|--------|

| **Color Palette** | Soft Periwinkle |

| **Dark Mode** | Yes - toggle in settings |

| **Default Theme** | System preference on first visit |

| **Persistence** | localStorage |

  

**Soft Periwinkle Palette (Tailwind-ready):**

  

```javascript

// tailwind.config.js

{

  "soft-periwinkle": {

    "50": "#edecf8",

    "100": "#dbdaf1",

    "200": "#b7b5e3",

    "300": "#938fd6",

    "400": "#6f6ac8",

    "500": "#4b45ba",

    "600": "#3c3795",

    "700": "#2d2970",

    "800": "#1e1c4a",

    "900": "#0f0e25",

    "950": "#0a0a1a"

  }

}

```

  

**Semantic Colors:**

  

| Purpose | Light Mode | Dark Mode |

|---------|------------|-----------|

| Primary accent | periwinkle-500 | periwinkle-400 |

| Sidebar background | periwinkle-100 | periwinkle-950 |

| Price drop (good) | green-600 | green-500 |

| Price rise (bad) | red-600 | red-500 |

| Status healthy | green-600 | green-500 |

| Status degraded | amber-600 | amber-500 |

| Status error | red-600 | red-500 |

  

### 9.7 Pages

  

| Page | Route | Purpose |

|------|-------|---------|

| **Dashboard** | `/` | Overview: recent products, biggest drops, quick stats |

| **Products** | `/products` | List all tracked products with filters |

| **Product Detail** | `/products/:id` | Price history chart, alerts, schedule settings |

| **Alerts** | `/alerts` | Manage all alerts, notification history |

| **Schedules** | `/schedules` | Advanced schedule management |

| **Stores** | `/stores` | View supported stores, health status (read-only) |

| **Settings** | `/settings` | Theme toggle, system info, about |

| **Chat Panel** | (overlay) | AI agent conversation, accessible from any page |

  

### 9.8 Page Details

  

#### Dashboard (`/`)

  

| Section | Content |

|---------|---------|

| **Stats Cards** | Total products, active alerts, price drops today |

| **Recent Products** | Last 5 added products |

| **Biggest Drops** | Top 5 price drops (24h/7d) |

| **Quick Add** | URL input to quickly add product |

| **Store Health** | Summary of any failing stores |

  

#### Products (`/products`)

  

| Feature | Implementation |

|---------|----------------|

| **View Modes** | List / Grid toggle |

| **Filters** | Store, status, price range |

| **Sort** | Name, price, last checked, date added |

| **Search** | Search by name (via RAG) |

| **Bulk Actions** | Delete selected (with confirmation) |

| **Pagination** | Offset-based, 20 per page |

  

#### Product Detail (`/products/:id`)

  

| Section | Content |

|---------|---------|

| **Header** | Product image, name, store, current price |

| **Price Chart** | Recharts line chart (7d/30d/90d/all) |

| **Price Stats** | Lowest, highest, average, % change |

| **Alerts** | List alerts for this product, create new |

| **Schedule** | Current schedule, enable/disable, simple edit |

| **Actions** | Refresh now, remove product |

  

#### Alerts (`/alerts`)

  

| Section | Content |

|---------|---------|

| **Active Alerts** | List with product, type, target, status |

| **Create Alert** | Form: select product, type, target value |

| **Notification History** | Recent notifications sent |

| **Filters** | By product, by type, triggered/not |

  

#### Schedules (`/schedules`)

  

| Section | Content |

|---------|---------|

| **Product Schedules** | Custom schedules per product |

| **Store Schedules** | Store-wide schedules |

| **Default Schedule** | Display system default (6 AM ±30min) |

| **Create Schedule** | Form: CRON builder, product/store selector |

| **Next Runs** | Preview upcoming scheduled checks |

  

#### Stores (`/stores`)

  

| Section | Content |

|---------|---------|

| **Store List** | All stores with domain, name |

| **Health Status** | Success rate, last success, failing products |

| **Whitelisted Badge** | Indicate P0/P1/P2 vs auto-added |

| **Filter** | Healthy/degraded/failing, whitelisted/all |

  

**Note:** Read-only for MVP. Store CRUD deferred to SaaS admin.

  

#### Settings (`/settings`)

  

| Section | Content |

|---------|---------|

| **Theme** | Light/Dark/System toggle |

| **System Info** | App version, uptime |

| **Stats** | Product count, store count, DB size |

| **About** | Perpee description, links |

  

**Note:** Notification preferences are in env vars for MVP. Full settings when moving to SaaS.

  

### 9.9 Chat Panel

  

#### Behavior

  

| Setting | Value |

|---------|-------|

| **Position** | Right side of screen |

| **Width** | 380px (fixed) |

| **Toggle** | Floating button when collapsed |

| **Default State** | Expanded on desktop (≥1280px) |

| **Connection** | WebSocket to `/api/chat/ws` |

| **Persistence** | Messages cleared on page refresh (session-only) |

  

#### Features

  

| Feature | Implementation |

|---------|----------------|

| **Message Display** | User messages right, agent left |

| **Streaming** | Show response as it streams |

| **Thinking Indicator** | Animated dots while processing |

| **Tool Calls** | Show tool being called (collapsible) |

| **Quick Actions** | Preset buttons: "Check prices", "Show drops" |

| **Welcome Message** | Display on connect (from C1) |

  

#### Message Types Display

  

| Type | Display |

|------|---------|

| `thinking` | "Perpee is thinking..." with animation |

| `tool_call` | "🔧 Calling: scrape_product..." (collapsible) |

| `tool_result` | Hidden or collapsed by default |

| `response` | Normal message bubble |

| `error` | Red error message |

  

### 9.10 Responsive Breakpoints

  

| Breakpoint | Width | Layout Changes |

|------------|-------|----------------|

| **Mobile** | <768px | Sidebar hidden (hamburger), chat as full overlay |

| **Tablet** | 768-1023px | Sidebar collapsed, chat as overlay |

| **Desktop** | 1024-1279px | Sidebar expanded, chat collapsed |

| **Wide** | ≥1280px | Sidebar expanded, chat expanded |

  

### 9.11 Components

  

#### Layout Components

  

| Component | Purpose |

|-----------|---------|

| `Layout` | Main 3-column layout wrapper |

| `Sidebar` | Navigation sidebar |

| `ChatPanel` | Collapsible chat interface |

| `Header` | Optional top header |

| `PageHeader` | Page title + actions |

  

#### Shared Components

  

| Component | Purpose |

|-----------|---------|

| `ProductCard` | Product display (list/grid) |

| `PriceDisplay` | Formatted price with currency |

| `PriceChange` | Price change with color (green/red) |

| `PriceChart` | Recharts line chart |

| `AlertBadge` | Alert type + status indicator |

| `StoreBadge` | Store name with health indicator |

| `StatusBadge` | Generic status indicator |

| `ConfirmDialog` | Destructive action confirmation |

| `EmptyState` | No data placeholder |

| `LoadingState` | Loading spinner/skeleton |

| `ErrorState` | Error message with retry |

  

#### Form Components

  

| Component | Purpose |

|-----------|---------|

| `ProductForm` | Add product by URL |

| `AlertForm` | Create/edit alert |

| `ScheduleForm` | Create/edit schedule with CRON builder |

| `SearchInput` | Search with debounce |

| `FilterDropdown` | Filter selection |

  

### 9.12 API Integration

  

#### React Query Setup

  

```typescript

// lib/api.ts

import { QueryClient } from '@tanstack/react-query'

  

export const queryClient = new QueryClient({

  defaultOptions: {

    queries: {

      staleTime: 30 * 1000,      // 30 seconds

      refetchOnWindowFocus: true,

      retry: 1,

    },

  },

})

```

  

#### API Client

  

```typescript

// lib/api-client.ts

const API_BASE = '/api'

  

export const api = {

  products: {

    list: (params) => fetch(`${API_BASE}/products?${new URLSearchParams(params)}`),

    get: (id) => fetch(`${API_BASE}/products/${id}`),

    create: (data) => fetch(`${API_BASE}/products`, { method: 'POST', body: JSON.stringify(data) }),

    delete: (id) => fetch(`${API_BASE}/products/${id}`, { method: 'DELETE' }),

    refresh: (id) => fetch(`${API_BASE}/products/${id}/refresh`, { method: 'POST' }),

    history: (id) => fetch(`${API_BASE}/products/${id}/history`),

  },

  alerts: { /* similar */ },

  schedules: { /* similar */ },

  stores: { /* similar */ },

}

```

  

#### WebSocket Hook

  

```typescript

// hooks/useChat.ts

export function useChat() {

  const [messages, setMessages] = useState<Message[]>([])

  const [isConnected, setIsConnected] = useState(false)

  const ws = useRef<WebSocket | null>(null)

  

  useEffect(() => {

    ws.current = new WebSocket(`ws://${window.location.host}/api/chat/ws`)

    ws.current.onopen = () => setIsConnected(true)

    ws.current.onclose = () => setIsConnected(false)

    ws.current.onmessage = (event) => {

      const data = JSON.parse(event.data)

      // Handle different message types

    }

    return () => ws.current?.close()

  }, [])

  

  const sendMessage = (content: string) => {

    ws.current?.send(JSON.stringify({ message: content }))

  }

  

  return { messages, isConnected, sendMessage }

}

```

  

### 9.13 Security Considerations

  

| Risk | Severity | Mitigation |

|------|----------|------------|

| XSS from scraped content | HIGH | DOMPurify sanitization before render |

| XSS in product names | HIGH | React's default escaping + DOMPurify |

| Clickjacking | MEDIUM | X-Frame-Options header (backend) |

| CSRF | LOW | No auth = no CSRF risk for MVP |

| localStorage tampering | LOW | Theme only, no sensitive data |

  

#### DOMPurify Usage

  

```typescript

import DOMPurify from 'dompurify'

  

// Sanitize any scraped content before display

function ProductName({ name }: { name: string }) {

  return <span>{DOMPurify.sanitize(name)}</span>

}

```

  

### 9.14 File Structure

  

```

frontend/

├── src/

│   ├── components/

│   │   ├── layout/

│   │   │   ├── Layout.tsx

│   │   │   ├── Sidebar.tsx

│   │   │   ├── ChatPanel.tsx

│   │   │   └── PageHeader.tsx

│   │   ├── products/

│   │   │   ├── ProductCard.tsx

│   │   │   ├── ProductList.tsx

│   │   │   ├── ProductForm.tsx

│   │   │   └── PriceChart.tsx

│   │   ├── alerts/

│   │   │   ├── AlertCard.tsx

│   │   │   ├── AlertList.tsx

│   │   │   └── AlertForm.tsx

│   │   ├── schedules/

│   │   │   ├── ScheduleCard.tsx

│   │   │   ├── ScheduleList.tsx

│   │   │   └── ScheduleForm.tsx

│   │   ├── stores/

│   │   │   ├── StoreCard.tsx

│   │   │   └── StoreList.tsx

│   │   ├── chat/

│   │   │   ├── MessageBubble.tsx

│   │   │   ├── ChatInput.tsx

│   │   │   └── QuickActions.tsx

│   │   └── ui/                 # shadcn components

│   │       ├── button.tsx

│   │       ├── card.tsx

│   │       ├── input.tsx

│   │       └── ...

│   ├── pages/

│   │   ├── Dashboard.tsx

│   │   ├── Products.tsx

│   │   ├── ProductDetail.tsx

│   │   ├── Alerts.tsx

│   │   ├── Schedules.tsx

│   │   ├── Stores.tsx

│   │   └── Settings.tsx

│   ├── hooks/

│   │   ├── useChat.ts

│   │   ├── useProducts.ts

│   │   ├── useAlerts.ts

│   │   └── useTheme.ts

│   ├── lib/

│   │   ├── api.ts              # React Query client

│   │   ├── api-client.ts       # Fetch wrapper

│   │   ├── utils.ts            # Helpers

│   │   └── constants.ts

│   ├── App.tsx

│   ├── main.tsx

│   └── index.css               # Tailwind imports

├── public/

├── index.html

├── package.json

├── vite.config.ts

├── tailwind.config.js

└── tsconfig.json

```

  

### 9.15 Cross-Component Dependencies

  

| Component | Dependency |

|-----------|------------|

| Component 8 (API) | All REST endpoints + WebSocket |

| Component 7 (Notifications) | Notification history display |

| Component 6 (Scheduler) | Schedule display and creation |

| Component 5 (Self-Healing) | Store health status display |

| Component 4 (RAG) | Product search via chat |

| Component 1 (Agent) | Chat panel connects to agent |

  

---

  

## Implementation Phases

  

### Phase 1: Foundation (Week 1-2)

- [ ] Project structure setup

- [ ] Docker configuration

- [ ] SQLite + SQLModel setup

- [ ] Basic FastAPI skeleton

- [ ] Settings/config management

  

### Phase 2: Scraper Engine (Week 2-3)

- [ ] Crawl4AI integration

- [ ] Extraction strategies (JSON-LD, CSS, LLM)

- [ ] Store configurations

- [ ] Selector storage

  

### Phase 3: Database & Models (Week 3-4)

- [ ] All SQLModel models

- [ ] CRUD operations

- [ ] Price history tracking

  

### Phase 4: Agent Core (Week 4-5)

- [ ] Pydantic AI setup

- [ ] OpenRouter integration

- [ ] Tool definitions

- [ ] Guardrails implementation

  

### Phase 5: RAG System (Week 5-6)

- [ ] ChromaDB setup

- [ ] Embedding pipeline

- [ ] Hybrid search

  

### Phase 6: Self-Healing (Week 6-7)

- [ ] Failure detection

- [ ] Recovery strategies

- [ ] Health tracking

  

### Phase 7: Scheduler (Week 7-8)

- [ ] APScheduler integration

- [ ] CRON management

- [ ] Batch optimization

  

### Phase 8: Notifications (Week 8-9)

- [ ] Email (Resend)


- [ ] Alert rules

  

### Phase 9: API Endpoints (Week 9-10)

- [ ] REST endpoints

- [ ] WebSocket chat

- [ ] Error handling

  

### Phase 10: Web UI (Week 10-12)

- [ ] React setup

- [ ] All pages & components

- [ ] API integration

  

### Phase 11: Testing & Deployment (Week 12-13)

- [ ] Testing

- [ ] Oracle Cloud deployment

- [ ] Documentation

  

---

  

## Appendix A: Supported Stores (Initial Whitelist)

  

### P0 - MVP Launch (16 stores)

  

| Category | Store | Domain |

|----------|-------|--------|

| **General** | Amazon Canada | amazon.ca |

| **General** | Walmart Canada | walmart.ca |

| **General** | Costco Canada | costco.ca |

| **General** | Canadian Tire | canadiantire.ca |

| **Electronics** | Best Buy Canada | bestbuy.ca |

| **Electronics** | The Source | thesource.ca |

| **Electronics** | Memory Express | memoryexpress.com |

| **Electronics** | Canada Computers | canadacomputers.com |

| **Electronics** | Newegg Canada | newegg.ca |

| **Grocery** | Loblaws | loblaws.ca |

| **Grocery** | No Frills | nofrills.ca |

| **Grocery** | Real Canadian Superstore | realcanadiansuperstore.ca |

| **Grocery** | Metro | metro.ca |

| **Grocery** | Sobeys | sobeys.com |

| **Pharmacy** | Shoppers Drug Mart | shoppersdrugmart.ca |

| **Home** | Home Depot Canada | homedepot.ca |

  

### P1 - Post-MVP Phase 1 (15 stores)

  

| Category | Store | Domain |

|----------|-------|--------|

| **Grocery** | FreshCo | freshco.com |

| **Grocery** | Safeway Canada | safeway.ca |

| **Grocery** | Save-On-Foods | saveonfoods.com |

| **Grocery** | Food Basics | foodbasics.ca |

| **Grocery** | T&T Supermarket | tnt-supermarket.com |

| **Pharmacy** | London Drugs | londondrugs.com |

| **Pharmacy** | Rexall | rexall.ca |

| **Electronics** | Visions Electronics | visions.ca |

| **Home** | IKEA Canada | ikea.com/ca |

| **Home** | Lowe's Canada | lowes.ca |

| **Home** | Rona | rona.ca |

| **Home** | The Brick | thebrick.com |

| **Sports** | Sport Chek | sportchek.ca |

| **Sports** | MEC | mec.ca |

| **Sports** | Decathlon Canada | decathlon.ca |

  

### P2 - Post-MVP Phase 2 (17 stores)

  

| Category | Store | Domain |

|----------|-------|--------|

| **Grocery** | Voilà (Sobeys) | voila.ca |

| **Grocery** | PC Express | pcexpress.ca |

| **Pharmacy** | Jean Coutu | jeancoutu.com |

| **Home** | Wayfair Canada | wayfair.ca |

| **Home** | Structube | structube.com |

| **Home** | Leon's | leons.ca |

| **Sports** | Atmosphere | atmosphere.ca |

| **Sports** | Sporting Life | sportinglife.ca |

| **Fashion** | Hudson's Bay | thebay.com |

| **Fashion** | Simons | simons.ca |

| **Fashion** | Aritzia | aritzia.com |

| **Fashion** | Mark's | marks.com |

| **Pets** | PetSmart Canada | petsmart.ca |

| **Pets** | Pet Valu | petvalu.com |

| **Other** | Staples Canada | staples.ca |

| **Other** | Indigo/Chapters | indigo.ca |

| **Other** | Well.ca | well.ca |

  

### Store Addition Policy

- **Whitelisted stores:** P0/P1/P2 stores work immediately with pre-configured selectors
- **New stores:** Must use `scan_website` tool first to validate safety and feasibility
- **After scan:** If feasible, store is added to whitelist with learned selectors
- **User requests:** P2 stores can be prioritized based on demand

---

## Appendix B: Cost Breakdown

| Component | Monthly | Yearly |
|-----------|---------|--------|
| Hosting (Oracle Free) | $0 | $0 |
| Database (SQLite) | $0 | $0 |
| Vector DB (ChromaDB) | $0 | $0 |
| LLM (OpenRouter free tier) | ~$0.50 | ~$5 |
| Embeddings (OpenAI) | ~$0.10 | ~$1-2 |
| Email (Resend free tier) | $0 | $0 |
| **Total** | **~$0.60** | **~$7** |

---

## Appendix C: Component Dependencies

This dependency graph shows the implementation order for Claude Code:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Implementation Order                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Phase 1: Foundation                                             │
│  ┌──────────────┐     ┌──────────────┐                          │
│  │ C1: Project  │────►│ C2: Database │                          │
│  │   Structure  │     │    Schema    │                          │
│  └──────────────┘     └──────┬───────┘                          │
│                              │                                   │
│  Phase 2: Core Engine        ▼                                   │
│  ┌──────────────┐     ┌──────────────┐                          │
│  │ C3: Scraper  │◄────│ C4: RAG      │                          │
│  │    Engine    │     │   System     │                          │
│  └──────┬───────┘     └──────────────┘                          │
│         │                                                        │
│  Phase 3: Automation  ▼                                          │
│  ┌──────────────┐     ┌──────────────┐                          │
│  │ C5: Self-    │◄────│ C6: Scheduler│                          │
│  │    Healing   │     │              │                          │
│  └──────┬───────┘     └──────────────┘                          │
│         │                                                        │
│  Phase 4: Communication                                          │
│         ▼                                                        │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     │
│  │ C7: Notif.   │────►│ C8: API      │────►│ C9: Web UI   │     │
│  │              │     │              │     │              │     │
│  └──────────────┘     └──────────────┘     └──────────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Dependency Matrix

| Component | Depends On | Provides To |
|-----------|------------|-------------|
| C1: Project Structure | - | All components |
| C2: Database | C1 | C3, C4, C5, C6, C7, C8 |
| C3: Scraper | C1, C2 | C4, C5, C6 |
| C4: RAG | C1, C2, C3 | C1 (Agent), C8 |
| C5: Self-Healing | C2, C3 | C6, C7 |
| C6: Scheduler | C2, C3, C5 | C7 |
| C7: Notifications | C2, C5, C6 | C8 |
| C8: API | C1, C2, C4, C5, C6, C7 | C9 |
| C9: Web UI | C8 | - |

### Quick Implementation Checklist

- [ ] **Week 1-2:** C1 (Project Structure) + C2 (Database)
- [ ] **Week 2-3:** C3 (Scraper Engine)
- [ ] **Week 3-4:** C4 (RAG System)
- [ ] **Week 4-5:** C1 (Agent Core - tools integration)
- [ ] **Week 5-6:** C5 (Self-Healing)
- [ ] **Week 6-7:** C6 (Scheduler)
- [ ] **Week 7-8:** C7 (Notifications)
- [ ] **Week 8-9:** C8 (API Endpoints)
- [ ] **Week 9-11:** C9 (Web UI)
- [ ] **Week 11-12:** Integration Testing + Deployment

## Implementation Phases

  

### Phase 1: Foundation (Week 1-2)

- [ ] Project structure setup

- [ ] Docker configuration

- [ ] SQLite + SQLModel setup

- [ ] Basic FastAPI skeleton

- [ ] Settings/config management

  

### Phase 2: Scraper Engine (Week 2-3)

- [ ] Crawl4AI integration

- [ ] Extraction strategies (JSON-LD, CSS, LLM)

- [ ] Store configurations

- [ ] Selector storage

  

### Phase 3: Database & Models (Week 3-4)

- [ ] All SQLModel models

- [ ] CRUD operations

- [ ] Price history tracking

  

### Phase 4: Agent Core (Week 4-5)

- [ ] Pydantic AI setup

- [ ] OpenRouter integration

- [ ] Tool definitions

- [ ] Guardrails implementation

  

### Phase 5: RAG System (Week 5-6)

- [ ] ChromaDB setup

- [ ] Embedding pipeline

- [ ] Hybrid search

  

### Phase 6: Self-Healing (Week 6-7)

- [ ] Failure detection

- [ ] Recovery strategies

- [ ] Health tracking

  

### Phase 7: Scheduler (Week 7-8)

- [ ] APScheduler integration

- [ ] CRON management

- [ ] Batch optimization

  

### Phase 8: Notifications (Week 8-9)

- [ ] Email (Resend)


- [ ] Alert rules

  

### Phase 9: API Endpoints (Week 9-10)

- [ ] REST endpoints

- [ ] WebSocket chat

- [ ] Error handling

  

### Phase 10: Web UI (Week 10-12)

- [ ] React setup

- [ ] All pages & components

- [ ] API integration

  

### Phase 11: Testing & Deployment (Week 12-13)

- [ ] Testing

- [ ] Oracle Cloud deployment

- [ ] Documentation

  

---

  

## Appendix A: Supported Stores (Initial Whitelist)

  

### P0 - MVP Launch (16 stores)

  

| Category | Store | Domain |

|----------|-------|--------|

| **General** | Amazon Canada | amazon.ca |

| **General** | Walmart Canada | walmart.ca |

| **General** | Costco Canada | costco.ca |

| **General** | Canadian Tire | canadiantire.ca |

| **Electronics** | Best Buy Canada | bestbuy.ca |

| **Electronics** | The Source | thesource.ca |

| **Electronics** | Memory Express | memoryexpress.com |

| **Electronics** | Canada Computers | canadacomputers.com |

| **Electronics** | Newegg Canada | newegg.ca |

| **Grocery** | Loblaws | loblaws.ca |

| **Grocery** | No Frills | nofrills.ca |

| **Grocery** | Real Canadian Superstore | realcanadiansuperstore.ca |

| **Grocery** | Metro | metro.ca |

| **Grocery** | Sobeys | sobeys.com |

| **Pharmacy** | Shoppers Drug Mart | shoppersdrugmart.ca |

| **Home** | Home Depot Canada | homedepot.ca |

  

### P1 - Post-MVP Phase 1 (15 stores)

  

| Category | Store | Domain |

|----------|-------|--------|

| **Grocery** | FreshCo | freshco.com |

| **Grocery** | Safeway Canada | safeway.ca |

| **Grocery** | Save-On-Foods | saveonfoods.com |

| **Grocery** | Food Basics | foodbasics.ca |

| **Grocery** | T&T Supermarket | tnt-supermarket.com |

| **Pharmacy** | London Drugs | londondrugs.com |

| **Pharmacy** | Rexall | rexall.ca |

| **Electronics** | Visions Electronics | visions.ca |

| **Home** | IKEA Canada | ikea.com/ca |

| **Home** | Lowe's Canada | lowes.ca |

| **Home** | Rona | rona.ca |

| **Home** | The Brick | thebrick.com |

| **Sports** | Sport Chek | sportchek.ca |

| **Sports** | MEC | mec.ca |

| **Sports** | Decathlon Canada | decathlon.ca |

  

### P2 - Post-MVP Phase 2 (17 stores)

  

| Category | Store | Domain |

|----------|-------|--------|

| **Grocery** | Voilà (Sobeys) | voila.ca |

| **Grocery** | PC Express | pcexpress.ca |

| **Pharmacy** | Jean Coutu | jeancoutu.com |

| **Home** | Wayfair Canada | wayfair.ca |

| **Home** | Structube | structube.com |

| **Home** | Leon's | leons.ca |

| **Sports** | Atmosphere | atmosphere.ca |

| **Sports** | Sporting Life | sportinglife.ca |

| **Fashion** | Hudson's Bay | thebay.com |

| **Fashion** | Simons | simons.ca |

| **Fashion** | Aritzia | aritzia.com |

| **Fashion** | Mark's | marks.com |

| **Pets** | PetSmart Canada | petsmart.ca |

| **Pets** | Pet Valu | petvalu.com |

| **Other** | Staples Canada | staples.ca |

| **Other** | Indigo/Chapters | indigo.ca |

| **Other** | Well.ca | well.ca |

  

### Store Addition Policy

- **Whitelisted stores:** P0/P1/P2 stores work immediately with pre-configured selectors
- **New stores:** Must use `scan_website` tool first to validate safety and feasibility
- **After scan:** If feasible, store is added to whitelist with learned selectors
- **User requests:** P2 stores can be prioritized based on demand

---

## Appendix B: Cost Breakdown

| Component | Monthly | Yearly |
|-----------|---------|--------|
| Hosting (Oracle Free) | $0 | $0 |
| Database (SQLite) | $0 | $0 |
| Vector DB (ChromaDB) | $0 | $0 |
| LLM (OpenRouter free tier) | ~$0.50 | ~$5 |
| Embeddings (OpenAI) | ~$0.10 | ~$1-2 |
| Email (Resend free tier) | $0 | $0 |
| **Total** | **~$0.60** | **~$7** |

---

## Appendix C: Component Dependencies

This dependency graph shows the implementation order for Claude Code:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Implementation Order                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Phase 1: Foundation                                             │
│  ┌──────────────┐     ┌──────────────┐                          │
│  │ C1: Project  │────►│ C2: Database │                          │
│  │   Structure  │     │    Schema    │                          │
│  └──────────────┘     └──────┬───────┘                          │
│                              │                                   │
│  Phase 2: Core Engine        ▼                                   │
│  ┌──────────────┐     ┌──────────────┐                          │
│  │ C3: Scraper  │◄────│ C4: RAG      │                          │
│  │    Engine    │     │   System     │                          │
│  └──────┬───────┘     └──────────────┘                          │
│         │                                                        │
│  Phase 3: Automation  ▼                                          │
│  ┌──────────────┐     ┌──────────────┐                          │
│  │ C5: Self-    │◄────│ C6: Scheduler│                          │
│  │    Healing   │     │              │                          │
│  └──────┬───────┘     └──────────────┘                          │
│         │                                                        │
│  Phase 4: Communication                                          │
│         ▼                                                        │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     │
│  │ C7: Notif.   │────►│ C8: API      │────►│ C9: Web UI   │     │
│  │              │     │              │     │              │     │
│  └──────────────┘     └──────────────┘     └──────────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Dependency Matrix

| Component | Depends On | Provides To |
|-----------|------------|-------------|
| C1: Project Structure | - | All components |
| C2: Database | C1 | C3, C4, C5, C6, C7, C8 |
| C3: Scraper | C1, C2 | C4, C5, C6 |
| C4: RAG | C1, C2, C3 | C1 (Agent), C8 |
| C5: Self-Healing | C2, C3 | C6, C7 |
| C6: Scheduler | C2, C3, C5 | C7 |
| C7: Notifications | C2, C5, C6 | C8 |
| C8: API | C1, C2, C4, C5, C6, C7 | C9 |
| C9: Web UI | C8 | - |

### Quick Implementation Checklist

- [ ] **Week 1-2:** C1 (Project Structure) + C2 (Database)
- [ ] **Week 2-3:** C3 (Scraper Engine)
- [ ] **Week 3-4:** C4 (RAG System)
- [ ] **Week 4-5:** C1 (Agent Core - tools integration)
- [ ] **Week 5-6:** C5 (Self-Healing)
- [ ] **Week 6-7:** C6 (Scheduler)
- [ ] **Week 7-8:** C7 (Notifications)
- [ ] **Week 8-9:** C8 (API Endpoints)
- [ ] **Week 9-11:** C9 (Web UI)
- [ ] **Week 11-12:** Integration Testing + Deployment

## Appendix A: Supported Stores (Initial Whitelist)

  

### P0 - MVP Launch (16 stores)

  

| Category | Store | Domain |

|----------|-------|--------|

| **General** | Amazon Canada | amazon.ca |

| **General** | Walmart Canada | walmart.ca |

| **General** | Costco Canada | costco.ca |

| **General** | Canadian Tire | canadiantire.ca |

| **Electronics** | Best Buy Canada | bestbuy.ca |

| **Electronics** | The Source | thesource.ca |

| **Electronics** | Memory Express | memoryexpress.com |

| **Electronics** | Canada Computers | canadacomputers.com |

| **Electronics** | Newegg Canada | newegg.ca |

| **Grocery** | Loblaws | loblaws.ca |

| **Grocery** | No Frills | nofrills.ca |

| **Grocery** | Real Canadian Superstore | realcanadiansuperstore.ca |

| **Grocery** | Metro | metro.ca |

| **Grocery** | Sobeys | sobeys.com |

| **Pharmacy** | Shoppers Drug Mart | shoppersdrugmart.ca |

| **Home** | Home Depot Canada | homedepot.ca |

  

### P1 - Post-MVP Phase 1 (15 stores)

  

| Category | Store | Domain |

|----------|-------|--------|

| **Grocery** | FreshCo | freshco.com |

| **Grocery** | Safeway Canada | safeway.ca |

| **Grocery** | Save-On-Foods | saveonfoods.com |

| **Grocery** | Food Basics | foodbasics.ca |

| **Grocery** | T&T Supermarket | tnt-supermarket.com |

| **Pharmacy** | London Drugs | londondrugs.com |

| **Pharmacy** | Rexall | rexall.ca |

| **Electronics** | Visions Electronics | visions.ca |

| **Home** | IKEA Canada | ikea.com/ca |

| **Home** | Lowe's Canada | lowes.ca |

| **Home** | Rona | rona.ca |

| **Home** | The Brick | thebrick.com |

| **Sports** | Sport Chek | sportchek.ca |

| **Sports** | MEC | mec.ca |

| **Sports** | Decathlon Canada | decathlon.ca |

  

### P2 - Post-MVP Phase 2 (17 stores)

  

| Category | Store | Domain |

|----------|-------|--------|

| **Grocery** | Voilà (Sobeys) | voila.ca |

| **Grocery** | PC Express | pcexpress.ca |

| **Pharmacy** | Jean Coutu | jeancoutu.com |

| **Home** | Wayfair Canada | wayfair.ca |

| **Home** | Structube | structube.com |

| **Home** | Leon's | leons.ca |

| **Sports** | Atmosphere | atmosphere.ca |

| **Sports** | Sporting Life | sportinglife.ca |

| **Fashion** | Hudson's Bay | thebay.com |

| **Fashion** | Simons | simons.ca |

| **Fashion** | Aritzia | aritzia.com |

| **Fashion** | Mark's | marks.com |

| **Pets** | PetSmart Canada | petsmart.ca |

| **Pets** | Pet Valu | petvalu.com |

| **Other** | Staples Canada | staples.ca |

| **Other** | Indigo/Chapters | indigo.ca |

| **Other** | Well.ca | well.ca |

  

### Store Addition Policy

- **Whitelisted stores:** P0/P1/P2 stores work immediately with pre-configured selectors
- **New stores:** Must use `scan_website` tool first to validate safety and feasibility
- **After scan:** If feasible, store is added to whitelist with learned selectors
- **User requests:** P2 stores can be prioritized based on demand

---

## Appendix B: Cost Breakdown

| Component | Monthly | Yearly |
|-----------|---------|--------|
| Hosting (Oracle Free) | $0 | $0 |
| Database (SQLite) | $0 | $0 |
| Vector DB (ChromaDB) | $0 | $0 |
| LLM (OpenRouter free tier) | ~$0.50 | ~$5 |
| Embeddings (OpenAI) | ~$0.10 | ~$1-2 |
| Email (Resend free tier) | $0 | $0 |
| **Total** | **~$0.60** | **~$7** |

---

## Appendix C: Component Dependencies

This dependency graph shows the implementation order for Claude Code:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Implementation Order                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Phase 1: Foundation                                             │
│  ┌──────────────┐     ┌──────────────┐                          │
│  │ C1: Project  │────►│ C2: Database │                          │
│  │   Structure  │     │    Schema    │                          │
│  └──────────────┘     └──────┬───────┘                          │
│                              │                                   │
│  Phase 2: Core Engine        ▼                                   │
│  ┌──────────────┐     ┌──────────────┐                          │
│  │ C3: Scraper  │◄────│ C4: RAG      │                          │
│  │    Engine    │     │   System     │                          │
│  └──────┬───────┘     └──────────────┘                          │
│         │                                                        │
│  Phase 3: Automation  ▼                                          │
│  ┌──────────────┐     ┌──────────────┐                          │
│  │ C5: Self-    │◄────│ C6: Scheduler│                          │
│  │    Healing   │     │              │                          │
│  └──────┬───────┘     └──────────────┘                          │
│         │                                                        │
│  Phase 4: Communication                                          │
│         ▼                                                        │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     │
│  │ C7: Notif.   │────►│ C8: API      │────►│ C9: Web UI   │     │
│  │              │     │              │     │              │     │
│  └──────────────┘     └──────────────┘     └──────────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Dependency Matrix

| Component | Depends On | Provides To |
|-----------|------------|-------------|
| C1: Project Structure | - | All components |
| C2: Database | C1 | C3, C4, C5, C6, C7, C8 |
| C3: Scraper | C1, C2 | C4, C5, C6 |
| C4: RAG | C1, C2, C3 | C1 (Agent), C8 |
| C5: Self-Healing | C2, C3 | C6, C7 |
| C6: Scheduler | C2, C3, C5 | C7 |
| C7: Notifications | C2, C5, C6 | C8 |
| C8: API | C1, C2, C4, C5, C6, C7 | C9 |
| C9: Web UI | C8 | - |

### Quick Implementation Checklist

- [ ] **Week 1-2:** C1 (Project Structure) + C2 (Database)
- [ ] **Week 2-3:** C3 (Scraper Engine)
- [ ] **Week 3-4:** C4 (RAG System)
- [ ] **Week 4-5:** C1 (Agent Core - tools integration)
- [ ] **Week 5-6:** C5 (Self-Healing)
- [ ] **Week 6-7:** C6 (Scheduler)
- [ ] **Week 7-8:** C7 (Notifications)
- [ ] **Week 8-9:** C8 (API Endpoints)
- [ ] **Week 9-11:** C9 (Web UI)
- [ ] **Week 11-12:** Integration Testing + Deployment


---

## Appendix D: Component Dependencies

### Implementation Order

```
┌─────────────────────────────────────────────────────────────────┐
│                    Implementation Order                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Phase 1: Foundation                                             │
│  ┌──────────────┐     ┌──────────────┐                          │
│  │ C1: Project  │────►│ C2: Database │                          │
│  │   Structure  │     │    Schema    │                          │
│  └──────────────┘     └──────┬───────┘                          │
│                              │                                   │
│  Phase 2: Core Engine        ▼                                   │
│  ┌──────────────┐     ┌──────────────┐                          │
│  │ C3: Scraper  │◄────│ C4: RAG      │                          │
│  │    Engine    │     │   System     │                          │
│  └──────┬───────┘     └──────────────┘                          │
│         │                                                        │
│  Phase 3: Automation  ▼                                          │
│  ┌──────────────┐     ┌──────────────┐                          │
│  │ C5: Self-    │◄────│ C6: Scheduler│                          │
│  │    Healing   │     │              │                          │
│  └──────┬───────┘     └──────────────┘                          │
│         │                                                        │
│  Phase 4: Communication                                          │
│         ▼                                                        │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     │
│  │ C7: Notif.   │────►│ C8: API      │────►│ C9: Web UI   │     │
│  │              │     │              │     │              │     │
│  └──────────────┘     └──────────────┘     └──────────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Dependency Matrix

| Component | Depends On | Provides To |
|-----------|------------|-------------|
| C1: Project Structure | - | All components |
| C2: Database | C1 | C3, C4, C5, C6, C7, C8 |
| C3: Scraper | C1, C2 | C4, C5, C6 |
| C4: RAG | C1, C2, C3 | C1 (Agent), C8 |
| C5: Self-Healing | C2, C3 | C6, C7 |
| C6: Scheduler | C2, C3, C5 | C7 |
| C7: Notifications | C2, C5, C6 | C8 |
| C8: API | C1, C2, C4, C5, C6, C7 | C9 |
| C9: Web UI | C8 | - |

### Implementation Checklist

- [ ] **Week 1-2:** C1 (Project Structure) + C2 (Database)
- [ ] **Week 2-3:** C3 (Scraper Engine)
- [ ] **Week 3-4:** C4 (RAG System)
- [ ] **Week 4-5:** C1 (Agent Core - tools integration)
- [ ] **Week 5-6:** C5 (Self-Healing)
- [ ] **Week 6-7:** C6 (Scheduler)
- [ ] **Week 7-8:** C7 (Notifications)
- [ ] **Week 8-9:** C8 (API Endpoints)
- [ ] **Week 9-11:** C9 (Web UI)
- [ ] **Week 11-12:** Integration Testing + Deployment

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Jan 6, 2025 | Initial Technical Spec - split from combined PRD |

---

*This document defines HOW to build Perpee. See PRD.md for WHAT to build and WHY.*
