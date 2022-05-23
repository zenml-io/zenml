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

import json
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, List, Optional

from tfx.dsl.compiler.compiler import Compiler
from tfx.dsl.compiler.constants import PIPELINE_RUN_ID_PARAMETER_NAME
from tfx.orchestration import metadata
from tfx.orchestration.local import runner_utils
from tfx.orchestration.portable import (
    data_types,
    launcher,
    runtime_parameter_utils,
)
from tfx.proto.orchestration import executable_spec_pb2
from tfx.proto.orchestration.pipeline_pb2 import Pipeline as Pb2Pipeline
from tfx.proto.orchestration.pipeline_pb2 import PipelineNode

from zenml.enums import MetadataContextTypes, StackComponentType
from zenml.exceptions import DuplicateRunNameError
from zenml.logger import get_logger
from zenml.orchestrators import context_utils
from zenml.orchestrators.utils import (
    create_tfx_pipeline,
    get_cache_status,
    get_step_for_node,
)
from zenml.repository import Repository
from zenml.stack import StackComponent
from zenml.steps import BaseStep
from zenml.steps.utils import (
    INTERNAL_EXECUTION_PARAMETER_PREFIX,
    PARAM_PIPELINE_PARAMETER_NAME,
)
from zenml.utils import string_utils

if TYPE_CHECKING:
    from zenml.pipelines import BasePipeline
    from zenml.runtime_configuration import RuntimeConfiguration
    from zenml.stack import Stack

logger = get_logger(__name__)


class BaseOrchestrator(StackComponent, ABC):
    """
    Base class for all orchestrators. In order to implement an
    orchestrator you will need to subclass from this class.

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
        """
         This method needs to be implemented by the respective orchestrator.
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
             sorted_steps: List of sorted steps
             pipeline: Zenml Pipeline instance
             pb2_pipeline: Protobuf Pipeline instance
             stack: The stack the pipeline was run on
             runtime_configuration: The Runtime configuration of the current run

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
        """Runs a pipeline. To do this, a protobuf pipeline is created, the
        context of the individual steps is expanded to include relevant data,
        the steps are sorted into execution order and the implementation
        specific `prepare_or_run_pipeline()` method is called.

        Args:
            pipeline: The pipeline to run.
            stack: The stack on which the pipeline is run.
            runtime_configuration: Runtime configuration of the pipeline run.

        Return:
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
        """Get steps sorted in the execution order. This simplifies the
        building of a DAG at a later stage as it can be built with one iteration
        over this sorted list of steps.

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
        """
        step_name_param = (
            INTERNAL_EXECUTION_PARAMETER_PREFIX + PARAM_PIPELINE_PARAMETER_NAME
        )
        pipeline_step_name = tfx_launcher._pipeline_node.node_info.id
        start_time = time.time()
        logger.info(f"Step `{pipeline_step_name}` has started.")
        try:
            execution_info = tfx_launcher.launch()
            if execution_info and get_cache_status(execution_info):
                if execution_info.exec_properties:
                    step_name = json.loads(
                        execution_info.exec_properties[step_name_param]
                    )
                    logger.info(
                        f"Using cached version of `{pipeline_step_name}` "
                        f"[`{step_name}`].",
                    )
                else:
                    logger.error(
                        f"No execution properties found for step "
                        f"`{pipeline_step_name}`."
                    )
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
        """Given a step, use the associated pb2 node to find the names of all
        upstream nodes.

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
    def _get_node_with_step_name(
        step_name: str, pb2_pipeline: Pb2Pipeline
    ) -> PipelineNode:
        """Given the name of a step, return the node with that name from the
        pb2_pipeline.

        Args:
            step_name: Name of the step
            pb2_pipeline: pb2 pipeline containing nodes

        Returns:
            PipelineNode instance
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
        """Iterates through each node of a pb2_pipeline and attaches important
        contexts to the nodes; namely pipeline.requirements, stack
        information and the runtime configuration.

        Args:
            pipeline: Zenml Pipeline instance
            pb2_pipeline: Protobuf Pipeline instance
            stack: The stack the pipeline was run on
            runtime_configuration: The Runtime configuration of the current run
        """
        for node in pb2_pipeline.nodes:
            pipeline_node: PipelineNode = node.pipeline_node

            # Add pipeline requirements to the step context
            requirements = " ".join(sorted(pipeline.requirements))
            context_utils.add_context_to_node(
                pipeline_node,
                type_=MetadataContextTypes.PIPELINE_REQUIREMENTS.value,
                name=str(hash(requirements)),
                properties={"pipeline_requirements": requirements},
            )

            # Add the zenml stack to the step context
            context_utils.add_context_to_node(
                pipeline_node,
                type_=MetadataContextTypes.STACK.value,
                name=str(hash(json.dumps(stack.dict(), sort_keys=True))),
                properties=stack.dict(),
            )

            # Add all pydantic objects from runtime_configuration to the context
            context_utils.add_runtime_configuration_to_node(
                pipeline_node, runtime_configuration
            )
