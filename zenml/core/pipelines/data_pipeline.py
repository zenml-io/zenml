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
"""Pipeline to create data sources"""

from typing import Dict, Text, Any, List

from tfx.components.schema_gen.component import SchemaGen
from tfx.components.statistics_gen.component import StatisticsGen

from zenml.core.backends.orchestrator.local.orchestrator_local_backend import \
    OrchestratorLocalBackend
from zenml.core.backends.processing.processing_local_backend import \
    ProcessingLocalBackend
from zenml.core.components.data_gen.component import DataGen
from zenml.core.pipelines.base_pipeline import BasePipeline
from zenml.core.standards import standard_keys as keys
from zenml.core.standards.standard_keys import StepKeys
from zenml.utils.enums import GDPComponent
from zenml.utils.post_training.post_training_utils import \
    get_statistics_artifact, \
    get_schema_artifact, view_statistics, view_schema


class DataPipeline(BasePipeline):
    """DataPipeline definition to create datasources.

    A DataPipeline is used to create datasources in ZenML. Each data pipeline
    creates a snapshot of the datasource in time. All datasources are consumed
    by different ZenML pipelines like the TrainingPipeline.
    """
    PIPELINE_TYPE = 'data'

    def get_tfx_component_list(self, config: Dict[Text, Any]) -> List:
        """
        Creates a data tfx pipeline.

        Args:
            config: a ZenML config as a dict
        """
        data_config = config[keys.GlobalKeys.STEPS][keys.DataSteps.DATA]
        data_gen = DataGen(
            source=data_config[StepKeys.SOURCE],
            source_args=data_config[StepKeys.ARGS]).with_id(
            GDPComponent.DataGen.name
        )

        datapoints = data_gen.outputs.examples

        statistics_split = StatisticsGen(
            examples=datapoints).with_id(GDPComponent.SplitStatistics.name)

        schema_split = SchemaGen(
            statistics=statistics_split.outputs.output,
            infer_feature_shape=True).with_id(GDPComponent.SplitSchema.name)

        return [data_gen, statistics_split, schema_split]

    def view_statistics(self, magic: bool = False):
        """
        View statistics for data pipeline in HTML.

        Args:
            magic (bool): Creates HTML page if False, else
            creates a notebook cell.
        """
        uri = get_statistics_artifact(
            self.pipeline_name, GDPComponent.DataStatistics.name)
        view_statistics(uri, magic)

    def view_schema(self):
        """View schema of data flowing in pipeline."""
        uri = get_schema_artifact(
            self.pipeline_name, GDPComponent.DataSchema.name)
        view_schema(uri)

    def get_default_backends(self) -> Dict:
        """Gets list of default backends for this pipeline."""
        # For base class, orchestration is always necessary
        return {
            OrchestratorLocalBackend.BACKEND_KEY: OrchestratorLocalBackend(),
            ProcessingLocalBackend.BACKEND_KEY: ProcessingLocalBackend()
        }

    def steps_completed(self) -> bool:
        mandatory_steps = [keys.DataSteps.DATA]
        for step_name in mandatory_steps:
            if step_name not in self.steps_dict.keys():
                raise AssertionError(
                    f'Mandatory step {step_name} not added.')
        return True
