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

import os
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Type, Union
from uuid import UUID, uuid4

from pydantic import BaseModel

import zenml.client as client_mod
import zenml.pipelines.run_utils as run_utils
from zenml.enums import StackComponentType
from zenml.hooks.hook_validators import load_and_run_hook
from zenml.integrations.registry import integration_registry
from zenml.logger import get_logger
from zenml.models import PipelineSnapshotResponse
from zenml.models.v2.core.pipeline_run import PipelineRunResponse
from zenml.orchestrators.base_orchestrator import BaseOrchestrator
from zenml.orchestrators.local.local_orchestrator import (
    LocalOrchestrator,
    LocalOrchestratorConfig,
)
from zenml.stack import Stack

logger = get_logger(__name__)


class PipelineServingService:
    """Clean, elegant pipeline serving service with zero memory leaks."""

    def __init__(self, snapshot_id: Union[str, UUID]):
        """Initialize service with minimal state."""
        self.snapshot_id: Union[str, UUID] = snapshot_id
        self.snapshot: Optional[PipelineSnapshotResponse] = None
        self.pipeline_state: Optional[Any] = None

        # Execution tracking
        self.service_start_time = time.time()
        self.last_execution_time: Optional[datetime] = None
        self.total_executions = 0

        # Cache a local orchestrator instance to avoid per-request construction
        self._orchestrator: Optional[BaseOrchestrator] = None
        self._params_model: Optional[Type[BaseModel]] = None
        # Captured in-memory outputs from the last run (internal)
        self._last_runtime_outputs: Optional[Dict[str, Dict[str, Any]]] = None
        # Lazily initialized cached client
        self._client: Optional[Any] = None

        logger.info(f"Initializing service for snapshot: {snapshot_id}")

    @property
    def params_model(self) -> Optional[Type[BaseModel]]:
        """Get the parameter model.

        Returns:
            The parameter model.
        """
        return self._params_model

    def _get_max_output_size_bytes(self) -> int:
        """Get max output size in bytes with bounds checking."""
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

    def _get_client(self) -> Any:
        """Return a cached ZenML client instance."""
        if self._client is None:
            self._client = client_mod.Client()
        return self._client

    async def initialize(self) -> None:
        """Initialize service with proper error handling."""
        try:
            logger.info("Loading pipeline snapshot configuration...")

            # Load snapshot from ZenML store
            client = self._get_client()
            # Accept both str and UUID for flexibility
            snapshot_id = self.snapshot_id
            try:
                if isinstance(snapshot_id, str):
                    snapshot_id = UUID(snapshot_id)
            except Exception:
                pass

            self.snapshot = client.zen_store.get_snapshot(
                snapshot_id=snapshot_id
            )

            # Activate integrations to ensure all components are available
            integration_registry.activate_integrations()

            # Build parameter model
            self._params_model = self._build_params_model()

            # Initialize orchestrator
            self._orchestrator = LocalOrchestrator(
                name="serving-local",
                id=uuid4(),
                config=LocalOrchestratorConfig(),
                flavor="local",
                type=StackComponentType.ORCHESTRATOR,
                user=uuid4(),
                created=datetime.now(),
                updated=datetime.now(),
            )

            # Execute init hook
            await self._execute_init_hook()

            self._orchestrator.set_shared_run_state(self.pipeline_state)

            # Log success
            self._log_initialization_success()

        except Exception as e:
            logger.error(f"❌ Failed to initialize service: {e}")
            logger.error(f"   Traceback: {traceback.format_exc()}")
            raise

    async def cleanup(self) -> None:
        """Execute cleanup hook if present."""
        cleanup_hook_source = (
            self.snapshot
            and self.snapshot.pipeline_configuration.cleanup_hook_source
        )

        if not cleanup_hook_source:
            return

        logger.info("Executing pipeline's cleanup hook...")
        try:
            load_and_run_hook(cleanup_hook_source)
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

        if not self.snapshot:
            raise RuntimeError("Service not properly initialized")

        start_time = time.time()
        logger.info("Starting pipeline execution")

        try:
            # Validate parameters
            resolved_params = self._resolve_parameters(parameters)

            # Execute pipeline and get run; runtime outputs captured internally
            run = self._execute_with_orchestrator(
                resolved_params, use_in_memory
            )

            # Map outputs using fast (in-memory) or slow (artifact) path
            mapped_outputs = self._map_outputs(run, self._last_runtime_outputs)
            # Clear captured outputs after use
            self._last_runtime_outputs = None

            return self._build_success_response(
                mapped_outputs=mapped_outputs,
                start_time=start_time,
                resolved_params=resolved_params,
                run=run,
            )

        except Exception as e:
            logger.error(f"❌ Pipeline execution failed: {e}")
            return self._build_error_response(e=e, start_time=start_time)

    def get_service_info(self) -> Dict[str, Any]:
        """Get service information."""
        if not self.snapshot:
            return {"error": "Service not initialized"}

        return {
            "snapshot_id": str(self.snapshot_id),
            "pipeline_name": self.snapshot.pipeline_configuration.name,
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
        return self.snapshot is not None

    # Private helper methods

    def _map_outputs(
        self,
        run: PipelineRunResponse,
        runtime_outputs: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Map pipeline outputs using centralized runtime processing."""
        from zenml.deployers.serving import runtime

        if runtime_outputs is None and runtime.is_active():
            runtime_outputs = runtime.get_outputs()

        max_size_mb = self._get_max_output_size_bytes() // (1024 * 1024)
        return runtime.process_outputs(
            runtime_outputs=runtime_outputs,
            run=run,
            enforce_size_limits=True,
            max_output_size_mb=max_size_mb,
        )

    def _execute_with_orchestrator(
        self,
        resolved_params: Dict[str, Any],
        use_in_memory: Optional[bool] = None,
    ) -> PipelineRunResponse:
        """Run the snapshot via the orchestrator and return the concrete run."""
        client = self._get_client()
        active_stack: Stack = client.active_stack

        if self._orchestrator is None:
            raise RuntimeError("Orchestrator not initialized")

        # Create a placeholder run and execute with a known run id
        assert self.snapshot is not None
        placeholder_run = run_utils.create_placeholder_run(
            snapshot=self.snapshot, logs=None
        )

        # Start serving runtime context with parameters
        from zenml.deployers.serving import runtime

        runtime.start(
            request_id=str(uuid4()),
            snapshot=self.snapshot,
            parameters=resolved_params,
            use_in_memory=use_in_memory,
        )

        captured_outputs: Optional[Dict[str, Dict[str, Any]]] = None
        try:
            self._orchestrator.run(
                snapshot=self.snapshot,
                stack=active_stack,
                placeholder_run=placeholder_run,
            )

            # Capture in-memory outputs before stopping the runtime context
            try:
                if runtime.is_active():
                    captured_outputs = runtime.get_outputs()
            except ImportError:
                pass
        finally:
            # Always stop serving runtime context
            runtime.stop()

        # Fetch the concrete run via its id
        run: PipelineRunResponse = self._get_client().get_pipeline_run(
            name_id_or_prefix=placeholder_run.id,
            hydrate=True,
            include_full_metadata=True,
        )
        # Store captured outputs for the caller to use
        self._last_runtime_outputs = captured_outputs
        return run

    def _build_params_model(self) -> Any:
        """Build parameter model with proper error handling."""
        try:
            from zenml.deployers.serving.parameters import (
                build_params_model_from_snapshot,
            )

            assert self.snapshot is not None
            return build_params_model_from_snapshot(self.snapshot, strict=True)
        except Exception as e:
            logger.error(f"Failed to construct parameter model: {e}")
            raise

    async def _execute_init_hook(self) -> None:
        """Execute init hook if present."""
        init_hook_source = (
            self.snapshot
            and self.snapshot.pipeline_configuration.init_hook_source
        )
        init_hook_kwargs = (
            self.snapshot.pipeline_configuration.init_hook_kwargs
            if self.snapshot
            else None
        )

        if not init_hook_source:
            return

        logger.info("Executing pipeline's init hook...")
        try:
            self.pipeline_state = load_and_run_hook(
                init_hook_source, init_hook_kwargs
            )
        except Exception as e:
            logger.exception(f"Failed to execute init hook: {e}")
            raise

    def _log_initialization_success(self) -> None:
        """Log successful initialization."""
        assert self.snapshot is not None

        pipeline_name = self.snapshot.pipeline_configuration.name
        step_count = len(self.snapshot.step_configurations)
        stack_name = (
            self.snapshot.stack.name if self.snapshot.stack else "unknown"
        )

        logger.info("✅ Service initialized successfully:")
        logger.info(f"   Pipeline: {pipeline_name}")
        logger.info(f"   Steps: {step_count}")
        logger.info(f"   Stack: {stack_name}")

    def _resolve_parameters(
        self, request_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate and normalize parameters, preserving complex objects."""
        # If available, validate against the parameters model
        if self._params_model is None:
            try:
                self._params_model = self._build_params_model()
            except Exception:
                self._params_model = None

        if self._params_model is not None:
            params_obj = self._params_model.model_validate(
                request_params or {}
            )
            # Use the model class fields to avoid mypy issues with instance props
            fields = getattr(self._params_model, "model_fields")
            return {name: getattr(params_obj, name) for name in fields}

        # Otherwise, just return request parameters as-is (no nesting support)
        return dict(request_params or {})

    def _serialize_json_safe(self, value: Any) -> Any:
        """Delegate to the centralized runtime serializer."""
        from zenml.deployers.serving import runtime as serving_runtime

        return serving_runtime._make_json_safe(value)

    def _build_success_response(
        self,
        mapped_outputs: Dict[str, Any],
        start_time: float,
        resolved_params: Dict[str, Any],
        run: PipelineRunResponse,
    ) -> Dict[str, Any]:
        """Build success response with execution tracking."""
        execution_time = time.time() - start_time
        self.total_executions += 1
        self.last_execution_time = datetime.now(timezone.utc)

        assert self.snapshot is not None

        response = {
            "success": True,
            "outputs": mapped_outputs,
            "execution_time": execution_time,
            "metadata": {
                "pipeline_name": self.snapshot.pipeline_configuration.name,
                "run_id": run.id,
                "run_name": run.name,
                "parameters_used": self._serialize_json_safe(resolved_params),
                "snapshot_id": str(self.snapshot.id),
            },
        }

        # Add response schema if available
        # Add response schema only if the attribute exists and is set
        try:
            if (
                self.snapshot.pipeline_spec
                and self.snapshot.pipeline_spec.response_schema
            ):
                response["response_schema"] = (
                    self.snapshot.pipeline_spec.response_schema
                )
        except AttributeError:
            # Some tests may provide a lightweight snapshot stub without
            # a pipeline_spec attribute; ignore in that case.
            pass

        return response

    # ----------
    # Schemas for OpenAPI enrichment
    # ----------

    @property
    def request_schema(self) -> Optional[Dict[str, Any]]:
        """Return the JSON schema for pipeline parameters if available."""
        try:
            if self.snapshot and self.snapshot.pipeline_spec:
                return self.snapshot.pipeline_spec.parameters_schema
        except Exception:
            return None
        return None

    @property
    def response_schema(self) -> Optional[Dict[str, Any]]:
        """Return the JSON schema for the serving response if available."""
        try:
            if self.snapshot and self.snapshot.pipeline_spec:
                return self.snapshot.pipeline_spec.response_schema
        except Exception:
            return None
        return None

    def _build_error_response(
        self, e: Exception, start_time: float
    ) -> Dict[str, Any]:
        """Build error response.

        Args:
            e: The exception to build the error response from.
            start_time: The start time of the execution.

        Returns:
            A dictionary containing the error response.
        """
        execution_time = time.time() - start_time
        return {
            "success": False,
            "job_id": None,
            "error": str(e),
            "execution_time": execution_time,
            "metadata": {},
        }
