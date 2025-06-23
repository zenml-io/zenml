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
    Optional,
    Type,
    cast,
)
from uuid import UUID

from pydantic import model_validator

from zenml.constants import (
    ENV_ZENML_PREVENT_CLIENT_SIDE_CACHING,
    handle_bool_env_var,
)
from zenml.enums import ExecutionStatus, StackComponentType
from zenml.exceptions import RunMonitoringError
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType
from zenml.orchestrators.publish_utils import (
    publish_pipeline_run_metadata,
    publish_schedule_metadata,
)
from zenml.orchestrators.step_launcher import StepLauncher
from zenml.orchestrators.utils import get_config_environment_vars
from zenml.stack import Flavor, Stack, StackComponent, StackComponentConfig
from zenml.utils.pydantic_utils import before_validator_handler

if TYPE_CHECKING:
    from zenml.config.step_configurations import Step
    from zenml.models import PipelineDeploymentResponse, PipelineRunResponse

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


class BaseOrchestrator(StackComponent, ABC):
    """Base class for all orchestrators."""

    _active_deployment: Optional["PipelineDeploymentResponse"] = None

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
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
        environment: Dict[str, str],
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Optional[SubmissionResult]:
        """Submits a pipeline to the orchestrator.

        This method should only submit the pipeline and not wait for it to
        complete. If the orchestrator is configured to wait for the pipeline run
        to complete, a function that waits for the pipeline run to complete can
        be passed as part of the submission result.

        Args:
            deployment: The pipeline deployment to submit.
            stack: The stack the pipeline will run on.
            environment: Environment variables to set in the orchestration
                environment. These don't need to be set if running locally.
            placeholder_run: An optional placeholder run for the deployment.

        Returns:
            Optional submission result.
        """
        return None

    def prepare_or_run_pipeline(
        self,
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
        environment: Dict[str, str],
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Optional[Iterator[Dict[str, MetadataType]]]:
        """DEPRECATED: Prepare or run a pipeline.

        Args:
            deployment: The pipeline deployment to prepare or run.
            stack: The stack the pipeline will run on.
            environment: Environment variables to set in the orchestration
                environment. These don't need to be set if running locally.
            placeholder_run: An optional placeholder run for the deployment.
        """

    def run(
        self,
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> None:
        """Runs a pipeline on a stack.

        Args:
            deployment: The pipeline deployment.
            stack: The stack on which to run the pipeline.
            placeholder_run: An optional placeholder run for the deployment.
                This will be deleted in case the pipeline deployment failed.

        Raises:
            RunMonitoringError: If a failure happened while monitoring the
                pipeline run.
        """
        self._prepare_run(deployment=deployment)

        pipeline_run_id: Optional[UUID] = None
        schedule_id: Optional[UUID] = None
        if deployment.schedule:
            schedule_id = deployment.schedule.id
        if placeholder_run:
            pipeline_run_id = placeholder_run.id

        environment = get_config_environment_vars(
            schedule_id=schedule_id,
            pipeline_run_id=pipeline_run_id,
        )

        prevent_client_side_caching = handle_bool_env_var(
            ENV_ZENML_PREVENT_CLIENT_SIDE_CACHING, default=False
        )

        if (
            placeholder_run
            and self.config.supports_client_side_caching
            and not deployment.schedule
            and not prevent_client_side_caching
        ):
            from zenml.orchestrators import cache_utils

            run_required = (
                cache_utils.create_cached_step_runs_and_prune_deployment(
                    deployment=deployment,
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
                getattr(self.submit_pipeline, "__func__", None)
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
                    deployment=deployment,
                    stack=stack,
                    environment=environment,
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
                submission_result = self.submit_pipeline(
                    deployment=deployment,
                    stack=stack,
                    environment=environment,
                    placeholder_run=placeholder_run,
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
                        elif deployment.schedule:
                            try:
                                publish_schedule_metadata(
                                    schedule_id=deployment.schedule.id,
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
                        except BaseException as e:
                            raise RunMonitoringError(original_exception=e)
        finally:
            self._cleanup_run()

    def run_step(self, step: "Step") -> None:
        """Runs the given step.

        Args:
            step: The step to run.
        """
        assert self._active_deployment
        launcher = StepLauncher(
            deployment=self._active_deployment,
            step=step,
            orchestrator_run_id=self.get_orchestrator_run_id(),
        )
        launcher.launch()

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

    def _prepare_run(self, deployment: "PipelineDeploymentResponse") -> None:
        """Prepares a run.

        Args:
            deployment: The deployment to prepare.
        """
        self._active_deployment = deployment

    def _cleanup_run(self) -> None:
        """Cleans up the active run."""
        self._active_deployment = None

    def fetch_status(self, run: "PipelineRunResponse") -> ExecutionStatus:
        """Refreshes the status of a specific pipeline run.

        Args:
            run: A pipeline run response to fetch its status.

        Raises:
            NotImplementedError: If any orchestrator inheriting from the base
                class does not implement this logic.
        """
        raise NotImplementedError(
            "The fetch status functionality is not implemented for the "
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
