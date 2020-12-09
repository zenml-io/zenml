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

    def get_single_type(self, pipeline_type: Text):
        if pipeline_type in self.pipeline_types:
            return self.pipeline_types[pipeline_type]

    def get_type_from_pipeline(self, pipeline: Type):
        inverted_dict = dict((v, k) for k, v in self.pipeline_types.items())
        if pipeline in inverted_dict:
            return inverted_dict[pipeline]

    def register_type(self, pipeline_type: Text, pipeline: Type):
        self.pipeline_types[pipeline_type] = pipeline

    # TODO: [MED] These two functions might not belong here.
    def create_file_name(self, pipeline_object: BasePipeline):
        """
        Creates pipeline YAML file name from pipeline object.

        Args:
            pipeline_object: Object of type BasePipeline.
        """
        pipeline_type = self.get_type_from_pipeline(pipeline_object.__class__)
        return pipeline_type.lower() + '_' + pipeline_object.name + '.yaml'

    def get_type_from_file_name(self, file_name: Text):
        """
        Gets type of pipeline from file name.

        Args:
            file_name: YAML file name of pipeline.
        """
        return file_name.replace('.yaml', "").split('_')[0]


# Register the injections into the factory
pipeline_factory = PipelineFactory()
pipeline_factory.register_type('base', BasePipeline)
pipeline_factory.register_type('data', DataPipeline)
pipeline_factory.register_type('training', TrainingPipeline)
pipeline_factory.register_type('infer', BatchInferencePipeline)
