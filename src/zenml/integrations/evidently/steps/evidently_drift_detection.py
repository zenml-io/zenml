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
from evidently.pipeline.column_mapping import ColumnMapping  # type: ignore

# import pandas as pd
# import tensorflow as tf
from zenml.artifacts import DataArtifact, DataDriftArtifact
from zenml.steps import StepContext
from zenml.steps.step_interfaces.base_drift_detection_step import (
    BaseDriftDetectionConfig,
    BaseDriftDetectionStep,
)


class EvidentlyDriftDetectionConfig(BaseDriftDetectionConfig):
    """Config class for the Evidently drift detection step.

    column_mapping: properties of the dataframe's columns used for drift
    detection
    """

    column_mapping: ColumnMapping


class EvidentlyDriftDetectionStep(BaseDriftDetectionStep):
    """Simple step implementation which implements Evidently's functionality for
    detecting data drift."""

    def entrypoint(  # type: ignore[override]
        self,
        reference_dataset: DataArtifact,
        comparison_dataset: DataArtifact,
        config: EvidentlyDriftDetectionConfig,
        context: StepContext,
    ) -> DataDriftArtifact:
        """Main entrypoint for the Evidently drift detection step.

        Args:
            reference_dataset: a Pandas dataframe
            comparison_dataset: a Pandas dataframe of new data you wish to
                compare against the reference data
            config: the configuration for the step
            context: the context of the step

        Returns:
            a DataDriftArtifact containing the results of the drift detection
        """
        return DataDriftArtifact(1)
