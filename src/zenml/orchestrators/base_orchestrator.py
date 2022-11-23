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
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional, Type, Union, cast
from uuid import UUID

from pydantic import root_validator

from zenml.artifacts.base_artifact import BaseArtifact
from zenml.client import Client
from zenml.config.step_run_info import StepRunInfo
from zenml.enums import ExecutionStatus, StackComponentType
from zenml.logger import get_logger
from zenml.models import PipelineRunModel
from zenml.orchestrators.launcher import Launcher
from zenml.stack import Flavor, Stack, StackComponent, StackComponentConfig
from zenml.utils import source_utils, uuid_utils

if TYPE_CHECKING:
    from zenml.config.pipeline_deployment import PipelineDeployment
    from zenml.config.step_configurations import Step, StepConfiguration

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
                    "pipeline (see https://docs.zenml.io/advanced-guide/pipelines/containerization)."
                )

        return values


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

    _active_deployment: Optional["PipelineDeployment"] = None

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
        deployment: "PipelineDeployment",
        stack: "Stack",
    ) -> Any:
        """This method needs to be implemented by the respective orchestrator.

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

        Returns:
            The optional return value from this method will be returned by the
            `pipeline_instance.run()` call when someone is running a pipeline.
        """

    def run(self, deployment: "PipelineDeployment", stack: "Stack") -> Any:
        """Runs a pipeline on a stack.

        Args:
            deployment: The pipeline deployment.
            stack: The stack on which to run the pipeline.

        Returns:
            Orchestrator-specific return value.
        """
        self._prepare_run(deployment=deployment)

        result = self.prepare_or_run_pipeline(
            deployment=deployment, stack=stack
        )

        self._cleanup_run()

        return result

    def run_step(self, step: "Step") -> None:
        """This sets up a component launcher and executes the given step.

        Args:
            step: The step to be executed

        Returns:
            The execution info of the step.
        """
        assert self._active_deployment

        self._ensure_artifact_classes_loaded(step.config)

        run_model = self._create_or_reuse_run()

        step_run_info = StepRunInfo(
            config=step.config,
            pipeline=self._active_deployment.pipeline,
            run_name=run_model.name,
        )

        stack = Client().active_stack

        step_name = [
            name
            for name, s in self._active_deployment.steps.items()
            if s.config.name == step.config.name
        ][0]
        launcher = Launcher(
            step=step,
            step_name=step_name,
            run_name=run_model.name,
            pipeline_config=self._active_deployment.pipeline,
            stack=stack,
        )

        # If a step operator is used, the current environment will not be the
        # one executing the step function code and therefore we don't need to
        # run any preparation
        if step.config.step_operator:
            ...  # TODO
        else:
            stack.prepare_step_run(info=step_run_info)
            try:
                launcher.launch()
            except:  # noqa: E722

                self._publish_failed_run(run_name_or_id=run_model.name)
                raise
            finally:
                stack.cleanup_step_run(info=step_run_info)

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

    def _prepare_run(self, deployment: "PipelineDeployment") -> None:
        """Prepares a run.

        Args:
            deployment: The deployment to prepare.
        """
        self._active_deployment = deployment

    def _cleanup_run(self) -> None:
        """Cleans up the active run."""
        self._active_deployment = None
        self._active_pb2_pipeline = None

    def get_run_id_for_orchestrator_run_id(
        self, orchestrator_run_id: str
    ) -> UUID:
        """Generates a run ID from an orchestrator run id.

        Args:
            orchestrator_run_id: The orchestrator run id.

        Returns:
            The run id generated from the orchestrator run id.
        """
        run_id_seed = f"{self.id}-{orchestrator_run_id}"
        return uuid_utils.generate_uuid_from_string(run_id_seed)

    def _create_or_reuse_run(self) -> PipelineRunModel:
        """Creates a run or reuses an existing one.

        Returns:
            The created or existing run.
        """
        assert self._active_deployment
        orchestrator_run_id = self.get_orchestrator_run_id()

        run_id = self.get_run_id_for_orchestrator_run_id(orchestrator_run_id)

        date = datetime.now().strftime("%Y_%m_%d")
        time = datetime.now().strftime("%H_%M_%S_%f")
        run_name = self._active_deployment.run_name.format(date=date, time=time)

        logger.debug("Creating run with ID: %s, name: %s", run_id, run_name)

        client = Client()
        run_model = PipelineRunModel(
            id=run_id,
            name=run_name,
            orchestrator_run_id=orchestrator_run_id,
            user=client.active_user.id,
            project=client.active_project.id,
            stack_id=self._active_deployment.stack_id,
            pipeline_id=self._active_deployment.pipeline_id,
            enable_cache=self._active_deployment.pipeline.enable_cache,
            status=ExecutionStatus.RUNNING,
            pipeline_configuration=self._active_deployment.pipeline.dict(),
            num_steps=len(self._active_deployment.steps),
        )

        return client.zen_store.get_or_create_run(run_model)

    @staticmethod
    def _publish_failed_run(run_name_or_id: Union[str, UUID]) -> None:
        """Set run status to failed.

        Args:
            run_name_or_id: The name or ID of the run that failed.
        """
        client = Client()
        run = client.zen_store.get_run(run_name_or_id)
        run.status = ExecutionStatus.FAILED
        client.zen_store.update_run(run)

    # TODO: probably can remove this
    @staticmethod
    def _ensure_artifact_classes_loaded(
        step_configuration: "StepConfiguration",
    ) -> None:
        """Ensures that all artifact classes for a step are loaded.

        Args:
            step_configuration: A step configuration.
        """
        artifact_class_sources = set(
            input_.artifact_source
            for input_ in step_configuration.inputs.values()
        ) | set(
            output.artifact_source
            for output in step_configuration.outputs.values()
        )

        for source in artifact_class_sources:
            # Tfx depends on these classes being loaded so it can detect the
            # correct artifact class
            source_utils.validate_source_class(
                source, expected_class=BaseArtifact
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
