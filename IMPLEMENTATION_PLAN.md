# Perpee Implementation Plan

**Created:** January 7, 2025
**Status:** Ready for Implementation

---

## Overview

This plan breaks down Perpee implementation into 8 phases with clear dependencies. Each phase contains specific tasks that can be completed incrementally.

---

## Design Decisions (Clarified)

These decisions were clarified during planning and should be followed during implementation:

| Area | Decision | Implementation Notes |
|------|----------|---------------------|
| **Product Variants** | Track base product only | Single entry per URL, ignore size/color variants |
| **Timezone** | User's local (auto-detect) | Frontend detects TZ, backend stores UTC, converts on display |
| **Dead URLs** | Pause after 3 days of 404s | Mark status='needs_attention', stop checking, notify user |
| **Agent Language** | English only | Simpler prompts, lower token usage |
| **Hidden Prices** | Flag for user attention | Create 'price_unavailable' status, notify user to check manually |
| **Scale Target** | Under 100 products | Simple implementation sufficient, no complex pagination needed |
| **MSRP Tracking** | Track both prices | Display "Was $X, Now $Y" with discount percentage |
| **Dev Environment** | Windows native | Ensure Windows-compatible paths and commands |
| **Ambiguous Queries** | Ask clarifying questions | Agent asks "Which model? From which store?" |
| **Digest Emails** | No digest | Only alert on actual price changes |
| **Product Matching** | Exact UPC/model only | For cross-store comparison, require exact match |
| **Alert Threshold** | Configurable (default $1 or 1%) | Add `min_change_threshold` field to Alert model |

---

## Phase 1: Foundation (Backend Setup)

**Goal:** Project structure, configuration, and database models.

### 1.1 Project Initialization
- [ ] Create `backend/` directory structure per tech spec
- [ ] Initialize `pyproject.toml` with all dependencies
- [ ] Run `uv sync` to install dependencies
- [ ] Create `.env.example` with all required variables
- [ ] Set up `config/settings.py` with Pydantic Settings

### 1.2 Database Models (SQLModel)
- [ ] Create `src/database/models.py`:
  - `Product` model (id, url, store_domain, name, brand, upc, current_price, original_price, currency, in_stock, image_url, status [active/paused/error/needs_attention/price_unavailable/archived], canonical_id, last_checked_at, consecutive_failures, deleted_at, timestamps)
  - `PriceHistory` model (id, product_id, price, original_price, in_stock, scraped_at)
  - `Alert` model (id, product_id, alert_type enum, target_value, min_change_threshold, is_active, is_triggered, triggered_at, deleted_at, timestamps)
  - `Schedule` model (id, product_id, store_domain, cron_expression, is_active, last_run_at, next_run_at, deleted_at, timestamps)
  - `Store` model (domain PK, name, is_whitelisted, is_active, selectors JSON, rate_limit_rpm, success_rate, last_success_at, timestamps)
  - `CanonicalProduct` model (id, name, brand, upc, category, deleted_at, timestamps)
  - `ScrapeLog` model (id, product_id, success, strategy_used, error_type, error_message, response_time_ms, scraped_at)
  - `Notification` model (id, alert_id, product_id, channel, status, payload JSON, sent_at, error_message, timestamps)
- [ ] Create `src/database/session.py` with async session factory
- [ ] Create `src/database/repository.py` with CRUD operations

### 1.3 Database Migrations (Alembic)
- [ ] Initialize Alembic: `alembic init alembic`
- [ ] Configure `alembic/env.py` for SQLModel
- [ ] Create initial migration with all tables
- [ ] Test migration: `alembic upgrade head`

### 1.4 Core Utilities
- [ ] Create `src/core/exceptions.py` with custom exception classes
- [ ] Create `src/core/constants.py` with app-wide constants
- [ ] Create `src/core/security.py`:
  - URL validation (whitelist check)
  - Private IP blocking (SSRF protection)
  - Content sanitization utilities

