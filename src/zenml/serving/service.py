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
from typing import Any, AsyncGenerator, Dict, Optional
from uuid import UUID

from zenml.client import Client
from zenml.integrations.registry import integration_registry
from zenml.logger import get_logger
from zenml.models import PipelineDeploymentResponse
from zenml.serving.entrypoint import ServingPipelineEntrypoint
from zenml.serving.models import StreamEvent

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
        schema = {}

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
        """Execute pipeline synchronously with given parameters.

        Args:
            parameters: Parameters to pass to pipeline execution
            run_name: Optional custom name for the pipeline run
            timeout: Maximum execution time in seconds

        Returns:
            Dictionary containing execution results and metadata
        """
        start_time = time.time()
        execution_id = f"execution_{int(start_time)}"

        logger.info(f"Starting pipeline execution: {execution_id}")
        logger.info(f"Parameters: {parameters}")
        # TODO: Use run_name parameter when creating pipeline runs
        if run_name:
            logger.info(f"Using custom run name: {run_name}")

        try:
            # Validate service is initialized
            if not self.deployment:
                raise RuntimeError("Service not properly initialized")

            # Resolve parameters
            resolved_params = self._resolve_parameters(parameters)

            # Determine if we should create a ZenML run for tracking
            # This could be enhanced to check request headers or other indicators
            # For now, we'll default to not creating runs for standard HTTP requests
            # but this can be overridden with an environment variable
            create_zen_run = os.getenv("ZENML_SERVING_CREATE_RUNS", "false").lower() == "true"
            
            entrypoint = ServingPipelineEntrypoint(
                deployment_id=self.deployment_id,
                runtime_params=resolved_params,
                create_zen_run=create_zen_run,
            )

            # Execute with timeout
            logger.info(f"Executing pipeline with {timeout}s timeout...")
            result = await asyncio.wait_for(
                asyncio.to_thread(entrypoint.run), timeout=timeout
            )

            # Calculate execution time
            execution_time = time.time() - start_time
            self.last_execution_time = datetime.now(timezone.utc)

            # Update statistics
            self._update_execution_stats(
                success=True, execution_time=execution_time
            )

            logger.info(
                f"✅ Pipeline execution completed in {execution_time:.2f}s"
            )

            return {
                "success": True,
                "run_id": result.get("run_id"),  # Use actual run ID
                "results": result.get("output"),  # Return the pipeline output
                "execution_time": execution_time,
                "metadata": {
                    "pipeline_name": result.get("pipeline_name"),
                    "steps_executed": result.get("steps_executed", 0),
                    "parameters_used": resolved_params,
                    "execution_id": execution_id,
                    "deployment_id": result.get("deployment_id"),
                    "step_results": result.get("step_results", {}),
                    "debug": result.get("debug", {}),
                },
            }

        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            self._update_execution_stats(
                success=False, execution_time=execution_time
            )

            error_msg = f"Pipeline execution timed out after {timeout}s"
            logger.error(f"❌ {error_msg}")

            return {
                "success": False,
                "error": error_msg,
                "execution_time": execution_time,
                "metadata": {"execution_id": execution_id},
            }

        except Exception as e:
            execution_time = time.time() - start_time
            self._update_execution_stats(
                success=False, execution_time=execution_time
            )

            error_msg = f"Pipeline execution failed: {str(e)}"
            logger.error(f"❌ {error_msg}")

            return {
                "success": False,
                "error": error_msg,
                "execution_time": execution_time,
                "metadata": {"execution_id": execution_id},
            }

    async def execute_pipeline_streaming(
        self, parameters: Dict[str, Any], run_name: Optional[str] = None
    ) -> AsyncGenerator[StreamEvent, None]:
        """Execute pipeline with streaming updates.

        Args:
            parameters: Parameters to pass to pipeline execution
            run_name: Optional custom name for the pipeline run

        Yields:
            StreamEvent objects with execution updates
        """
        start_time = time.time()
        execution_id = f"stream_execution_{int(start_time)}"

        logger.info(f"Starting streaming pipeline execution: {execution_id}")

        try:
            # Send start event
            yield StreamEvent(
                event="pipeline_started",
                data={
                    "execution_id": execution_id,
                    "parameters": parameters,
                    "pipeline_name": self.deployment.pipeline_configuration.name
                    if self.deployment
                    else "unknown",
                },
                timestamp=datetime.now(timezone.utc),
            )

            # For MVP, we'll execute synchronously and provide periodic updates
            # In the future, this could be enhanced with real step-by-step streaming

            # Execute pipeline
            result = await self.execute_pipeline(
                parameters=parameters,
                run_name=run_name,
                timeout=600,  # Longer timeout for streaming
            )

            if result["success"]:
                # Send completion event with results
                yield StreamEvent(
                    event="pipeline_completed",
                    data={
                        "execution_id": execution_id,
                        "results": result["results"],
                        "execution_time": result["execution_time"],
                        "metadata": result["metadata"],
                    },
                    timestamp=datetime.now(timezone.utc),
                )
            else:
                # Send error event
                yield StreamEvent(
                    event="error",
                    error=result["error"],
                    data={
                        "execution_id": execution_id,
                        "execution_time": result["execution_time"],
                    },
                    timestamp=datetime.now(timezone.utc),
                )

        except Exception as e:
            logger.error(f"❌ Streaming execution failed: {str(e)}")
            yield StreamEvent(
                event="error",
                error=str(e),
                data={
                    "execution_id": execution_id,
                    "execution_time": time.time() - start_time,
                },
                timestamp=datetime.now(timezone.utc),
            )

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
