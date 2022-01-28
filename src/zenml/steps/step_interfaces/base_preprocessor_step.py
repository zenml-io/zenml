#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from abc import abstractmethod

from zenml.artifacts import DataArtifact, SchemaArtifact, StatisticsArtifact
from zenml.steps import BaseStep, BaseStepConfig, Output, StepContext


class BasePreprocessorConfig(BaseStepConfig):
    """Base class for Preprocessor step configurations"""


class BasePreprocessorStep(BaseStep):
    """Base step implementation for any Preprocessor step implementation on
    ZenML"""

    @abstractmethod
    def entrypoint(  # type: ignore[override]
        self,
        train_dataset: DataArtifact,
        test_dataset: DataArtifact,
        validation_dataset: DataArtifact,
        statistics: StatisticsArtifact,
        schema: SchemaArtifact,
        config: BasePreprocessorConfig,
        context: StepContext,
    ) -> Output(  # type:ignore[valid-type]
        train_transformed=DataArtifact,
        test_transformed=DataArtifact,
        validation_transformed=DataArtifact,
    ):
        """Base entrypoint for any Preprocessor implementation"""
