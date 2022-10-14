# Copyright 2019 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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

# The `run_step()` method of this file is a modified version of the local dag
# runner implementation of tfx
"""Base orchestrator class."""
import os
import time
import types
from abc import ABC, abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
    cast,
)

from google.protobuf import json_format
from pydantic import root_validator
from tfx.dsl.compiler.constants import PIPELINE_RUN_ID_PARAMETER_NAME
from tfx.dsl.io.fileio import NotFoundError
from tfx.orchestration import metadata
from tfx.orchestration.local import runner_utils
from tfx.orchestration.portable import (
    data_types,
    launcher,
    outputs_utils,
    runtime_parameter_utils,
)
from tfx.orchestration.portable.base_executor_operator import (
    BaseExecutorOperator,
)
from tfx.orchestration.portable.python_executor_operator import (
    PythonExecutorOperator,
)
from tfx.proto.orchestration import executable_spec_pb2
from tfx.proto.orchestration.pipeline_pb2 import Pipeline as Pb2Pipeline
from tfx.proto.orchestration.pipeline_pb2 import PipelineNode
from tfx.types.artifact import Artifact

from zenml.artifacts.base_artifact import BaseArtifact
from zenml.client import Client
from zenml.config.step_run_info import StepRunInfo
from zenml.enums import StackComponentType
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.orchestrators.utils import get_cache_status
from zenml.stack import Flavor, Stack, StackComponent, StackComponentConfig
from zenml.utils import proto_utils, source_utils, string_utils

if TYPE_CHECKING:
    from zenml.config.pipeline_deployment import PipelineDeployment
    from zenml.config.step_configurations import Step, StepConfiguration

logger = get_logger(__name__)


# TFX PATCH ####################################################################
# The following code patches a function in tfx which leads to an OSError on
# Windows.
def _patched_remove_stateful_working_dir(stateful_working_dir: str) -> None:
    """Deletes the stateful working directory if it exists.

    Args:
        stateful_working_dir: Stateful working directory to delete.
    """
    # The original implementation uses
    # `os.path.abspath(os.path.join(stateful_working_dir, os.pardir))` to
    # compute the parent directory that needs to be deleted. This however
    # doesn't work with our artifact store paths (e.g. s3://my-artifact-store)
    # which would get converted to something like this:
    # /path/to/current/working/directory/s3:/my-artifact-store. In order to
    # avoid that we use `os.path.dirname` instead as the stateful working dir
    # should already be an absolute path anyway.
    stateful_working_dir = os.path.dirname(stateful_working_dir)
    try:
        fileio.rmtree(stateful_working_dir)
    except NotFoundError:
        logger.debug(
            "Unable to find stateful working directory '%s'.",
            stateful_working_dir,
        )


def _patched_remove_output_dirs(output_dict: Dict[str, List[Artifact]]) -> None:
    """Remove dirs of output artifacts' URI.

    Args:
        output_dict: Dictionary of strings to output artifacts.
    """
    # The original implementation was doing a fileio.rmtree
    # without checking for the existence of the object. This
    # caused a cascading failure, and users of ZenML then see
    # an internal TFX error in some cases.
    for _, artifact_list in output_dict.items():
        for artifact in artifact_list:
            if fileio.isdir(artifact.uri):
                fileio.rmtree(artifact.uri)
            elif fileio.exists(artifact.uri):
                fileio.remove(artifact.uri)


assert hasattr(
    outputs_utils, "remove_stateful_working_dir"
), "Unable to find tfx function."
setattr(
    outputs_utils,
    "remove_stateful_working_dir",
    _patched_remove_stateful_working_dir,
)
assert hasattr(
    outputs_utils, "remove_output_dirs"
), "Unable to find tfx function."
setattr(
    outputs_utils,
    "remove_output_dirs",
    _patched_remove_output_dirs,
)


