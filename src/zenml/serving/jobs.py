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
"""Job management and state tracking for ZenML pipeline serving."""

import asyncio
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

from zenml.logger import get_logger

logger = get_logger(__name__)


class JobStatus(str, Enum):
    """Status of a serving job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class JobMetadata:
    """Metadata for a serving job."""

    job_id: str
    status: JobStatus
    parameters: Dict[str, Any]
    run_name: Optional[str] = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[Any] = None
    execution_time: Optional[float] = None
    pipeline_name: Optional[str] = None
    steps_executed: int = 0

    # Cancellation support
    cancellation_token: threading.Event = field(
        default_factory=threading.Event
    )
    canceled_by: Optional[str] = None
    cancel_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert job metadata to dictionary for API responses."""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "parameters": self.parameters,
            "run_name": self.run_name,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat()
            if self.started_at
            else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "error": self.error,
            "result": self.result,
            "execution_time": self.execution_time,
            "pipeline_name": self.pipeline_name,
            "steps_executed": self.steps_executed,
            "canceled_by": self.canceled_by,
            "cancel_reason": self.cancel_reason,
        }


class JobRegistry:
    """Thread-safe in-memory registry for tracking serving jobs.

    This provides a simple in-memory job tracking system with basic
    lifecycle management, cancellation, and cleanup. Uses threading.Lock
    for thread-safety across worker threads and the main event loop.

    For production deployments with multiple replicas, this could be
    extended to use Redis or another shared storage backend.
    """

    def __init__(self, max_jobs: int = 1000, cleanup_interval: int = 3600):
        """Initialize the job registry.

        Args:
            max_jobs: Maximum number of jobs to keep in memory
            cleanup_interval: Interval in seconds to cleanup old completed jobs
        """
        self._jobs: Dict[str, JobMetadata] = {}
        self._max_jobs = max_jobs
        self._cleanup_interval = cleanup_interval
        self._lock = threading.RLock()  # Thread-safe for cross-thread access
        self._cleanup_task: Optional[asyncio.Task[None]] = None
        self._shutdown = False

        # Callback for handling job status transitions (e.g., closing streams)
        self._status_change_callback: Optional[
            Callable[[str, JobStatus], None]
        ] = None

        logger.info(f"JobRegistry initialized with max_jobs={max_jobs}")

    def set_status_change_callback(
        self, callback: Callable[[str, JobStatus], None]
    ) -> None:
        """Set callback to be called when job status changes to final state.

        Args:
            callback: Function that takes (job_id, new_status) and handles cleanup
        """
        with self._lock:
            self._status_change_callback = callback
            logger.debug("Job status change callback registered")

    async def start_cleanup_task(self) -> None:
        """Start the background cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Job cleanup task started")

    async def stop_cleanup_task(self) -> None:
        """Stop the background cleanup task."""
        self._shutdown = True
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Job cleanup task stopped")

    def create_job(
        self,
        parameters: Dict[str, Any],
        run_name: Optional[str] = None,
        pipeline_name: Optional[str] = None,
    ) -> str:
        """Create a new job and return its ID.

        Args:
            parameters: Pipeline parameters
            run_name: Optional run name
            pipeline_name: Optional pipeline name

        Returns:
            Job ID
        """
        job_id = str(uuid4())

        job_metadata = JobMetadata(
            job_id=job_id,
            status=JobStatus.PENDING,
            parameters=parameters,
            run_name=run_name,
            pipeline_name=pipeline_name,
        )

        with self._lock:
            self._jobs[job_id] = job_metadata

            # Cleanup old jobs if we're at capacity
            if len(self._jobs) > self._max_jobs:
                self._cleanup_old_jobs()

        logger.debug(f"Created job {job_id}")
        return job_id

    def get_job(self, job_id: str) -> Optional[JobMetadata]:
        """Get job metadata by ID.

        Args:
            job_id: Job ID to retrieve

        Returns:
            JobMetadata if found, None otherwise
        """
        with self._lock:
            return self._jobs.get(job_id)

    def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        error: Optional[str] = None,
        result: Optional[Any] = None,
        execution_time: Optional[float] = None,
        steps_executed: Optional[int] = None,
    ) -> bool:
        """Update job status and metadata.

        Args:
            job_id: Job ID to update
            status: New status
            error: Error message if failed
            result: Execution result if completed
            execution_time: Total execution time
            steps_executed: Number of steps executed

        Returns:
            True if job was updated, False if not found
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False

            job.status = status

            if status == JobStatus.RUNNING and not job.started_at:
                job.started_at = datetime.now(timezone.utc)
            elif status in [
                JobStatus.COMPLETED,
                JobStatus.FAILED,
                JobStatus.CANCELED,
            ]:
                job.completed_at = datetime.now(timezone.utc)

            if error:
                job.error = error
            if result is not None:
                job.result = result
            if execution_time is not None:
                job.execution_time = execution_time
            if steps_executed is not None:
                job.steps_executed = steps_executed

            # Call status change callback for final states (close streams, etc.)
            if status in [
                JobStatus.COMPLETED,
                JobStatus.FAILED,
                JobStatus.CANCELED,
            ]:
                if self._status_change_callback:
                    try:
                        self._status_change_callback(job_id, status)
                    except Exception as e:
                        logger.warning(
                            f"Status change callback failed for job {job_id}: {e}"
                        )

            logger.debug(f"Updated job {job_id} status to {status.value}")
            return True

    def cancel_job(
        self,
        job_id: str,
        canceled_by: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> bool:
        """Cancel a job and trigger its cancellation token.

        Args:
            job_id: Job ID to cancel
            canceled_by: Who requested the cancellation
            reason: Reason for cancellation

        Returns:
            True if job was canceled, False if not found or already completed
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False

            # Can only cancel pending or running jobs
            if job.status in [
                JobStatus.COMPLETED,
                JobStatus.FAILED,
                JobStatus.CANCELED,
            ]:
                return False

            job.status = JobStatus.CANCELED
            job.completed_at = datetime.now(timezone.utc)
            job.canceled_by = canceled_by
            job.cancel_reason = reason

            # Trigger cancellation token (this is thread-safe)
            job.cancellation_token.set()

            # Call status change callback for cancellation (close streams, etc.)
            if self._status_change_callback:
                try:
                    self._status_change_callback(job_id, JobStatus.CANCELED)
                except Exception as e:
                    logger.warning(
                        f"Status change callback failed for canceled job {job_id}: {e}"
                    )

            logger.info(
                f"Canceled job {job_id} (by: {canceled_by}, reason: {reason})"
            )
            return True

    def list_jobs(
        self, status_filter: Optional[JobStatus] = None, limit: int = 100
    ) -> list[Dict[str, Any]]:
        """List jobs with optional filtering.

        Args:
            status_filter: Optional status to filter by
            limit: Maximum number of jobs to return

        Returns:
            List of job dictionaries
        """
        with self._lock:
            jobs = list(self._jobs.values())

        # Filter by status if requested
        if status_filter:
            jobs = [job for job in jobs if job.status == status_filter]

        # Sort by creation time (newest first)
        jobs.sort(key=lambda x: x.created_at, reverse=True)

        # Apply limit
        jobs = jobs[:limit]

        return [job.to_dict() for job in jobs]

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics.

        Returns:
            Dictionary with registry statistics
        """
        with self._lock:
            total_jobs = len(self._jobs)
            status_counts: Dict[str, int] = {}

            for job in self._jobs.values():
                status = job.status.value
                status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_jobs": total_jobs,
            "max_jobs": self._max_jobs,
            "status_counts": status_counts,
        }

    def _cleanup_old_jobs(self) -> None:
        """Clean up old completed jobs to prevent memory growth.

        Note: This method assumes _lock is already held by the caller.
        """
        # Get all completed jobs sorted by completion time
        completed_jobs = [
            (job_id, job)
            for job_id, job in self._jobs.items()
            if job.status
            in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELED]
            and job.completed_at is not None
        ]

        completed_jobs.sort(key=lambda x: x[1].completed_at)  # type: ignore

        # Remove oldest jobs if we have too many
        jobs_to_remove = max(
            0, len(self._jobs) - int(self._max_jobs * 0.8)
        )  # Keep 80% capacity

        for i in range(min(jobs_to_remove, len(completed_jobs))):
            job_id, _ = completed_jobs[i]
            del self._jobs[job_id]
            logger.debug(f"Cleaned up old job: {job_id}")

    async def _cleanup_loop(self) -> None:
        """Background task to periodically clean up old jobs."""
        while not self._shutdown:
            try:
                await asyncio.sleep(self._cleanup_interval)
                if not self._shutdown:
                    with self._lock:
                        self._cleanup_old_jobs()
                    logger.debug("Periodic job cleanup completed")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in job cleanup loop: {e}")


