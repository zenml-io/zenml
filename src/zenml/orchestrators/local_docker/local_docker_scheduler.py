#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Scheduler for the local Docker orchestrator."""

import atexit
import threading
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional
from uuid import UUID

from zenml.client import Client
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.models import ScheduleResponse

logger = get_logger(__name__)

# APScheduler is an optional dependency
try:
    from apscheduler.executors.pool import ThreadPoolExecutor
    from apscheduler.jobstores.memory import MemoryJobStore
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.date import DateTrigger
    from apscheduler.triggers.interval import IntervalTrigger

    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False


class LocalDockerOrchestratorScheduler:
    """Scheduler for the local Docker orchestrator using APScheduler.

    This scheduler runs as a background service and manages scheduled
    pipeline executions for the local Docker orchestrator.
    """

    _instance: Optional["LocalDockerOrchestratorScheduler"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "LocalDockerOrchestratorScheduler":
        """Create a singleton instance of the scheduler.

        Returns:
            The singleton scheduler instance.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the scheduler."""
        if hasattr(self, "_initialized"):
            return

        self._initialized = True
        self._scheduler: Optional[BackgroundScheduler] = None
        self._orchestrator_id: Optional[UUID] = None

        # Register cleanup on exit
        atexit.register(self.stop)

    def start(self, orchestrator_id: UUID) -> None:
        """Start the scheduler for a specific orchestrator.

        Args:
            orchestrator_id: The UUID of the orchestrator.

        Raises:
            ImportError: If APScheduler is not installed.
        """
        if not APSCHEDULER_AVAILABLE:
            raise ImportError(
                "APScheduler is required for scheduling support in the local "
                "Docker orchestrator. Please install it with: "
                "`pip install 'zenml[local_scheduler]'` or `pip install apscheduler>=3.10.0`"
            )

        if self._scheduler and self._scheduler.running:
            logger.debug("Scheduler is already running.")
            return

        self._orchestrator_id = orchestrator_id

        # Configure the scheduler
        jobstores = {"default": MemoryJobStore()}
        executors = {
            "default": ThreadPoolExecutor(max_workers=10),
        }
        job_defaults = {
            "coalesce": True,  # Combine multiple pending executions into one
            "max_instances": 1,  # Only one instance of a job can run at a time
            "misfire_grace_time": 3600,  # 1 hour grace period for missed jobs
        }

        self._scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="UTC",
        )

        self._scheduler.start()
        logger.info(
            f"Local Docker orchestrator scheduler started for orchestrator {orchestrator_id}."
        )

    def stop(self) -> None:
        """Stop the scheduler."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=True)
            logger.info("Local Docker orchestrator scheduler stopped.")

    def add_schedule(self, schedule: "ScheduleResponse") -> None:
        """Add a schedule to the scheduler.

        Args:
            schedule: The schedule to add.

        Raises:
            RuntimeError: If the scheduler is not running.
            ValueError: If the schedule configuration is invalid.
        """
        if not self._scheduler or not self._scheduler.running:
            raise RuntimeError("Scheduler is not running. Call start() first.")

        job_id = str(schedule.id)

        # Remove existing job if it exists
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)

        # Determine the trigger based on the schedule configuration
        trigger = self._create_trigger(schedule)

        if trigger is None:
            raise ValueError(
                f"Invalid schedule configuration for schedule {schedule.id}"
            )

        # Add the job to the scheduler
        self._scheduler.add_job(
            func=self._execute_pipeline,
            trigger=trigger,
            id=job_id,
            name=schedule.name,
            kwargs={"schedule_id": schedule.id},
            replace_existing=True,
        )

        logger.info(f"Added schedule '{schedule.name}' (ID: {schedule.id})")

    def update_schedule(self, schedule: "ScheduleResponse") -> None:
        """Update an existing schedule.

        Args:
            schedule: The updated schedule.

        Raises:
            RuntimeError: If the scheduler is not running.
        """
        if not self._scheduler or not self._scheduler.running:
            raise RuntimeError("Scheduler is not running. Call start() first.")

        job_id = str(schedule.id)

        if not schedule.active:
            # If the schedule is inactive, remove it
            if self._scheduler.get_job(job_id):
                self._scheduler.remove_job(job_id)
                logger.info(
                    f"Removed inactive schedule '{schedule.name}' (ID: {schedule.id})"
                )
            return

        # Recreate the job with updated configuration
        self.add_schedule(schedule)

    def delete_schedule(self, schedule_id: UUID) -> None:
        """Delete a schedule from the scheduler.

        Args:
            schedule_id: The ID of the schedule to delete.

        Raises:
            RuntimeError: If the scheduler is not running.
        """
        if not self._scheduler or not self._scheduler.running:
            raise RuntimeError("Scheduler is not running. Call start() first.")

        job_id = str(schedule_id)

        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
            logger.info(f"Deleted schedule with ID: {schedule_id}")

    def _create_trigger(self, schedule: "ScheduleResponse") -> Optional[Any]:
        """Create an APScheduler trigger from a ZenML schedule.

        Args:
            schedule: The ZenML schedule.

        Returns:
            An APScheduler trigger, or None if the configuration is invalid.
        """
        # Priority: cron_expression > interval > run_once
        if schedule.cron_expression:
            return CronTrigger.from_crontab(
                schedule.cron_expression,
                timezone="UTC",
            )
        elif schedule.start_time and schedule.interval_second:
            return IntervalTrigger(
                seconds=schedule.interval_second.total_seconds(),
                start_date=schedule.start_time,
                end_date=schedule.end_time,
                timezone="UTC",
            )
        elif schedule.run_once_start_time:
            return DateTrigger(
                run_date=schedule.run_once_start_time,
                timezone="UTC",
            )

        return None

    def _execute_pipeline(self, schedule_id: UUID) -> None:
        """Execute a pipeline for a given schedule.

        This method is called by APScheduler when a schedule fires.

        Args:
            schedule_id: The ID of the schedule.
        """
        try:
            client = Client()

            # Get the schedule
            schedule = client.get_schedule(schedule_id=schedule_id)

            if not schedule.active:
                logger.info(
                    f"Schedule '{schedule.name}' is inactive, skipping execution."
                )
                return

            # Check if we're past the end time
            if schedule.end_time and datetime.utcnow() > schedule.end_time:
                logger.info(
                    f"Schedule '{schedule.name}' has passed its end time, skipping execution."
                )
                return

            if not schedule.pipeline_id:
                logger.warning(
                    f"Schedule '{schedule.name}' has no associated pipeline."
                )
                return

            # Get the pipeline
            pipeline = client.get_pipeline(schedule.pipeline_id)

            logger.info(
                f"Executing scheduled pipeline '{pipeline.name}' for schedule '{schedule.name}'"
            )

            # Run the pipeline with the schedule
            # Note: This will trigger the pipeline to run through the normal
            # execution flow, but with the schedule context
            from zenml import get_pipeline

            try:
                # Get the pipeline instance and run it
                # The pipeline should be registered with the same name
                pipeline_instance = get_pipeline(pipeline.name)
                if pipeline_instance:
                    pipeline_instance.run(schedule=schedule_id)
                    logger.info(
                        f"Successfully triggered pipeline '{pipeline.name}' for schedule '{schedule.name}'"
                    )
                else:
                    logger.error(
                        f"Could not find pipeline instance for '{pipeline.name}'"
                    )
            except Exception as e:
                logger.error(
                    f"Failed to execute pipeline '{pipeline.name}' for schedule '{schedule.name}': {e}"
                )

        except Exception as e:
            logger.error(
                f"Error executing scheduled pipeline for schedule {schedule_id}: {e}",
                exc_info=True,
            )

    def list_jobs(self) -> Dict[str, Any]:
        """List all scheduled jobs.

        Returns:
            A dictionary of job information.

        Raises:
            RuntimeError: If the scheduler is not running.
        """
        if not self._scheduler or not self._scheduler.running:
            raise RuntimeError("Scheduler is not running. Call start() first.")

        jobs = {}
        for job in self._scheduler.get_jobs():
            jobs[job.id] = {
                "name": job.name,
                "next_run_time": job.next_run_time,
                "trigger": str(job.trigger),
            }

        return jobs
