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
"""Base analyzer step."""

from abc import abstractmethod

from zenml.artifacts import DataArtifact, SchemaArtifact, StatisticsArtifact
from zenml.steps import BaseStep, BaseStepConfig, Output, StepContext


class BaseAnalyzerConfig(BaseStepConfig):
    """Base class for analyzer step configurations."""


class BaseAnalyzerStep(BaseStep):
    """Base step implementation for any analyzer step implementation."""

    @abstractmethod
    def entrypoint(  # type: ignore[override]
        self,
        dataset: DataArtifact,
        config: BaseAnalyzerConfig,
        context: StepContext,
    ) -> Output(  # type:ignore[valid-type]
        statistics=StatisticsArtifact, schema=SchemaArtifact
    ):
        """Base entrypoint for any analyzer implementation.

        Args:
            dataset: The dataset to analyze.
            config: The configuration for the step.
            context: The context for the step.

        Returns:
            The statistics and the schema of the given dataset.
        """