# Global job registry instance
_job_registry: Optional[JobRegistry] = None


def get_job_registry_sync() -> JobRegistry:
    """Get the global job registry instance synchronously.

    Returns:
        Global JobRegistry instance
    """
    global _job_registry
    if _job_registry is None:
        _job_registry = JobRegistry()
        # Start cleanup task will be called from async context when needed
    return _job_registry


def get_job_registry() -> JobRegistry:
    """Get the global job registry instance (sync version for thread safety).

    Returns:
        Global sync JobRegistry instance
    """
    global _job_registry
    if _job_registry is None:
        _job_registry = JobRegistry()
        # Start cleanup task in background
        import asyncio

        try:
            asyncio.create_task(_job_registry.start_cleanup_task())
        except RuntimeError:
            # No event loop running, will be started later
            pass

    return _job_registry


# Removed AsyncJobRegistryWrapper - using sync JobRegistry directly for thread safety


def set_job_registry(registry: JobRegistry) -> None:
    """Set a custom job registry (useful for testing).

    Args:
        registry: Custom job registry instance
    """
    global _job_registry
    _job_registry = registry


async def shutdown_job_registry() -> None:
    """Shutdown the global job registry."""
    global _job_registry
    if _job_registry is not None:
        await _job_registry.stop_cleanup_task()
        _job_registry = None
