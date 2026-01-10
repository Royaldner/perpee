# Perpee Change Log

---

## [2026-01-09 Session 7]

### Changes
- **Phase 5 Automation Complete**: Implemented all 5 sections of Phase 5
- Created Self-Healing system:
  - `FailureDetector` - Classify errors into categories (parse, structure, validation, network)
  - `SelectorRegenerator` - LLM-based CSS selector regeneration using Pydantic AI
  - `SelfHealingService` - Orchestrate healing cycles with retry limits
  - `StoreHealthCalculator` - Calculate 7-day success rate metrics per store
- Created Scheduler system:
  - `SchedulerService` - APScheduler AsyncIOScheduler with configurable job stores
  - `BatchProcessor` - Group products by store for efficient browser session reuse
  - `ScheduleTriggers` - CRON expression parsing/validation with croniter
  - Job definitions: daily_scrape, health_calculation, healing, cleanup
- Added healing and scheduler exceptions to core/exceptions.py
- Created regeneration prompt template for LLM selector generation
- Added croniter dependency for CRON parsing
- Wrote 83 comprehensive tests for healing and scheduler functionality

### Files Created
- `backend/src/healing/detector.py` - Failure classification and tracking
- `backend/src/healing/regenerator.py` - LLM-based selector regeneration
- `backend/src/healing/service.py` - SelfHealingService orchestration
- `backend/src/healing/health.py` - Store health metrics calculation
- `backend/src/healing/__init__.py` - Public exports
- `backend/src/scheduler/service.py` - APScheduler service
- `backend/src/scheduler/jobs.py` - Scheduled job definitions
- `backend/src/scheduler/batching.py` - Batch processing by store
- `backend/src/scheduler/triggers.py` - CRON utilities
- `backend/config/prompts/regenerate_selectors.txt` - Regeneration prompt
- `backend/tests/test_healing.py` - 43 healing tests
- `backend/tests/test_scheduler.py` - 40 scheduler tests

### Files Modified
- `backend/pyproject.toml` - Added croniter>=3.0.0
- `backend/src/core/exceptions.py` - Added HealingError, SchedulerError exceptions
- `backend/src/scheduler/__init__.py` - Updated public exports
- `backend/uv.lock` - Updated dependencies

### Notes
- All 242 tests passing (159 previous + 83 new)
- Ruff linting clean
- Followed proper git workflow: feature branch → build → test → document → PR
- Ready for Phase 6 (Notifications)

---

## [2026-01-09 Session 6]

### Changes
- **Phase 4 Agent Core Complete**: Implemented all 6 sections of Phase 4
- Created PerpeeAgent with Pydantic AI integration:
  - OpenRouter model configuration for LLM access
  - Model fallback chain: Gemini 2.0 Flash -> Llama 3.3 70B -> Claude 3.5 Haiku
  - ConversationMemory with sliding window (15 messages)
  - PerpeeAgent high-level interface with guardrails integration
- Implemented all 10 agent tools:
  - `scrape_product(url)` - Extract product data and save to DB
  - `scan_website(url)` - Analyze unknown site for scrapeability
  - `search_products(query, store?)` - RAG semantic search
  - `web_search(query)` - DuckDuckGo product search
  - `get_price_history(product_id, days?)` - Query price history
  - `create_schedule(product_id, cron)` - Set monitoring schedule
  - `set_alert(product_id, alert_type, target?)` - Configure price alerts
  - `compare_prices(canonical_id)` - Cross-store comparison
  - `list_products(store?, limit?)` - List tracked products
  - `remove_product(product_id)` - Soft delete product
- Created guardrails system:
  - DailyTokenTracker - 100k tokens/day budget with daily reset
  - LLMRateLimiter - 30 requests/minute sliding window
  - InputValidator - Token estimation and input truncation
  - with_timeout decorator - Operation timeout enforcement
- Created AgentDependencies for service injection
- Created prompt templates (system.txt, scan_website.txt, extract_product.txt)
- Wrote 42 comprehensive tests for all agent components

### Files Created
- `backend/src/agent/agent.py` - PerpeeAgent with Pydantic AI
- `backend/src/agent/tools.py` - All 10 agent tools
- `backend/src/agent/dependencies.py` - Service injection
- `backend/src/agent/guardrails.py` - Token/rate limits
- `backend/config/prompts/system.txt` - Main agent prompt
- `backend/config/prompts/scan_website.txt` - Website analysis prompt
- `backend/config/prompts/extract_product.txt` - LLM extraction prompt
- `backend/tests/test_agent.py` - 42 unit tests

### Files Modified
- `backend/src/agent/__init__.py` - Updated public exports

### Notes
- All 159 tests passing (50 P1 + 37 P2 + 30 P3 + 42 P4)
- Ruff linting clean
- Followed proper git workflow: feature branch → build → test → document → PR
- Ready for Phase 5 (Automation - Self-Healing & Scheduler)

---

## [2026-01-08 Session 5]

