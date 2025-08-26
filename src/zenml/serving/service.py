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
"""Core pipeline serving service implementation."""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator, Dict, Optional
from uuid import UUID

from zenml.client import Client
from zenml.integrations.registry import integration_registry
from zenml.logger import get_logger
from zenml.models import PipelineDeploymentResponse
from zenml.serving.concurrency import (
    TooManyRequestsError,
    get_execution_manager,
)
from zenml.serving.direct_execution import DirectExecutionEngine
from zenml.serving.events import ServingEvent, create_event_builder
from zenml.serving.jobs import (
    JobStatus,
    get_job_registry,
)

# StreamEvent is deprecated, using ServingEvent instead
from zenml.serving.streams import get_stream_manager, get_stream_manager_sync

logger = get_logger(__name__)


class PipelineServingService:
    """Core service for serving ZenML pipelines via FastAPI.

    This service handles the loading, execution, and monitoring of ZenML pipelines
    in a serving context. It provides both synchronous and streaming execution
    capabilities while maintaining compatibility with ZenML's existing execution
    infrastructure.
    """

    def __init__(self, deployment_id: str):
        """Initialize the pipeline serving service.

        Args:
            deployment_id: UUID of the pipeline deployment to serve
        """
        self.deployment_id = deployment_id
        self.deployment: Optional[PipelineDeploymentResponse] = None
        self.parameter_schema: Dict[str, Any] = {}
        self.service_start_time = time.time()
        self.last_execution_time: Optional[datetime] = None

        # Execution statistics
        self.execution_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_execution_time": 0.0,
            "executions_24h": [],  # Store timestamps for 24h tracking
        }

        logger.info(
            f"Initializing PipelineServingService for deployment: {deployment_id}"
        )

    async def initialize(self) -> None:
        """Initialize the service by loading deployment configuration.

        This method loads the pipeline deployment, extracts parameter schema,
        and sets up the execution environment.

        Raises:
            ValueError: If deployment ID is invalid or deployment not found
            Exception: If initialization fails
        """
        try:
            logger.info("Loading pipeline deployment configuration...")

            # Load deployment from ZenML store
            client = Client()

            # Convert deployment_id to UUID safely
            try:
                if isinstance(self.deployment_id, str):
                    deployment_uuid = UUID(self.deployment_id)
                else:
                    deployment_uuid = self.deployment_id
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"Invalid deployment ID format: {self.deployment_id}"
                ) from e

            self.deployment = client.zen_store.get_deployment(
                deployment_id=deployment_uuid
            )

            # Activate integrations to ensure all components are available
            integration_registry.activate_integrations()

            # Extract parameter schema for validation
            self.parameter_schema = self._extract_parameter_schema()

            # Log successful initialization
            pipeline_name = self.deployment.pipeline_configuration.name
            step_count = len(self.deployment.step_configurations)

            logger.info("✅ Service initialized successfully:")
            logger.info(f"   Pipeline: {pipeline_name}")
            logger.info(f"   Steps: {step_count}")
            logger.info(
                f"   Stack: {self.deployment.stack.name if self.deployment.stack else 'unknown'}"
            )
            logger.info(f"   Parameters: {list(self.parameter_schema.keys())}")

        except Exception as e:
            logger.error(f"❌ Failed to initialize service: {str(e)}")
            logger.error(f"   Error type: {type(e)}")
            import traceback

            logger.error(f"   Traceback: {traceback.format_exc()}")
            raise

    def _extract_parameter_schema(self) -> Dict[str, Any]:
        """Extract parameter schema from pipeline deployment.

        Returns:
            Dictionary containing parameter information with types and defaults
        """
        schema: Dict[str, Any] = {}

        if not self.deployment:
            return schema

        # Get parameters from pipeline configuration
        pipeline_params = (
            self.deployment.pipeline_configuration.parameters or {}
        )

        for param_name, param_value in pipeline_params.items():
            # Handle parameter type safely
            try:
                param_type = (
                    type(param_value).__name__
                    if param_value is not None
                    else "NoneType"
                )
            except Exception:
                param_type = "unknown"

            schema[param_name] = {
                "type": param_type,
                "default": param_value,
                "required": False,  # Since it has a default
            }

        # TODO: Enhanced parameter schema extraction
        # In the future, we could:
        # 1. Parse the actual pipeline function signature to get types
        # 2. Extract parameter descriptions from docstrings
        # 3. Identify required vs optional parameters
        # 4. Validate parameter constraints

        logger.debug(f"Extracted parameter schema: {schema}")
        return schema

    def _resolve_parameters(
        self, request_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve and validate pipeline parameters.

        Parameter resolution priority:
        1. Request parameters (highest priority)
        2. Deployment default parameters
        3. Pipeline function defaults (handled by ZenML)

        Args:
            request_params: Parameters provided in the API request

        Returns:
            Dictionary of resolved parameters

        Raises:
            ValueError: If parameter validation fails
        """
        # Start with deployment defaults
        deployment_params = {}
        if self.deployment:
            deployment_params = (
                self.deployment.pipeline_configuration.parameters or {}
            )

        # Merge with request parameters (request takes priority)
        resolved_params = {**deployment_params, **request_params}

        # TODO: Add parameter validation
        # We could validate:
        # 1. Required parameters are present
        # 2. Parameter types match expected types
        # 3. Parameter values are within valid ranges
        # 4. Unknown parameters are flagged

        logger.debug(f"Resolved parameters: {resolved_params}")
        return resolved_params

    async def execute_pipeline(
        self,
        parameters: Dict[str, Any],
        run_name: Optional[str] = None,
        timeout: Optional[int] = 300,
    ) -> Dict[str, Any]:
        """Execute pipeline synchronously with given parameters using ExecutionManager.

        Args:
            parameters: Parameters to pass to pipeline execution
            run_name: Optional custom name for the pipeline run
            timeout: Maximum execution time in seconds

        Returns:
            Dictionary containing execution results and metadata

        Raises:
            TooManyRequestsError: If service is overloaded
        """
        if not self.deployment:
            raise RuntimeError("Service not properly initialized")

        # Get execution manager and job registry
        execution_manager = get_execution_manager()
        job_registry = get_job_registry()

        # Create job for tracking
        job_id = job_registry.create_job(
            parameters=parameters,
            run_name=run_name,
            pipeline_name=self.deployment.pipeline_configuration.name,
        )

        logger.info(f"Starting pipeline execution: {job_id}")
        logger.info(f"Parameters: {parameters}")

        try:
            # Update job to running status
            job_registry.update_job_status(job_id, JobStatus.RUNNING)

            # Resolve parameters
            resolved_params = self._resolve_parameters(parameters)

            # Execute with the execution manager (handles concurrency and timeout)
            result = await execution_manager.execute_with_limits(
                self._execute_pipeline_sync,
                resolved_params,
                job_id,
                timeout=timeout,
            )

            # Calculate execution time from job metadata
            job = job_registry.get_job(job_id)
            execution_time = job.execution_time if job else 0

            # Update statistics
            self._update_execution_stats(
                success=True, execution_time=execution_time
            )
            self.last_execution_time = datetime.now(timezone.utc)

            logger.info(
                f"✅ Pipeline execution completed in {execution_time:.2f}s"
            )

            return {
                "success": True,
                "job_id": job_id,
                "run_id": result.get("run_id"),
                "results": result.get("output"),
                "execution_time": execution_time,
                "metadata": {
                    "pipeline_name": result.get("pipeline_name"),
                    "steps_executed": result.get("steps_executed", 0),
                    "parameters_used": resolved_params,
                    "job_id": job_id,
                    "deployment_id": result.get("deployment_id"),
                    "step_results": result.get("step_results", {}),
                    "debug": result.get("debug", {}),
                },
            }

        except TooManyRequestsError:
            # Clean up job
            job_registry.update_job_status(
                job_id, JobStatus.FAILED, error="Service overloaded"
            )
            raise

        except asyncio.TimeoutError:
            # Update job and stats
            execution_time = time.time() - (
                job.created_at.timestamp() if job else time.time()
            )
            job_registry.update_job_status(
                job_id,
                JobStatus.FAILED,
                error=f"Pipeline execution timed out after {timeout}s",
                execution_time=execution_time,
            )
            self._update_execution_stats(
                success=False, execution_time=execution_time
            )

            error_msg = f"Pipeline execution timed out after {timeout}s"
            logger.error(f"❌ {error_msg}")

            return {
                "success": False,
                "job_id": job_id,
                "error": error_msg,
                "execution_time": execution_time,
                "metadata": {"job_id": job_id},
            }

        except Exception as e:
            # Update job and stats
            job = job_registry.get_job(job_id)
            execution_time = time.time() - (
                job.created_at.timestamp() if job else time.time()
            )
            job_registry.update_job_status(
                job_id,
                JobStatus.FAILED,
                error=str(e),
                execution_time=execution_time,
            )
            self._update_execution_stats(
                success=False, execution_time=execution_time
            )

            error_msg = f"Pipeline execution failed: {str(e)}"
            logger.error(f"❌ {error_msg}")

            return {
                "success": False,
                "job_id": job_id,
                "error": error_msg,
                "execution_time": execution_time,
                "metadata": {"job_id": job_id},
            }

    async def submit_pipeline(
        self,
        parameters: Dict[str, Any],
        run_name: Optional[str] = None,
        timeout: Optional[int] = 600,
    ) -> Dict[str, Any]:
        """Submit pipeline for asynchronous execution without blocking.

        This method starts pipeline execution in the background and returns
        immediately with job information for polling or streaming.

        Args:
            parameters: Parameters to pass to pipeline execution
            run_name: Optional custom name for the pipeline run
            timeout: Maximum execution time in seconds

        Returns:
            Dictionary containing job information for tracking

        Raises:
            TooManyRequestsError: If service is overloaded
        """
        if not self.deployment:
            raise RuntimeError("Service not properly initialized")

        # Get execution manager and job registry
        execution_manager = get_execution_manager()
        job_registry = get_job_registry()

        # Create job for tracking
        job_id = job_registry.create_job(
            parameters=parameters,
            run_name=run_name,
            pipeline_name=self.deployment.pipeline_configuration.name,
        )

        logger.info(f"Submitting pipeline for async execution: {job_id}")
        logger.info(f"Parameters: {parameters}")

        try:
            # Resolve parameters
            resolved_params = self._resolve_parameters(parameters)

            # Start execution in background without waiting
            async def background_execution():
                try:
                    # Update job to running status
                    job_registry.update_job_status(job_id, JobStatus.RUNNING)

                    # Execute with the execution manager (handles concurrency and timeout)
                    await execution_manager.execute_with_limits(
                        self._execute_pipeline_sync,
                        resolved_params,
                        job_id,
                        timeout=timeout,
                    )

                    logger.info(
                        f"✅ Async pipeline execution completed: {job_id}"
                    )

                except TooManyRequestsError:
                    job_registry.update_job_status(
                        job_id, JobStatus.FAILED, error="Service overloaded"
                    )
                    logger.error(
                        f"❌ Async execution failed - overloaded: {job_id}"
                    )

                except asyncio.TimeoutError:
                    job_registry.update_job_status(
                        job_id,
                        JobStatus.FAILED,
                        error=f"Pipeline execution timed out after {timeout}s",
                    )
                    logger.error(f"❌ Async execution timed out: {job_id}")

                except Exception as e:
                    job_registry.update_job_status(
                        job_id, JobStatus.FAILED, error=str(e)
                    )
                    logger.error(
                        f"❌ Async execution failed: {job_id} - {str(e)}"
                    )

            # Start background task (fire and forget)
            asyncio.create_task(background_execution())

            return {
                "success": True,
                "job_id": job_id,
                "message": "Pipeline execution submitted successfully",
                "status": "submitted",
                "metadata": {
                    "job_id": job_id,
                    "pipeline_name": self.deployment.pipeline_configuration.name,
                    "parameters_used": resolved_params,
                    "deployment_id": self.deployment_id,
                    "poll_url": f"/jobs/{job_id}",
                    "stream_url": f"/stream/{job_id}",
                    "estimated_timeout": timeout,
                },
            }

        except Exception as e:
            # Update job as failed and clean up
            job_registry.update_job_status(
                job_id, JobStatus.FAILED, error=str(e)
            )

            error_msg = f"Failed to submit pipeline execution: {str(e)}"
            logger.error(f"❌ {error_msg}")

            return {
                "success": False,
                "job_id": job_id,
                "error": error_msg,
                "metadata": {"job_id": job_id},
            }

    def _execute_pipeline_sync(
        self, resolved_params: Dict[str, Any], job_id: str
    ) -> Dict[str, Any]:
        """Execute pipeline synchronously using DirectExecutionEngine.

        This method is called by the execution manager in a worker thread.

        Args:
            resolved_params: Resolved pipeline parameters
            job_id: Job ID for tracking

        Returns:
            Pipeline execution results
        """
        start_time = time.time()

        try:
            # Get job registry using sync version for worker thread
            job_registry = get_job_registry()

            # Get stream manager reference (should be initialized from main thread)
            stream_manager = get_stream_manager_sync()

            # Create thread-safe event callback - no async operations in worker thread!
            def event_callback(event: ServingEvent):
                if stream_manager:
                    try:
                        # Use thread-safe method to send events to main loop
                        stream_manager.send_event_threadsafe(event)
                    except Exception as e:
                        logger.warning(
                            f"Failed to send event from worker thread: {e}"
                        )
                else:
                    logger.warning(
                        "Stream manager not available for event sending"
                    )

            # Get job for cancellation token using sync method
            job = job_registry.get_job(job_id)
            cancellation_token = job.cancellation_token if job else None

            # Assert deployment is not None for mypy
            assert self.deployment is not None

            # Create direct execution engine
            engine = DirectExecutionEngine(
                deployment=self.deployment,
                event_callback=event_callback,
                cancellation_token=cancellation_token,
            )

            # Execute pipeline
            result = engine.execute(resolved_params, job_id=job_id)

            execution_time = time.time() - start_time

            # Update job as completed using sync method - no async operations in worker thread!
            job_registry.update_job_status(
                job_id,
                JobStatus.COMPLETED,
                result=result,
                execution_time=execution_time,
                steps_executed=len(engine._execution_order),
            )

            return {
                "output": result,
                "pipeline_name": self.deployment.pipeline_configuration.name,
                "steps_executed": len(engine._execution_order),
                "job_id": job_id,
                "deployment_id": self.deployment_id,
                "step_results": {},  # Could be enhanced to track individual step results
                "debug": {},
            }

        except asyncio.CancelledError:
            execution_time = time.time() - start_time
            # Use sync method - no async operations in worker thread!
            job_registry.update_job_status(
                job_id,
                JobStatus.CANCELED,
                error="Execution was cancelled",
                execution_time=execution_time,
            )
            raise

        except Exception as e:
            execution_time = time.time() - start_time
            # Use sync method - no async operations in worker thread!
            job_registry.update_job_status(
                job_id,
                JobStatus.FAILED,
                error=str(e),
                execution_time=execution_time,
            )
            raise

        finally:
            # No cleanup needed for thread-safe sync implementation
            pass

    async def execute_pipeline_streaming(
        self, parameters: Dict[str, Any], run_name: Optional[str] = None
    ) -> AsyncGenerator[ServingEvent, None]:
        """Execute pipeline with true streaming updates.

        Args:
            parameters: Parameters to pass to pipeline execution
            run_name: Optional custom name for the pipeline run

        Yields:
            ServingEvent objects with real-time execution updates
        """
        if not self.deployment:
            raise RuntimeError("Service not properly initialized")

        # Get execution manager, job registry, and stream manager
        execution_manager = get_execution_manager()
        job_registry = get_job_registry()
        stream_manager = await get_stream_manager()

        # Create job for tracking
        job_id = job_registry.create_job(
            parameters=parameters,
            run_name=run_name,
            pipeline_name=self.deployment.pipeline_configuration.name,
        )

        logger.info(f"Starting streaming pipeline execution: {job_id}")

        try:
            # Start the execution in background
            execution_task = asyncio.create_task(
                execution_manager.execute_with_limits(
                    self._execute_pipeline_sync,
                    self._resolve_parameters(parameters),
                    job_id,
                    timeout=600,  # Longer timeout for streaming
                )
            )

            # Subscribe to events for this job
            async for event in stream_manager.subscribe_to_job(job_id):
                yield event

                # If we get a pipeline completed, failed, or canceled event, we can stop
                if event.event_type in [
                    "pipeline_completed",
                    "pipeline_failed",
                    "cancellation_requested",
                ]:
                    break

            # Wait for execution to complete and handle any remaining cleanup
            try:
                await execution_task
            except Exception as e:
                logger.error(f"Background execution failed: {e}")
                # Error should have been captured in events already

        except TooManyRequestsError:
            # Send overload event
            event_builder = create_event_builder(job_id)
            error_event = event_builder.error(
                "Service overloaded - too many concurrent requests"
            )
            yield error_event

        except Exception as e:
            logger.error(f"❌ Streaming execution failed: {str(e)}")
            # Send error event
            event_builder = create_event_builder(job_id)
            error_event = event_builder.error(str(e))
            yield error_event

        finally:
            # Close the stream for this job
            await stream_manager.close_stream(job_id)

    def _update_execution_stats(
        self, success: bool, execution_time: float
    ) -> None:
        """Update execution statistics.

        Args:
            success: Whether the execution was successful
            execution_time: Execution time in seconds
        """
        current_time = datetime.now(timezone.utc)

        # Update counters
        self.execution_stats["total_executions"] += 1
        if success:
            self.execution_stats["successful_executions"] += 1
        else:
            self.execution_stats["failed_executions"] += 1

        # Update timing
        self.execution_stats["total_execution_time"] += execution_time

        # Track 24h executions
        self.execution_stats["executions_24h"].append(current_time)

        # Clean up old 24h entries (keep only last 24 hours)
        cutoff_time = current_time - timedelta(hours=24)
        self.execution_stats["executions_24h"] = [
            ts
            for ts in self.execution_stats["executions_24h"]
            if ts > cutoff_time
        ]

    def get_execution_metrics(self) -> Dict[str, Any]:
        """Get current execution metrics and statistics.

        Returns:
            Dictionary containing execution metrics
        """
        stats = self.execution_stats
        total_executions = max(
            stats["total_executions"], 1
        )  # Avoid division by zero

        return {
            "total_executions": stats["total_executions"],
            "successful_executions": stats["successful_executions"],
            "failed_executions": stats["failed_executions"],
            "success_rate": stats["successful_executions"] / total_executions,
            "average_execution_time": stats["total_execution_time"]
            / total_executions,
            "last_24h_executions": len(stats["executions_24h"]),
        }

    def get_service_info(self) -> Dict[str, Any]:
        """Get service information including pipeline and deployment details.

        Returns:
            Dictionary containing service information
        """
        if not self.deployment:
            return {"error": "Service not initialized"}

        return {
            "service": {
                "name": "ZenML Pipeline Serving",
                "version": "0.1.0",
                "deployment_id": self.deployment_id,
                "uptime": time.time() - self.service_start_time,
                "status": "healthy",
            },
            "pipeline": {
                "name": self.deployment.pipeline_configuration.name,
                "steps": list(self.deployment.step_configurations.keys()),
                "parameters": self.parameter_schema,
            },
            "deployment": {
                "id": self.deployment_id,
                "created_at": self.deployment.created,
                "stack": self.deployment.stack.name
                if self.deployment.stack
                else "unknown",
            },
        }

    def is_healthy(self) -> bool:
        """Check if the service is healthy and ready to serve requests.

        Returns:
            True if service is healthy, False otherwise
        """
        return self.deployment is not None
