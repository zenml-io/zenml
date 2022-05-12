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
import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, List, Optional

from tfx.dsl.compiler.compiler import Compiler
from tfx.dsl.compiler.constants import PIPELINE_RUN_ID_PARAMETER_NAME
from tfx.orchestration import metadata
from tfx.orchestration.local import runner_utils
from tfx.orchestration.pipeline import Pipeline as TfxPipeline
from tfx.orchestration.portable import (
    data_types,
    launcher,
    runtime_parameter_utils,
)
from tfx.proto.orchestration import executable_spec_pb2
from tfx.proto.orchestration.pipeline_pb2 import Pipeline as Pb2Pipeline
from tfx.proto.orchestration.pipeline_pb2 import PipelineNode

from zenml.enums import MetadataContextTypes, StackComponentType
from zenml.logger import get_logger
from zenml.orchestrators import context_utils
from zenml.orchestrators.utils import (
    create_tfx_pipeline,
    execute_step,
    get_step_for_node,
)
from zenml.repository import Repository
from zenml.stack import StackComponent
from zenml.steps import BaseStep

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
        The **run_pipeline** method is the entrypoint that is executed when the
        pipeline's run method is called within the user code
        (`pipeline_instance.run()`).

        This method will take the ZenML Pipeline instance and prepare it for
        eventual execution. To do this the following steps are taken:

        * The underlying tfx and protobuf pipelines
        are created within the **set_class_attributes** method.

        * Within the **configure_step_context** method the pipeline
        requirements, stack and runtime configuration is added to the step
        context

        * The **get_sorted_steps** method then generates a sorted_list_of_steps
        which will later be used to directly execute these steps in order, or to
        easily build a dag

        * After these initial steps comes the most crucial one. Within the
        **prepare_or_run_pipeline** method each orchestrator will have its own
        implementation that dictates the pipeline orchestration. In the simplest
        case this method will iterate through all steps and execute them one by
        one. In other cases this method will build and deploy an intermediate
        representation of the pipeline (e.g an airflow dag or a kubeflow.yaml)
        to be executed within the orchestrators environmenrt.

        * Finally the private class attributes will be reset using the
        **clean_class_attributes** method in order to be able to run another
        pipeline from the same orchestrator instance.

    Building your own:
        In order to build your own orchestrator, all you need to do is subclass
        from this class and implement your own **prepare_or_run_pipeline**
        method. Overwriting other methods is NOT recommended but possible and
        maybe even necessary for complex implementations. See the docstring of
        the prepare_or_run_pipeline method to find out details of what needs
        to be implemented.
    """

    _stack: Optional["Stack"] = None
    _runtime_configuration: Optional["RuntimeConfiguration"] = None
    _tfx_pipeline: Optional["TfxPipeline"] = None
    _pb2_pipeline: Optional["Pb2Pipeline"] = None

    # Class Configuration
    TYPE: ClassVar[StackComponentType] = StackComponentType.ORCHESTRATOR

    @abstractmethod
    def prepare_or_run_pipeline(
        self,
        sorted_list_of_steps: List[BaseStep],
        pipeline: "BasePipeline",
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> Any:
        """
        This method needs to be implemented by the respective orchestrator.
        Depending on the type of orchestrator you'll have to perform slightly
        different operations.

        Simple Case:
            The Steps are run directly from within the environment in which the
            orchestrator code is executed. In this case you will need to deal
            with implementation-specific runtime configurations (like the
            schedule) and then iterate through each step and finally call
            self.setup_and_execute_step() to run the step.

        Advanced Case:
            Most orchestrators will run the pipeline in a non-trivial way. ...

        ...
        """

    def run_pipeline(
        self,
        pipeline: "BasePipeline",
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> Any:
        """Runs a pipeline.

        Args:
            pipeline: The pipeline to run.
            stack: The stack on which the pipeline is run.
            runtime_configuration: Runtime configuration of the pipeline run.
        """
        self.set_class_attributes(pipeline, stack)

        self.configure_node_context(pipeline, stack, runtime_configuration)

        sorted_list_of_steps = self.get_sorted_steps(pipeline)

        prepared_steps = self.prepare_or_run_pipeline(
            sorted_list_of_steps=sorted_list_of_steps,
            pipeline=pipeline,
            stack=stack,
            runtime_configuration=runtime_configuration,
        )

        self.clean_class_attributes()

        return prepared_steps

    def get_sorted_steps(self, pipeline: "BasePipeline") -> List["BaseStep"]:
        """Get steps sorted in the execution order. This simplifies the
        building of a DAG at a later stage as it can be built with one iteration
        over this sorted list of steps.

        Args:
            pipeline: The pipeline

        Returns:
            List of steps in execution order
        """
        # Create a list of sorted steps
        sorted_steps = []
        for node in self._pb2_pipeline.nodes:
            pipeline_node: PipelineNode = node.pipeline_node
            sorted_steps.append(
                get_step_for_node(
                    pipeline_node, steps=list(pipeline.steps.values())
                )
            )
        return sorted_steps

    def set_class_attributes(
        self,
        pipeline: "BasePipeline",
        stack: "Stack",
    ):

        self._tfx_pipeline: TfxPipeline = create_tfx_pipeline(
            pipeline, stack=stack
        )

        self._pb2_pipeline: Pb2Pipeline = Compiler().compile(self._tfx_pipeline)

    def configure_node_context(
        self,
        pipeline: "BasePipeline",
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ):
        for node in self._pb2_pipeline.nodes:
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

    def setup_and_execute_step(
        self,
        step: "BaseStep",
        run_name: str,
        pb2_pipeline: Optional[Pb2Pipeline] = None,
    ) -> Optional[data_types.ExecutionInfo]:
        """ """

        pb2_pipeline = pb2_pipeline or self._pb2_pipeline

        assert pb2_pipeline

        # Substitute the runtime parameter to be a concrete run_id
        runtime_parameter_utils.substitute_runtime_parameter(
            pb2_pipeline,
            {PIPELINE_RUN_ID_PARAMETER_NAME: run_name},
        )

        deployment_config = runner_utils.extract_local_deployment_config(
            pb2_pipeline
        )
        executor_spec = runner_utils.extract_executor_spec(
            deployment_config, step.name
        )
        custom_driver_spec = runner_utils.extract_custom_driver_spec(
            deployment_config, step.name
        )

        repo = Repository()
        metadata_store = repo.active_stack.metadata_store
        metadata_connection = metadata.Metadata(
            metadata_store.get_tfx_metadata_config()
        )
        custom_executor_operators = {
            executable_spec_pb2.PythonClassExecutableSpec: step.executor_operator
        }

        pipeline_node = self._get_node_with_step_name(
            step_name=step.name, pb2_pipeline=pb2_pipeline
        )

        component_launcher = launcher.Launcher(
            pipeline_node=pipeline_node,
            mlmd_connection=metadata_connection,
            pipeline_info=pb2_pipeline.pipeline_info,
            pipeline_runtime_spec=pb2_pipeline.runtime_spec,
            executor_spec=executor_spec,
            custom_driver_spec=custom_driver_spec,
            custom_executor_operators=custom_executor_operators,
        )

        repo.active_stack.prepare_step_run()
        execution_info = execute_step(component_launcher)
        repo.active_stack.prepare_step_run()

        return execution_info

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

    def get_upstream_steps(self, step: "BaseStep") -> List[str]:
        """Given a step, use the associated pb2 node to find the names of all
        upstream nodes.

        Args:
            step: Instance of a Pipeline Step

        Returns:
            List of step names from direct upstream steps
        """
        node = self._get_node_with_step_name(step.name, self._pb2_pipeline)

        upstream_steps = []
        for upstream_node in node.upstream_nodes:
            upstream_steps.append(upstream_node)

        return upstream_steps

    def clean_class_attributes(self) -> None:
        """
        Resets all class attributes so that the same orchestrator instance
        can be reused for another pipeline run with no adverse effects.
        """

        self._stack = None
        self._tfx_pipeline = None
        self._pb2_pipeline = None
        self._runtime_configuration = None
