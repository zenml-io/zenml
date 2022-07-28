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

import hashlib
import json
import os
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, List, Optional

from pydantic.json import pydantic_encoder
from tfx.dsl.compiler.compiler import Compiler
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
from tfx.proto.orchestration import executable_spec_pb2
from tfx.proto.orchestration.pipeline_pb2 import Pipeline as Pb2Pipeline
from tfx.proto.orchestration.pipeline_pb2 import PipelineNode

from zenml.constants import (
    MLMD_CONTEXT_PIPELINE_REQUIREMENTS_PROPERTY_NAME,
    MLMD_CONTEXT_RUNTIME_CONFIG_PROPERTY_NAME,
    MLMD_CONTEXT_STACK_PROPERTY_NAME,
    MLMD_CONTEXT_STEP_RESOURCES_PROPERTY_NAME,
    ZENML_MLMD_CONTEXT_TYPE,
)
from zenml.enums import StackComponentType
from zenml.exceptions import DuplicateRunNameError
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.orchestrators.utils import (
    add_context_to_node,
    create_tfx_pipeline,
    get_cache_status,
    get_step_for_node,
)
from zenml.repository import Repository
from zenml.stack import StackComponent
from zenml.steps import BaseStep
from zenml.utils import string_utils

if TYPE_CHECKING:
    from zenml.pipelines import BasePipeline
    from zenml.runtime_configuration import RuntimeConfiguration
    from zenml.stack import Stack

logger = get_logger(__name__)


### TFX PATCH
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


assert hasattr(
    outputs_utils, "remove_stateful_working_dir"
), "Unable to find tfx function."
setattr(
    outputs_utils,
    "remove_stateful_working_dir",
    _patched_remove_stateful_working_dir,
)
### END OF TFX PATCH


