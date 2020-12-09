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

from typing import Dict, Text, Any, Type

from tfx.components.schema_gen.component import SchemaGen
from tfx.components.statistics_gen.component import StatisticsGen
from tfx.orchestration import pipeline

from zenml.core.backends.orchestrator.orchestrator_local_backend import \
    OrchestratorLocalBackend
from zenml.core.backends.processing.processing_local_backend import \
    ProcessingLocalBackend
from zenml.core.components.data_gen.component import DataGen
from zenml.core.components.data_gen.constants import SpecParamKeys
from zenml.core.pipelines.base_pipeline import BasePipeline
from zenml.core.pipelines.standards.standard_training_pipeline import \
    GlobalKeys
from zenml.core.steps.data.base_data_step import BaseDataStep
from zenml.utils.enums import GDPComponent
from zenml.utils.post_training_utils import view_statistics, \
    get_schema_proto, \
    evaluate_single_pipeline


class DataPipeline(BasePipeline):
    """DataPipeline definition to create datasources.

    A DataPipeline is used to create datasources in ZenML. Each data pipeline
    creates a snapshot of the datasource in time. All datasources are consumed
    by different ZenML pipelines like the TrainingPipeline.
    """

    def get_tfx_pipeline(self, config: Dict[Text, Any]) -> pipeline.Pipeline:
        """
        Creates a data tfx pipeline.

        Args:
            config: a ZenML config as a dict
        """
        data_config = config[GlobalKeys.STEPS]['data']
        data_gen = DataGen(source=data_config[SpecParamKeys.SOURCE],
                           source_args=data_config[SpecParamKeys.SOURCE_ARGS],
                           instance_name=GDPComponent.DataGen.name)

        datapoints = data_gen.outputs.examples

        statistics_split = StatisticsGen(
            examples=datapoints,
            instance_name=GDPComponent.SplitStatistics.name)

        schema_split = SchemaGen(
            statistics=statistics_split.outputs.output,
            infer_feature_shape=False,
            instance_name=GDPComponent.SplitSchema.name)

        from zenml.core.components.split_gen.component import SplitGen
        split_config = config[GlobalKeys.STEPS]['split']
        split_gen = SplitGen(
            input_examples=datapoints,
            source=split_config[SpecParamKeys.SOURCE],
            source_args=split_config[SpecParamKeys.SOURCE_ARGS],
            schema=schema_split.outputs.schema,
            statistics=statistics_split.outputs.output,
        )

        # TODO: [HIGH] Temporary hack to get splitgen tested
        # from zenml.core.components.split_gen.component import SplitGen
        # splits = SplitGen(
        #     data=datapoints,
        #     statistics=statistics_split.outputs.output,
        #     schema=schema_split.outputs.schema,
        #     config=config,
        #     instance_name=GDPComponent.SplitGen.name)

        component_list = [data_gen, statistics_split, schema_split, split_gen]

        # TODO: [HIGH] Temp hack to get it going
        from zenml.core.repo.repo import Repository
        from tfx.orchestration import metadata
        repo: Repository = Repository.get_instance()
        return pipeline.Pipeline(
            pipeline_name=config['environment']['pipeline_name'],
            pipeline_root=repo.zenml_config.get_artifact_store().path,
            metadata_connection_config=metadata
                .sqlite_metadata_connection_config(
                repo.get_metadata_store().uri),
            components=component_list,
            enable_cache=False
        )

    def add_data_step(self, data_step: Type[BaseDataStep]):
        self.steps_dict['data'] = data_step

    def add_split_step(self, split_step):
        self.steps_dict['split'] = split_step

    def view_statistics(self):
        """View statistics for training pipeline."""
        # TODO: [HIGH] Remove hard-coded StatisticsGen name
        artifact_uris = self.repo.get_artifacts_uri_by_component(
            self.pipeline_name, 'StatisticsGen')
        view_statistics(artifact_uris[0])

    def view_schema(self):
        """View schema of data flowing in pipeline."""
        # TODO: [HIGH] Remove hard-coded SchemaGen name
        artifact_uris = self.repo.get_artifacts_uri_by_component(
            self.pipeline_name, 'SchemaGen')
        return get_schema_proto(artifact_uris[0])

    def evaluate(self):
        """Evaluate pipeline."""
        trainer_paths = self.repo.get_artifacts_uri_by_component(
            'penguin_local_no_tuning_4', 'Trainer')
        eval_paths = self.repo.get_artifacts_uri_by_component(
            'penguin_local_no_tuning_4', 'Evaluator')
        evaluate_single_pipeline(self.name, trainer_paths[0], eval_paths[0])

    def download_model(self):
        """Download model."""
        model_paths = self.repo.get_artifacts_uri_by_component(
            'penguin_local_no_tuning_4', 'Pusher')
        print(f'Model: {model_paths[0]}')

    def get_default_backends(self) -> Dict:
        """Gets list of default backends for this pipeline."""
        # For base class, orchestration is always necessary
        return {
            OrchestratorLocalBackend.BACKEND_KEY: OrchestratorLocalBackend(),
            ProcessingLocalBackend.BACKEND_KEY: ProcessingLocalBackend()
        }

    def is_completed(self) -> bool:
        mandatory_steps = ['data']
        for step_name in mandatory_steps:
            if step_name not in self.steps_dict.keys():
                raise AssertionError(
                    f'Mandatory step {step_name} not added.')
        return True
