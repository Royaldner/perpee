# Perpee Project Status

**Last Updated:** 2026-01-09

---

## Current Phase

**Phase 4: Agent Core Complete** - All 6 sections implemented. Ready for Phase 5.

---

## Recent Development

### This Session (2026-01-09 Session 6)
- **Phase 4 Agent Core Complete**: All 6 sections implemented
- Created PerpeeAgent with Pydantic AI and OpenRouter integration
- Implemented all 10 agent tools for price monitoring operations
- Created guardrails system (token tracking, rate limiting, timeouts)
- Added window-based conversation memory (15 messages)
- Created prompt templates for agent personality and LLM extraction
- 42 new tests, 159 total tests passing, lint clean
- Followed proper git workflow: feature branch → build → test → document → PR

### Previous Session (2026-01-08 Session 5)
- **Phase 3 RAG System Complete**: All 5 sections implemented
- Created RAGService with ChromaDB client and collection management
- Created EmbeddingService using OpenAI text-embedding-3-small (1536 dims)
- Implemented ProductSearchService (semantic, hybrid, SQLite fallback)
- Created IndexSyncService for product CRUD sync operations
- 30 new tests, 117 total tests passing, lint clean

### Previous Session (2026-01-08 Session 4)
- **Phase 2 Plan Alignment**: Fixed all deviations from IMPLEMENTATION_PLAN.md
- Created validators.py and sanitization.py per plan
- Integrated Crawl4AI native components
- 87 total tests passing, lint clean

---

## Completed Features

### Phase 1: Foundation (Backend Setup) - COMPLETE
- [x] **1.1 Project Initialization**
  - Directory structure per tech spec
  - `pyproject.toml` with 40+ dependencies
  - Pydantic Settings configuration
  - `.env.example` with all variables

- [x] **1.2 Database Models (SQLModel)**
  - Product, Store, Alert, Schedule, PriceHistory
  - ScrapeLog, Notification, CanonicalProduct
  - Enums: ProductStatus, AlertType, ExtractionStrategy, etc.
  - Soft delete with deleted_at, timestamps
  - Repository with CRUD operations

- [x] **1.3 Database Migrations (Alembic)**
  - SQLite-compatible sync migrations
  - Initial migration with all tables
  - render_as_batch for ALTER support

- [x] **1.4 Core Utilities**
  - Custom exceptions (ScraperError, URLError, AgentError, etc.)
  - Constants (rate limits, timeouts, P0_STORES)
  - Security (URL validation, SSRF protection, XSS sanitization)

- [x] **1.5 Store Seed Data**
  - 16 P0 Canadian stores configured
  - CSS selectors for price, name, availability
  - JSON-LD support flags
  - Per-store rate limits

- [x] **1.6 Basic Docker Setup**
  - Dockerfile with Python 3.11 + Playwright
  - docker-compose.yml for development
  - Oracle Cloud compatible (900MB memory limit)

### Phase 2: Scraper Engine - COMPLETE
- [x] **2.1 Scraper Core**
  - ScraperEngine class with async scrape method
  - Waterfall extraction: JSON-LD -> CSS -> XPath -> LLM
  - Crawl4AI browser configuration (stealth mode)

- [x] **2.2 Rate Limiting & Concurrency**
  - Per-store rate limiting
  - Global rate limit: 10 scrapes/minute
  - Semaphore-based concurrency (3 concurrent browsers)

- [x] **2.3 Retry Strategy & Block Detection**
  - Retry matrix implementation
  - Error categorization (network, timeout, blocked, etc.)
  - Exponential backoff with jitter
  - CAPTCHA/login wall detection
  - Bot detection patterns

- [x] **2.4 Timeout Configuration**
  - 30s request timeout, 2min operation timeout
  - Per-store wait_for selectors

- [x] **2.5 Validation & Sanitization**
  - URL validation, domain whitelist
  - Private IP blocking (SSRF)

- [x] **2.6 User Agent & Headers**
  - Realistic browser user agents
  - Proper Accept/Accept-Language headers
  - User agent rotation with failure tracking

- [x] **2.7 Scraper Tests**
  - JSON-LD extraction tests
  - CSS selector tests
  - Rate limiter tests
  - Block detection tests
  - Retry logic tests
  - User agent tests

### Phase 3: RAG System - COMPLETE
- [x] **3.1 ChromaDB Setup**
  - RAGService class with client management
  - In-memory mode (testing) and persistent mode (production)
  - Collection management with cosine similarity
  - Metadata sanitization for ChromaDB

- [x] **3.2 Embeddings**
  - EmbeddingService with OpenAI text-embedding-3-small
  - 1536-dimensional embeddings
  - Batch embedding with automatic chunking
  - Tenacity retries with exponential backoff

- [x] **3.3 Search Implementation**
  - Semantic search using ChromaDB
  - Hybrid search (embedding + SQLite enrichment)
  - SQLite LIKE fallback when ChromaDB unavailable
  - Metadata filtering (store, price, stock)

- [x] **3.4 Index Synchronization**
  - IndexSyncService for CRUD operations
  - Smart sync based on changed fields
  - Bulk index/remove operations
  - Re-embed on name/brand change

- [x] **3.5 RAG Tests**
  - RAGService tests (10 tests)
  - Embedding tests (6 tests)
  - Search tests (9 tests)
  - Sync tests (3 tests)
  - Integration tests (2 tests)

### Phase 4: Agent Core - COMPLETE
- [x] **4.1 Agent Configuration**
  - PerpeeAgent class with Pydantic AI
  - OpenRouter model configuration (primary + fallbacks)
  - System prompt from `config/prompts/system.txt`
  - Conversation memory (window-based, 15 messages)

