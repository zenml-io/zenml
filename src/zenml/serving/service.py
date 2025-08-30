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
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator, Dict, Optional, Union
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
from zenml.serving.events import EventType, ServingEvent, create_event_builder
from zenml.serving.jobs import (
    JobStatus,
    get_job_registry,
)
from zenml.serving.policy import (
    get_endpoint_default_policy,
    resolve_effective_policy,
    should_create_runs,
)

# StreamEvent is deprecated, using ServingEvent instead
from zenml.serving.streams import get_stream_manager, get_stream_manager_sync
from zenml.serving.tracking import TrackingManager

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
        self.execution_stats: Dict[str, Any] = {
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
        """Extract parameter schema from pipeline deployment and function signature.

        Returns:
            Dictionary containing parameter information with types and defaults
        """
        schema: Dict[str, Any] = {}

        if not self.deployment:
            return schema

        deployment = self.deployment  # Local var for type narrowing

        # Get parameters from pipeline configuration
        pipeline_params = deployment.pipeline_configuration.parameters or {}

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

        # Enhanced: Extract parameters from pipeline function signature
        try:
            # Get the pipeline source and load it to inspect the function signature
            pipeline_spec = getattr(
                self.deployment.pipeline_configuration, "spec", None
            )
            if pipeline_spec and getattr(pipeline_spec, "source", None):
                import inspect

                from zenml.utils import source_utils

                # Load the pipeline function
                pipeline_func = source_utils.load(pipeline_spec.source)

                # Get function signature
                sig = inspect.signature(pipeline_func)

                for param_name, param in sig.parameters.items():
                    # Skip if we already have this parameter from deployment config
                    if param_name in schema:
                        continue

                    # Extract type information
                    param_type = "str"  # Default fallback
                    if param.annotation != inspect.Parameter.empty:
                        if hasattr(param.annotation, "__name__"):
                            param_type = param.annotation.__name__
                        else:
                            param_type = str(param.annotation)

                    # Extract default value
                    has_default = param.default != inspect.Parameter.empty
                    default_value = param.default if has_default else None

                    schema[param_name] = {
                        "type": param_type,
                        "default": default_value,
                        "required": not has_default,
                    }

                    logger.debug(
                        f"Extracted function parameter: {param_name} ({param_type}) = {default_value}"
                    )

        except Exception as e:
            logger.warning(
                f"Failed to extract pipeline function signature: {e}"
            )
            # Continue with just deployment parameters

        logger.debug(f"Final extracted parameter schema: {schema}")
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
        # TODO: Maybe use FastAPI's parameter validation instead?
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

        # Log parameter keys only to avoid PII exposure in debug logs
        logger.debug(f"Resolved parameters: {list(resolved_params.keys())}")
        return resolved_params

    async def execute_pipeline(
        self,
        parameters: Dict[str, Any],
        run_name: Optional[str] = None,
        timeout: Optional[int] = 300,
        capture_override: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute pipeline synchronously with given parameters using ExecutionManager.

        Args:
            parameters: Parameters to pass to pipeline execution
            run_name: Optional custom name for the pipeline run
            timeout: Maximum execution time in seconds
            capture_override: Optional capture policy overrides for tracking

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
        # Log parameter keys only to avoid PII exposure
        logger.info(f"Parameters: {list(parameters.keys())}")

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
                capture_override,
                timeout=timeout,
            )

            # Calculate execution time from job metadata
            job = job_registry.get_job(job_id)
            execution_time = (
                job.execution_time
                if job and job.execution_time is not None
                else 0.0
            )

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
        capture_override: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Submit pipeline for asynchronous execution without blocking.

        This method starts pipeline execution in the background and returns
        immediately with job information for polling or streaming.

        Args:
            parameters: Parameters to pass to pipeline execution
            run_name: Optional custom name for the pipeline run
            timeout: Maximum execution time in seconds
            capture_override: Optional capture policy overrides for tracking

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
        # Log parameter keys only to avoid PII exposure
        logger.info(f"Parameters: {list(parameters.keys())}")

        try:
            # Resolve parameters
            resolved_params = self._resolve_parameters(parameters)

            # Start execution in background without waiting
            async def background_execution() -> None:
                try:
                    # Update job to running status
                    job_registry.update_job_status(job_id, JobStatus.RUNNING)

                    # Execute with the execution manager (handles concurrency and timeout)
                    await execution_manager.execute_with_limits(
                        self._execute_pipeline_sync,
                        resolved_params,
                        job_id,
                        capture_override,
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
        self,
        resolved_params: Dict[str, Any],
        job_id: str,
        capture_override: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute pipeline synchronously using DirectExecutionEngine.

        This method is called by the execution manager in a worker thread.

        Args:
            resolved_params: Resolved pipeline parameters
            job_id: Job ID for tracking
            capture_override: Optional capture policy overrides for tracking

        Returns:
            Pipeline execution results
        """
        start_time = time.time()

        # Guard against None deployment
        if self.deployment is None:
            raise RuntimeError("Service not properly initialized")
        deployment = self.deployment  # Local var for type narrowing

        try:
            # Get job registry using sync version for worker thread
            # TODO: move this to serving execution manager and keep this function agnostic of job management.
            job_registry = get_job_registry()

            # Get stream manager reference (should be initialized from main thread)
            stream_manager = get_stream_manager_sync()

            # Setup tracking manager if enabled
            tracking_manager = None
            pipeline_per_value_overrides: Dict[
                str, Union[str, Dict[str, str]]
            ] = {}
            # Always resolve policy first, then apply global off-switch
            try:
                from zenml.utils.settings_utils import (
                    get_pipeline_serving_capture_settings,
                )

                # Extract pipeline-level capture settings using normalization
                code_override: Optional[Dict[str, Any]] = None
                pipeline_capture_settings = None
                if deployment.pipeline_configuration.settings:
                    pipeline_capture_settings = (
                        get_pipeline_serving_capture_settings(
                            deployment.pipeline_configuration.settings
                        )
                    )

                    if pipeline_capture_settings:
                        # Convert to legacy format for policy resolution (backward compatibility)
                        code_override = {}
                        if (
                            pipeline_capture_settings.mode != "full"
                        ):  # Only set if different from default
                            code_override["mode"] = (
                                pipeline_capture_settings.mode
                            )
                        if pipeline_capture_settings.sample_rate is not None:
                            code_override["sample_rate"] = (
                                pipeline_capture_settings.sample_rate
                            )
                        if pipeline_capture_settings.max_bytes is not None:
                            code_override["max_bytes"] = (
                                pipeline_capture_settings.max_bytes
                            )
                        if pipeline_capture_settings.redact is not None:
                            code_override["redact"] = (
                                pipeline_capture_settings.redact
                            )
                        if (
                            pipeline_capture_settings.retention_days
                            is not None
                        ):
                            code_override["retention_days"] = (
                                pipeline_capture_settings.retention_days
                            )

                        # Extract per-value overrides for later use
                        if pipeline_capture_settings.inputs:
                            pipeline_per_value_overrides["inputs"] = dict(
                                pipeline_capture_settings.inputs
                            )
                        if pipeline_capture_settings.outputs:
                            if isinstance(
                                pipeline_capture_settings.outputs, str
                            ):
                                pipeline_per_value_overrides["outputs"] = (
                                    pipeline_capture_settings.outputs
                                )
                            else:
                                pipeline_per_value_overrides["outputs"] = dict(
                                    pipeline_capture_settings.outputs
                                )

                    # Fallback: check legacy format if no new format found
                    if (
                        not pipeline_capture_settings
                        and "serving"
                        in deployment.pipeline_configuration.settings
                    ):
                        serving_settings = (
                            deployment.pipeline_configuration.settings[
                                "serving"
                            ]
                        )
                        if (
                            isinstance(serving_settings, dict)
                            and "capture" in serving_settings
                        ):
                            code_override = serving_settings["capture"]

                # Resolve effective capture policy with all override levels
                endpoint_default = get_endpoint_default_policy()
                effective_policy = resolve_effective_policy(
                    endpoint_default=endpoint_default,
                    request_override=capture_override,
                    code_override=code_override,
                )

                # Apply global off-switch (ops safeguard)
                if (
                    os.getenv("ZENML_SERVING_CREATE_RUNS", "true").lower()
                    == "false"
                ):
                    from zenml.serving.policy import (
                        ArtifactCaptureMode,
                        CapturePolicy,
                        CapturePolicyMode,
                    )

                    # Create new policy instead of mutating in place
                    effective_policy = CapturePolicy(
                        mode=CapturePolicyMode.NONE,
                        artifacts=ArtifactCaptureMode.NONE,
                        sample_rate=effective_policy.sample_rate,
                        max_bytes=effective_policy.max_bytes,
                        redact=effective_policy.redact,
                        retention_days=effective_policy.retention_days,
                    )

                if should_create_runs(effective_policy):
                    tracking_manager = TrackingManager(
                        deployment=deployment,
                        policy=effective_policy,
                        create_runs=True,
                        invocation_id=job_id,
                    )

                    # Set pipeline-level per-value overrides if present
                    if pipeline_per_value_overrides:
                        tracking_manager.set_pipeline_capture_overrides(
                            pipeline_per_value_overrides
                        )

                    # Start pipeline tracking
                    run_id = tracking_manager.start_pipeline(
                        run_name=None,  # Will be auto-generated
                        params=resolved_params,
                    )
                    if run_id:
                        logger.info(f"Pipeline run tracking started: {run_id}")
            except Exception as e:
                logger.warning(f"Failed to initialize tracking manager: {e}")
                tracking_manager = None

            # Create combined event callback - no async operations in worker thread!
            def event_callback(event: ServingEvent) -> None:
                # Send to stream manager
                if stream_manager:
                    try:
                        stream_manager.send_event_threadsafe(event)
                    except Exception as e:
                        logger.warning(
                            f"Failed to send event from worker thread: {e}"
                        )
                else:
                    logger.warning(
                        "Stream manager not available for event sending"
                    )

                # Send to tracking manager
                if tracking_manager:
                    try:
                        tracking_manager.handle_event(event)
                    except Exception as e:
                        logger.warning(f"Failed to handle tracking event: {e}")

            # Create result callback for raw step outputs
            def result_callback(
                step_name: str, output: Any, success: bool
            ) -> None:
                if tracking_manager:
                    try:
                        # Get step config for better materializer resolution
                        step_config = deployment.step_configurations.get(
                            step_name
                        )
                        tracking_manager.handle_step_result(
                            step_name, output, success, step_config
                        )
                    except Exception as e:
                        logger.warning(f"Failed to handle step result: {e}")

            # Get job for cancellation token using sync method
            job = job_registry.get_job(job_id)
            cancellation_token = job.cancellation_token if job else None

            # Create direct execution engine
            engine = DirectExecutionEngine(
                deployment=deployment,
                event_callback=event_callback,
                result_callback=result_callback,
                cancellation_token=cancellation_token,
            )

            # Get step capture overrides from engine for TrackingManager
            if tracking_manager:
                step_capture_overrides = engine.get_step_capture_overrides()
                tracking_manager.set_step_capture_overrides(
                    step_capture_overrides
                )

                # Get step mode overrides from engine for TrackingManager
                step_mode_overrides = engine.get_step_mode_overrides()
                tracking_manager.set_step_mode_overrides(step_mode_overrides)

            # Execute pipeline
            result = engine.execute(resolved_params, job_id=job_id)

            execution_time = time.time() - start_time

            # Complete pipeline tracking if enabled
            if tracking_manager:
                try:
                    tracking_manager.complete_pipeline(
                        success=True,
                        execution_time=execution_time,
                        steps_executed=len(engine._execution_order),
                        results=result,
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to complete pipeline tracking: {e}"
                    )

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
                "run_id": str(tracking_manager.pipeline_run.id)
                if tracking_manager and tracking_manager.pipeline_run
                else None,
                "step_results": {},  # Could be enhanced to track individual step results
                "debug": {},
            }

        except asyncio.CancelledError:
            execution_time = time.time() - start_time

            # Complete pipeline tracking if enabled
            if tracking_manager:
                try:
                    tracking_manager.complete_pipeline(
                        success=False,
                        error="Execution was cancelled",
                        execution_time=execution_time,
                        steps_executed=len(tracking_manager.step_runs)
                        if hasattr(tracking_manager, "step_runs")
                        else 0,
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to complete pipeline tracking on cancellation: {e}"
                    )

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

            # Complete pipeline tracking if enabled
            if tracking_manager:
                try:
                    tracking_manager.complete_pipeline(
                        success=False,
                        error=str(e),
                        execution_time=execution_time,
                        steps_executed=len(tracking_manager.step_runs)
                        if hasattr(tracking_manager, "step_runs")
                        else 0,
                    )
                except Exception as track_e:
                    logger.warning(
                        f"Failed to complete pipeline tracking on error: {track_e}"
                    )

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
                    EventType.PIPELINE_COMPLETED,
                    EventType.PIPELINE_FAILED,
                    EventType.CANCELLATION_REQUESTED,
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
