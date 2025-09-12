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
"""Clean, elegant pipeline serving service implementation.

This service provides high-performance pipeline serving with proper memory management,
clean architecture, and zero memory leaks.
"""

import inspect
import os
import time
import traceback
from dataclasses import dataclass
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
from zenml.utils import source_utils

logger = get_logger(__name__)


@dataclass(frozen=True)
class ExecutionResult:
    """Immutable result of pipeline execution."""

    run: PipelineRunResponse
    outputs: Optional[Dict[str, Dict[str, Any]]] = None


class PipelineOrchestrator:
    """Clean orchestrator management with proper resource lifecycle."""

    def __init__(self):
        """Initialize with lazy orchestrator creation."""
        self._cached_orchestrator: Optional[BaseOrchestrator] = None

    def execute_pipeline(
        self,
        deployment: PipelineDeploymentResponse,
        parameters: Dict[str, Any],
        use_in_memory: Optional[bool] = None,
    ) -> ExecutionResult:
        """Execute pipeline and return immutable result."""
        orchestrator = self._get_orchestrator()
        placeholder_run = create_placeholder_run(
            deployment=deployment, logs=None
        )

        # Import runtime here to avoid circular imports
        from zenml.deployers.serving import runtime

        # Start request-scoped runtime context
        runtime.start(
            request_id=str(uuid4()),
            deployment=deployment,
            parameters=parameters,
            use_in_memory=use_in_memory,
        )

        try:
            # Execute pipeline
            orchestrator.run(
                deployment=deployment,
                stack=Client().active_stack,
                placeholder_run=placeholder_run,
            )

            # Capture outputs from THIS REQUEST's context
            outputs = runtime.get_outputs() if runtime.is_active() else None

        finally:
            # Always cleanup runtime context
            runtime.stop()

        # Fetch the completed run
        run = Client().get_pipeline_run(
            name_id_or_prefix=placeholder_run.id,
            hydrate=True,
            include_full_metadata=True,
        )

        return ExecutionResult(run=run, outputs=outputs)

    def _get_orchestrator(self) -> BaseOrchestrator:
        """Get cached orchestrator, creating if needed."""
        if self._cached_orchestrator is None:
            from zenml.enums import StackComponentType
            from zenml.orchestrators.local.local_orchestrator import (
                LocalOrchestrator,
                LocalOrchestratorConfig,
            )

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

        return self._cached_orchestrator


