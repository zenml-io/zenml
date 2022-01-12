#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
from typing import cast

from evidently.model_profile import Profile  # type: ignore
from evidently.pipeline.column_mapping import ColumnMapping  # type: ignore
from evidently.profile_sections import (  # type: ignore
    RegressionPerformanceProfileSection,
)

from zenml.artifacts import DataArtifact
from zenml.steps import StepContext
from zenml.steps.step_interfaces.base_drift_detection_step import (
    BaseDriftDetectionConfig,
    BaseDriftDetectionStep,
)


class EvidentlyRegressionModelPerformanceConfig(BaseDriftDetectionConfig):
    """Config class for the Evidently regression model performance step.

    column_mapping: properties of the dataframe's columns used for regression model performance detection
    """

    column_mapping: ColumnMapping


class EvidentlyRegressionModelPerformanceStep(BaseDriftDetectionStep):
    """Simple step implementation which implements Evidently's functionality for
    calculating regression model performance."""

    def entrypoint(  # type: ignore[override]
        self,
        reference_dataset: DataArtifact,
        comparison_dataset: DataArtifact,
        config: EvidentlyRegressionModelPerformanceConfig,
        context: StepContext,
    ) -> dict:  # type: ignore[type-arg]
        """Main entrypoint for the Evidently regression model performance step.

        Args:
            reference_dataset: a Pandas dataframe
            comparison_dataset: a Pandas dataframe of new data you wish to
                compare against the reference data
            config: the configuration for the step
            context: the context of the step

        Returns:
            a dict containing the results of the model performance
        """
        regression_model_performance_profile = Profile(
            sections=[RegressionPerformanceProfileSection()]
        )
        regression_model_performance_profile.calculate(
            reference_dataset,
            None,
            column_mapping=config.column_mapping,
        )
        return cast(dict, regression_model_performance_profile.object())  # type: ignore[type-arg]
