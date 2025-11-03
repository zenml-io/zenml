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

import time
import traceback
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Dict,
    Optional,
    Tuple,
    Type,
)
from uuid import uuid4

from pydantic import BaseModel, WithJsonSchema

import zenml.pipelines.run_utils as run_utils
from zenml.client import Client
from zenml.deployers.server import runtime
from zenml.deployers.server.models import (
    AppInfo,
    BaseDeploymentInvocationRequest,
    BaseDeploymentInvocationResponse,
    DeploymentInfo,
    DeploymentInvocationResponseMetadata,
    ExecutionMetrics,
    PipelineInfo,
    ServiceInfo,
    SnapshotInfo,
)
from zenml.deployers.utils import (
    deployment_snapshot_request_from_source_snapshot,
)
from zenml.enums import StackComponentType
from zenml.hooks.hook_validators import load_and_run_hook
from zenml.logger import get_logger
from zenml.models import (
    PipelineRunResponse,
    PipelineRunTriggerInfo,
    PipelineSnapshotResponse,
)
from zenml.orchestrators.base_orchestrator import BaseOrchestrator
from zenml.orchestrators.local.local_orchestrator import (
    LocalOrchestrator,
    LocalOrchestratorConfig,
)
from zenml.stack import Stack
from zenml.steps.utils import get_unique_step_output_names
from zenml.utils import env_utils, source_utils
from zenml.zen_stores.rest_zen_store import RestZenStore

if TYPE_CHECKING:
    from zenml.deployers.server.app import BaseDeploymentAppRunner
    from zenml.pipelines.pipeline_definition import Pipeline

logger = get_logger(__name__)


class SharedLocalOrchestrator(LocalOrchestrator):
    """Local orchestrator tweaked for deployments.

    This is a slight modification of the LocalOrchestrator: it bypasses the
    init/cleanup hook execution because they are run globally by the deployment
    service
    """

    @classmethod
    def run_init_hook(cls, snapshot: "PipelineSnapshotResponse") -> None:
        """Runs the init hook.

        Args:
            snapshot: The snapshot to run the init hook for.
        """
        # Bypass the init hook execution because it is run globally by
        # the deployment service
        pass

    @classmethod
    def run_cleanup_hook(cls, snapshot: "PipelineSnapshotResponse") -> None:
        """Runs the cleanup hook.

        Args:
            snapshot: The snapshot to run the cleanup hook for.
        """
        # Bypass the cleanup hook execution because it is run globally by
        # the deployment service
        pass


