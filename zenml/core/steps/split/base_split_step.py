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

from abc import abstractmethod
from typing import Text, List

from tensorflow_metadata.proto.v0.schema_pb2 import Schema
from tensorflow_metadata.proto.v0.statistics_pb2 import \
    DatasetFeatureStatisticsList

from zenml.core.steps.base_step import BaseStep
from zenml.utils.enums import StepTypes


class BaseSplitStep(BaseStep):
    STEP_TYPE = StepTypes.split.name

    def __init__(self,
                 statistics: DatasetFeatureStatisticsList = None,
                 schema: Schema = None,
                 **kwargs):
        """
        Constructor for BaseSplitStep.

        Args:
            statistics: output of a preceding StatisticsGen
            schema: output of a preceding SchemaGen
        """
        super().__init__(**kwargs)
        self.statistics = statistics
        self.schema = schema

    @abstractmethod
    def partition_fn(self):
        pass

    @abstractmethod
    def get_split_names(self) -> List[Text]:
        pass

    def get_num_splits(self):
        return len(self.get_split_names())
