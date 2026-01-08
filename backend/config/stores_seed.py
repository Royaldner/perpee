"""
P0 Store seed data for Perpee.
Contains CSS selectors and configuration for 16 Canadian retailers.

Selector priority: JSON-LD > CSS > XPath > LLM
Most Canadian stores support JSON-LD structured data.
"""

from src.database.models import Store

# ===========================================
# Store Configurations
# ===========================================

P0_STORES: list[dict] = [
    # ===========================================
    # General Retailers (4)
    # ===========================================
    {
        "domain": "amazon.ca",
        "name": "Amazon Canada",
        "is_whitelisted": True,
        "is_active": True,
        "rate_limit_rpm": 5,  # Amazon is strict
        "selectors": {
            "json_ld": True,  # Amazon has good JSON-LD
            "price": {
                "css": [
                    "span.a-price span.a-offscreen",
                    "#priceblock_ourprice",
                    "#priceblock_dealprice",
                    "span.priceToPay span.a-offscreen",
                ],
            },
            "name": {
                "css": ["#productTitle", "h1.a-size-large"],
            },
            "availability": {
                "css": ["#availability span", "#outOfStock"],
                "in_stock_patterns": ["in stock", "in_stock", "available"],
            },
            "image": {
                "css": ["#landingImage", "#imgBlkFront", "#main-image-container img"],
            },
            "original_price": {
                "css": [
                    "span.a-price[data-a-strike] span.a-offscreen",
                    ".basisPrice span.a-offscreen",
                ],
            },
            "wait_for": "#productTitle",
        },
    },
    {
        "domain": "walmart.ca",
        "name": "Walmart Canada",
        "is_whitelisted": True,
        "is_active": True,
        "rate_limit_rpm": 8,
        "selectors": {
            "json_ld": True,  # Walmart has JSON-LD
            "price": {
                "css": [
                    "[data-testid='price-value']",
                    ".css-1rkhjmb",  # Current price
                    "[itemprop='price']",
                ],
            },
            "name": {
                "css": ["h1[itemprop='name']", "[data-testid='product-title']"],
            },
            "availability": {
                "css": ["[data-testid='add-to-cart-btn']", ".fulfillment-option"],
                "in_stock_patterns": ["add to cart", "in stock"],
            },
            "image": {
                "css": ["[data-testid='hero-image'] img", "img.db"],
            },
            "wait_for": "[data-testid='product-title']",
        },
    },
    {
        "domain": "costco.ca",
        "name": "Costco Canada",
        "is_whitelisted": True,
        "is_active": True,
        "rate_limit_rpm": 6,
        "selectors": {
            "json_ld": True,
            "price": {
                "css": [
                    ".price-info .your-price .value",
                    "#pull-right-price span",
                    ".product-price",
                ],
            },
            "name": {
                "css": ["h1.product-name", ".product-h1-container h1"],
            },
            "availability": {
                "css": ["#add-to-cart-btn", ".inventory-status"],
                "in_stock_patterns": ["add to cart", "in stock"],
            },
            "image": {
                "css": [".product-image img", "#RICHFXViewerContainer img"],
            },
            "wait_for": "h1.product-name",
        },
    },
    {
        "domain": "canadiantire.ca",
        "name": "Canadian Tire",
        "is_whitelisted": True,
        "is_active": True,
        "rate_limit_rpm": 8,
        "selectors": {
            "json_ld": True,
            "price": {
                "css": [
                    "[data-testid='price']",
                    ".product-price__actual-price",
                    "[itemprop='price']",
                ],
            },
            "name": {
                "css": ["h1[data-testid='product-title']", "h1.pdp-product-title__title"],
            },
            "availability": {
                "css": ["[data-testid='add-to-cart']", ".fulfillment-options"],
                "in_stock_patterns": ["add to cart", "in stock", "available"],
            },
            "image": {
                "css": [".product-image-carousel img", "[data-testid='product-image']"],
            },
            "wait_for": "h1[data-testid='product-title']",
        },
    },
    # ===========================================
    # Electronics (5)
    # ===========================================
    {
        "domain": "bestbuy.ca",
        "name": "Best Buy Canada",
        "is_whitelisted": True,
        "is_active": True,
        "rate_limit_rpm": 8,
        "selectors": {
            "json_ld": True,  # Best Buy has good JSON-LD
            "price": {
                "css": [
                    "[data-automation='product-price'] .price_FHDfG",
                    ".productPricing_price",
                    "[itemprop='price']",
                ],
            },
            "name": {
                "css": ["h1.productName_2KoPa", "[data-automation='product-title']", "h1"],
            },
            "availability": {
                "css": [
                    "[data-automation='add-to-cart-button']",
                    ".availabilityMessage_ig-Cp",
                ],
                "in_stock_patterns": ["add to cart", "available", "in stock"],
            },
            "image": {
                "css": [".productImage_1pZcy img", "[data-automation='product-gallery'] img"],
            },
            "original_price": {
                "css": [".priceWithSavings_3yEes .line-through", ".wasPrice"],
            },
            "wait_for": "[data-automation='product-title']",
        },
    },
    {
        "domain": "thesource.ca",
        "name": "The Source",
        "is_whitelisted": True,
        "is_active": True,
        "rate_limit_rpm": 10,
        "selectors": {
            "json_ld": True,
            "price": {
                "css": [".product-price .price", "[itemprop='price']", ".price-box .price"],
            },
            "name": {
                "css": ["h1.page-title", ".product-info h1"],
            },
            "availability": {
                "css": [".add-to-cart-buttons button", ".stock-status"],
                "in_stock_patterns": ["add to cart", "in stock"],
            },
            "image": {
                "css": [".product-image img", ".gallery-image img"],
            },
            "wait_for": "h1.page-title",
        },
    },
    {
        "domain": "memoryexpress.com",
        "name": "Memory Express",
        "is_whitelisted": True,
        "is_active": True,
        "rate_limit_rpm": 10,
        "selectors": {
            "json_ld": True,
            "price": {
                "css": [".GrandTotal", ".ProductPrice", "[itemprop='price']"],
            },
            "name": {
                "css": ["h1.ProductTitle", ".product-page h1"],
            },
            "availability": {
                "css": [".AddToCart", ".InventoryLevelStatus"],
                "in_stock_patterns": ["add to cart", "in stock"],
            },
            "image": {
                "css": [".ProductImage img", "#ProductImage"],
            },
            "wait_for": "h1.ProductTitle",
        },
    },
    {
        "domain": "canadacomputers.com",
        "name": "Canada Computers",
        "is_whitelisted": True,
        "is_active": True,
        "rate_limit_rpm": 10,
        "selectors": {
            "json_ld": True,
            "price": {
                "css": [".price-show-panel strong", "[itemprop='price']", ".price-display"],
            },
            "name": {
                "css": ["h1.h3", ".product-name h1", "h1[itemprop='name']"],
            },
            "availability": {
                "css": [".btn-add-cart", ".stocklevel-icon"],
                "in_stock_patterns": ["add to cart", "in stock", "available online"],
            },
            "image": {
                "css": [".product-img-main img", ".productpage-main-image img"],
            },
            "wait_for": ".price-show-panel",
        },
    },
    {
        "domain": "newegg.ca",
        "name": "Newegg Canada",
        "is_whitelisted": True,
        "is_active": True,
        "rate_limit_rpm": 8,
        "selectors": {
            "json_ld": True,
            "price": {
                "css": [
                    ".product-price .price-current strong",
                    "[itemprop='price']",
                    ".price-main-product",
                ],
            },
            "name": {
                "css": [".product-title h1", "[itemprop='name']"],
            },
            "availability": {
                "css": [".product-buy-box .btn-primary", ".product-inventory"],
                "in_stock_patterns": ["add to cart", "in stock"],
            },
            "image": {
                "css": [".product-view-img-original", ".swiper-slide img"],
            },
            "original_price": {
                "css": [".price-was-data", ".price-save-percent"],
            },
            "wait_for": ".product-title",
        },
    },
    # ===========================================
    # Grocery (5)
    # ===========================================
    {
        "domain": "loblaws.ca",
        "name": "Loblaws",
        "is_whitelisted": True,
        "is_active": True,
        "rate_limit_rpm": 8,
        "selectors": {
            "json_ld": True,
            "price": {
                "css": [
                    "[data-testid='product-price']",
                    ".product-price__value",
                    "[data-testid='pdp-price']",
                ],
            },
            "name": {
                "css": ["[data-testid='product-title']", "h1.product-name"],
            },
            "availability": {
                "css": ["[data-testid='add-to-cart-button']", ".fulfillment-atc"],
                "in_stock_patterns": ["add to cart", "add to list"],
            },
            "image": {
                "css": [
                    "[data-testid='product-image'] img",
                    ".product-image-container img",
                ],
            },
            "wait_for": "[data-testid='product-title']",
        },
    },
    {
        "domain": "nofrills.ca",
        "name": "No Frills",
        "is_whitelisted": True,
        "is_active": True,
        "rate_limit_rpm": 8,
        "selectors": {
            "json_ld": True,  # Uses same platform as Loblaws
            "price": {
                "css": [
                    "[data-testid='product-price']",
                    ".product-price__value",
                ],
            },
            "name": {
                "css": ["[data-testid='product-title']", "h1.product-name"],
            },
            "availability": {
                "css": ["[data-testid='add-to-cart-button']"],
                "in_stock_patterns": ["add to cart"],
            },
            "image": {
                "css": ["[data-testid='product-image'] img"],
            },
            "wait_for": "[data-testid='product-title']",
        },
    },
    {
        "domain": "realcanadiansuperstore.ca",
        "name": "Real Canadian Superstore",
        "is_whitelisted": True,
        "is_active": True,
        "rate_limit_rpm": 8,
        "selectors": {
            "json_ld": True,  # Uses same platform as Loblaws
            "price": {
                "css": [
                    "[data-testid='product-price']",
                    ".product-price__value",
                ],
            },
            "name": {
                "css": ["[data-testid='product-title']", "h1.product-name"],
            },
            "availability": {
                "css": ["[data-testid='add-to-cart-button']"],
                "in_stock_patterns": ["add to cart"],
            },
            "image": {
                "css": ["[data-testid='product-image'] img"],
            },
            "wait_for": "[data-testid='product-title']",
        },
    },
    {
        "domain": "metro.ca",
        "name": "Metro",
        "is_whitelisted": True,
        "is_active": True,
        "rate_limit_rpm": 8,
        "selectors": {
            "json_ld": True,
            "price": {
                "css": [
                    ".price-product-tile .pi--price",
                    ".product-price",
                    "[data-main-price]",
                ],
            },
            "name": {
                "css": [".pi--product-name", ".product-info h1"],
            },
            "availability": {
                "css": [".add-to-cart-button", ".pi--atc-btn"],
                "in_stock_patterns": ["add to cart", "add"],
            },
            "image": {
                "css": [".pi--product-image img", ".product-image img"],
            },
            "wait_for": ".pi--product-name",
        },
    },
    {
        "domain": "sobeys.com",
        "name": "Sobeys",
        "is_whitelisted": True,
        "is_active": True,
        "rate_limit_rpm": 8,
        "selectors": {
            "json_ld": True,
            "price": {
                "css": [
                    ".product-price .price",
                    "[data-testid='product-price']",
                ],
            },
            "name": {
                "css": ["h1.product-name", "[data-testid='product-name']"],
            },
            "availability": {
                "css": ["[data-testid='add-to-cart']", ".add-to-cart"],
                "in_stock_patterns": ["add to cart"],
            },
            "image": {
                "css": [".product-image img", "[data-testid='product-image']"],
            },
            "wait_for": "h1.product-name",
        },
    },
    # ===========================================
    # Pharmacy (1)
    # ===========================================
    {
        "domain": "shoppersdrugmart.ca",
        "name": "Shoppers Drug Mart",
        "is_whitelisted": True,
        "is_active": True,
        "rate_limit_rpm": 8,
        "selectors": {
            "json_ld": True,
            "price": {
                "css": [
                    ".price-section .price",
                    "[data-testid='price']",
                    ".product-price",
                ],
            },
            "name": {
                "css": ["h1.product-name", "[data-testid='product-name']", "h1"],
            },
            "availability": {
                "css": ["[data-testid='add-to-cart']", ".add-to-cart-button"],
                "in_stock_patterns": ["add to cart", "add to bag"],
            },
            "image": {
                "css": [".product-image-main img", "[data-testid='product-image']"],
            },
            "wait_for": "h1.product-name",
        },
    },
    # ===========================================
    # Home Improvement (1)
    # ===========================================
    {
        "domain": "homedepot.ca",
        "name": "Home Depot Canada",
        "is_whitelisted": True,
        "is_active": True,
        "rate_limit_rpm": 8,
        "selectors": {
            "json_ld": True,
            "price": {
                "css": [
                    ".price__dollars",
                    "[data-automation='product-price']",
                    ".acl-product-price__price",
                ],
            },
            "name": {
                "css": ["h1.product-title", ".product-details__title h1"],
            },
            "availability": {
                "css": ["[data-automation='add-to-cart']", ".store-availability"],
                "in_stock_patterns": ["add to cart", "in stock", "available"],
            },
            "image": {
                "css": [".mediagallery__mainimage img", "[data-automation='product-image']"],
            },
            "original_price": {
                "css": [".acl-product-price__was-price", ".price--was"],
            },
            "wait_for": "h1.product-title",
        },
    },
]


