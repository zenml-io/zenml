# Original Licence:
# Copyright 2019 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# New Licence:
#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

"""Definition of Beam TFX runner. Inspired by local dag runner implementation
by Google at: https://github.com/tensorflow/tfx/blob/master/tfx/orchestration
/local/local_dag_runner.py"""

import time
from datetime import datetime
from typing import Optional

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

logger = get_logger(__name__)


def format_timedelta_pretty(seconds: float) -> str:
    """Format a float representing seconds into a string.

    Args:
      seconds: result of a time.time() - time.time().

    Returns:
        Pretty formatted string according to specification.
    """
    int_seconds = int(seconds)
    days, int_seconds = divmod(int_seconds, 86400)
    hours, int_seconds = divmod(int_seconds, 3600)
    minutes, int_seconds = divmod(int_seconds, 60)
    if days > 0:
        return "%dd%dh%dm%ds" % (days, hours, minutes, int_seconds)
    elif hours > 0:
        return "%dh%dm%ds" % (hours, minutes, int_seconds)
    elif minutes > 0:
        return "%dm%ds" % (minutes, int_seconds)
    else:
        return f"{seconds:.3f}s"


class LocalDagRunner(tfx_runner.TfxRunner):
    """Local TFX DAG runner."""

    def __init__(self) -> None:
        """Initializes LocalDagRunner as a TFX orchestrator."""

    def run(
        self, pipeline: tfx_pipeline.Pipeline, run_name: Optional[str] = None
    ) -> None:
        """Runs given logical pipeline locally.

        Args:
          pipeline: Logical pipeline containing pipeline args and components.
          run_name: Optional name for the run.
        """
        for component in pipeline.components:
            if isinstance(component, base_component.BaseComponent):
                component._resolve_pip_dependencies(
                    pipeline.pipeline_info.pipeline_root
                )

        c = compiler.Compiler()
        pipeline = c.compile(pipeline)

        run_name = run_name or datetime.now().strftime("%d_%h_%y-%H_%M_%S_%f")
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
            start = time.time()
            logger.info(f"Step `{node_id}` has started.")
            component_launcher.launch()
            end = time.time()
            logger.info(
                f"Step `{node_id}` has finished"
                f" in {format_timedelta_pretty(end - start)}."
            )
