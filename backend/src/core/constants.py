"""
Application-wide constants for Perpee.
"""

# ===========================================
# Rate Limits
# ===========================================

MAX_SCRAPES_PER_MINUTE = 10
MAX_LLM_REQUESTS_PER_MINUTE = 30
DAILY_TOKEN_LIMIT = 100_000

# ===========================================
# Timeouts (seconds)
# ===========================================

REQUEST_TIMEOUT = 30
OPERATION_TIMEOUT = 120
PAGE_LOAD_DELAY = 1.0

# ===========================================
# Agent Limits
# ===========================================

INPUT_TOKEN_LIMIT = 4_000
OUTPUT_TOKEN_LIMIT = 1_000
CONVERSATION_WINDOW_SIZE = 15

# ===========================================
# Scraper Configuration
# ===========================================

MAX_CONCURRENT_BROWSERS = 3
MEMORY_THRESHOLD_PERCENT = 0.70
MAX_RETRIES = 3

# Retry delays (seconds)
RETRY_DELAYS = {
    "network_error": [2, 4, 8],  # Exponential backoff
    "timeout": [2, 4, 8],
    "server_error": [2, 4, 8],
    "rate_limited": [5, 10, 20],
    "forbidden": [5],  # Single retry
}

# ===========================================
# Self-Healing
# ===========================================

MAX_CONSECUTIVE_FAILURES = 3
MAX_HEALING_ATTEMPTS = 3
STORE_FAILURE_THRESHOLD = 0.50  # Flag store if >50% products failing
DEAD_URL_DAYS = 3  # Pause after 3 days of 404s

# ===========================================
# Data Retention (days)
# ===========================================

SCRAPE_LOG_RETENTION_DAYS = 30
NOTIFICATION_RETENTION_DAYS = 90
PRICE_HISTORY_RETENTION_DAYS = 365

# ===========================================
# Price Validation
# ===========================================

MIN_VALID_PRICE = 0.01
MAX_VALID_PRICE = 1_000_000.00
DEFAULT_CURRENCY = "CAD"

# Alert thresholds
DEFAULT_MIN_CHANGE_THRESHOLD = 1.0  # $1 or 1%

# ===========================================
# Scheduler
# ===========================================

DEFAULT_CHECK_HOUR = 6  # 6 AM
DEFAULT_CRON_EXPRESSION = "0 6 * * *"  # Daily at 6 AM
MIN_CHECK_INTERVAL_HOURS = 24  # Minimum 24h between checks

# ===========================================
# User Agent Strings
# ===========================================

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

# ===========================================
# HTTP Headers
# ===========================================

DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-CA,en-US;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

# ===========================================
# Store Categories
# ===========================================

STORE_CATEGORIES = {
    "general": ["amazon.ca", "walmart.ca", "costco.ca", "canadiantire.ca"],
    "electronics": [
        "bestbuy.ca",
        "thesource.ca",
        "memoryexpress.com",
        "canadacomputers.com",
        "newegg.ca",
    ],
    "grocery": [
        "loblaws.ca",
        "nofrills.ca",
        "realcanadiansuperstore.ca",
        "metro.ca",
        "sobeys.com",
    ],
    "pharmacy": ["shoppersdrugmart.ca"],
    "home": ["homedepot.ca"],
}

# All P0 store domains
P0_STORES = [
    store for category in STORE_CATEGORIES.values() for store in category
]

# ===========================================
# Extraction Priorities
# ===========================================

EXTRACTION_PRIORITY = [
    "json_ld",      # 1. Structured data (free)
    "css_selector", # 2. CSS selectors (free)
    "xpath",        # 3. XPath (free)
    "llm",          # 4. LLM extraction (costs tokens)
]

# ===========================================
# JSON-LD Types
# ===========================================

JSON_LD_PRODUCT_TYPES = [
    "Product",
    "IndividualProduct",
    "ProductModel",
]

JSON_LD_OFFER_TYPES = [
    "Offer",
    "AggregateOffer",
]

# ===========================================
# Content Sanitization
# ===========================================

ALLOWED_HTML_TAGS: list[str] = []  # Strip all HTML tags
MAX_TEXT_LENGTH = 10_000  # Max characters for scraped text fields

# ===========================================
# Private IP Ranges (SSRF Protection)
# ===========================================

PRIVATE_IP_RANGES = [
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "127.0.0.0/8",
    "169.254.0.0/16",
    "::1/128",
    "fc00::/7",
    "fe80::/10",
]

# ===========================================
# API Pagination
# ===========================================

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