### 1.5 Store Seed Data
- [ ] Create `config/stores_seed.py` with P0 store configurations (16 stores):
  - **General (4):** Amazon Canada (amazon.ca), Walmart Canada (walmart.ca), Costco Canada (costco.ca), Canadian Tire (canadiantire.ca)
  - **Electronics (5):** Best Buy Canada (bestbuy.ca), The Source (thesource.ca), Memory Express (memoryexpress.com), Canada Computers (canadacomputers.com), Newegg Canada (newegg.ca)
  - **Grocery (5):** Loblaws (loblaws.ca), No Frills (nofrills.ca), Real Canadian Superstore (realcanadiansuperstore.ca), Metro (metro.ca), Sobeys (sobeys.com)
  - **Pharmacy (1):** Shoppers Drug Mart (shoppersdrugmart.ca)
  - **Home (1):** Home Depot Canada (homedepot.ca)
- [ ] Include CSS selectors for each store (price, name, availability, image)
- [ ] Research JSON-LD availability for each store (prioritize stores with good structured data)

### 1.6 Basic Docker Setup
- [ ] Create `docker/Dockerfile`:
  - Python 3.11 base image
  - Install system dependencies (Playwright browsers)
  - Install Python dependencies with uv
  - Basic entrypoint for FastAPI
- [ ] Create `docker/docker-compose.yml`:
  - Single service configuration
  - Volume mounts for `data/` (SQLite, ChromaDB, logs)
  - Environment variable passthrough from `.env`
  - Port mapping (8000)
- [ ] Verify Playwright/Crawl4AI works in container:
  - Test headless browser launches
  - Test basic page fetch
  - Validate memory usage within 1GB constraint
- [ ] Document local Docker development workflow

**Deliverables:** Working database with migrations, seed data loaded, core utilities ready, Docker environment validated for Playwright.

---

## Phase 2: Scraper Engine

**Goal:** Extract product data from URLs using waterfall strategy.

### 2.1 Scraper Core
- [ ] Create `src/scraper/engine.py`:
  - `ScraperEngine` class with async scrape method
  - Waterfall extraction: JSON-LD → CSS → XPath → LLM
  - Crawl4AI browser configuration (stealth mode)
- [ ] Create `src/scraper/strategies.py`:
  - `JsonLdStrategy` - Parse `<script type="application/ld+json">`
  - `CssSelectorStrategy` - Use store-specific selectors
  - `XPathStrategy` - Fallback XPath extraction
  - `LlmExtractionStrategy` - OpenRouter LLM for unknown stores

### 2.2 Rate Limiting & Concurrency
- [ ] Create `src/scraper/rate_limiter.py`:
  - Per-store rate limiting (respect robots.txt)
  - Global rate limit: 10 scrapes/minute
  - Crawl4AI RateLimiter integration
- [ ] Configure `MemoryAdaptiveDispatcher`:
  - Max 3 concurrent browsers
  - 70% memory threshold

### 2.3 Retry Strategy & Block Detection
- [ ] Create `src/scraper/retry.py`:
  - Retry matrix implementation:
    - Network errors/timeouts: 3 retries, exponential backoff
    - 5xx server errors: 3 retries, exponential backoff
    - 429 rate limited: 3 retries, exponential backoff
    - 403 forbidden: 1 retry, then fail
    - 404 not found: No retry, mark `broken_link`
  - User feedback messages ("Retrying 1/3...")
- [ ] Create `src/scraper/block_detection.py`:
  - Detection layers: CAPTCHA, login walls, empty responses, rate limit pages
  - Progressive evasion: delay increase → header rotation → session reset
- [ ] Create `src/scraper/robots.py`:
  - Crawl4AI native `check_robots_txt` integration
  - User notification if robots.txt disallows (warn, proceed on confirm)

### 2.4 Timeout Configuration
- [ ] Configure timeouts in scraper engine:
  - Request timeout: 30 seconds
  - Operation timeout: 2 minutes
  - Page load wait: 1 second (`delay_before_return_html`)
  - Per-store `wait_for` CSS selectors

### 2.5 Validation & Sanitization
- [ ] Create `src/scraper/validators.py`:
  - URL format validation
  - Domain whitelist check
  - Private IP blocking after DNS resolution