### Changes
- **Phase 3 RAG System Complete**: Implemented all 5 sections of Phase 3
- Created RAGService for ChromaDB client and collection management:
  - In-memory mode for testing, persistent mode for production
  - Cosine similarity for semantic search
  - Metadata sanitization for ChromaDB compatibility
- Created EmbeddingService using OpenAI text-embedding-3-small:
  - 1536-dimensional embeddings
  - Batch embedding with automatic chunking (100 batch max)
  - Tenacity retries with exponential backoff
  - Helper functions: `create_product_document`, `create_product_metadata`
- Implemented ProductSearchService:
  - Semantic search using ChromaDB
  - Hybrid search (embedding + SQLite enrichment)
  - SQLite LIKE fallback when ChromaDB unavailable
  - Metadata filtering (store, price, stock)
- Created IndexSyncService for product CRUD sync:
  - `index_product` - Add new product to index
  - `update_metadata` - Update without re-embedding (price/stock)
  - `reembed_product` - Re-generate embedding (name/brand change)
  - `remove_product` - Remove on soft delete
  - Smart `sync_product` determines operation type
  - Bulk operations for batch indexing/removal
- Added RAG exceptions to core/exceptions.py:
  - `RAGError` - Base exception
  - `EmbeddingError` - Embedding generation failed
  - `SearchError` - Semantic search failed
  - `IndexSyncError` - Index synchronization failed
- Wrote 30 comprehensive tests for all RAG components

### Files Created
- `backend/src/rag/service.py` - RAGService with ChromaDB
- `backend/src/rag/embeddings.py` - EmbeddingService with OpenAI
- `backend/src/rag/search.py` - ProductSearchService (semantic, hybrid, fallback)
- `backend/src/rag/sync.py` - IndexSyncService for CRUD sync
- `backend/tests/test_rag.py` - 30 unit tests

### Files Modified
- `backend/src/core/exceptions.py` - Added RAG exceptions
- `backend/src/rag/__init__.py` - Updated public exports

### Notes
- All 117 tests passing (50 Phase 1 + 37 Phase 2 + 30 Phase 3)
- Ruff linting clean
- Followed proper git workflow: feature branch → build → test → document → PR
- Ready for Phase 4 (Pydantic AI Agent)

---

## [2026-01-08 Session 4]

### Changes
- **Phase 2 Plan Alignment**: Fixed deviations from IMPLEMENTATION_PLAN.md
- Added critical rule to CLAUDE.md to never deviate from original plan
- Created missing files per plan specification:
  - `validators.py` - URL format validation, domain whitelist, private IP blocking
  - `sanitization.py` - HTML stripping, XSS prevention, price normalization
- Integrated Crawl4AI native components:
  - Added Crawl4AI RateLimiter integration to `rate_limiter.py`
  - Configured MemoryAdaptiveDispatcher in `engine.py` (3 browsers, 70% memory)
  - Added batch scraping method using `arun_many()` with dispatcher
  - Integrated Crawl4AI native `check_robots_txt` in `robots.py`
- Updated `__init__.py` exports for new modules

### Files Created
- `backend/src/scraper/validators.py` - URL validation and SSRF protection
- `backend/src/scraper/sanitization.py` - Content sanitization utilities

### Files Modified
- `CLAUDE.md` - Added critical rule about plan adherence
- `backend/src/scraper/rate_limiter.py` - Added Crawl4AI RateLimiter integration
- `backend/src/scraper/engine.py` - Added MemoryAdaptiveDispatcher and batch scraping
- `backend/src/scraper/robots.py` - Added Crawl4AI native robots.txt functions
- `backend/src/scraper/__init__.py` - Updated exports

### Notes
- All 87 tests passing, ruff linting clean
- Phase 2 now fully aligned with IMPLEMENTATION_PLAN.md
- Ready for Phase 3 (RAG System)

---

## [2026-01-08 Session 3]

### Changes
- **Phase 2 Scraper Engine Complete**: Implemented all 7 sections of Phase 2
- Created extraction strategies module:
  - `JsonLdStrategy` - Extract from JSON-LD structured data
  - `CssSelectorStrategy` - Extract using store-specific CSS selectors
  - `XPathStrategy` - Fallback XPath extraction
  - `LlmExtractionStrategy` - Placeholder for LLM-based extraction
- Implemented ScraperEngine class with waterfall extraction (JSON-LD -> CSS -> XPath -> LLM)
- Created rate limiting system:
  - Global rate limit (10 scrapes/minute)
  - Per-store rate limits (configurable)
  - Async-safe with semaphore-based concurrency control
- Implemented retry strategy:
  - Error categorization (network, timeout, blocked, etc.)
  - Exponential backoff with configurable delays
  - Category-specific retry rules (no retry for 404, limited for 403)
- Created block detection module:
  - CAPTCHA detection (reCAPTCHA, hCAPTCHA, etc.)
  - Bot detection patterns (Cloudflare, Akamai, etc.)
  - Rate limit detection (429, patterns)
  - Login wall detection, geo-blocking, age gate
