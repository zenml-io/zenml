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

import apache_beam as beam
from tfx.orchestration import pipeline
from tfx.orchestration.beam.beam_dag_runner import BeamDagRunner, \
    _ComponentAsDoFn
from tfx.orchestration.config import config_utils

from zenml.logger import get_logger

logger = get_logger(__name__)


class ZenMLBeamlDagRunner(BeamDagRunner):
    """
    This is the same as the super class from tfx:
    tfx.orchestration.beam.beam_dag_runner.BeamDagRunner with the exception
    being that the pipeline_run is not overridden. Full credit to Google LLC
    for the original source code found at:
    https://github.com/tensorflow/tfx/tree/master/tfx/orchestration/beam/
    """

    def run(self, tfx_pipeline: pipeline.Pipeline) -> None:

        with beam.Pipeline(argv=self._beam_orchestrator_args) as p:
            root = p | 'CreateRoot' >> beam.Create([None])

            signal_map = {}
            for component in tfx_pipeline.components:
                component_id = component.id

                signals_to_wait = []
                if component.upstream_nodes:
                    for upstream_node in component.upstream_nodes:
                        assert upstream_node in signal_map, (
                            'Components is not in '
                            'topological order')
                        signals_to_wait.append(
                            signal_map[upstream_node])
                logger.debug('Component %s depends on %s.',
                             component_id,
                             [s.producer.full_label for s in
                              signals_to_wait])

                (component_launcher_class,
                 component_config) = \
                    config_utils.find_component_launch_info(
                        self._config, component)

                signal_map[component] = (
                        root
                        | 'Run[%s]' % component_id >> beam.ParDo(
                    _ComponentAsDoFn(component,
                                     component_launcher_class,
                                     component_config, tfx_pipeline),
                    *[beam.pvalue.AsIter(s) for s in signals_to_wait]))
                logger.debug('Component %s is scheduled.',
                             component_id)
