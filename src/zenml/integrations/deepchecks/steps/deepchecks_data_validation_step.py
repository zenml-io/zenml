#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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

import pandas as pd
from deepchecks import Dataset
from deepchecks.core import SuiteResult

from zenml.artifacts import DataAnalysisArtifact
from zenml.steps.step_interfaces.base_drift_detection_step import (
    BaseDriftDetectionConfig,
    BaseDriftDetectionStep,
)


class DeepchecksDataValidatorConfig(BaseDriftDetectionConfig):
    """Config class for DeepChecks data validator steps."""


class DeepchecksDataValidatorStep(BaseDriftDetectionStep):
    """Simple step implementation which implements Deepchecks functionality for
    data validation."""

    OUTPUT_SPEC = {
        "check_result": DataAnalysisArtifact,
    }

    def entrypoint(  # type: ignore[override]
        self,
        df_train: pd.DataFrame,
        df_test: pd.DataFrame,
        config: DeepchecksDataValidatorConfig,
    ) -> SuiteResult:
        """Main entrypoint for the DeepChecks categorical target drift detection
        step.

        Args:
            df_train: a Pandas dataframe
            df_test: a Pandas dataframe of new data you wish to
                compare against the reference data
            config: the configuration for the step

        Returns:
            profile: dictionary report extracted from an DeepChecks Profile
              generated for the data drift
            dashboard: HTML report extracted from an DeepChecks Dashboard
              generated for the data drift
        """

        Dataset(df_train)
        Dataset(df_test)

        return result
