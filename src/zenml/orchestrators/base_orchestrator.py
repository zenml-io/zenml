#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Base orchestrator class."""

from abc import ABC, abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    cast,
)
from uuid import UUID

from pydantic import model_validator

from zenml.constants import (
    ENV_ZENML_PREVENT_CLIENT_SIDE_CACHING,
    handle_bool_env_var,
)
from zenml.enums import ExecutionMode, ExecutionStatus, StackComponentType
from zenml.exceptions import (
    HookExecutionException,
    IllegalOperationError,
    RunMonitoringError,
)
from zenml.hooks.hook_validators import load_and_run_hook
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType
from zenml.orchestrators.publish_utils import (
    publish_pipeline_run_metadata,
    publish_pipeline_run_status_update,
    publish_schedule_metadata,
)
from zenml.orchestrators.utils import get_config_environment_vars
from zenml.stack import Flavor, Stack, StackComponent, StackComponentConfig
from zenml.steps.step_context import RunContext, get_or_create_run_context
from zenml.utils.env_utils import temporary_environment
from zenml.utils.pydantic_utils import before_validator_handler

if TYPE_CHECKING:
    from zenml.config.step_configurations import Step
    from zenml.config.step_run_info import StepRunInfo
    from zenml.models import (
        PipelineRunResponse,
        PipelineSnapshotResponse,
        ScheduleResponse,
        ScheduleUpdate,
    )

logger = get_logger(__name__)


class SubmissionResult:
    """Result of submitting a pipeline run."""

    def __init__(
        self,
        wait_for_completion: Optional[Callable[[], None]] = None,
        metadata: Optional[Dict[str, MetadataType]] = None,
    ):
        """Initialize a submission result.

        Args:
            wait_for_completion: A function that waits for the pipeline run to
                complete. If provided, this will be called after the pipeline
                run was submitted successfully.
            metadata: Metadata for the pipeline run or schedule.
        """
        self.wait_for_completion = wait_for_completion
        self.metadata = metadata