class BaseOrchestrator(StackComponent, ABC):
    """Base class for all orchestrators.

    In order to implement an orchestrator you will need to subclass from this
    class.

    How it works:
    -------------
    The `run()` method is the entrypoint that is executed when the
    pipeline's run method is called within the user code
    (`pipeline_instance.run()`).

    This method will take the ZenML Pipeline instance and prepare it for
    eventual execution. To do this the following steps are taken:

    * The underlying protobuf pipeline is created.

    * Within the `_configure_node_context()` method the pipeline
    requirements, stack and runtime configuration is added to the step
    context

    * The `_get_sorted_steps()` method then generates a sorted list of
    steps which will later be used to directly execute these steps in order,
    or to easily build a dag

    * After these initial steps comes the most crucial one. Within the
    `prepare_or_run_pipeline()` method each orchestrator will have its own
    implementation that dictates the pipeline orchestration. In the simplest
    case this method will iterate through all steps and execute them one by
    one. In other cases this method will build and deploy an intermediate
    representation of the pipeline (e.g an airflow dag or a kubeflow
    pipelines yaml) to be executed within the orchestrators environment.

    Building your own:
    ------------------
    In order to build your own orchestrator, all you need to do is subclass
    from this class and implement your own `prepare_or_run_pipeline()`
    method. Overwriting other methods is NOT recommended but possible.
    See the docstring of the `prepare_or_run_pipeline()` method to find out
    details of what needs to be implemented within it.
    """

    # Class Configuration
    TYPE: ClassVar[StackComponentType] = StackComponentType.ORCHESTRATOR

    @abstractmethod
    def prepare_or_run_pipeline(
        self,
        sorted_steps: List[BaseStep],
        pipeline: "BasePipeline",
        pb2_pipeline: Pb2Pipeline,
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> Any:
        """This method needs to be implemented by the respective orchestrator.

        Depending on the type of orchestrator you'll have to perform slightly
        different operations.

        Simple Case:
        ------------
        The Steps are run directly from within the same environment in which
        the orchestrator code is executed. In this case you will need to
        deal with implementation-specific runtime configurations (like the
        schedule) and then iterate through each step and finally call
        `self.run_step()` to execute each step.

        Advanced Case:
        --------------
        Most orchestrators will not run the steps directly. Instead, they
        build some intermediate representation of the pipeline that is then
        used to create and run the pipeline and its steps on the target
        environment. For such orchestrators this method will have to build
        this representation and either deploy it directly or return it.

        Regardless of the implementation details, the orchestrator will need
        to a way to trigger each step in the target environment. For this
        the `run_step()` method should be used.

        In case the orchestrator is using docker containers for orchestration
        of each step, the `zenml.entrypoints.step_entrypoint` module can be
        used as a generalized entrypoint that sets up all the necessary
        prerequisites, parses input parameters and finally executes the step
        using the `run_step()`method.

        If the orchestrator needs to know the upstream steps for a specific
        step to build a DAG, it can use the `get_upstream_step_names()` method
        to get them.

        Args:
            sorted_steps: List of sorted steps.
            pipeline: Zenml Pipeline instance.
            pb2_pipeline: Protobuf Pipeline instance.
            stack: The stack the pipeline was run on.
            runtime_configuration: The Runtime configuration of the current run.

        Returns:
            The optional return value from this method will be returned by the
            `pipeline_instance.run()` call when someone is running a pipeline.
        """

    def run(
        self,
        pipeline: "BasePipeline",
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> Any:
        """Runs a pipeline.

        To do this, a protobuf pipeline is created, the context of the
        individual steps is expanded to include relevant data, the steps are
        sorted into execution order and the implementation specific
        `prepare_or_run_pipeline()` method is called.

        Args:
            pipeline: The pipeline to run.
            stack: The stack on which the pipeline is run.
            runtime_configuration: Runtime configuration of the pipeline run.

        Returns:
            The result of the call to `prepare_or_run_pipeline()`.
        """
        # Create the protobuf pipeline which will be needed for various reasons
        # in the following steps
        pb2_pipeline: Pb2Pipeline = Compiler().compile(
            create_tfx_pipeline(pipeline, stack=stack)
        )

        self._configure_node_context(
            pipeline=pipeline,
            pb2_pipeline=pb2_pipeline,
            stack=stack,
            runtime_configuration=runtime_configuration,
        )

        sorted_steps = self._get_sorted_steps(
            pipeline=pipeline, pb2_pipeline=pb2_pipeline
        )

        result = self.prepare_or_run_pipeline(
            sorted_steps=sorted_steps,
            pipeline=pipeline,
            pb2_pipeline=pb2_pipeline,
            stack=stack,
            runtime_configuration=runtime_configuration,
        )

        return result

    @staticmethod
    def _get_sorted_steps(
        pipeline: "BasePipeline", pb2_pipeline: Pb2Pipeline
    ) -> List["BaseStep"]:
        """Get steps sorted in the execution order.

        This simplifies the building of a DAG at a later stage as it can be
        built with one iteration over this sorted list of steps.

        Args:
            pipeline: The pipeline
            pb2_pipeline: The protobuf pipeline representation

        Returns:
            List of steps in execution order
        """
        # Create a list of sorted steps
        sorted_steps = []
        for node in pb2_pipeline.nodes:
            pipeline_node: PipelineNode = node.pipeline_node
            sorted_steps.append(
                get_step_for_node(
                    pipeline_node, steps=list(pipeline.steps.values())
                )
            )
        return sorted_steps

    def run_step(
        self,
        step: "BaseStep",
        run_name: str,
        pb2_pipeline: Pb2Pipeline,
    ) -> Optional[data_types.ExecutionInfo]:
        """This sets up a component launcher and executes the given step.

        Args:
            step: The step to be executed
            run_name: The unique run name
            pb2_pipeline: Protobuf Pipeline instance

        Returns:
            The execution info of the step.
        """
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
            deployment_config, step.name
        )
        custom_driver_spec = runner_utils.extract_custom_driver_spec(
            deployment_config, step.name
        )

        # At this point the active metadata store is queried for the
        # metadata_connection
        repo = Repository()
        metadata_store = repo.active_stack.metadata_store
        metadata_connection = metadata.Metadata(
            metadata_store.get_tfx_metadata_config()
        )
        custom_executor_operators = {
            executable_spec_pb2.PythonClassExecutableSpec: step.executor_operator
        }

        # The protobuf node for the current step is loaded here.
        pipeline_node = self._get_node_with_step_name(
            step_name=step.name, pb2_pipeline=pb2_pipeline
        )

        # Create the tfx launcher responsible for executing the step.
        component_launcher = launcher.Launcher(
            pipeline_node=pipeline_node,
            mlmd_connection=metadata_connection,
            pipeline_info=pb2_pipeline.pipeline_info,
            pipeline_runtime_spec=pb2_pipeline.runtime_spec,
            executor_spec=executor_spec,
            custom_driver_spec=custom_driver_spec,
            custom_executor_operators=custom_executor_operators,
        )

        # In some stack configurations, some stack components (like experiment
        # trackers) will run some code before and after the actual step run.
        # This is where the step actually gets executed using the
        # component_launcher
        repo.active_stack.prepare_step_run()
        execution_info = self._execute_step(component_launcher)
        repo.active_stack.cleanup_step_run()

        return execution_info

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
            DuplicateRunNameError: If the run name is already in use.
        """
        pipeline_step_name = tfx_launcher._pipeline_node.node_info.id
        start_time = time.time()
        logger.info(f"Step `{pipeline_step_name}` has started.")
        try:
            execution_info = tfx_launcher.launch()
            if execution_info and get_cache_status(execution_info):
                logger.info(f"Using cached version of `{pipeline_step_name}`.")
        except RuntimeError as e:
            if "execution has already succeeded" in str(e):
                # Hacky workaround to catch the error that a pipeline run with
                # this name already exists. Raise an error with a more
                # descriptive
                # message instead.
                raise DuplicateRunNameError()
            else:
                raise

        run_duration = time.time() - start_time
        logger.info(
            f"Step `{pipeline_step_name}` has finished in "
            f"{string_utils.get_human_readable_time(run_duration)}."
        )
        return execution_info

    def get_upstream_step_names(
        self, step: "BaseStep", pb2_pipeline: Pb2Pipeline
    ) -> List[str]:
        """Given a step, use the associated pb2 node to find the names of all upstream nodes.

        Args:
            step: Instance of a Pipeline Step
            pb2_pipeline: Protobuf Pipeline instance

        Returns:
            List of step names from direct upstream steps
        """
        node = self._get_node_with_step_name(step.name, pb2_pipeline)

        upstream_steps = []
        for upstream_node in node.upstream_nodes:
            upstream_steps.append(upstream_node)

        return upstream_steps

    @staticmethod
    def requires_resources_in_orchestration_environment(
        step: "BaseStep",
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
        return not (
            step.custom_step_operator or step.resource_configuration.empty
        )

    @staticmethod
    def _get_node_with_step_name(
        step_name: str, pb2_pipeline: Pb2Pipeline
    ) -> PipelineNode:
        """Given the name of a step, return the node with that name from the pb2_pipeline.

        Args:
            step_name: Name of the step
            pb2_pipeline: pb2 pipeline containing nodes

        Returns:
            PipelineNode instance

        Raises:
            KeyError: If the step name is not found in the pipeline.
        """
        for node in pb2_pipeline.nodes:
            if (
                node.WhichOneof("node") == "pipeline_node"
                and node.pipeline_node.node_info.id == step_name
            ):
                return node.pipeline_node

        raise KeyError(
            f"Step {step_name} not found in Pipeline "
            f"{pb2_pipeline.pipeline_info.id}"
        )

    @staticmethod
    def _configure_node_context(
        pipeline: "BasePipeline",
        pb2_pipeline: Pb2Pipeline,
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> None:
        """Iterates through each node of a pb2_pipeline.

        This attaches important contexts to the nodes; namely
        pipeline.requirements, stack information and the runtime configuration.

        Args:
            pipeline: Zenml Pipeline instance
            pb2_pipeline: Protobuf Pipeline instance
            stack: The stack the pipeline was run on
            runtime_configuration: The Runtime configuration of the current run
        """
        requirements = " ".join(sorted(pipeline.requirements))
        stack_json = json.dumps(stack.dict(), sort_keys=True)

        # Copy and remove the run name so an otherwise identical run reuses
        # our MLMD context
        runtime_config_copy = runtime_configuration.copy()
        runtime_config_copy.pop("run_name")
        runtime_config_json = json.dumps(
            runtime_config_copy, sort_keys=True, default=pydantic_encoder
        )

        context_properties = {
            MLMD_CONTEXT_STACK_PROPERTY_NAME: stack_json,
            MLMD_CONTEXT_RUNTIME_CONFIG_PROPERTY_NAME: runtime_config_json,
            MLMD_CONTEXT_PIPELINE_REQUIREMENTS_PROPERTY_NAME: requirements,
        }

        for node in pb2_pipeline.nodes:
            pipeline_node: PipelineNode = node.pipeline_node

            step = get_step_for_node(
                pipeline_node, steps=list(pipeline.steps.values())
            )
            step_context_properties = context_properties.copy()
            step_context_properties[
                MLMD_CONTEXT_STEP_RESOURCES_PROPERTY_NAME
            ] = step.resource_configuration.json(sort_keys=True)

            properties_json = json.dumps(
                step_context_properties, sort_keys=True
            )
            context_name = hashlib.md5(properties_json.encode()).hexdigest()

            add_context_to_node(
                pipeline_node,
                type_=ZENML_MLMD_CONTEXT_TYPE,
                name=context_name,
                properties=step_context_properties,
            )
