# Original License:
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

# New License:
#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
from typing import TYPE_CHECKING, Any

from tfx.dsl.compiler.compiler import Compiler
from tfx.dsl.compiler.constants import PIPELINE_RUN_ID_PARAMETER_NAME
from tfx.dsl.components.base import base_component
from tfx.orchestration import metadata
from tfx.orchestration.local import runner_utils
from tfx.orchestration.pipeline import Pipeline as TfxPipeline
from tfx.orchestration.portable import launcher, runtime_parameter_utils
from tfx.proto.orchestration import executable_spec_pb2
from tfx.proto.orchestration.pipeline_pb2 import Pipeline as Pb2Pipeline
from tfx.proto.orchestration.pipeline_pb2 import PipelineNode

from zenml.enums import MetadataContextTypes, OrchestratorFlavor
from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestrator, context_utils
from zenml.orchestrators.utils import (
    create_tfx_pipeline,
    execute_step,
    get_step_for_node,
)
from zenml.repository import Repository

if TYPE_CHECKING:
    from zenml.pipelines.base_pipeline import BasePipeline
    from zenml.runtime_configuration import RuntimeConfiguration
    from zenml.stack import Stack


logger = get_logger(__name__)


class LocalOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines locally."""

    supports_local_execution = True
    supports_remote_execution = False

    @property
    def flavor(self) -> OrchestratorFlavor:
        """The orchestrator flavor."""
        return OrchestratorFlavor.LOCAL

    def run_pipeline(
        self,
        pipeline: "BasePipeline",
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> Any:
        """Runs a pipeline locally"""

        tfx_pipeline: TfxPipeline = create_tfx_pipeline(pipeline, stack=stack)

        if runtime_configuration is None:
            runtime_configuration = RuntimeConfiguration()

        if runtime_configuration.schedule:
            logger.warning(
                "Local Orchestrator currently does not support the"
                "use of schedules. The `schedule` will be ignored "
                "and the pipeline will be run directly"
            )

        pipeline_root = tfx_pipeline.pipeline_info.pipeline_root
        if not isinstance(pipeline_root, str):
            raise TypeError(
                "TFX Pipeline root may not be a Placeholder, "
                "but must be a specific string."
            )

        for component in tfx_pipeline.components:
            if isinstance(component, base_component.BaseComponent):
                component._resolve_pip_dependencies(pipeline_root)

        pb2_pipeline: Pb2Pipeline = Compiler().compile(tfx_pipeline)

        # Substitute the runtime parameter to be a concrete run_id
        runtime_parameter_utils.substitute_runtime_parameter(
            pb2_pipeline,
            {
                PIPELINE_RUN_ID_PARAMETER_NAME: runtime_configuration.run_name,
            },
        )

        deployment_config = runner_utils.extract_local_deployment_config(
            pb2_pipeline
        )
        connection_config = (
            Repository().active_stack.metadata_store.get_tfx_metadata_config()
        )

        logger.debug(f"Using deployment config:\n {deployment_config}")
        logger.debug(f"Using connection config:\n {connection_config}")

        # Run each component. Note that the pipeline.components list is in
        # topological order.
        for node in pb2_pipeline.nodes:
            pipeline_node: PipelineNode = node.pipeline_node

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

            # Add pipeline requirements as a context
            requirements = " ".join(sorted(pipeline.requirements))
            context_utils.add_context_to_node(
                pipeline_node,
                type_=MetadataContextTypes.PIPELINE_REQUIREMENTS.value,
                name=str(hash(requirements)),
                properties={"pipeline_requirements": requirements},
            )

            node_id = pipeline_node.node_info.id
            executor_spec = runner_utils.extract_executor_spec(
                deployment_config, node_id
            )
            custom_driver_spec = runner_utils.extract_custom_driver_spec(
                deployment_config, node_id
            )

            p_info = pb2_pipeline.pipeline_info
            r_spec = pb2_pipeline.runtime_spec

            # set custom executor operator to allow custom execution logic for
            # each step
            step = get_step_for_node(
                pipeline_node, steps=list(pipeline.steps.values())
            )
            custom_executor_operators = {
                executable_spec_pb2.PythonClassExecutableSpec: step.executor_operator
            }

            component_launcher = launcher.Launcher(
                pipeline_node=pipeline_node,
                mlmd_connection=metadata.Metadata(connection_config),
                pipeline_info=p_info,
                pipeline_runtime_spec=r_spec,
                executor_spec=executor_spec,
                custom_driver_spec=custom_driver_spec,
                custom_executor_operators=custom_executor_operators,
            )
            execute_step(component_launcher)