class BasePipelineDeploymentService(ABC):
    """Abstract base class for pipeline deployment services.

    Subclasses must implement lifecycle management, execution, health,
    and schema accessors. This contract enables swapping implementations
    via import-source configuration without modifying the FastAPI app
    wiring code.
    """

    def __init__(
        self, app_runner: "BaseDeploymentAppRunner", **kwargs: Any
    ) -> None:
        """Initialize the deployment service.

        Args:
            app_runner: The deployment application runner used with this service.
            **kwargs: Additional keyword arguments for the deployment service.

        Raises:
            RuntimeError: If snapshot cannot be loaded.
        """
        self.app_runner = app_runner
        self.deployment = app_runner.deployment
        if self.deployment.snapshot is None:
            raise RuntimeError("Deployment has no snapshot")
        self.snapshot = self.deployment.snapshot

    @abstractmethod
    def initialize(self) -> None:
        """Initialize service resources and run init hooks.

        Raises:
            Exception: If the service cannot be initialized.
        """

    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup service resources and run cleanup hooks."""

    @abstractmethod
    def execute_pipeline(
        self, request: BaseDeploymentInvocationRequest
    ) -> BaseDeploymentInvocationResponse:
        """Execute the deployment with the given parameters.

        Args:
            request: Runtime parameters supplied by the caller.

        Returns:
            A BaseDeploymentInvocationResponse describing the execution result.
        """

    @abstractmethod
    def get_service_info(self) -> ServiceInfo:
        """Get service information.

        Returns:
            A dictionary containing service information.
        """

    @abstractmethod
    def get_execution_metrics(self) -> ExecutionMetrics:
        """Return lightweight execution metrics for observability.

        Returns:
            A dictionary containing execution metrics.
        """

    @abstractmethod
    def health_check(self) -> None:
        """Check service health.

        Raises:
            RuntimeError: If the service is not healthy.
        """

    # ----------
    # Schemas and models for OpenAPI enrichment
    # ----------

    @property
    def input_model(
        self,
    ) -> Type[BaseModel]:
        """Construct a Pydantic model representing pipeline input parameters.

        Load the pipeline class from `pipeline_spec.source` and derive the
        entrypoint signature types to create a dynamic Pydantic model
        (extra='forbid') to use for parameter validation.

        Returns:
            A Pydantic `BaseModel` subclass that validates the pipeline input
            parameters.

        Raises:
            RuntimeError: If the pipeline class cannot be loaded or if no
                parameters model can be constructed for the pipeline.
        """
        if (
            not self.snapshot.pipeline_spec
            or not self.snapshot.pipeline_spec.source
        ):
            raise RuntimeError(
                f"Snapshot `{self.snapshot.id}` is missing a "
                "pipeline_spec.source; cannot build input model."
            )

        try:
            pipeline_class: "Pipeline" = source_utils.load(
                self.snapshot.pipeline_spec.source
            )
        except Exception as e:
            raise RuntimeError(
                "Failed to load pipeline class from snapshot"
            ) from e

        model = pipeline_class._compute_input_model()
        if not model:
            raise RuntimeError(
                f"Failed to construct input model from pipeline "
                f"`{self.snapshot.pipeline_configuration.name}`."
            )
        return model

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Return the JSON schema for pipeline input parameters.

        Returns:
            The JSON schema for pipeline parameters.

        Raises:
            RuntimeError: If the pipeline input schema is not available.
        """
        if (
            self.snapshot.pipeline_spec
            and self.snapshot.pipeline_spec.input_schema
        ):
            return self.snapshot.pipeline_spec.input_schema
        # This should never happen, given that we check for this in the
        # base deployer.
        raise RuntimeError("The pipeline input schema is not available.")

    @property
    def output_schema(self) -> Dict[str, Any]:
        """Return the JSON schema for the pipeline outputs.

        Returns:
            The JSON schema for the pipeline outputs.

        Raises:
            RuntimeError: If the pipeline output schema is not available.
        """
        if (
            self.snapshot.pipeline_spec
            and self.snapshot.pipeline_spec.output_schema
        ):
            return self.snapshot.pipeline_spec.output_schema
        # This should never happen, given that we check for this in the
        # base deployer.
        raise RuntimeError("The pipeline output schema is not available.")

    def get_pipeline_invoke_models(
        self,
    ) -> Tuple[Type[BaseModel], Type[BaseModel]]:
        """Generate the request and response models for the pipeline invoke endpoint.

        Returns:
            A tuple containing the request and response models.
        """
        if TYPE_CHECKING:
            # mypy has a difficult time with dynamic models, so we return something
            # static for mypy to use
            return BaseModel, BaseModel

        else:

            class PipelineInvokeRequest(BaseDeploymentInvocationRequest):
                parameters: Annotated[
                    self.input_model,
                    WithJsonSchema(self.input_schema, mode="validation"),
                ]

            class PipelineInvokeResponse(BaseDeploymentInvocationResponse):
                outputs: Annotated[
                    Optional[Dict[str, Any]],
                    WithJsonSchema(self.output_schema, mode="serialization"),
                ]

            return PipelineInvokeRequest, PipelineInvokeResponse


