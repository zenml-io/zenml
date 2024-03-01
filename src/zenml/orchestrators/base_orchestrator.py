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
from typing import TYPE_CHECKING, Any, Dict, Optional, Type, cast

from pydantic import root_validator

from zenml.enums import StackComponentType
from zenml.logger import get_logger
from zenml.orchestrators.step_launcher import StepLauncher
from zenml.orchestrators.utils import get_config_environment_vars
from zenml.stack import Flavor, Stack, StackComponent, StackComponentConfig

if TYPE_CHECKING:
    from zenml.config.step_configurations import Step
    from zenml.models import PipelineDeploymentResponse

logger = get_logger(__name__)


class BaseOrchestratorConfig(StackComponentConfig):
    """Base orchestrator config."""

    @root_validator(pre=True)
    def _deprecations(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and/or remove deprecated fields.

        Args:
            values: The values to validate.

        Returns:
            The validated values.
        """
        if "custom_docker_base_image_name" in values:
            image_name = values.pop("custom_docker_base_image_name", None)
            if image_name:
                logger.warning(
                    "The 'custom_docker_base_image_name' field has been "
                    "deprecated. To use a custom base container image with your "
                    "orchestrators, please use the DockerSettings in your "
                    "pipeline (see https://docs.zenml.io/user-guide/advanced-guide/environment-management/containerize-your-pipeline)."
                )

        return values

    @property
    def is_synchronous(self) -> bool:
        """Whether the orchestrator runs synchronous or not.

        Returns:
            Whether the orchestrator runs synchronous or not.
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
    ) -> Any:
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
    ) -> Any:
        """Runs a pipeline on a stack.

        Args:
            deployment: The pipeline deployment.
            stack: The stack on which to run the pipeline.

        Returns:
            Orchestrator-specific return value.
        """
        self._prepare_run(deployment=deployment)

        environment = get_config_environment_vars(deployment=deployment)

        try:
            result = self.prepare_or_run_pipeline(
                deployment=deployment, stack=stack, environment=environment
            )
        finally:
            self._cleanup_run()

        return result

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