def get_store_models() -> list[Store]:
    """
    Convert seed data to Store model instances.

    Returns:
        List of Store model instances ready to insert
    """
    return [
        Store(
            domain=store["domain"],
            name=store["name"],
            is_whitelisted=store["is_whitelisted"],
            is_active=store["is_active"],
            rate_limit_rpm=store["rate_limit_rpm"],
            selectors=store["selectors"],
        )
        for store in P0_STORES
    ]


async def seed_stores(session) -> int:
    """
    Seed the database with P0 store configurations.

    Args:
        session: Async database session

    Returns:
        Number of stores inserted/updated
    """
    from src.database.repository import upsert_store

    count = 0
    for store_data in P0_STORES:
        store = Store(
            domain=store_data["domain"],
            name=store_data["name"],
            is_whitelisted=store_data["is_whitelisted"],
            is_active=store_data["is_active"],
            rate_limit_rpm=store_data["rate_limit_rpm"],
            selectors=store_data["selectors"],
        )
        await upsert_store(session, store)
        count += 1

    return count


# ===========================================
# Store Lookup Helpers
# ===========================================


def get_store_config(domain: str) -> dict | None:
    """
    Get store configuration by domain.

    Args:
        domain: Store domain (e.g., 'amazon.ca')

    Returns:
        Store config dict or None if not found
    """
    # Normalize domain
    if domain.startswith("www."):
        domain = domain[4:]

    for store in P0_STORES:
        if store["domain"] == domain:
            return store

    return None


def get_store_selectors(domain: str) -> dict | None:
    """
    Get CSS selectors for a store.

    Args:
        domain: Store domain

    Returns:
        Selectors dict or None
    """
    config = get_store_config(domain)
    if config:
        return config.get("selectors")
    return None


def store_supports_json_ld(domain: str) -> bool:
    """
    Check if store supports JSON-LD extraction.

    Args:
        domain: Store domain

    Returns:
        True if JSON-LD is supported
    """
    selectors = get_store_selectors(domain)
    if selectors:
        return selectors.get("json_ld", False)
    return False