- [ ] Create `src/scraper/sanitization.py`:
  - HTML tag stripping
  - XSS prevention (bleach)
  - Price normalization (handle $, CAD, commas)

### 2.6 User Agent & Headers
- [ ] Create `src/scraper/user_agent.py`:
  - Realistic browser user agents
  - Proper headers (Accept, Accept-Language, etc.)

### 2.7 Scraper Tests
- [ ] Create `tests/test_scraper.py`:
  - Test JSON-LD extraction
  - Test CSS selector extraction for 2-3 P0 stores
  - Test price normalization
  - Test URL validation

**Deliverables:** Working scraper that can extract product data from P0 stores.

---

## Phase 3: RAG System

**Goal:** Semantic search over tracked products.

### 3.1 ChromaDB Setup
- [ ] Create `src/rag/service.py`:
  - `RAGService` class
  - ChromaDB client initialization
  - Collection management (products collection)

### 3.2 Embeddings
- [ ] Create `src/rag/embeddings.py`:
  - OpenAI `text-embedding-3-small` integration
  - Batch embedding support
  - Error handling with retries

### 3.3 Search Implementation
- [ ] Create `src/rag/search.py`:
  - Semantic search with metadata filters
  - Hybrid search (embedding + SQLite enrichment)
  - Fallback to SQLite LIKE when ChromaDB unavailable

### 3.4 Index Synchronization
- [ ] Create `src/rag/sync.py`:
  - Index on product create
  - Update metadata on price/stock change
  - Re-embed on name/description change
  - Remove from index on soft delete

### 3.5 RAG Tests
- [ ] Create `tests/test_rag.py`:
  - Test embedding generation
  - Test semantic search
  - Test index sync operations

**Deliverables:** Working semantic search for natural language product queries.

---

## Phase 4: Agent Core

**Goal:** Pydantic AI agent with all tools.

### 4.1 Agent Configuration
- [ ] Create `src/agent/agent.py`:
  - Pydantic AI agent setup
  - OpenRouter model configuration (primary + fallbacks)
  - System prompt from `config/prompts/system.txt`
  - Conversation memory (window-based, 15 messages)

### 4.2 Agent Tools Implementation
- [ ] Create `src/agent/tools.py`:
  - `scrape_product(url)` - Extract product data, save to DB
  - `scan_website(url)` - Analyze unknown site structure
  - `search_products(query, store?)` - RAG search
  - `web_search(query)` - DuckDuckGo product search
  - `get_price_history(product_id, days?)` - Query history
  - `create_schedule(product_id, cron)` - Set monitoring
  - `set_alert(product_id, alert_type, target_value?)` - Configure alert
  - `compare_prices(canonical_id)` - Cross-store comparison
  - `list_products(store?, limit?)` - List tracked products
  - `remove_product(product_id)` - Soft delete product

### 4.3 Tool Dependencies
- [ ] Create `src/agent/dependencies.py`:
  - Database session injection
  - Scraper engine injection
  - RAG service injection

### 4.4 Guardrails
- [ ] Create `src/agent/guardrails.py`:
  - Input token limit (4,000)
  - Output token limit (1,000)
  - Daily token tracking (100,000/day)
  - Request timeout (30s)
  - Operation timeout (2min)

### 4.5 Prompt Templates
- [ ] Create `config/prompts/system.txt` - Main system prompt
- [ ] Create `config/prompts/scan_website.txt` - Website analysis prompt
- [ ] Create `config/prompts/extract_product.txt` - LLM extraction prompt

### 4.6 Agent Tests
- [ ] Create `tests/test_agent.py`:
  - Test tool invocation
  - Test guardrail enforcement
  - Test conversation memory

**Deliverables:** Working AI agent with all 10 tools functional.

---

## Phase 5: Automation (Self-Healing & Scheduler)

**Goal:** Automated price monitoring and failure recovery.

### 5.1 Self-Healing Module
- [ ] Create `src/healing/detector.py`:
  - Failure classification (parse_failure, price_validation, structure_change)
  - Track consecutive failures per product
  - Trigger threshold: 3 consecutive failures
