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

from typing import Dict, Text, Any

from tfx.components.bulk_inferrer.component import BulkInferrer
from tfx.components.common_nodes.importer_node import ImporterNode
from tfx.orchestration import pipeline
from tfx.types import standard_artifacts

import zenml.core.pipelines.config.standard_config as exp_keys
from zenml.core.components.session_transform.sequence_transform import \
    SequenceTransform
from zenml.core.components.split_gen.component import SplitGen
from zenml.core.pipelines.base_pipeline import BasePipeline
from zenml.utils.enums import GDPComponent
from zenml.core.backends.orchestrator.orchestrator_local_backend import \
    OrchestratorLocalBackend
from zenml.core.backends.processing.processing_local_backend import \
    ProcessingLocalBackend

class BatchInferencePipeline(BasePipeline):
    """BatchInferencePipeline definition to run batch inference pipelines.

    A BatchInferencePipeline is used to run an inference based on a
    TrainingPipeline.
    """
    def __init__(self, name="DataPipeline", enable_cache=True):
        """
        Args:
            name:
            enable_cache:
        """
        super().__init__(name, enable_cache)
        self.name = name
        self.enable_cache = enable_cache

    def get_tfx_pipeline(self, spec: Dict[Text, Any]) -> pipeline.Pipeline:
        """
        Args:
            spec:
        """
        component_list = list()

        # Create the single split
        splits = SplitGen(config=train_config,
                          instance_name=GDPComponent.SplitGen.name)
        component_list.append(splits)
        datapoints = splits.outputs.examples

        # Handle timeseries
        if exp_keys.GlobalKeys.TIMESERIES_ in train_config:
            schema = ImporterNode(instance_name='Schema',
                                  source_uri=spec['schema_uri'],
                                  artifact_type=standard_artifacts.Schema)

            sequence_transform = SequenceTransform(
                examples=datapoints,
                schema=schema,
                config=train_config,
                instance_name=GDPComponent.SequenceTransform.name)
            datapoints = sequence_transform.outputs.output
            component_list.extend([schema, sequence_transform])

        # Infer the results
        model = ImporterNode(instance_name='Trainer',
                             source_uri=spec['model_uri'],
                             artifact_type=standard_artifacts.Model)

        bulk_inferrer = BulkInferrer(examples=datapoints,
                                     model=model.outputs['result'],
                                     instance_name=GDPComponent.Inferrer.name)

        component_list.extend([model, bulk_inferrer])

        return pipeline.Pipeline(
            pipeline_name=spec['pipeline_name'],
            pipeline_root=spec['pipeline_root'],
            components=component_list,
            beam_pipeline_args=spec['execution_args'],
            enable_cache=spec['pipeline_enable_cache'],
            metadata_connection_config=spec['metadata_connection_config'],
            log_root=spec['pipeline_log_root']
        )

    def get_default_backends(self) -> Dict:
        """Gets list of default backends for this pipeline."""
        # For base class, orchestration is always necessary
        return {
            OrchestratorLocalBackend.BACKEND_KEY: OrchestratorLocalBackend(),
            ProcessingLocalBackend.BACKEND_KEY: ProcessingLocalBackend()
        }