class PipelineDeploymentService(BasePipelineDeploymentService):
    """Default pipeline deployment service implementation."""

    def initialize(self) -> None:
        """Initialize service with proper error handling.

        Raises:
            Exception: If the service cannot be initialized.
        """
        self._client = Client()

        if isinstance(self._client.zen_store, RestZenStore):
            # Set the connection pool size to match the number of threads
            self._client.zen_store.config.connection_pool_size = (
                self.app_runner.settings.thread_pool_size
            )
            self._client.zen_store.reinitialize_session()

        # Execution tracking
        self.service_start_time = time.time()
        self.last_execution_time: Optional[datetime] = None
        self.total_executions = 0
        self.orchestrator_class = SharedLocalOrchestrator

        try:
            # Execute init hook
            BaseOrchestrator.run_init_hook(self.snapshot)

            # Log success
            self._log_initialization_success()

        except Exception as e:
            logger.error(f"❌ Failed to initialize service: {e}")
            logger.error(f"   Traceback: {traceback.format_exc()}")
            raise

    def cleanup(self) -> None:
        """Execute cleanup hook if present."""
        BaseOrchestrator.run_cleanup_hook(self.snapshot)

    def execute_pipeline(
        self,
        request: BaseDeploymentInvocationRequest,
    ) -> BaseDeploymentInvocationResponse:
        """Execute the deployment with the given parameters.

        Args:
            request: Runtime parameters supplied by the caller.

        Returns:
            A BaseDeploymentInvocationResponse describing the execution result.
        """
        # Unused parameters for future implementation
        _ = request.run_name, request.timeout
        parameters = request.parameters.model_dump()
        start_time = time.time()
        logger.info("Starting pipeline execution")

        placeholder_run: Optional[PipelineRunResponse] = None
        try:
            # Create a placeholder run separately from the actual execution,
            # so that we have a run ID to include in the response even if the
            # pipeline execution fails.
            placeholder_run, deployment_snapshot = (
                self._prepare_execute_with_orchestrator(
                    resolved_params=parameters,
                )
            )

            captured_outputs = self._execute_with_orchestrator(
                placeholder_run=placeholder_run,
                deployment_snapshot=deployment_snapshot,
                resolved_params=parameters,
                skip_artifact_materialization=request.skip_artifact_materialization,
            )

            # Map outputs using fast (in-memory) or slow (artifact) path
            mapped_outputs = self._map_outputs(captured_outputs)

            return self._build_response(
                placeholder_run=placeholder_run,
                mapped_outputs=mapped_outputs,
                start_time=start_time,
                resolved_params=parameters,
            )

        except Exception as e:
            logger.error(f"❌ Pipeline execution failed: {e}")
            return self._build_response(
                placeholder_run=placeholder_run,
                mapped_outputs=None,
                start_time=start_time,
                resolved_params=parameters,
                error=e,
            )

    def get_service_info(self) -> ServiceInfo:
        """Get service information.

        Returns:
            A dictionary containing service information.
        """
        uptime = time.time() - self.service_start_time
        settings = self.app_runner.settings
        api_urlpath = f"{self.app_runner.settings.root_url_path}{self.app_runner.settings.api_url_path}"
        return ServiceInfo(
            deployment=DeploymentInfo(
                id=self.deployment.id,
                name=self.deployment.name,
                auth_enabled=self.deployment.auth_key is not None,
            ),
            snapshot=SnapshotInfo(
                id=self.snapshot.id,
                name=self.snapshot.name,
            ),
            pipeline=PipelineInfo(
                name=self.snapshot.pipeline_configuration.name,
                parameters=self.snapshot.pipeline_spec.parameters
                if self.snapshot.pipeline_spec
                else None,
                input_schema=self.input_schema,
                output_schema=self.output_schema,
            ),
            app=AppInfo(
                app_runner_flavor=self.app_runner.flavor.name,
                docs_url_path=settings.docs_url_path,
                redoc_url_path=settings.redoc_url_path,
                invoke_url_path=api_urlpath + settings.invoke_url_path,
                health_url_path=api_urlpath + settings.health_url_path,
                info_url_path=api_urlpath + settings.info_url_path,
                metrics_url_path=api_urlpath + settings.metrics_url_path,
            ),
            total_executions=self.total_executions,
            last_execution_time=self.last_execution_time,
            status="healthy",
            uptime=uptime,
        )

    def get_execution_metrics(self) -> ExecutionMetrics:
        """Return lightweight execution metrics for observability.

        Returns:
            Aggregated execution metrics.
        """
        return ExecutionMetrics(
            total_executions=self.total_executions,
            last_execution_time=self.last_execution_time,
        )

    def health_check(self) -> None:
        """Check service health."""
        pass

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

            unique_step_output_mapping = get_unique_step_output_names(
                {(o.step_name, o.output_name): o for o in output_mappings}
            )

            for output_mapping in output_mappings:
                unique_step_output_name = unique_step_output_mapping[
                    (
                        output_mapping.step_name,
                        output_mapping.output_name,
                    )
                ][1]
                if output_mapping.step_name in runtime_outputs.keys():
                    filtered_outputs[unique_step_output_name] = (
                        runtime_outputs[output_mapping.step_name].get(
                            output_mapping.output_name, None
                        )
                    )
                else:
                    logger.warning(
                        f"Output {output_mapping.output_name} not found in "
                        f"runtime outputs for step {output_mapping.step_name}"
                    )
                    filtered_outputs[unique_step_output_name] = None
        else:
            logger.debug("No output mappings found, returning empty outputs")

        return filtered_outputs

    def _prepare_execute_with_orchestrator(
        self,
        resolved_params: Dict[str, Any],
    ) -> Tuple[PipelineRunResponse, PipelineSnapshotResponse]:
        """Prepare the execution with the orchestrator.

        Args:
            resolved_params: The resolved parameters.

        Returns:
            A tuple of (placeholder_run, deployment_snapshot).
        """
        deployment_snapshot_request = (
            deployment_snapshot_request_from_source_snapshot(
                source_snapshot=self.snapshot,
                deployment_parameters=resolved_params,
            )
        )

        # Create the new snapshot in the store
        deployment_snapshot = self._client.zen_store.create_snapshot(
            deployment_snapshot_request
        )

        # Create a placeholder run using the new deployment snapshot
        placeholder_run = run_utils.create_placeholder_run(
            snapshot=deployment_snapshot,
            logs=None,
            trigger_info=PipelineRunTriggerInfo(
                deployment_id=self.deployment.id,
            ),
        )

        return placeholder_run, deployment_snapshot

    def _execute_with_orchestrator(
        self,
        placeholder_run: PipelineRunResponse,
        deployment_snapshot: PipelineSnapshotResponse,
        resolved_params: Dict[str, Any],
        skip_artifact_materialization: bool,
    ) -> Optional[Dict[str, Dict[str, Any]]]:
        """Run the snapshot via the orchestrator and return the concrete run.

        Args:
            placeholder_run: The placeholder run to execute the pipeline on.
            deployment_snapshot: The deployment snapshot to execute the pipeline
                on.
            resolved_params: Normalized pipeline parameters.
            skip_artifact_materialization: Whether runtime should skip artifact
                materialization.

        Returns:
            The in-memory outputs of the execution.

        Raises:
            RuntimeError: If the orchestrator has not been initialized.
            RuntimeError: If the pipeline cannot be executed.

        """
        active_stack: Stack = self._client.active_stack

        orchestrator = self.orchestrator_class(
            name="deployment-local",
            id=uuid4(),
            config=LocalOrchestratorConfig(),
            flavor="local",
            type=StackComponentType.ORCHESTRATOR,
            user=uuid4(),
            created=datetime.now(),
            updated=datetime.now(),
        )

        # Start deployment runtime context with parameters (still needed for
        # in-memory materializer)
        runtime.start(
            request_id=str(uuid4()),
            snapshot=deployment_snapshot,
            parameters=resolved_params,
            skip_artifact_materialization=skip_artifact_materialization,
        )

        captured_outputs: Optional[Dict[str, Dict[str, Any]]] = None
        try:
            # Use the new deployment snapshot with pre-configured settings
            orchestrator.run(
                snapshot=deployment_snapshot,
                stack=active_stack,
                placeholder_run=placeholder_run,
            )

            # Capture in-memory outputs before stopping the runtime context
            if runtime.is_active():
                captured_outputs = runtime.get_outputs()
        except Exception as e:
            logger.exception(f"Failed to execute pipeline: {e}")
            raise RuntimeError(f"Failed to execute pipeline: {e}")
        finally:
            # Always stop deployment runtime context
            runtime.stop()

        return captured_outputs

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
            with env_utils.temporary_environment(
                self.snapshot.pipeline_configuration.environment
            ):
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
        logger.info(f"   Deployment: {self.deployment.name}")
        logger.info(f"   Pipeline: {pipeline_name}")
        logger.info(f"   Steps: {step_count}")
        logger.info(f"   Stack: {stack_name}")

    def _build_response(
        self,
        resolved_params: Dict[str, Any],
        start_time: float,
        mapped_outputs: Optional[Dict[str, Any]] = None,
        placeholder_run: Optional[PipelineRunResponse] = None,
        error: Optional[Exception] = None,
    ) -> BaseDeploymentInvocationResponse:
        """Build success response with execution tracking.

        Args:
            resolved_params: The resolved parameters.
            start_time: The start time of the execution.
            mapped_outputs: The mapped outputs.
            placeholder_run: The placeholder run that was executed.
            error: The error that occurred.

        Returns:
            A BaseDeploymentInvocationResponse describing the execution.
        """
        execution_time = time.time() - start_time
        self.total_executions += 1
        self.last_execution_time = datetime.now(timezone.utc)

        run: Optional[PipelineRunResponse] = placeholder_run
        if placeholder_run:
            try:
                # Fetch the concrete run via its id
                run = self._client.get_pipeline_run(
                    name_id_or_prefix=placeholder_run.id,
                    hydrate=True,
                    include_full_metadata=True,
                )
            except Exception:
                logger.exception(
                    f"Failed to fetch concrete run: {placeholder_run.id}"
                )
                run = placeholder_run

        return BaseDeploymentInvocationResponse(
            success=(error is None),
            outputs=mapped_outputs,
            error=str(error) if error else None,
            execution_time=execution_time,
            metadata=DeploymentInvocationResponseMetadata(
                deployment_id=self.deployment.id,
                deployment_name=self.deployment.name,
                pipeline_name=self.snapshot.pipeline_configuration.name,
                run_id=run.id if run else None,
                run_name=run.name if run else None,
                parameters_used=resolved_params,
                snapshot_id=self.snapshot.id,
                snapshot_name=self.snapshot.name,
            ),
        )