class PipelineServingService:
    """Clean, elegant pipeline serving service with zero memory leaks."""

    def __init__(self, deployment_id: UUID):
        """Initialize service with minimal state."""
        self.deployment_id = deployment_id
        self.deployment: Optional[PipelineDeploymentResponse] = None
        self.pipeline_state: Optional[Any] = None

        # Execution tracking
        self.service_start_time = time.time()
        self.last_execution_time: Optional[datetime] = None
        self.total_executions = 0

        # Clean component composition
        self._orchestrator = PipelineOrchestrator()
        self._params_model: Optional[Any] = None

        logger.info(f"Initializing service for deployment: {deployment_id}")

    async def initialize(self) -> None:
        """Initialize service with proper error handling."""
        try:
            logger.info("Loading pipeline deployment configuration...")

            # Load deployment
            self.deployment = Client().zen_store.get_deployment(
                deployment_id=self.deployment_id
            )

            # Activate integrations
            integration_registry.activate_integrations()

            # Build parameter model
            self._params_model = self._build_params_model()

            # Execute init hook
            await self._execute_init_hook()

            # Log success
            self._log_initialization_success()

        except Exception as e:
            logger.error(f"❌ Failed to initialize service: {e}")
            logger.error(f"   Traceback: {traceback.format_exc()}")
            raise

    async def cleanup(self) -> None:
        """Execute cleanup hook if present."""
        cleanup_hook_source = (
            self.deployment
            and self.deployment.pipeline_configuration.cleanup_hook_source
        )

        if not cleanup_hook_source:
            return

        logger.info("Executing pipeline's cleanup hook...")
        try:
            cleanup_hook = source_utils.load(cleanup_hook_source)

            if inspect.iscoroutinefunction(cleanup_hook):
                await cleanup_hook()
            else:
                cleanup_hook()
        except Exception as e:
            logger.exception(f"Failed to execute cleanup hook: {e}")
            raise

    def execute_pipeline(
        self,
        parameters: Dict[str, Any],
        run_name: Optional[str] = None,
        timeout: Optional[int] = 300,
        use_in_memory: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Execute pipeline with clean error handling and resource management."""
        # Unused parameters for future implementation
        _ = run_name, timeout

        if not self.deployment:
            raise RuntimeError("Service not properly initialized")

        start_time = time.time()
        logger.info("Starting pipeline execution")

        try:
            # Validate parameters
            resolved_params = self._resolve_parameters(parameters)

            # Execute pipeline (returns immutable result)
            result = self._orchestrator.execute_pipeline(
                deployment=self.deployment,
                parameters=resolved_params,
                use_in_memory=use_in_memory,
            )

            # Process outputs using runtime functions
            from zenml.deployers.serving import runtime

            outputs = runtime.process_outputs(
                runtime_outputs=result.outputs,
                run=result.run,
                enforce_size_limits=not use_in_memory,
                max_output_size_mb=self._get_max_output_size_mb(),
            )

            return self._build_success_response(
                outputs=outputs,
                start_time=start_time,
                resolved_params=resolved_params,
            )

        except Exception as e:
            logger.error(f"❌ Pipeline execution failed: {e}")
            return self._build_error_response(error=e, start_time=start_time)

    def get_service_info(self) -> Dict[str, Any]:
        """Get service information."""
        if not self.deployment:
            return {"error": "Service not initialized"}

        return {
            "deployment_id": str(self.deployment_id),
            "pipeline_name": self.deployment.pipeline_configuration.name,
            "total_executions": self.total_executions,
            "last_execution_time": (
                self.last_execution_time.isoformat()
                if self.last_execution_time
                else None
            ),
            "status": "healthy",
        }

    def get_execution_metrics(self) -> Dict[str, Any]:
        """Get execution metrics."""
        return {
            "total_executions": self.total_executions,
            "last_execution_time": (
                self.last_execution_time.isoformat()
                if self.last_execution_time
                else None
            ),
        }

    def is_healthy(self) -> bool:
        """Check service health."""
        return self.deployment is not None

    # Private helper methods

    def _get_max_output_size_mb(self) -> int:
        """Get max output size from environment with bounds checking."""
        try:
            size_mb = int(
                os.environ.get("ZENML_SERVING_MAX_OUTPUT_SIZE_MB", "1")
            )
            return max(1, min(size_mb, 100))  # Enforce 1MB-100MB bounds
        except (ValueError, TypeError):
            logger.warning(
                "Invalid ZENML_SERVING_MAX_OUTPUT_SIZE_MB. Using 1MB."
            )
            return 1

    def _build_params_model(self) -> Any:
        """Build parameter model with proper error handling."""
        try:
            from zenml.deployers.serving.parameters import (
                build_params_model_from_deployment,
            )

            assert self.deployment is not None
            return build_params_model_from_deployment(
                self.deployment, strict=True
            )

        except Exception as e:
            logger.error(f"Failed to construct parameter model: {e}")
            raise

    async def _execute_init_hook(self) -> None:
        """Execute init hook if present."""
        init_hook_source = (
            self.deployment
            and self.deployment.pipeline_configuration.init_hook_source
        )

        if not init_hook_source:
            return

        logger.info("Executing pipeline's init hook...")
        try:
            init_hook = source_utils.load(init_hook_source)

            if inspect.iscoroutinefunction(init_hook):
                self.pipeline_state = await init_hook()
            else:
                self.pipeline_state = init_hook()
        except Exception as e:
            logger.exception(f"Failed to execute init hook: {e}")
            raise

    def _log_initialization_success(self) -> None:
        """Log successful initialization."""
        assert self.deployment is not None

        pipeline_name = self.deployment.pipeline_configuration.name
        step_count = len(self.deployment.step_configurations)
        stack_name = (
            self.deployment.stack.name if self.deployment.stack else "unknown"
        )

        logger.info("✅ Service initialized successfully:")
        logger.info(f"   Pipeline: {pipeline_name}")
        logger.info(f"   Steps: {step_count}")
        logger.info(f"   Stack: {stack_name}")

    def _resolve_parameters(
        self, request_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate and normalize parameters."""
        assert self._params_model is not None
        parameters = self._params_model.model_validate(request_params or {})
        return parameters.model_dump()  # type: ignore[return-value]

    def _build_success_response(
        self,
        outputs: Dict[str, Any],
        start_time: float,
        resolved_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build success response with execution tracking."""
        execution_time = time.time() - start_time
        self.total_executions += 1
        self.last_execution_time = datetime.now(timezone.utc)

        assert self.deployment is not None

        response = {
            "success": True,
            "outputs": outputs,
            "execution_time": execution_time,
            "metadata": {
                "pipeline_name": self.deployment.pipeline_configuration.name,
                "parameters_used": resolved_params,  # Already JSON-safe from validation
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

    def _build_error_response(
        self, error: Exception, start_time: float
    ) -> Dict[str, Any]:
        """Build error response."""
        execution_time = time.time() - start_time
        return {
            "success": False,
            "job_id": None,
            "error": str(error),
            "execution_time": execution_time,
            "metadata": {},
        }