class BaseOrchestratorConfig(StackComponentConfig):
    """Base orchestrator config."""

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def _deprecations(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and/or remove deprecated fields.

        Args:
            data: The values to validate.

        Returns:
            The validated values.
        """
        if "custom_docker_base_image_name" in data:
            image_name = data.pop("custom_docker_base_image_name", None)
            if image_name:
                logger.warning(
                    "The 'custom_docker_base_image_name' field has been "
                    "deprecated. To use a custom base container image with your "
                    "orchestrators, please use the DockerSettings in your "
                    "pipeline (see https://docs.zenml.io/concepts/containerization)."
                )

        return data

    @property
    def is_synchronous(self) -> bool:
        """Whether the orchestrator runs synchronous or not.

        Returns:
            Whether the orchestrator runs synchronous or not.
        """
        return False

    @property
    def is_schedulable(self) -> bool:
        """Whether the orchestrator is schedulable or not.

        Returns:
            Whether the orchestrator is schedulable or not.
        """
        return False

    @property
    def supports_client_side_caching(self) -> bool:
        """Whether the orchestrator supports client side caching.

        Returns:
            Whether the orchestrator supports client side caching.
        """
        return True

    @property
    def handles_step_retries(self) -> bool:
        """Whether the orchestrator handles step retries.

        Returns:
            Whether the orchestrator handles step retries.
        """
        return False


class BaseOrchestrator(StackComponent, ABC):
    """Base class for all orchestrators."""

    _active_snapshot: Optional["PipelineSnapshotResponse"] = None

    @property
    def config(self) -> BaseOrchestratorConfig:
        """Returns the `BaseOrchestratorConfig` config.

        Returns:
            The configuration.
        """
        return cast(BaseOrchestratorConfig, self._config)

    @abstractmethod
    def get_orchestrator_run_id(self) -> str:
        """Returns the run id of the active orchestrator run.

        Important: This needs to be a unique ID and return the same value for
        all steps of a pipeline run.

        Returns:
            The orchestrator run id.
        """

    def submit_pipeline(
        self,
        snapshot: "PipelineSnapshotResponse",
        stack: "Stack",
        base_environment: Dict[str, str],
        step_environments: Dict[str, Dict[str, str]],
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Optional[SubmissionResult]:
        """Submits a pipeline to the orchestrator.

        This method should only submit the pipeline and not wait for it to
        complete. If the orchestrator is configured to wait for the pipeline run
        to complete, a function that waits for the pipeline run to complete can
        be passed as part of the submission result.

        Args:
            snapshot: The pipeline snapshot to submit.
            stack: The stack the pipeline will run on.
            base_environment: Base environment shared by all steps. This should
                be set if your orchestrator for example runs one container that
                is responsible for starting all the steps.
            step_environments: Environment variables to set when executing
                specific steps.
            placeholder_run: An optional placeholder run for the snapshot.

        Returns:
            Optional submission result.
        """
        return None

    def submit_dynamic_pipeline(
        self,
        snapshot: "PipelineSnapshotResponse",
        stack: "Stack",
        environment: Dict[str, str],
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Optional[SubmissionResult]:
        """Submits a dynamic pipeline to the orchestrator.

        Args:
            snapshot: The pipeline snapshot to submit.
            stack: The stack the pipeline will run on.
            environment: Environment variables to set in the orchestration
                environment.
            placeholder_run: An optional placeholder run.

        Returns:
            Optional submission result.
        """
        return None

    def prepare_or_run_pipeline(
        self,
        deployment: "PipelineSnapshotResponse",
        stack: "Stack",
        environment: Dict[str, str],
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Optional[Iterator[Dict[str, MetadataType]]]:
        """DEPRECATED: Prepare or run a pipeline.

        Args:
            deployment: The deployment to prepare or run.
            stack: The stack the pipeline will run on.
            environment: Environment variables to set in the orchestration
                environment. These don't need to be set if running locally.
            placeholder_run: An optional placeholder run for the deployment.
        """

    def run(
        self,
        snapshot: "PipelineSnapshotResponse",
        stack: "Stack",
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> None:
        """Runs a pipeline on a stack.

        Args:
            snapshot: The pipeline snapshot.
            stack: The stack on which to run the pipeline.
            placeholder_run: An optional placeholder run for the snapshot.
                This will be deleted in case the pipeline run failed.

        Raises:
            RunMonitoringError: If a failure happened while monitoring the
                pipeline run.
        """
        self._prepare_run(snapshot=snapshot)

        pipeline_run_id: Optional[UUID] = None
        schedule_id: Optional[UUID] = None
        if snapshot.schedule:
            schedule_id = snapshot.schedule.id
        if placeholder_run:
            pipeline_run_id = placeholder_run.id

        base_environment, secrets = get_config_environment_vars(
            schedule_id=schedule_id,
            pipeline_run_id=pipeline_run_id,
        )

        # TODO: for now, we don't support separate secrets from environment
        # in the orchestrator environment
        base_environment.update(secrets)

        prevent_client_side_caching = handle_bool_env_var(
            ENV_ZENML_PREVENT_CLIENT_SIDE_CACHING, default=False
        )

        if (
            placeholder_run
            and self.config.supports_client_side_caching
            and not snapshot.schedule
            and not snapshot.is_dynamic
            and not prevent_client_side_caching
        ):
            from zenml.orchestrators import cache_utils

            run_required = (
                cache_utils.create_cached_step_runs_and_prune_snapshot(
                    snapshot=snapshot,
                    pipeline_run=placeholder_run,
                    stack=stack,
                )
            )

            if not run_required:
                self._cleanup_run()
                return
        else:
            logger.debug("Skipping client-side caching.")

        try:
            if (
                not snapshot.is_dynamic
                and getattr(self.submit_pipeline, "__func__", None)
                is BaseOrchestrator.submit_pipeline
            ):
                logger.warning(
                    "The orchestrator '%s' is still using the deprecated "
                    "`prepare_or_run_pipeline(...)` method which will be "
                    "removed in the future. Please implement the replacement "
                    "`submit_pipeline(...)` method for your custom "
                    "orchestrator.",
                    self.name,
                )
                if metadata_iterator := self.prepare_or_run_pipeline(
                    deployment=snapshot,
                    stack=stack,
                    environment=base_environment,
                    placeholder_run=placeholder_run,
                ):
                    for metadata_dict in metadata_iterator:
                        try:
                            if placeholder_run:
                                publish_pipeline_run_metadata(
                                    pipeline_run_id=placeholder_run.id,
                                    pipeline_run_metadata={
                                        self.id: metadata_dict
                                    },
                                )
                        except Exception as e:
                            logger.debug(
                                "Something went went wrong trying to publish the"
                                f"run metadata: {e}"
                            )
            else:
                if snapshot.is_dynamic:
                    submission_result = self.submit_dynamic_pipeline(
                        snapshot=snapshot,
                        stack=stack,
                        environment=base_environment,
                        placeholder_run=placeholder_run,
                    )
                else:
                    step_environments = {}
                    for (
                        invocation_id,
                        step,
                    ) in snapshot.step_configurations.items():
                        from zenml.utils.env_utils import get_step_environment

                        step_environment = get_step_environment(
                            step_config=step.config,
                            stack=stack,
                        )

                        combined_environment = base_environment.copy()
                        combined_environment.update(step_environment)
                        step_environments[invocation_id] = combined_environment

                    submission_result = self.submit_pipeline(
                        snapshot=snapshot,
                        stack=stack,
                        base_environment=base_environment,
                        step_environments=step_environments,
                        placeholder_run=placeholder_run,
                    )
                if placeholder_run:
                    publish_pipeline_run_status_update(
                        pipeline_run_id=placeholder_run.id,
                        status=ExecutionStatus.PROVISIONING,
                    )

                if submission_result:
                    if submission_result.metadata:
                        if placeholder_run:
                            try:
                                publish_pipeline_run_metadata(
                                    pipeline_run_id=placeholder_run.id,
                                    pipeline_run_metadata={
                                        self.id: submission_result.metadata
                                    },
                                )
                            except Exception as e:
                                logger.debug(
                                    "Error publishing run metadata: %s", e
                                )
                        elif snapshot.schedule:
                            try:
                                publish_schedule_metadata(
                                    schedule_id=snapshot.schedule.id,
                                    schedule_metadata={
                                        self.id: submission_result.metadata
                                    },
                                )
                            except Exception as e:
                                logger.debug(
                                    "Error publishing schedule metadata: %s", e
                                )

                    if submission_result.wait_for_completion:
                        try:
                            submission_result.wait_for_completion()
                        except KeyboardInterrupt as e:
                            message = (
                                "Run monitoring interrupted, but "
                                "the pipeline is still executing."
                            )
                            if placeholder_run:
                                message += (
                                    " If you want to stop the run, use: `zenml "
                                    f"pipeline runs stop {placeholder_run.id}`"
                                )
                            # TODO: once we don't support Python 3.10 anymore,
                            # use `exception.add_note` instead.
                            e.args = (message,)
                            raise RunMonitoringError(original_exception=e)
                        except BaseException as e:
                            raise RunMonitoringError(original_exception=e)

        finally:
            self._cleanup_run()

    def run_step(
        self,
        step: "Step",
    ) -> None:
        """Runs the given step.

        Args:
            step: The step to run.
        """
        from zenml.execution.step.utils import launch_step

        assert self._active_snapshot

        launch_step(
            snapshot=self._active_snapshot,
            step=step,
            orchestrator_run_id=self.get_orchestrator_run_id(),
            retry=not self.config.handles_step_retries,
        )

    @property
    def supports_dynamic_pipelines(self) -> bool:
        """Whether the orchestrator supports dynamic pipelines.

        Returns:
            Whether the orchestrator supports dynamic pipelines.
        """
        return (
            getattr(self.submit_dynamic_pipeline, "__func__", None)
            is not BaseOrchestrator.submit_dynamic_pipeline
        )

    @property
    def can_run_isolated_steps(self) -> bool:
        """Whether the orchestrator can run isolated steps.

        Returns:
            Whether the orchestrator can run isolated steps.
        """
        return (
            getattr(self.run_isolated_step, "__func__", None)
            is not BaseOrchestrator.run_isolated_step
        )

    def run_isolated_step(
        self, step_run_info: "StepRunInfo", environment: Dict[str, str]
    ) -> None:
        """Run an isolated step.

        Args:
            step_run_info: The step run information.
            environment: The environment variables to set in the execution
                environment.

        Raises:
            NotImplementedError: If the orchestrator does not implement this
                method.
        """
        raise NotImplementedError(
            "Running isolated steps is not implemented for "
            f"the {self.__class__.__name__} orchestrator."
        )

    @staticmethod
    def requires_resources_in_orchestration_environment(
        step: "Step",
    ) -> bool:
        """Checks if the orchestrator should run this step on special resources.

        Args:
            step: The step that will be checked.

        Returns:
            True if the step requires special resources in the orchestration
            environment, False otherwise.
        """
        # If the step requires custom resources and doesn't run with a step
        # operator, it would need these requirements in the orchestrator
        # environment
        if step.config.step_operator:
            return False

        return not step.config.resource_settings.empty

    def _prepare_run(self, snapshot: "PipelineSnapshotResponse") -> None:
        """Prepares a run.

        Args:
            snapshot: The snapshot to prepare.
        """
        self._validate_execution_mode(snapshot)
        self._active_snapshot = snapshot

    def _cleanup_run(self) -> None:
        """Cleans up the active run."""
        self._active_snapshot = None

    @property
    def supported_execution_modes(self) -> List[ExecutionMode]:
        """Returns the supported execution modes for this flavor.

        Returns:
            A tuple of supported execution modes.
        """
        return [ExecutionMode.CONTINUE_ON_FAILURE]

    @property
    def run_init_cleanup_at_step_level(self) -> bool:
        """Whether the orchestrator runs the init and cleanup hooks at step level.

        For orchestrators that run their steps in isolated step environments,
        the run context cannot be shared between steps. In this case, the init
        and cleanup hooks need to be run at step level for each individual step.

        For orchestrators that run their steps in a shared environment with a
        shared memory (e.g. the local orchestrator), the init and cleanup hooks
        can be run at run level and this property should be overridden to return
        True.

        Returns:
            Whether the orchestrator runs the init and cleanup hooks at step
            level.
        """
        return True

    @classmethod
    def run_init_hook(cls, snapshot: "PipelineSnapshotResponse") -> None:
        """Runs the init hook.

        Args:
            snapshot: The snapshot to run the init hook for.

        Raises:
            HookExecutionException: If the init hook fails.
        """
        # The lifetime of the run context starts when the init hook is executed
        # and ends when the cleanup hook is executed
        run_context = get_or_create_run_context()
        init_hook_source = snapshot.pipeline_configuration.init_hook_source
        init_hook_kwargs = snapshot.pipeline_configuration.init_hook_kwargs

        # We only run the init hook once, if the (thread-local) run context
        # associated with the current run has not been initialized yet. This
        # allows us to run the init hook only once per run per execution
        # environment (process, container, etc.).
        if not run_context.initialized:
            if not init_hook_source:
                run_context.initialize(None)
                return

            logger.info("Executing the pipeline's init hook...")
            try:
                with temporary_environment(
                    snapshot.pipeline_configuration.environment
                ):
                    run_state = load_and_run_hook(
                        init_hook_source,
                        hook_parameters=init_hook_kwargs,
                        raise_on_error=True,
                    )
            except Exception as e:
                raise HookExecutionException(
                    f"Failed to execute init hook for pipeline "
                    f"{snapshot.pipeline_configuration.name}"
                ) from e

            run_context.initialize(run_state)

    @classmethod
    def run_cleanup_hook(cls, snapshot: "PipelineSnapshotResponse") -> None:
        """Runs the cleanup hook.

        Args:
            snapshot: The snapshot to run the cleanup hook for.
        """
        # The lifetime of the run context starts when the init hook is executed
        # and ends when the cleanup hook is executed
        if not RunContext._exists():
            return

        if (
            cleanup_hook_source
            := snapshot.pipeline_configuration.cleanup_hook_source
        ):
            logger.info("Executing the pipeline's cleanup hook...")
            with temporary_environment(
                snapshot.pipeline_configuration.environment
            ):
                load_and_run_hook(
                    cleanup_hook_source,
                    raise_on_error=False,
                )

        # Destroy the run context, so it's created anew for the next run
        RunContext._clear()

    def _validate_execution_mode(
        self, snapshot: "PipelineSnapshotResponse"
    ) -> None:
        """Validate that the requested execution mode is supported.

        Args:
            snapshot: The snapshot to validate.

        Raises:
            ValueError: If the execution mode is not supported.
        """
        execution_mode = snapshot.pipeline_configuration.execution_mode

        if execution_mode not in self.supported_execution_modes:
            raise ValueError(
                f"Execution mode {execution_mode} is not supported by the "
                f"{self.__class__.__name__} orchestrator."
            )

    def fetch_status(
        self, run: "PipelineRunResponse", include_steps: bool = False
    ) -> Tuple[
        Optional[ExecutionStatus], Optional[Dict[str, ExecutionStatus]]
    ]:
        """Refreshes the status of a specific pipeline run.

        Args:
            run: A pipeline run response to fetch its status.
            include_steps: If True, also fetch the status of individual steps.

        Raises:
            NotImplementedError: If any orchestrator inheriting from the base
                class does not implement this logic.
        """
        raise NotImplementedError(
            "The fetch status functionality is not implemented for the "
            f"'{self.__class__.__name__}' orchestrator."
        )

    def stop_run(
        self, run: "PipelineRunResponse", graceful: bool = False
    ) -> None:
        """Stops a specific pipeline run.

        This method should only be called if the orchestrator's
        supports_cancellation property is True.

        Args:
            run: A pipeline run response to stop.
            graceful: If True, allows for graceful shutdown where possible.
                If False, forces immediate termination. Default is False.

        Raises:
            NotImplementedError: If any orchestrator inheriting from the base
                class does not implement this logic.
            IllegalOperationError: If the run has no orchestrator run id yet.
        """
        # Check if the orchestrator supports cancellation
        if (
            getattr(self._stop_run, "__func__", None)
            is BaseOrchestrator._stop_run
        ):
            raise NotImplementedError(
                f"The '{self.__class__.__name__}' orchestrator does not "
                "support stopping pipeline runs."
            )

        if not run.orchestrator_run_id:
            raise IllegalOperationError(
                "Cannot stop a pipeline run that has no orchestrator run id "
                "yet."
            )

        # Update pipeline status to STOPPING before calling concrete implementation
        publish_pipeline_run_status_update(
            pipeline_run_id=run.id,
            status=ExecutionStatus.STOPPING,
            status_reason="Manual stop requested.",
        )

        # Now call the concrete implementation
        self._stop_run(run=run, graceful=graceful)

    def _stop_run(
        self, run: "PipelineRunResponse", graceful: bool = False
    ) -> None:
        """Concrete implementation of pipeline stopping logic.

        This method should be implemented by concrete orchestrator classes
        instead of stop_run to ensure proper status management.

        Args:
            run: A pipeline run response to stop (already updated to STOPPING status).
            graceful: If True, allows for graceful shutdown where possible.
                If False, forces immediate termination. Default is True.

        Raises:
            NotImplementedError: If any orchestrator inheriting from the base
                class does not implement this logic.
        """
        raise NotImplementedError(
            "The stop run functionality is not implemented for the "
            f"'{self.__class__.__name__}' orchestrator."
        )

    @property
    def supports_schedule_updates(self) -> bool:
        """Whether the orchestrator supports updating schedules.

        Returns:
            Whether the orchestrator supports updating schedules.
        """
        return (
            getattr(self.update_schedule, "__func__", None)
            is not BaseOrchestrator.update_schedule
        )

    @property
    def supports_schedule_deletion(self) -> bool:
        """Whether the orchestrator supports deleting schedules.

        Returns:
            Whether the orchestrator supports deleting schedules.
        """
        return (
            getattr(self.delete_schedule, "__func__", None)
            is not BaseOrchestrator.delete_schedule
        )

    def update_schedule(
        self, schedule: "ScheduleResponse", update: "ScheduleUpdate"
    ) -> None:
        """Updates a schedule.

        Args:
            schedule: The schedule to update.
            update: The update to apply to the schedule.

        Raises:
            NotImplementedError: If the functionality is not implemented.
        """
        raise NotImplementedError(
            "Schedule updating is not implemented for the "
            f"'{self.__class__.__name__}' orchestrator."
        )

    def delete_schedule(self, schedule: "ScheduleResponse") -> None:
        """Deletes a schedule.

        Args:
            schedule: The schedule to delete.

        Raises:
            NotImplementedError: If the functionality is not implemented.
        """
        raise NotImplementedError(
            "Schedule deletion is not implemented for the "
            f"'{self.__class__.__name__}' orchestrator."
        )


class BaseOrchestratorFlavor(Flavor):
    """Base orchestrator flavor class."""

    @property
    def type(self) -> StackComponentType:
        """Returns the flavor type.

        Returns:
            The flavor type.
        """
        return StackComponentType.ORCHESTRATOR

    @property
    def config_class(self) -> Type[BaseOrchestratorConfig]:
        """Config class for the base orchestrator flavor.

        Returns:
            The config class.
        """
        return BaseOrchestratorConfig

    @property
    @abstractmethod
    def implementation_class(self) -> Type["BaseOrchestrator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
