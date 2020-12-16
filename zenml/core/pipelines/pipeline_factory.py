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
"""Factory to register step classes to steps"""

from typing import Type, Text, Dict

from zenml.core.pipelines.base_pipeline import BasePipeline
from zenml.core.pipelines.data_pipeline import DataPipeline
from zenml.core.pipelines.infer_pipeline import BatchInferencePipeline
from zenml.core.pipelines.training_pipeline import TrainingPipeline


class PipelineFactory:
    """Definition of PipelineFactory to track all pipelines in ZenML.

    All pipelines (including custom ones) are to be registered here.
    """

    def __init__(self):
        self.pipeline_types: Dict[Text, Type] = {}

    def get_pipeline_types(self) -> Dict:
        return self.pipeline_types

    def get_pipeline_by_type(self, pipeline_type: Text):
        if pipeline_type in self.pipeline_types:
            return self.pipeline_types[pipeline_type]

    def register_type(self, pipeline_type: Text, pipeline: Type):
        self.pipeline_types[pipeline_type] = pipeline


# Register the injections into the factory
pipeline_factory = PipelineFactory()
pipeline_factory.register_type(BasePipeline.PIPELINE_TYPE, BasePipeline)
pipeline_factory.register_type(DataPipeline.PIPELINE_TYPE, DataPipeline)
pipeline_factory.register_type(TrainingPipeline.PIPELINE_TYPE,
                               TrainingPipeline)
pipeline_factory.register_type(BatchInferencePipeline.PIPELINE_TYPE,
                               BatchInferencePipeline)
