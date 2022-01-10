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

"""Inspired by local dag runner implementation
by Google at: https://github.com/tensorflow/tfx/blob/master/tfx/orchestration
/local/local_dag_runner.py"""


import tfx.orchestration.pipeline as tfx_pipeline
from tfx.dsl.compiler import compiler
from tfx.dsl.compiler.constants import PIPELINE_RUN_ID_PARAMETER_NAME
from tfx.dsl.components.base import base_component
from tfx.orchestration import metadata
from tfx.orchestration.local import runner_utils
from tfx.orchestration.portable import (
    launcher,
    runtime_parameter_utils,
    tfx_runner,
)

from zenml.logger import get_logger
from zenml.orchestrators.utils import execute_step

logger = get_logger(__name__)


class LocalDagRunner(tfx_runner.TfxRunner):
    """Local TFX DAG runner."""

    def __init__(self) -> None:
        """Initializes LocalDagRunner as a TFX orchestrator."""

    def run(self, pipeline: tfx_pipeline.Pipeline, run_name: str = "") -> None:
        """Runs given logical pipeline locally.

        Args:
          pipeline: Logical pipeline containing pipeline args and components.
          run_name: Name of the pipeline run.
        """
        for component in pipeline.components:
            if isinstance(component, base_component.BaseComponent):
                component._resolve_pip_dependencies(
                    pipeline.pipeline_info.pipeline_root
                )

        c = compiler.Compiler()
        pipeline = c.compile(pipeline)

        # Substitute the runtime parameter to be a concrete run_id
        runtime_parameter_utils.substitute_runtime_parameter(
            pipeline,
            {
                PIPELINE_RUN_ID_PARAMETER_NAME: run_name,
            },
        )

        deployment_config = runner_utils.extract_local_deployment_config(
            pipeline
        )
        connection_config = deployment_config.metadata_connection_config  # type: ignore[attr-defined] # noqa

        logger.debug(f"Using deployment config:\n {deployment_config}")
        logger.debug(f"Using connection config:\n {connection_config}")

        # Run each component. Note that the pipeline.components list is in
        # topological order.
        for node in pipeline.nodes:
            pipeline_node = node.pipeline_node
            node_id = pipeline_node.node_info.id
            executor_spec = runner_utils.extract_executor_spec(
                deployment_config, node_id
            )
            custom_driver_spec = runner_utils.extract_custom_driver_spec(
                deployment_config, node_id
            )

            component_launcher = launcher.Launcher(
                pipeline_node=pipeline_node,
                mlmd_connection=metadata.Metadata(connection_config),
                pipeline_info=pipeline.pipeline_info,
                pipeline_runtime_spec=pipeline.runtime_spec,
                executor_spec=executor_spec,
                custom_driver_spec=custom_driver_spec,
            )
            execute_step(component_launcher)