- Implemented robots.txt handler with caching
- Created user agent rotation utility with failure-based rotation
- Wrote 37 unit tests for all scraper components

### Files Created
- `backend/src/scraper/strategies.py` - Extraction strategies
- `backend/src/scraper/engine.py` - Main ScraperEngine class
- `backend/src/scraper/rate_limiter.py` - Rate limiting
- `backend/src/scraper/retry.py` - Retry with exponential backoff
- `backend/src/scraper/block_detection.py` - Block detection
- `backend/src/scraper/robots.py` - robots.txt handling
- `backend/src/scraper/user_agent.py` - User agent management
- `backend/src/scraper/__init__.py` - Public API exports
- `backend/tests/test_scraper.py` - 37 unit tests

### Notes
- All 87 tests passing (50 from Phase 1 + 37 from Phase 2)
- Ruff linting clean
- Ready for Phase 3 (RAG System)

---

## [2026-01-08 Session 2]

### Changes
- **Phase 1 Foundation Complete**: Implemented all 6 sections of Phase 1
- Created GitHub repository (Royaldner/perpee) and connected local project
- Added comprehensive .gitignore for Python/React/SQLite stack
- Set up backend project structure with FastAPI, SQLModel, Pydantic AI
- Created all database models with SQLModel:
  - Product, Store, Alert, Schedule, PriceHistory
  - ScrapeLog, Notification, CanonicalProduct
  - Proper enums (ProductStatus, AlertType, ExtractionStrategy, etc.)
  - Soft delete support with deleted_at timestamps
- Configured Alembic migrations with SQLite-compatible sync migrations
- Implemented core utilities:
  - Custom exception hierarchy (ScraperError, URLError, AgentError, etc.)
  - App-wide constants (rate limits, timeouts, store lists)
  - Security utilities (URL validation, SSRF protection, XSS sanitization)
- Created P0 store seed data for 16 Canadian retailers with CSS selectors
- Set up Docker with Playwright/Chromium support (Oracle Cloud compatible)
- Wrote 50 unit tests covering models, security, and constants
- Created PR #1 for Phase 1

### Files Modified
- `backend/` - New Python backend (35 files)
  - `backend/pyproject.toml` - Dependencies and project config
  - `backend/config/settings.py` - Pydantic Settings
  - `backend/config/stores_seed.py` - 16 store configurations
  - `backend/src/database/models.py` - SQLModel models
  - `backend/src/database/repository.py` - CRUD operations
  - `backend/src/database/session.py` - Async session factory
  - `backend/src/core/exceptions.py` - Custom exceptions
  - `backend/src/core/constants.py` - App constants
  - `backend/src/core/security.py` - Security utilities
  - `backend/src/api/main.py` - FastAPI app entry point
  - `backend/alembic/` - Migration configuration
  - `backend/tests/test_phase1.py` - 50 unit tests
- `docker/` - Docker configuration
  - `docker/Dockerfile` - Python 3.11 + Playwright
  - `docker/docker-compose.yml` - Development config
- `.gitignore` - Added for Python/React/SQLite

### Notes
- All 50 tests passing, ruff linting clean
- PR #1 open: https://github.com/Royaldner/perpee/pull/1
- Ready for Phase 2 (Scraper Engine) after PR merge

---

## [2026-01-07 Session 1]

### Changes
- Reviewed IMPLEMENTATION_PLAN.md against TECHNICAL_SPEC for completeness
- Moved Docker setup from Phase 8 to Phase 1 (early container validation for Playwright/Crawl4AI)
- Fixed P0 store list: changed from 9 incorrect fashion/footwear stores to 16 correct stores per tech spec:
  - General (4): Amazon, Walmart, Costco, Canadian Tire
  - Electronics (5): Best Buy, The Source, Memory Express, Canada Computers, Newegg
  - Grocery (5): Loblaws, No Frills, Real Canadian Superstore, Metro, Sobeys
  - Pharmacy (1): Shoppers Drug Mart
  - Home (1): Home Depot
- Added missing scraper details to Phase 2:
  - Section 2.3: Retry Strategy & Block Detection (retry matrix, user feedback, CAPTCHA detection, progressive evasion, robots.txt)
  - Section 2.4: Timeout Configuration (30s request, 2min operation, page load wait, per-store selectors)
- Added Soft Periwinkle theme color palette to Phase 7 frontend setup (hex values 50-950)
- Updated Phase 8 integration tests to reference 16 P0 stores
- Split Docker tasks: Phase 1 = basic setup + Playwright validation, Phase 8 = production optimization

### Files Modified
- `IMPLEMENTATION_PLAN.md` - Major updates to Phases 1, 2, 7, and 8

### Notes
- Docker moved to Phase 1 because Playwright/Crawl4AI behavior differs significantly between Windows (dev) and Linux (container). Early validation prevents architecture rework later.
- Tech spec has 16 P0 stores; original implementation plan had wrong stores from an earlier draft.
- CLAUDE.md already consistent with tech spec, no changes needed.
