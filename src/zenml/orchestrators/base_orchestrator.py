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
    """Base class for all ZenML orchestrators."""

    _stack: Optional["Stack"] = None
    _runtime_configuration: Optional["RuntimeConfiguration"] = None
    _tfx_pipeline: Optional["TfxPipeline"] = None
    _pb2_pipeline: Optional["Pb2Pipeline"] = None

    # Class Configuration
    TYPE: ClassVar[StackComponentType] = StackComponentType.ORCHESTRATOR

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
        self.set_class_attributes(pipeline, stack, runtime_configuration)

        # Create a list of sorted steps
        sorted_steps = []
        for node in self._pb2_pipeline.nodes:
            pipeline_node: PipelineNode = node.pipeline_node
            sorted_steps.append(
                get_step_for_node(
                    pipeline_node, steps=list(pipeline.steps.values())
                )
            )

        prepared_steps = self.prepare_steps(
            pipeline=pipeline,
            sorted_list_of_steps=sorted_steps,
            runtime_configuration=runtime_configuration,
        )

        self.clean_class_attributes()

        return prepared_steps

    @abstractmethod
    def prepare_steps(
        self,
        pipeline: "BasePipeline",
        sorted_list_of_steps: List[BaseStep],
        runtime_configuration: "RuntimeConfiguration",
    ) -> Any:
        """BLAH BLAH BLAH"""

    def setup_and_execute_step(
        self,
        step: "BaseStep",
        run_name: str,
        pb2_pipeline: Optional[Pb2Pipeline] = None,
    ) -> Optional[data_types.ExecutionInfo]:

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

    def set_class_attributes(
        self,
        pipeline: "BasePipeline",
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ):
        self._stack = stack

        self._runtime_configuration = runtime_configuration

        self._tfx_pipeline: TfxPipeline = create_tfx_pipeline(
            pipeline, stack=stack
        )

        self._pb2_pipeline: Pb2Pipeline = Compiler().compile(self._tfx_pipeline)

        for node in self._pb2_pipeline.nodes:
            pipeline_node: PipelineNode = node.pipeline_node

            step = get_step_for_node(
                pipeline_node, steps=list(pipeline.steps.values())
            )

            # Add pipeline requirements as a context
            requirements = " ".join(sorted(pipeline.requirements))
            context_utils.add_context_to_node(
                pipeline_node,
                type_=MetadataContextTypes.PIPELINE_REQUIREMENTS.value,
                name=str(hash(requirements)),
                properties={"pipeline_requirements": requirements},
            )

            # fill out that context
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

    def get_upstream_steps(self, step: "BaseStep") -> List[str]:
        """Given a step use the associated pb2 node to find the names of all
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

    def prepare_entrypoint(self) -> None:
        # ...

        # self._pb2_pipeline

        # ...
        pass

    def clean_class_attributes(self) -> None:
        # ...
        pass
