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

from tfx.orchestration import data_types
from tfx.orchestration import metadata
from tfx.orchestration import pipeline
from tfx.orchestration.config import config_utils
from tfx.orchestration.local.local_dag_runner import LocalDagRunner

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

    def run(self, tfx_pipeline: pipeline.Pipeline) -> None:
        for component in tfx_pipeline.components:
            (component_launcher_class, component_config) = (
                config_utils.find_component_launch_info(self._config,
                                                        component))
            driver_args = data_types.DriverArgs(
                enable_cache=tfx_pipeline.enable_cache)
            metadata_connection = metadata.Metadata(
                tfx_pipeline.metadata_connection_config)
            component_launcher = component_launcher_class.create(
                component=component,
                pipeline_info=tfx_pipeline.pipeline_info,
                driver_args=driver_args,
                metadata_connection=metadata_connection,
                beam_pipeline_args=tfx_pipeline.beam_pipeline_args,
                additional_pipeline_args=tfx_pipeline
                    .additional_pipeline_args,
                component_config=component_config)
            logger.info('Component %s is running.', component.id)
            component_launcher.launch()
            logger.info('Component %s is finished.', component.id)