- [ ] Create `src/healing/regenerator.py`:
  - LLM-based selector regeneration
  - Max 3 healing attempts per product
  - Store-wide selector updates
- [ ] Create `src/healing/service.py`:
  - `SelfHealingService` orchestration
  - Health calculation (7-day success rate)
  - Store flagging (>50% products failing)
- [ ] Create `src/healing/health.py`:
  - Store health metrics calculation
  - Success rate tracking

### 5.2 Scheduler Setup
- [ ] Create `src/scheduler/service.py`:
  - APScheduler `AsyncIOScheduler` configuration
  - SQLAlchemy job store for persistence
  - Missed job handling (coalesce, misfire_grace_time)
- [ ] Create `src/scheduler/jobs.py`:
  - `daily_scrape_job` - Default 6 AM check with jitter
  - `custom_product_job` - Per-product CRON
  - `store_batch_job` - Store-wide CRON
  - `cleanup_job` - Weekly data retention (scrape_logs 30d, notifications 90d)
  - `health_calculation_job` - Daily store health update

### 5.3 Batch Processing
- [ ] Create `src/scheduler/batching.py`:
  - Group products by store
  - Reuse browser session per store
  - Respect per-store rate limits

### 5.4 Schedule Triggers
- [ ] Create `src/scheduler/triggers.py`:
  - CRON expression parsing and validation
  - Minimum interval enforcement (24h MVP)
  - Schedule hierarchy: product > store > system

### 5.5 Automation Tests
- [ ] Create `tests/test_healing.py`:
  - Test failure detection
  - Test selector regeneration
- [ ] Create `tests/test_scheduler.py`:
  - Test job scheduling
  - Test batch processing

**Deliverables:** Automated price checks with self-healing on failures.

---

## Phase 6: Notifications & API

**Goal:** Email alerts and REST/WebSocket API.

### 6.1 Email Notifications
- [ ] Create `src/notifications/channels/email.py`:
  - Resend SDK integration
  - Retry logic (3 attempts, exponential backoff)
- [ ] Create `src/notifications/templates/`:
  - `price_alert.html` - Price drop notification
  - `back_in_stock.html` - Stock availability alert
  - `product_error.html` - Tracking failure notice
  - `store_flagged.html` - Store health warning
- [ ] Create `src/notifications/service.py`:
  - `NotificationService` class
  - Duplicate prevention (check last notified price)
  - Notification logging to DB

### 6.2 API Schemas
- [ ] Create `src/api/schemas/`:
  - `products.py` - ProductCreate, ProductResponse, ProductList
  - `alerts.py` - AlertCreate, AlertUpdate, AlertResponse
  - `schedules.py` - ScheduleCreate, ScheduleUpdate, ScheduleResponse
  - `stores.py` - StoreResponse, StoreHealth
  - `common.py` - PaginatedResponse, ErrorResponse

### 6.3 API Routes
- [ ] Create `src/api/routes/products.py`:
  - `GET /api/products` - List (paginated)
  - `GET /api/products/{id}` - Detail
  - `POST /api/products` - Create via URL
  - `DELETE /api/products/{id}` - Soft delete
  - `GET /api/products/{id}/history` - Price history
  - `POST /api/products/{id}/refresh` - Manual scrape
- [ ] Create `src/api/routes/alerts.py`:
  - `GET /api/alerts` - List
  - `POST /api/alerts` - Create
  - `PATCH /api/alerts/{id}` - Update
  - `DELETE /api/alerts/{id}` - Delete
- [ ] Create `src/api/routes/schedules.py`:
  - `GET /api/schedules` - List
  - `POST /api/schedules` - Create
  - `PATCH /api/schedules/{id}` - Update
  - `DELETE /api/schedules/{id}` - Delete
- [ ] Create `src/api/routes/stores.py`:
  - `GET /api/stores` - List with health
- [ ] Create `src/api/routes/health.py`:
  - `GET /api/health` - Health check
  - `GET /api/stats` - Dashboard statistics

