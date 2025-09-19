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
"""Pipeline deployment service."""

import os
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, Type, Union
from uuid import UUID, uuid4

from pydantic import BaseModel

import zenml.pipelines.run_utils as run_utils
from zenml.client import Client
from zenml.deployers.server import runtime
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
from zenml.utils import env_utils

logger = get_logger(__name__)


class PipelineDeploymentService:
    """Pipeline deployment service."""

    def __init__(self, snapshot_id: Union[str, UUID]) -> None:
        """Initialize service with minimal state.

        Args:
            snapshot_id: The ID of the snapshot to deploy.

        Raises:
            RuntimeError: If the snapshot cannot be loaded.
        """
        self.snapshot_id: Union[str, UUID] = snapshot_id
        self._client = Client()
        self.pipeline_state: Optional[Any] = None

        # Execution tracking
        self.service_start_time = time.time()
        self.last_execution_time: Optional[datetime] = None
        self.total_executions = 0

        # Cache a local orchestrator instance to avoid per-request construction
        self._orchestrator: Optional[BaseOrchestrator] = None
        self._params_model: Optional[Type[BaseModel]] = None
        # Lazily initialized cached client

        logger.info("Loading pipeline snapshot configuration...")

        try:
            # Accept both str and UUID for flexibility
            if isinstance(self.snapshot_id, str):
                snapshot_id = UUID(self.snapshot_id)
            else:
                snapshot_id = self.snapshot_id

            self.snapshot: PipelineSnapshotResponse = (
                self._client.zen_store.get_snapshot(snapshot_id=snapshot_id)
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load snapshot: {e}")

    @property
    def params_model(self) -> Optional[Type[BaseModel]]:
        """Get the parameter model.

        Returns:
            The parameter model.
        """
        return self._params_model

    def _get_max_output_size_bytes(self) -> int:
        """Get max output size in bytes with bounds checking.

        Returns:
            The max output size in bytes.
        """
        try:
            size_mb = int(
                os.environ.get("ZENML_DEPLOYMENT_MAX_OUTPUT_SIZE_MB", "1")
            )
            # Enforce reasonable bounds: 1MB to 100MB
            size_mb = max(1, min(size_mb, 100))
            return size_mb * 1024 * 1024
        except (ValueError, TypeError):
            logger.warning(
                "Invalid ZENML_DEPLOYMENT_MAX_OUTPUT_SIZE_MB. Using 1MB."
            )
            return 1024 * 1024

    def _get_client(self) -> Client:
        """Return a cached ZenML client instance.

        Returns:
            The cached ZenML client instance.
        """
        return self._client

    def initialize(self) -> None:
        """Initialize service with proper error handling.

        Raises:
            Exception: If the service cannot be initialized.
        """
        try:
            # Activate integrations to ensure all components are available
            integration_registry.activate_integrations()

            # Build parameter model
            self._params_model = self._build_params_model()

            # Initialize orchestrator
            self._orchestrator = LocalOrchestrator(
                name="deployment-local",
                id=uuid4(),
                config=LocalOrchestratorConfig(),
                flavor="local",
                type=StackComponentType.ORCHESTRATOR,
                user=uuid4(),
                created=datetime.now(),
                updated=datetime.now(),
            )

            # Execute init hook
            self._execute_init_hook()

            self._orchestrator.set_shared_run_state(self.pipeline_state)

            # Log success
            self._log_initialization_success()

        except Exception as e:
            logger.error(f"❌ Failed to initialize service: {e}")
            logger.error(f"   Traceback: {traceback.format_exc()}")
            raise

    def cleanup(self) -> None:
        """Execute cleanup hook if present.

        Raises:
            Exception: If the cleanup hook cannot be executed.
        """
        cleanup_hook_source = (
            self.snapshot
            and self.snapshot.pipeline_configuration.cleanup_hook_source
        )

        if not cleanup_hook_source:
            return

        logger.info("Executing pipeline's cleanup hook...")
        try:
            environment = {}
            if self.snapshot:
                environment = self.snapshot.pipeline_configuration.environment
            with env_utils.temporary_environment(environment):
                load_and_run_hook(cleanup_hook_source)
        except Exception as e:
            logger.exception(f"Failed to execute cleanup hook: {e}")
            raise

    def execute_pipeline(
        self,
        parameters: Dict[str, Any],
        run_name: Optional[str] = None,
        timeout: Optional[int] = 300,
        use_in_memory: bool = False,
    ) -> Dict[str, Any]:
        """Execute the deployment with the given parameters.

        Args:
            parameters: Runtime parameters supplied by the caller.
            run_name: Optional name override for the run.
            timeout: Optional timeout for the run (currently unused).
            use_in_memory: Whether to keep outputs in memory for fast access.

        Returns:
            A dictionary containing details about the execution result.
        """
        # Unused parameters for future implementation
        _ = run_name, timeout
        start_time = time.time()
        logger.info("Starting pipeline execution")

        try:
            # Execute pipeline and get run; runtime outputs captured internally
            run, captured_outputs = self._execute_with_orchestrator(
                parameters, use_in_memory
            )

            # Map outputs using fast (in-memory) or slow (artifact) path
            mapped_outputs = self._map_outputs(captured_outputs)

            return self._build_success_response(
                mapped_outputs=mapped_outputs,
                start_time=start_time,
                resolved_params=parameters,
                run=run,
            )

        except Exception as e:
            logger.error(f"❌ Pipeline execution failed: {e}")
            return self._build_error_response(e=e, start_time=start_time)

    def get_service_info(self) -> Dict[str, Any]:
        """Get service information.

        Returns:
            A dictionary containing service information.
        """
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
        """Return lightweight execution metrics for observability.

        Returns:
            A dictionary with aggregated execution metrics.
        """
        return {
            "total_executions": self.total_executions,
            "last_execution_time": (
                self.last_execution_time.isoformat()
                if self.last_execution_time
                else None
            ),
        }

    def is_healthy(self) -> bool:
        """Check service health.

        Returns:
            True if the service is healthy, otherwise False.
        """
        return True

    def _map_outputs(
        self,
        runtime_outputs: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Map pipeline outputs using centralized runtime processing.

        Args:
            runtime_outputs: Optional in-memory outputs captured from runtime.

        Returns:
            A dictionary containing outputs and any warnings from filtering.
        """
        filtered_outputs = {}
        if runtime_outputs and self.snapshot.pipeline_spec:
            # Filter outputs based on pipeline schema (raises RuntimeError if missing)
            output_mappings = self.snapshot.pipeline_spec.outputs
            for output_mapping in output_mappings:
                if output_mapping.step_name in runtime_outputs.keys():
                    filtered_outputs[
                        f"{output_mapping.step_name}-{output_mapping.output_name}"
                    ] = runtime_outputs[output_mapping.step_name].get(
                        output_mapping.output_name, None
                    )
                else:
                    logger.warning(
                        f"Output {output_mapping.output_name} not found in runtime outputs for step {output_mapping.step_name}"
                    )
                    filtered_outputs[
                        f"{output_mapping.step_name}-{output_mapping.output_name}"
                    ] = None
        else:
            logger.debug("No output mappings found, returning empty outputs")

        return filtered_outputs

    def _execute_with_orchestrator(
        self,
        resolved_params: Dict[str, Any],
        use_in_memory: bool,
    ) -> Tuple[PipelineRunResponse, Optional[Dict[str, Dict[str, Any]]]]:
        """Run the snapshot via the orchestrator and return the concrete run.

        Args:
            resolved_params: Normalized pipeline parameters.
            use_in_memory: Whether runtime should capture in-memory outputs.

        Returns:
            The fully materialized pipeline run response.

        Raises:
            RuntimeError: If the orchestrator has not been initialized.
            RuntimeError: If the pipeline cannot be executed.

        """
        client = self._client
        active_stack: Stack = client.active_stack

        if self._orchestrator is None:
            raise RuntimeError("Orchestrator not initialized")

        # Create a placeholder run and execute with a known run id
        placeholder_run = run_utils.create_placeholder_run(
            snapshot=self.snapshot, logs=None
        )

        # Start deployment runtime context with parameters
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
            if runtime.is_active():
                captured_outputs = runtime.get_outputs()
        except Exception as e:
            logger.error(f"Failed to execute pipeline: {e}")
            raise RuntimeError(f"Failed to execute pipeline: {e}")
        finally:
            # Always stop deployment runtime context
            runtime.stop()

        # Fetch the concrete run via its id
        run: PipelineRunResponse = self._client.get_pipeline_run(
            name_id_or_prefix=placeholder_run.id,
            hydrate=True,
            include_full_metadata=True,
        )
        # Store captured outputs for the caller to use
        return run, captured_outputs

    def _build_params_model(self) -> Any:
        """Build the pipeline parameters model from the deployment.

        Returns:
            A parameters model derived from the deployment configuration.

        Raises:
            Exception: If the model cannot be constructed.
        """
        try:
            from zenml.deployers.server.parameters import (
                build_params_model_from_snapshot,
            )

            return build_params_model_from_snapshot(self.snapshot, strict=True)
        except Exception as e:
            logger.error(f"Failed to construct parameter model: {e}")
            raise

    def _execute_init_hook(self) -> None:
        """Execute init hook if present.

        Raises:
            Exception: If executing the hook fails.
        """
        init_hook_source = (
            self.snapshot.pipeline_configuration.init_hook_source
        )
        init_hook_kwargs = (
            self.snapshot.pipeline_configuration.init_hook_kwargs
        )

        if not init_hook_source:
            return

        logger.info("Executing pipeline's init hook...")
        try:
            environment = {}
            if self.snapshot:
                environment = self.snapshot.pipeline_configuration.environment
            with env_utils.temporary_environment(environment):
                self.pipeline_state = load_and_run_hook(
                    init_hook_source, init_hook_kwargs
                )
        except Exception as e:
            logger.exception(f"Failed to execute init hook: {e}")
            raise

    def _log_initialization_success(self) -> None:
        """Log successful initialization."""
        pipeline_name = self.snapshot.pipeline_configuration.name
        step_count = len(self.snapshot.step_configurations)
        stack_name = (
            self.snapshot.stack.name if self.snapshot.stack else "unknown"
        )

        logger.info("✅ Service initialized successfully:")
        logger.info(f"   Pipeline: {pipeline_name}")
        logger.info(f"   Steps: {step_count}")
        logger.info(f"   Stack: {stack_name}")

    def _build_success_response(
        self,
        mapped_outputs: Dict[str, Any],
        start_time: float,
        resolved_params: Dict[str, Any],
        run: PipelineRunResponse,
    ) -> Dict[str, Any]:
        """Build success response with execution tracking.

        Args:
            mapped_outputs: The mapped outputs.
            start_time: The start time of the execution.
            resolved_params: The resolved parameters.
            run: The pipeline run that was executed.

        Returns:
            A dictionary describing the successful execution.
        """
        execution_time = time.time() - start_time
        self.total_executions += 1
        self.last_execution_time = datetime.now(timezone.utc)

        response = {
            "success": True,
            "outputs": mapped_outputs,
            "execution_time": execution_time,
            "metadata": {
                "pipeline_name": self.snapshot.pipeline_configuration.name,
                "run_id": run.id,
                "run_name": run.name,
                "parameters_used": resolved_params,
                "snapshot_id": str(self.snapshot.id),
            },
        }

        return response

    # ----------
    # Schemas for OpenAPI enrichment
    # ----------

    @property
    def request_schema(self) -> Optional[Dict[str, Any]]:
        """Return the JSON schema for pipeline parameters if available.

        Returns:
            The JSON schema for pipeline parameters if available.
        """
        try:
            if self.snapshot.pipeline_spec:
                return self.snapshot.pipeline_spec.input_schema
        except Exception:
            return None
        return None

    @property
    def output_schema(self) -> Optional[Dict[str, Any]]:
        """Return the JSON schema for the deployment response if available.

        Returns:
            The JSON schema for the deployment response if available.
        """
        try:
            if self.snapshot.pipeline_spec:
                return self.snapshot.pipeline_spec.output_schema
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
