"""
Self-healing module for Perpee.

Handles automatic recovery when scraper selectors break.
"""

from .detector import (
    DEFAULT_ATTENTION_THRESHOLD,
    DEFAULT_FAILURE_THRESHOLD,
    HEALABLE_CATEGORIES,
    MAX_HEALING_ATTEMPTS,
    FailureAnalysis,
    FailureCategory,
    FailureDetector,
    get_failure_detector,
)
from .health import (
    HealthReport,
    StoreHealth,
    StoreHealthCalculator,
    get_store_health_calculator,
)
from .regenerator import (
    RegenerationResult,
    SelectorConfig,
    SelectorRegenerator,
    get_selector_regenerator,
)
from .service import (
    HealingAttempt,
    HealingReport,
    SelfHealingService,
    get_self_healing_service,
)

__all__ = [
    # Detector
    "FailureDetector",
    "FailureCategory",
    "FailureAnalysis",
    "get_failure_detector",
    # Regenerator
    "SelectorRegenerator",
    "SelectorConfig",
    "RegenerationResult",
    "get_selector_regenerator",
    # Service
    "SelfHealingService",
    "HealingAttempt",
    "HealingReport",
    "get_self_healing_service",
    # Health
    "StoreHealthCalculator",
    "StoreHealth",
    "HealthReport",
    "get_store_health_calculator",
    # Constants
    "DEFAULT_FAILURE_THRESHOLD",
    "DEFAULT_ATTENTION_THRESHOLD",
    "MAX_HEALING_ATTEMPTS",
    "HEALABLE_CATEGORIES",
]
