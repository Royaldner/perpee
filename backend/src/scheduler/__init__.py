"""
Scheduler module for Perpee.

Handles automated price monitoring with APScheduler.
"""

from .batching import BatchProcessor, BatchResult, get_batch_processor
from .jobs import (
    JOB_CLEANUP,
    JOB_DAILY_SCRAPE,
    JOB_HEALING,
    JOB_HEALTH_CHECK,
    JOB_PREFIX_PRODUCT,
    JOB_PREFIX_STORE,
    cleanup_job,
    daily_scrape_job,
    healing_job,
    health_calculation_job,
    product_scrape_job,
    register_default_jobs,
    register_product_job,
    register_store_job,
    store_batch_job,
)
from .service import (
    SchedulerService,
    get_scheduler_service,
    shutdown_scheduler,
    start_scheduler,
)
from .triggers import (
    DEFAULT_CRON,
    MIN_INTERVAL_HOURS,
    SCHEDULE_PRESETS,
    WEEKLY_CRON,
    CronValidation,
    ScheduleInfo,
    create_schedule,
    describe_cron,
    get_effective_schedule,
    get_next_run_time,
    get_preset_schedule,
    parse_cron_to_trigger,
    update_schedule_next_run,
    validate_cron,
    validate_cron_with_minimum,
)

__all__ = [
    # Service
    "SchedulerService",
    "get_scheduler_service",
    "start_scheduler",
    "shutdown_scheduler",
    # Jobs
    "daily_scrape_job",
    "product_scrape_job",
    "store_batch_job",
    "health_calculation_job",
    "healing_job",
    "cleanup_job",
    "register_default_jobs",
    "register_product_job",
    "register_store_job",
    # Job IDs
    "JOB_DAILY_SCRAPE",
    "JOB_HEALTH_CHECK",
    "JOB_CLEANUP",
    "JOB_HEALING",
    "JOB_PREFIX_PRODUCT",
    "JOB_PREFIX_STORE",
    # Batching
    "BatchProcessor",
    "BatchResult",
    "get_batch_processor",
    # Triggers
    "validate_cron",
    "validate_cron_with_minimum",
    "parse_cron_to_trigger",
    "get_next_run_time",
    "get_effective_schedule",
    "create_schedule",
    "update_schedule_next_run",
    "describe_cron",
    "get_preset_schedule",
    "CronValidation",
    "ScheduleInfo",
    # Constants
    "MIN_INTERVAL_HOURS",
    "DEFAULT_CRON",
    "WEEKLY_CRON",
    "SCHEDULE_PRESETS",
]
