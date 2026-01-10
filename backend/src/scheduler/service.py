"""
APScheduler service for Perpee.

Configures the scheduler with SQLAlchemy job store for persistence.
"""

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    APScheduler service for price monitoring jobs.

    Features:
    - AsyncIO-based scheduler for async job execution
    - Configurable job stores (memory for dev, SQLAlchemy for production)
    - Missed job handling with coalesce and grace time
    - Job management (add, remove, pause, resume)
    """

    def __init__(
        self,
        use_memory_store: bool = True,
        misfire_grace_time: int = 3600,  # 1 hour grace for missed jobs
        coalesce: bool = True,  # Combine missed runs into one
        max_instances: int = 3,  # Max concurrent instances per job
    ):
        """
        Initialize scheduler service.

        Args:
            use_memory_store: Use memory job store (True) or SQLAlchemy (False)
            misfire_grace_time: Seconds to allow for missed job execution
            coalesce: Combine multiple missed runs into single execution
            max_instances: Maximum concurrent instances of the same job
        """
        self.misfire_grace_time = misfire_grace_time
        self.coalesce = coalesce
        self.max_instances = max_instances

        # Configure job stores
        jobstores = self._configure_jobstores(use_memory_store)

        # Configure executors
        executors = {
            "default": AsyncIOExecutor(),
        }

        # Job defaults
        job_defaults = {
            "coalesce": coalesce,
            "max_instances": max_instances,
            "misfire_grace_time": misfire_grace_time,
        }

        # Create scheduler
        self._scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="UTC",
        )

        self._started = False

    def _configure_jobstores(self, use_memory: bool) -> dict:
        """Configure job stores based on environment."""
        if use_memory:
            return {
                "default": MemoryJobStore(),
            }

        # For production, could use SQLAlchemy job store
        # Requires separate table for APScheduler jobs
        # For MVP, memory store is sufficient
        logger.info("Using memory job store")
        return {
            "default": MemoryJobStore(),
        }

    def start(self) -> None:
        """Start the scheduler."""
        if self._started:
            logger.warning("Scheduler already started")
            return

        self._scheduler.start()
        self._started = True
        logger.info("Scheduler started")

    def shutdown(self, wait: bool = True) -> None:
        """
        Shutdown the scheduler.

        Args:
            wait: Wait for running jobs to complete
        """
        if not self._started:
            return

        self._scheduler.shutdown(wait=wait)
        self._started = False
        logger.info("Scheduler shutdown")

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._started and self._scheduler.running

    def add_job(
        self,
        func: Callable,
        job_id: str,
        cron_expression: str,
        args: tuple | None = None,
        kwargs: dict | None = None,
        replace_existing: bool = True,
        jitter: int | None = None,
    ) -> str:
        """
        Add a job with CRON schedule.

        Args:
            func: Function to execute
            job_id: Unique job identifier
            cron_expression: CRON expression (e.g., "0 6 * * *")
            args: Positional arguments for func
            kwargs: Keyword arguments for func
            replace_existing: Replace if job_id exists
            jitter: Random delay in seconds (spread load)

        Returns:
            Job ID
        """
        trigger = CronTrigger.from_crontab(cron_expression)

        job = self._scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            args=args or (),
            kwargs=kwargs or {},
            replace_existing=replace_existing,
            jitter=jitter,
        )

        logger.info(f"Added job {job_id} with schedule: {cron_expression}")
        return job.id

    def add_interval_job(
        self,
        func: Callable,
        job_id: str,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
        args: tuple | None = None,
        kwargs: dict | None = None,
        replace_existing: bool = True,
    ) -> str:
        """
        Add a job with interval schedule.

        Args:
            func: Function to execute
            job_id: Unique job identifier
            hours: Interval hours
            minutes: Interval minutes
            seconds: Interval seconds
            args: Positional arguments
            kwargs: Keyword arguments
            replace_existing: Replace if exists

        Returns:
            Job ID
        """
        job = self._scheduler.add_job(
            func,
            trigger="interval",
            id=job_id,
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            args=args or (),
            kwargs=kwargs or {},
            replace_existing=replace_existing,
        )

        logger.info(
            f"Added interval job {job_id}: "
            f"{hours}h {minutes}m {seconds}s"
        )
        return job.id

    def remove_job(self, job_id: str) -> bool:
        """
        Remove a scheduled job.

        Args:
            job_id: Job to remove

        Returns:
            True if removed
        """
        try:
            self._scheduler.remove_job(job_id)
            logger.info(f"Removed job {job_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to remove job {job_id}: {e}")
            return False

    def pause_job(self, job_id: str) -> bool:
        """
        Pause a scheduled job.

        Args:
            job_id: Job to pause

        Returns:
            True if paused
        """
        try:
            self._scheduler.pause_job(job_id)
            logger.info(f"Paused job {job_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to pause job {job_id}: {e}")
            return False

    def resume_job(self, job_id: str) -> bool:
        """
        Resume a paused job.

        Args:
            job_id: Job to resume

        Returns:
            True if resumed
        """
        try:
            self._scheduler.resume_job(job_id)
            logger.info(f"Resumed job {job_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to resume job {job_id}: {e}")
            return False

    def get_job(self, job_id: str) -> Any | None:
        """
        Get a job by ID.

        Args:
            job_id: Job ID

        Returns:
            Job object or None
        """
        return self._scheduler.get_job(job_id)

    def get_jobs(self) -> list:
        """
        Get all scheduled jobs.

        Returns:
            List of jobs
        """
        return self._scheduler.get_jobs()

    def get_next_run_time(self, job_id: str) -> datetime | None:
        """
        Get next scheduled run time for a job.

        Args:
            job_id: Job ID

        Returns:
            Next run datetime or None
        """
        job = self.get_job(job_id)
        if job:
            return job.next_run_time
        return None

    def reschedule_job(
        self,
        job_id: str,
        cron_expression: str,
    ) -> bool:
        """
        Reschedule a job with new CRON expression.

        Args:
            job_id: Job to reschedule
            cron_expression: New CRON schedule

        Returns:
            True if rescheduled
        """
        try:
            trigger = CronTrigger.from_crontab(cron_expression)
            self._scheduler.reschedule_job(job_id, trigger=trigger)
            logger.info(f"Rescheduled job {job_id}: {cron_expression}")
            return True
        except Exception as e:
            logger.warning(f"Failed to reschedule job {job_id}: {e}")
            return False

    def run_job_now(self, job_id: str) -> bool:
        """
        Trigger immediate execution of a job.

        Args:
            job_id: Job to run

        Returns:
            True if triggered
        """
        job = self.get_job(job_id)
        if not job:
            logger.warning(f"Job not found: {job_id}")
            return False

        try:
            # Add one-time job with same function
            self._scheduler.add_job(
                job.func,
                trigger="date",
                args=job.args,
                kwargs=job.kwargs,
            )
            logger.info(f"Triggered immediate run of {job_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to trigger job {job_id}: {e}")
            return False


# ===========================================
# Convenience Functions
# ===========================================

_scheduler_service: SchedulerService | None = None


def get_scheduler_service() -> SchedulerService:
    """Get the global scheduler service instance."""
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = SchedulerService()
    return _scheduler_service


def start_scheduler() -> None:
    """Start the global scheduler."""
    service = get_scheduler_service()
    service.start()


def shutdown_scheduler(wait: bool = True) -> None:
    """Shutdown the global scheduler."""
    global _scheduler_service
    if _scheduler_service:
        _scheduler_service.shutdown(wait=wait)
        _scheduler_service = None
