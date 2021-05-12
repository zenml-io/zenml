#  Copyright (c) maiot GmbH 2020. All Rights Reserved.
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

import os
from typing import Union

from absl import logging
from tfx.dsl.compiler import compiler
from tfx.dsl.compiler import constants
from tfx.orchestration import metadata
from tfx.orchestration import pipeline as pipeline_py
from tfx.orchestration.local import runner_utils
from tfx.orchestration.local.local_dag_runner import LocalDagRunner
from tfx.orchestration.portable import launcher
from tfx.orchestration.portable import runtime_parameter_utils
from tfx.proto.orchestration import pipeline_pb2
from tfx.utils import telemetry_utils

from zenml.logger import get_logger

logger = get_logger(__name__)


class ZenMLLocalDagRunner(LocalDagRunner):
    """
    This is the almost the same as the super class from tfx:
    tfx.orchestration.base.local_dag_runner.LocalDagRunner with the exception
    being that the pipeline_run is not overridden. Full credit to Google LLC
    for the original source code found at:
    https://github.com/tensorflow/tfx/blob/master/tfx/orchestration/local/
    """

    def run(self, pipeline: Union[pipeline_pb2.Pipeline,
                                  pipeline_py.Pipeline]) -> None:
        """Runs given logical pipeline locally.

        Args:
          pipeline: Logical pipeline containing pipeline args and components.
        """
        # For CLI, while creating or updating pipeline, pipeline_args are extracted
        # and hence we avoid executing the pipeline.
        if 'TFX_JSON_EXPORT_PIPELINE_ARGS_PATH' in os.environ:
            return
        run_id = pipeline.pipeline_info.run_id

        if isinstance(pipeline, pipeline_py.Pipeline):
            c = compiler.Compiler()
            pipeline = c.compile(pipeline)

        # Substitute the runtime parameter to be a concrete run_id
        runtime_parameter_utils.substitute_runtime_parameter(
            pipeline, {
                constants.PIPELINE_RUN_ID_PARAMETER_NAME: run_id
            })

        deployment_config = runner_utils.extract_local_deployment_config(
            pipeline)
        connection_config = deployment_config.metadata_connection_config

        logging.info('Running pipeline:\n %s', pipeline)
        logging.info('Using deployment config:\n %s', deployment_config)
        logging.info('Using connection config:\n %s', connection_config)

        with telemetry_utils.scoped_labels(
                {telemetry_utils.LABEL_TFX_RUNNER: 'local'}):
            # Run each component. Note that the pipeline.components list is in
            # topological order.
            # TODO(b/171319478): After IR-based execution is used, used multi-threaded
            #   execution so that independent components can be run in parallel.
            for node in pipeline.nodes:
                pipeline_node = node.pipeline_node
                node_id = pipeline_node.node_info.id
                executor_spec = runner_utils.extract_executor_spec(
                    deployment_config, node_id)
                custom_driver_spec = runner_utils.extract_custom_driver_spec(
                    deployment_config, node_id)

                component_launcher = launcher.Launcher(
                    pipeline_node=pipeline_node,
                    mlmd_connection=metadata.Metadata(connection_config),
                    pipeline_info=pipeline.pipeline_info,
                    pipeline_runtime_spec=pipeline.runtime_spec,
                    executor_spec=executor_spec,
                    custom_driver_spec=custom_driver_spec)
                logging.info('Component %s is running.', node_id)
                component_launcher.launch()
                logging.info('Component %s is finished.', node_id)