### 6.4 WebSocket Chat
- [ ] Create `src/api/routes/chat.py`:
  - `WebSocket /api/chat/ws`
  - Message types: welcome, message, thinking, tool_call, tool_result, response, error
  - Agent integration
  - Connection management

### 6.5 FastAPI App
- [ ] Create `src/api/main.py`:
  - FastAPI app initialization
  - Lifespan events (startup/shutdown)
  - CORS middleware
  - Static file serving (frontend build)
  - Router registration
- [ ] Create `src/api/dependencies.py`:
  - Database session dependency
  - Service injection

### 6.6 API Tests
- [ ] Create `tests/test_api.py`:
  - Test product CRUD endpoints
  - Test alert endpoints
  - Test WebSocket chat

**Deliverables:** Complete REST API and WebSocket chat endpoint.

---

## Phase 7: Frontend

**Goal:** React web application with chat interface.

### 7.1 Project Setup
- [ ] Initialize Vite + React + TypeScript project
- [ ] Install dependencies: TanStack Query, React Router, shadcn/ui
- [ ] Configure Tailwind CSS with Perpee theme:
  - **Soft Periwinkle palette** (add to `tailwind.config.js`):
    ```
    50: #edecf8, 100: #dbdaf1, 200: #b7b5e3, 300: #938fd6,
    400: #6f6ac8, 500: #4b45ba, 600: #3c3795, 700: #2d2970,
    800: #1e1c4a, 900: #0f0e25, 950: #0a0a1a
    ```
  - Dark mode support (system preference default, toggle in settings)
  - Theme persistence via localStorage
- [ ] Set up path aliases in `vite.config.ts`

### 7.2 Layout Components
- [ ] Create `src/components/layout/Layout.tsx` - 3-column layout
- [ ] Create `src/components/layout/Sidebar.tsx` - Navigation sidebar
- [ ] Create `src/components/layout/ChatPanel.tsx` - Collapsible chat
- [ ] Create `src/components/layout/PageHeader.tsx` - Page titles

### 7.3 API Client
- [ ] Create `src/lib/api.ts`:
  - Fetch wrapper with error handling
  - Product API functions
  - Alert API functions
  - Schedule API functions
- [ ] Create `src/lib/websocket.ts`:
  - WebSocket connection management
  - Message parsing
  - Reconnection logic

### 7.4 TanStack Query Hooks
- [ ] Create `src/hooks/useProducts.ts` - Product queries/mutations
- [ ] Create `src/hooks/useAlerts.ts` - Alert queries/mutations
- [ ] Create `src/hooks/useSchedules.ts` - Schedule queries/mutations
- [ ] Create `src/hooks/useChat.ts` - WebSocket chat hook

### 7.5 Pages
- [ ] Create `src/pages/Dashboard.tsx`:
  - Overview statistics
  - Recent products
  - Biggest price drops
- [ ] Create `src/pages/Products.tsx`:
  - Product list with filtering
  - Add product form
- [ ] Create `src/pages/ProductDetail.tsx`:
  - Price history chart (recharts)
  - Alert configuration
  - Schedule management
- [ ] Create `src/pages/Alerts.tsx`:
  - All alerts list
  - Alert management
- [ ] Create `src/pages/Schedules.tsx`:
  - Schedule list and management
- [ ] Create `src/pages/Stores.tsx`:
  - Supported stores (read-only)
  - Store health indicators
- [ ] Create `src/pages/Settings.tsx`:
  - Theme toggle (dark/light)
  - System information

### 7.6 Chat Components
- [ ] Create `src/components/chat/ChatInput.tsx` - Message input
- [ ] Create `src/components/chat/ChatMessage.tsx` - Message display
- [ ] Create `src/components/chat/ThinkingIndicator.tsx` - Loading state
- [ ] Create `src/components/chat/ToolCallDisplay.tsx` - Show tool usage

### 7.7 Product Components
- [ ] Create `src/components/products/ProductCard.tsx`
- [ ] Create `src/components/products/ProductList.tsx`
- [ ] Create `src/components/products/PriceChart.tsx`
- [ ] Create `src/components/products/AddProductForm.tsx`

