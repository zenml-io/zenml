#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Core pipeline serving service implementation.

This service defers all execution responsibilities to the orchestrator
configured in the deployment stack. It only resolves request parameters,
applies them to the loaded deployment, and triggers the orchestrator.
"""

import inspect
import json
import os
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from zenml.client import Client
from zenml.integrations.registry import integration_registry
from zenml.logger import get_logger
from zenml.models import PipelineDeploymentResponse
from zenml.models.v2.core.pipeline_run import PipelineRunResponse
from zenml.orchestrators.base_orchestrator import BaseOrchestrator
from zenml.pipelines.run_utils import create_placeholder_run
from zenml.stack import Stack
from zenml.utils import source_utils
from zenml.utils.json_utils import pydantic_encoder

logger = get_logger(__name__)


class PipelineServingService:
    """Core service for serving ZenML pipelines via FastAPI.

    This service handles the loading, execution, and monitoring of ZenML pipelines
    in a serving context. It provides both synchronous and streaming execution
    capabilities while maintaining compatibility with ZenML's existing execution
    infrastructure.
    """

    def __init__(self, deployment_id: UUID):
        """Initialize the pipeline serving service.

        Args:
            deployment_id: UUID of the pipeline deployment to serve
        """
        self.deployment_id = deployment_id
        self.deployment: Optional[PipelineDeploymentResponse] = None
        self.service_start_time = time.time()
        self.last_execution_time: Optional[datetime] = None
        self.pipeline_state: Optional[Any] = None
        # Cache a local orchestrator instance to avoid per-request construction
        self._cached_orchestrator: Optional["BaseOrchestrator"] = None
        # Cached Pydantic params model built from deployment
        self._params_model: Optional[Any] = None

        # Simple execution tracking
        self.total_executions = 0

        logger.info(
            f"Initializing PipelineServingService for deployment: {deployment_id}"
        )

    # Internal helpers
    def _get_max_output_size_bytes(self) -> int:
        try:
            size_mb = int(
                os.environ.get("ZENML_SERVING_MAX_OUTPUT_SIZE_MB", "1")
            )
            # Enforce reasonable bounds: 1MB to 100MB
            size_mb = max(1, min(size_mb, 100))
            return size_mb * 1024 * 1024
        except (ValueError, TypeError):
            logger.warning(
                "Invalid ZENML_SERVING_MAX_OUTPUT_SIZE_MB. Using 1MB."
            )
            return 1024 * 1024

    async def initialize(self) -> None:
        """Initialize the service by loading deployment configuration.

        This method loads the pipeline deployment, extracts parameter schema,
        and sets up the execution environment.

        Raises:
            ValueError: If deployment ID is invalid or deployment not found
        """
        try:
            logger.info("Loading pipeline deployment configuration...")

            # Load deployment from ZenML store
            client = Client()

            self.deployment = client.zen_store.get_deployment(
                deployment_id=self.deployment_id
            )

            # Activate integrations to ensure all components are available
            integration_registry.activate_integrations()

            # Build and cache a strict Pydantic params model from the packaged
            # model source to fail fast if the deployment is inconsistent.
            try:
                from zenml.deployers.serving.parameters import (
                    build_params_model_from_deployment,
                )

                assert self.deployment is not None
                self._params_model = build_params_model_from_deployment(
                    self.deployment, strict=True
                )
            except Exception as e:
                logger.error(
                    "Failed to construct parameter model from deployment: %s",
                    e,
                )
                raise

            # Execute the init hook, if present
            await self._execute_init_hook()

            # Log successful initialization
            pipeline_name = self.deployment.pipeline_configuration.name
            step_count = len(self.deployment.step_configurations)

            logger.info("✅ Service initialized successfully:")
            logger.info(f"   Pipeline: {pipeline_name}")
            logger.info(f"   Steps: {step_count}")
            logger.info(
                f"   Stack: {self.deployment.stack.name if self.deployment.stack else 'unknown'}"
            )

        except Exception as e:
            logger.error(f"❌ Failed to initialize service: {e}")
            logger.error(f"   Traceback: {traceback.format_exc()}")
            raise

    async def cleanup(self) -> None:
        """Cleanup the service by executing the pipeline's cleanup hook, if present."""
        if (
            not self.deployment
            or not self.deployment.pipeline_configuration.cleanup_hook_source
        ):
            return

        logger.info("Executing pipeline's cleanup hook...")
        try:
            cleanup_hook = source_utils.load(
                self.deployment.pipeline_configuration.cleanup_hook_source
            )
            if inspect.iscoroutinefunction(cleanup_hook):
                await cleanup_hook()
            else:
                cleanup_hook()
        except Exception as e:
            logger.exception(f"Failed to execute cleanup hook: {e}")
            raise

    def _serialize_json_safe(self, value: Any) -> Any:
        """Make value JSON-serializable using ZenML's encoder."""
        try:
            # Use ZenML's comprehensive encoder
            json.dumps(value, default=pydantic_encoder)
            return value
        except (TypeError, ValueError, OverflowError):
            # Fallback to string representation
            s = str(value)
            return s if len(s) <= 1000 else f"{s[:1000]}... [truncated]"

    def _map_outputs(self, run: PipelineRunResponse) -> Dict[str, Any]:
        """Map pipeline outputs using fast in-memory data when available."""
        # Try fast path: use in-memory outputs from serving context
        try:
            from zenml.deployers.serving import runtime

            if runtime.is_active():
                in_memory_outputs = runtime.get_outputs()
                if in_memory_outputs:
                    # Format with qualified names (step.output)
                    mapped_outputs = {}
                    for step_name, step_outputs in in_memory_outputs.items():
                        for out_name, value in step_outputs.items():
                            # Check if data is too large (configurable via env var)
                            try:
                                max_size_bytes = (
                                    self._get_max_output_size_bytes()
                                )
                                max_size_mb = max_size_bytes // (1024 * 1024)
                                serialized = self._serialize_json_safe(value)
                                if (
                                    isinstance(serialized, str)
                                    and len(serialized) > max_size_bytes
                                ):
                                    # Too large, return metadata instead
                                    mapped_outputs[
                                        f"{step_name}.{out_name}"
                                    ] = {
                                        "data_too_large": True,
                                        "size_estimate": f"{len(serialized) // 1024}KB",
                                        "max_size_mb": max_size_mb,
                                        "type": str(type(value).__name__),
                                        "note": "Use artifact loading endpoint for large outputs",
                                    }
                                else:
                                    mapped_outputs[
                                        f"{step_name}.{out_name}"
                                    ] = serialized
                            except Exception:
                                # Fallback to basic info if serialization fails
                                mapped_outputs[f"{step_name}.{out_name}"] = {
                                    "serialization_failed": True,
                                    "type": str(type(value).__name__),
                                    "note": "Use artifact loading endpoint for this output",
                                }
                    return mapped_outputs
        except ImportError:
            pass

        # Fallback: original expensive artifact loading
        logger.debug("Using slow artifact loading fallback")
        from zenml.artifacts.utils import load_artifact_from_response

        fallback_outputs: Dict[str, Any] = {}
        for step_name, step_run in (run.steps or {}).items():
            if not step_run or not step_run.outputs:
                continue
            for out_name, arts in (step_run.outputs or {}).items():
                if not arts:
                    continue
                try:
                    val = load_artifact_from_response(arts[0])
                    if val is not None:
                        fallback_outputs[f"{step_name}.{out_name}"] = (
                            self._serialize_json_safe(val)
                        )
                except Exception as e:
                    logger.debug(
                        f"Failed to load artifact for {step_name}.{out_name}: {e}"
                    )
                    continue
        return fallback_outputs

    async def _execute_init_hook(self) -> None:
        """Execute the pipeline's init hook, if present."""
        if (
            not self.deployment
            or not self.deployment.pipeline_configuration.init_hook_source
        ):
            return

        logger.info("Executing pipeline's init hook...")
        try:
            init_hook = source_utils.load(
                self.deployment.pipeline_configuration.init_hook_source
            )

            if inspect.iscoroutinefunction(init_hook):
                self.pipeline_state = await init_hook()
            else:
                self.pipeline_state = init_hook()
        except Exception as e:
            logger.exception(f"Failed to execute init hook: {e}")
            raise

    def _resolve_parameters(
        self, request_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate and normalize request parameters with the params model.

        Assumes the service was initialized successfully and a params model is
        available. Defaults are applied by the model during validation.

        Args:
            request_params: The request parameters to validate and normalize.

        Returns:
            The validated and normalized request parameters.

        Raises:
            ValueError: If the request parameters are invalid.
        """
        assert self._params_model is not None
        parameters = self._params_model.model_validate(request_params or {})
        return parameters.model_dump()  # type: ignore[return-value]

    def execute_pipeline(
        self,
        parameters: Dict[str, Any],
        run_name: Optional[str] = None,
        timeout: Optional[int] = 300,
    ) -> Dict[str, Any]:
        """Execute pipeline by delegating to orchestrator with small helpers."""
        # Note: run_name and timeout are reserved for future implementation
        del run_name, timeout  # Silence unused parameter warnings

        if not self.deployment:
            raise RuntimeError("Service not properly initialized")

        start = time.time()
        logger.info("Starting pipeline execution")

        try:
            resolved_params = self._resolve_parameters(parameters)
            run = self._execute_with_orchestrator(resolved_params)
            mapped_outputs = self._map_outputs(run)
            return self._build_success_response(
                mapped_outputs=mapped_outputs,
                start_time=start,
                resolved_params=resolved_params,
            )
        except Exception as e:  # noqa: BLE001
            logger.error(f"❌ Pipeline execution failed: {e}")
            return self._build_error_response(e=e, start_time=start)

    def _execute_with_orchestrator(
        self, resolved_params: Dict[str, Any]
    ) -> PipelineRunResponse:
        """Run the deployment via the (forced local) orchestrator and return the run."""
        client = Client()
        active_stack: Stack = client.active_stack

        # Instantiate a local orchestrator explicitly and run with the active stack
        from zenml.enums import StackComponentType
        from zenml.orchestrators.local.local_orchestrator import (
            LocalOrchestrator,
            LocalOrchestratorConfig,
        )

        if self._cached_orchestrator is None:
            self._cached_orchestrator = LocalOrchestrator(
                name="serving-local",
                id=uuid4(),
                config=LocalOrchestratorConfig(),
                flavor="local",
                type=StackComponentType.ORCHESTRATOR,
                user=uuid4(),
                created=datetime.now(),
                updated=datetime.now(),
            )

        # Create a placeholder run and execute with a known run id
        assert self.deployment is not None
        placeholder_run = create_placeholder_run(
            deployment=self.deployment, logs=None
        )

        # Start serving runtime context with parameters
        from zenml.deployers.serving import runtime

        runtime.start(
            request_id=str(uuid4()),
            deployment=self.deployment,
            parameters=resolved_params,
        )

        try:
            self._cached_orchestrator.run(
                deployment=self.deployment,
                stack=active_stack,
                placeholder_run=placeholder_run,
            )
        finally:
            # Always stop serving runtime context
            runtime.stop()

        # Fetch the concrete run via its id
        run: PipelineRunResponse = Client().get_pipeline_run(
            name_id_or_prefix=placeholder_run.id,
            hydrate=True,
            include_full_metadata=True,
        )
        return run

    def _build_success_response(
        self,
        mapped_outputs: Dict[str, Any],
        start_time: float,
        resolved_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        execution_time = time.time() - start_time
        self.total_executions += 1
        self.last_execution_time = datetime.now(timezone.utc)
        assert self.deployment is not None
        response = {
            "success": True,
            "outputs": mapped_outputs,
            "execution_time": execution_time,
            "metadata": {
                "pipeline_name": self.deployment.pipeline_configuration.name,
                "parameters_used": self._serialize_json_safe(resolved_params),
                "deployment_id": str(self.deployment.id),
            },
        }

        # Add response schema if available
        if (
            self.deployment.pipeline_spec
            and self.deployment.pipeline_spec.response_schema
        ):
            response["response_schema"] = (
                self.deployment.pipeline_spec.response_schema
            )

        return response

    def _build_timeout_response(
        self, start_time: float, timeout: Optional[int]
    ) -> Dict[str, Any]:
        execution_time = time.time() - start_time
        return {
            "success": False,
            "job_id": None,
            "error": f"Pipeline execution timed out after {timeout}s",
            "execution_time": execution_time,
            "metadata": {},
        }

    def _build_error_response(
        self, e: Exception, start_time: float
    ) -> Dict[str, Any]:
        execution_time = time.time() - start_time
        return {
            "success": False,
            "job_id": None,
            "error": str(e),
            "execution_time": execution_time,
            "metadata": {},
        }

    def get_service_info(self) -> Dict[str, Any]:
        """Get service information including pipeline and deployment details.

        Returns:
            Dictionary containing service information
        """
        if not self.deployment:
            return {"error": "Service not initialized"}

        return {
            "deployment_id": str(self.deployment_id),
            "pipeline_name": self.deployment.pipeline_configuration.name,
            "total_executions": self.total_executions,
            "last_execution_time": self.last_execution_time.isoformat()
            if self.last_execution_time
            else None,
            "status": "healthy",
        }

    def get_execution_metrics(self) -> Dict[str, Any]:
        """Get simple execution metrics."""
        return {
            "total_executions": self.total_executions,
            "last_execution_time": self.last_execution_time.isoformat()
            if self.last_execution_time
            else None,
        }

    def is_healthy(self) -> bool:
        """Check if the service is healthy and ready to serve requests.

        Returns:
            True if service is healthy, False otherwise
        """
        return self.deployment is not None