- [x] **4.2 Agent Tools Implementation**
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

- [x] **4.3 Tool Dependencies**
  - AgentDependencies dataclass for service injection
  - Factory method with default service creation

- [x] **4.4 Guardrails**
  - DailyTokenTracker (100k tokens/day)
  - LLMRateLimiter (30 requests/minute)
  - InputValidator (token estimation, truncation)
  - with_timeout decorator (operation timeout)

- [x] **4.5 Prompt Templates**
  - `system.txt` - Main agent personality
  - `scan_website.txt` - Website analysis prompt
  - `extract_product.txt` - LLM extraction prompt

- [x] **4.6 Agent Tests**
  - Guardrails tests (14 tests)
  - Conversation memory tests (4 tests)
  - Tool result types tests (6 tests)
  - Dependencies tests (2 tests)
  - Agent response tests (2 tests)
  - System prompt tests (2 tests)
  - Integration tests (2 tests)
  - Edge case tests (4 tests)
  - Additional tests (6 tests)

### Documentation
- [x] PRD PERPEE.md - Product requirements
- [x] TECHNICAL_SPEC PERPEE.md - Technical specification
- [x] IMPLEMENTATION_PLAN.md - 8-phase plan
- [x] CLAUDE.md - Claude Code guidance
- [x] docs/change_logs.md - Change tracking
- [x] docs/project_status.md - Status tracking

---

## In Progress

Nothing currently in progress. Ready for Phase 5.

---

## Next Steps

### Phase 5: Automation (Self-Healing & Scheduler)
1. **5.1 Self-Healing Module**
   - Failure classification (parse_failure, price_validation, structure_change)
   - Track consecutive failures per product
   - LLM-based selector regeneration

2. **5.2 Scheduler Setup**
   - APScheduler AsyncIOScheduler configuration
   - SQLAlchemy job store for persistence
   - Missed job handling

3. **5.3 Batch Processing**
   - Group products by store
   - Reuse browser session per store
   - Respect per-store rate limits

4. **5.4 Schedule Triggers**
   - CRON expression parsing and validation
   - Minimum interval enforcement (24h MVP)
   - Schedule hierarchy: product > store > system

5. **5.5 Automation Tests**
   - Failure detection tests
   - Selector regeneration tests
   - Job scheduling tests

---

## Known Issues

None at this time.

---

## Test Status

| Phase | Tests | Status |
|-------|-------|--------|
| Phase 1 | 50 tests | All passing |
| Phase 2 | 37 tests | All passing |
| Phase 3 | 30 tests | All passing |
| Phase 4 | 42 tests | All passing |
| **Total** | **159 tests** | **All passing** |

---

## Architecture Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Docker timing | Phase 1 | Validate Playwright early (Windows -> Linux) |
| P0 Stores | 16 stores | General/Electronics/Grocery per spec |
| Theme | Soft Periwinkle | Defined palette with dark mode |
| Migrations | Sync + render_as_batch | SQLite compatibility |
| Boolean queries | `.is_(True)` | SQLAlchemy/ruff linting compatible |
| Extraction priority | JSON-LD -> CSS -> XPath -> LLM | Free strategies first, LLM as fallback |
| Rate limiting | Sliding window | Simple, memory-efficient |
| Retry strategy | Category-based | Different errors need different handling |
| Agent framework | Pydantic AI | Type-safe, OpenRouter compatible |
| Token budget | 100k/day | OpenRouter free tier limits |
| Conversation memory | Window (15 msgs) | Balance context vs tokens |

---

## Repository

- **GitHub**: https://github.com/Royaldner/perpee
- **Branch**: main (stable), feature/* (development)
- **PR #1**: Phase 1 Foundation (merged)
- **PR #2**: Phase 2 Scraper Engine (merged)
- **PR #3**: Phase 3 RAG System (merged)
- **PR #4**: Phase 4 Agent Core (pending)

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `backend/src/database/models.py` | SQLModel database models |
| `backend/src/database/repository.py` | CRUD operations |
| `backend/src/core/security.py` | URL/SSRF/XSS utilities |
| `backend/config/stores_seed.py` | P0 store configurations |
| `backend/config/settings.py` | Pydantic Settings |
| `backend/src/scraper/engine.py` | Main scraper engine with MemoryAdaptiveDispatcher |
| `backend/src/scraper/strategies.py` | Extraction strategies (JSON-LD, CSS, XPath, LLM) |
| `backend/src/scraper/rate_limiter.py` | Rate limiting + Crawl4AI RateLimiter |
| `backend/src/scraper/block_detection.py` | Block detection |
| `backend/src/scraper/validators.py` | URL validation, SSRF protection |
| `backend/src/scraper/sanitization.py` | Content sanitization, XSS prevention |
| `backend/src/scraper/robots.py` | Robots.txt + Crawl4AI native integration |
| `backend/src/rag/service.py` | RAGService with ChromaDB client |
| `backend/src/rag/embeddings.py` | EmbeddingService with OpenAI |
| `backend/src/rag/search.py` | ProductSearchService (semantic, hybrid, fallback) |
| `backend/src/rag/sync.py` | IndexSyncService for CRUD sync |
| `backend/src/agent/agent.py` | PerpeeAgent with Pydantic AI |
| `backend/src/agent/tools.py` | All 10 agent tools |
| `backend/src/agent/guardrails.py` | Token/rate limits, timeouts |
| `backend/src/agent/dependencies.py` | Service injection |
| `backend/config/prompts/system.txt` | Agent system prompt |
| `IMPLEMENTATION_PLAN.md` | Task breakdown by phase |
| `referrence/TECHNICAL_SPEC PERPEE.md` | Detailed specs |