### 7.8 Alert Components
- [ ] Create `src/components/alerts/AlertCard.tsx`
- [ ] Create `src/components/alerts/AlertForm.tsx`

### 7.9 Security
- [ ] Integrate DOMPurify for XSS prevention on scraped content
- [ ] Sanitize all product descriptions before rendering

### 7.10 Responsive Design
- [ ] Implement mobile breakpoint (<768px): sidebar hidden, chat overlay
- [ ] Implement tablet breakpoint (768-1023px): sidebar collapsed
- [ ] Implement desktop breakpoint (1024-1279px): chat collapsed
- [ ] Implement wide breakpoint (>=1280px): both expanded

### 7.11 Frontend Tests
- [ ] Set up Vitest
- [ ] Test key components
- [ ] Test API hooks

**Deliverables:** Complete React frontend with responsive design.

---

## Phase 8: Integration & Deployment

**Goal:** Production-ready Docker deployment and final testing.

### 8.1 Docker Production Optimization
- [ ] Upgrade `docker/Dockerfile` for production:
  - Multi-stage build (separate build and runtime stages)
  - Frontend build step (copy Vite build output)
  - Minimize image size (remove build dependencies)
  - Non-root user for security
  - Health check instruction
- [ ] Upgrade `docker/docker-compose.yml`:
  - Resource limits (memory: 900MB for Oracle Cloud 1GB)
  - Restart policy (unless-stopped)
  - Logging configuration
  - Production environment variables

### 8.2 Integration Testing
- [ ] End-to-end test: Add product via chat
- [ ] End-to-end test: Price check and alert trigger
- [ ] End-to-end test: Self-healing on selector failure
- [ ] Load test: 50+ products tracked
- [ ] Test all 16 P0 stores extraction

### 8.3 Production Hardening
- [ ] Set `DEBUG=false` in production
- [ ] Configure proper logging
- [ ] Set up log rotation
- [ ] Verify all rate limits active
- [ ] Verify token budget enforcement

### 8.4 Documentation
- [ ] Update README.md with setup instructions
- [ ] Document environment variables
- [ ] Create deployment guide for Oracle Cloud

**Deliverables:** Deployable Docker container, passing all tests.

---

## Dependencies Graph

```
Phase 1 (Foundation)
    └── Phase 2 (Scraper)
        └── Phase 3 (RAG)
            └── Phase 4 (Agent)
                ├── Phase 5 (Automation)
                │   └── Phase 6 (API + Notifications)
                │       └── Phase 7 (Frontend)
                │           └── Phase 8 (Deployment)
                └── Phase 6 (API basics can start in parallel)
```

---

## Quick Start Commands

After each phase, verify with:

```bash
# Phase 1: Test database and Docker
cd backend && uv run alembic upgrade head
cd docker && docker-compose up --build  # Verify Playwright works in container

# Phase 2: Test scraper
cd backend && uv run pytest tests/test_scraper.py -v

# Phase 3: Test RAG
cd backend && uv run pytest tests/test_rag.py -v

# Phase 4: Test agent
cd backend && uv run pytest tests/test_agent.py -v

# Phase 5: Test automation
cd backend && uv run pytest tests/test_healing.py tests/test_scheduler.py -v

# Phase 6: Test API
cd backend && uv run pytest tests/test_api.py -v
cd backend && uv run uvicorn src.api.main:app --reload --port 8000

# Phase 7: Test frontend
cd frontend && npm run dev

# Phase 8: Full stack
cd docker && docker-compose up --build
```

---

## Notes

- Each phase should be completed and tested before moving to the next
- **Docker is in Phase 1** to validate Playwright/Crawl4AI works in the target Linux container early (Windows dev → Linux deploy)
- The agent (Phase 4) is the integration point where scraper + RAG come together
- Frontend can start after API routes are ready (Phase 6)
- Self-healing and scheduler can be developed in parallel after agent core
- Phase 8 focuses on production hardening (multi-stage builds, resource limits) since basic Docker is already working