# END OF TFX PATCH #############################################################


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

    # Class Configuration
    TYPE: ClassVar[StackComponentType] = StackComponentType.ORCHESTRATOR
    _active_deployment: Optional["PipelineDeployment"] = None
    _active_pb2_pipeline: Optional[Pb2Pipeline] = None

    @property
    def config(self) -> BaseOrchestratorConfig:
        """Returns the `BaseOrchestratorConfig` config.

        Returns:
            The configuration.
        """
        return cast(BaseOrchestratorConfig, self._config)

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

    def run_step(
        self, step: "Step", run_name: Optional[str] = None
    ) -> Optional[data_types.ExecutionInfo]:
        """This sets up a component launcher and executes the given step.

        Args:
            step: The step to be executed
            run_name: The unique run name

        Returns:
            The execution info of the step.
        """
        assert self._active_deployment
        assert self._active_pb2_pipeline

        self._ensure_artifact_classes_loaded(step.config)

        step_name = step.config.name
        pb2_pipeline = self._active_pb2_pipeline

        run_name = run_name or self._active_deployment.run_name
        # Substitute the runtime parameter to be a concrete run_id, it is
        # important for this to be unique for each run.
        runtime_parameter_utils.substitute_runtime_parameter(
            pb2_pipeline,
            {PIPELINE_RUN_ID_PARAMETER_NAME: run_name},
        )

        # Extract the deployment_configs and use it to access the executor and
        # custom driver spec
        deployment_config = runner_utils.extract_local_deployment_config(
            pb2_pipeline
        )
        executor_spec = runner_utils.extract_executor_spec(
            deployment_config, step_name
        )
        custom_driver_spec = runner_utils.extract_custom_driver_spec(
            deployment_config, step_name
        )

        metadata_connection_cfg = Client().zen_store.get_metadata_config()

        # At this point the active metadata store is queried for the
        # metadata_connection
        stack = Client().active_stack
        executor_operator = self._get_executor_operator(
            step_operator=step.config.step_operator
        )
        custom_executor_operators = {
            executable_spec_pb2.PythonClassExecutableSpec: executor_operator
        }

        step_run_info = StepRunInfo(
            config=step.config,
            pipeline=self._active_deployment.pipeline,
            run_name=run_name,
        )

        # The protobuf node for the current step is loaded here.
        pipeline_node = self._get_node_with_step_name(step_name)

        proto_utils.add_mlmd_contexts(
            pipeline_node=pipeline_node,
            step=step,
            deployment=self._active_deployment,
            stack=stack,
        )

        component_launcher = launcher.Launcher(
            pipeline_node=pipeline_node,
            mlmd_connection=metadata.Metadata(metadata_connection_cfg),
            pipeline_info=pb2_pipeline.pipeline_info,
            pipeline_runtime_spec=pb2_pipeline.runtime_spec,
            executor_spec=executor_spec,
            custom_driver_spec=custom_driver_spec,
            custom_executor_operators=custom_executor_operators,
        )

        # If a step operator is used, the current environment will not be the
        # one executing the step function code and therefore we don't need to
        # run any preparation
        if step.config.step_operator:
            execution_info = self._execute_step(component_launcher)
        else:
            stack.prepare_step_run(info=step_run_info)
            try:
                execution_info = self._execute_step(component_launcher)
            finally:
                stack.cleanup_step_run(info=step_run_info)

        return execution_info

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

        pb2_pipeline = Pb2Pipeline()
        pb2_pipeline_json = string_utils.b64_decode(
            self._active_deployment.proto_pipeline
        )
        json_format.Parse(pb2_pipeline_json, pb2_pipeline)
        self._active_pb2_pipeline = pb2_pipeline

    def _cleanup_run(self) -> None:
        """Cleans up the active run."""
        self._active_deployment = None
        self._active_pb2_pipeline = None

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

    @staticmethod
    def _execute_step(
        tfx_launcher: launcher.Launcher,
    ) -> Optional[data_types.ExecutionInfo]:
        """Executes a tfx component.

        Args:
            tfx_launcher: A tfx launcher to execute the component.

        Returns:
            Optional execution info returned by the launcher.

        Raises:
            RuntimeError: If the execution failed during preparation.
        """
        pipeline_step_name = tfx_launcher._pipeline_node.node_info.id
        start_time = time.time()
        logger.info(f"Step `{pipeline_step_name}` has started.")

        # There is no way to differentiate between a cached and a failed
        # execution based on the execution info returned by the TFX launcher.
        # We patch the _publish_failed_execution method in order to check
        # if an execution failed.
        execution_failed = False
        original_publish_failed_execution = (
            tfx_launcher._publish_failed_execution
        )

        def _new_publish_failed_execution(
            self: launcher.Launcher, *args: Any, **kwargs: Any
        ) -> None:
            original_publish_failed_execution(*args, **kwargs)
            nonlocal execution_failed
            execution_failed = True

        setattr(
            tfx_launcher,
            "_publish_failed_execution",
            types.MethodType(_new_publish_failed_execution, tfx_launcher),
        )
        execution_info = tfx_launcher.launch()
        if execution_failed:
            raise RuntimeError(
                "Failed to execute step. This is probably because some input "
                f"artifacts for the step {pipeline_step_name} could not be "
                "found in the database."
            )

        if execution_info and get_cache_status(execution_info):
            logger.info(f"Using cached version of `{pipeline_step_name}`.")

        run_duration = time.time() - start_time
        logger.info(
            f"Step `{pipeline_step_name}` has finished in "
            f"{string_utils.get_human_readable_time(run_duration)}."
        )
        return execution_info

    @staticmethod
    def _get_executor_operator(
        step_operator: Optional[str],
    ) -> Type[BaseExecutorOperator]:
        """Gets the TFX executor operator for the given step operator.

        Args:
            step_operator: The optional step operator used to run a step.

        Returns:
            The executor operator for the given step operator.
        """
        if step_operator:
            from zenml.step_operators.step_executor_operator import (
                StepExecutorOperator,
            )

            return StepExecutorOperator
        else:
            return PythonExecutorOperator

    def _get_node_with_step_name(self, step_name: str) -> PipelineNode:
        """Given the name of a step, return the node with that name from the pb2_pipeline.

        Args:
            step_name: Name of the step

        Returns:
            PipelineNode instance

        Raises:
            KeyError: If the step name is not found in the pipeline.
        """
        assert self._active_pb2_pipeline

        for node in self._active_pb2_pipeline.nodes:
            if (
                node.WhichOneof("node") == "pipeline_node"
                and node.pipeline_node.node_info.id == step_name
            ):
                return node.pipeline_node

        raise KeyError(
            f"Step {step_name} not found in Pipeline "
            f"{self._active_pb2_pipeline.pipeline_info.id}"
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
