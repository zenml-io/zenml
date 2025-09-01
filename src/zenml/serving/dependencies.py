"""Dependency injection container for ZenML serving."""

import time
from typing import Optional
from uuid import uuid4

from zenml.logger import get_logger
from zenml.serving.concurrency import ServingExecutionManager
from zenml.serving.jobs import JobRegistry, JobStatus
from zenml.serving.service import PipelineServingService
from zenml.serving.streams import StreamManager

logger = get_logger(__name__)


class ServingContainer:
    """Dependency injection container for serving services."""

    def __init__(self) -> None:
        """Initialize empty container."""
        self._pipeline_service: Optional[PipelineServingService] = None
        self._job_registry: Optional[JobRegistry] = None
        self._stream_manager: Optional[StreamManager] = None
        self._execution_manager: Optional[ServingExecutionManager] = None
        self._initialized = False

    async def initialize(self, deployment_id: str) -> None:
        """Initialize all services in correct dependency order."""
        if self._initialized:
            return

        logger.info("Initializing serving container...")

        # Initialize services
        self._job_registry = JobRegistry()
        self._execution_manager = ServingExecutionManager()
        self._stream_manager = StreamManager()

        self._pipeline_service = PipelineServingService(deployment_id)
        await self._pipeline_service.initialize()

        # Start background tasks
        await self._job_registry.start_cleanup_task()
        await self._stream_manager.start_cleanup_task()

        # Set up inter-service relationships
        # Create adapter function to match expected signature
        def status_change_callback(job_id: str, status: JobStatus) -> None:
            if self._stream_manager:
                self._stream_manager.close_stream_threadsafe(job_id)

        self._job_registry.set_status_change_callback(status_change_callback)

        self._initialized = True
        logger.info("✅ Serving container initialized")

    async def shutdown(self) -> None:
        """Shutdown all services."""
        if not self._initialized:
            return

        logger.info("Shutting down serving container...")

        if self._stream_manager:
            await self._stream_manager.stop_cleanup_task()
        if self._execution_manager:
            await self._execution_manager.shutdown()
        if self._job_registry:
            await self._job_registry.stop_cleanup_task()

        self._initialized = False
        logger.info("✅ Serving container shutdown complete")

    # Getters
    def get_pipeline_service(self) -> PipelineServingService:
        """Get the pipeline service instance."""
        if not self._initialized or not self._pipeline_service:
            raise RuntimeError("Pipeline service not initialized")
        return self._pipeline_service

    def get_job_registry(self) -> JobRegistry:
        """Get the job registry instance."""
        if not self._initialized or not self._job_registry:
            raise RuntimeError("Job registry not initialized")
        return self._job_registry

    def get_stream_manager(self) -> StreamManager:
        """Get the stream manager instance."""
        if not self._initialized or not self._stream_manager:
            raise RuntimeError("Stream manager not initialized")
        return self._stream_manager

    def get_execution_manager(self) -> ServingExecutionManager:
        """Get the execution manager instance."""
        if not self._initialized or not self._execution_manager:
            raise RuntimeError("Execution manager not initialized")
        return self._execution_manager


# Global container instance
_container: Optional[ServingContainer] = None


def get_container() -> ServingContainer:
    """Get the global serving container."""
    global _container
    if _container is None:
        raise RuntimeError("Container not initialized")
    return _container


async def initialize_container(deployment_id: str) -> None:
    """Initialize the global container."""
    global _container
    if _container is None:
        _container = ServingContainer()
    await _container.initialize(deployment_id)


async def shutdown_container() -> None:
    """Shutdown the global container."""
    global _container
    if _container:
        await _container.shutdown()
        _container = None


# FastAPI dependency functions
def get_pipeline_service() -> PipelineServingService:
    """FastAPI dependency for pipeline service."""
    return get_container().get_pipeline_service()


def get_job_registry() -> JobRegistry:
    """FastAPI dependency for job registry."""
    return get_container().get_job_registry()


def get_stream_manager() -> StreamManager:
    """FastAPI dependency for stream manager."""
    return get_container().get_stream_manager()


def get_execution_manager() -> ServingExecutionManager:
    """FastAPI dependency for execution manager."""
    return get_container().get_execution_manager()


# Request-scoped dependencies
class RequestContext:
    """Request-specific context."""

    def __init__(self) -> None:
        """Initialize request context with unique ID and start time."""
        self.request_id = str(uuid4())
        self.start_time = time.time()


def get_request_context() -> RequestContext:
    """FastAPI dependency for request context."""
    return RequestContext()
