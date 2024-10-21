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
from typing import TYPE_CHECKING, Any, Dict, Iterator, Optional, Type, cast

from pydantic import model_validator

from zenml.constants import (
    ENV_ZENML_PREVENT_CLIENT_SIDE_CACHING,
    handle_bool_env_var,
)
from zenml.enums import ExecutionStatus, StackComponentType
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType
from zenml.orchestrators.publish_utils import publish_pipeline_run_metadata
from zenml.orchestrators.step_launcher import StepLauncher
from zenml.orchestrators.utils import get_config_environment_vars
from zenml.stack import Flavor, Stack, StackComponent, StackComponentConfig
from zenml.utils.pydantic_utils import before_validator_handler

if TYPE_CHECKING:
    from zenml.config.step_configurations import Step
    from zenml.models import PipelineDeploymentResponse, PipelineRunResponse

logger = get_logger(__name__)


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
                    "pipeline (see https://docs.zenml.io/how-to/customize-docker-builds)."
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


class BaseOrchestrator(StackComponent, ABC):
    """Base class for all orchestrators.

    In order to implement an orchestrator you will need to subclass from this
    class.

    How it works:
    -------------
    The `run(...)` method is the entrypoint that is executed when the
    pipeline's run method is called within the user code
    (`pipeline_instance.run(...)`).

    This method will do some internal preparation and then call the
    `prepare_or_run_pipeline(...)` method. BaseOrchestrator subclasses must
    implement this method and either run the pipeline steps directly or deploy
    the pipeline to some remote infrastructure.
    """

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

    @abstractmethod
    def prepare_or_run_pipeline(
        self,
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
        environment: Dict[str, str],
    ) -> Optional[Iterator[Dict[str, MetadataType]]]:
        """The method needs to be implemented by the respective orchestrator.

        Depending on the type of orchestrator you'll have to perform slightly
        different operations.

        Simple Case:
        ------------
        The Steps are run directly from within the same environment in which
        the orchestrator code is executed. In this case you will need to
        deal with implementation-specific runtime configurations (like the
        schedule) and then iterate through the steps and finally call
        `self.run_step(...)` to execute each step.

        Advanced Case:
        --------------
        Most orchestrators will not run the steps directly. Instead, they
        build some intermediate representation of the pipeline that is then
        used to create and run the pipeline and its steps on the target
        environment. For such orchestrators this method will have to build
        this representation and deploy it.

        Regardless of the implementation details, the orchestrator will need
        to run each step in the target environment. For this the
        `self.run_step(...)` method should be used.

        The easiest way to make this work is by using an entrypoint
        configuration to run single steps (`zenml.entrypoints.step_entrypoint_configuration.StepEntrypointConfiguration`)
        or entire pipelines (`zenml.entrypoints.pipeline_entrypoint_configuration.PipelineEntrypointConfiguration`).

        Args:
            deployment: The pipeline deployment to prepare or run.
            stack: The stack the pipeline will run on.
            environment: Environment variables to set in the orchestration
                environment. These don't need to be set if running locally.

        Returns:
            The optional return value from this method will be returned by the
            `pipeline_instance.run()` call when someone is running a pipeline.
        """

    def run(
        self,
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Any:
        """Runs a pipeline on a stack.

        Args:
            deployment: The pipeline deployment.
            stack: The stack on which to run the pipeline.
            placeholder_run: An optional placeholder run for the deployment.
                This will be deleted in case the pipeline deployment failed.
        """
        self._prepare_run(deployment=deployment)

        environment = get_config_environment_vars(deployment=deployment)

        prevent_client_side_caching = handle_bool_env_var(
            ENV_ZENML_PREVENT_CLIENT_SIDE_CACHING, default=False
        )

        if (
            placeholder_run
            and not deployment.schedule
            and not prevent_client_side_caching
        ):
            from zenml.orchestrators import step_run_utils

            cached_invocations = step_run_utils.create_cached_step_runs(
                deployment=deployment,
                pipeline_run=placeholder_run,
                stack=stack,
            )

            for invocation_id in cached_invocations:
                # Remove the cached step invocations from the deployment so
                # the orchestrator does not try to run them
                deployment.step_configurations.pop(invocation_id)

            if len(deployment.step_configurations) == 0:
                # All steps were cached, we update the pipeline run status and
                # don't actually use the orchestrator to run the pipeline
                self._cleanup_run()
                logger.info("All steps of the pipeline run were cached.")
                return

        try:
            if metadata_iterator := self.prepare_or_run_pipeline(
                deployment=deployment,
                stack=stack,
                environment=environment,
            ):
                for metadata_dict in metadata_iterator:
                    try:
                        if placeholder_run:
                            publish_pipeline_run_metadata(
                                pipeline_run_id=placeholder_run.id,
                                pipeline_run_metadata={self.id: metadata_dict},
                            )
                    except Exception as e:
                        logger.debug(
                            "Something went went wrong trying to publish the"
                            f"run metadata: {e}"
                        )
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
