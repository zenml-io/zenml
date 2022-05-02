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
from typing import Optional, Sequence

import pandas as pd
from deepchecks.core import SuiteResult

from zenml.artifacts import DataAnalysisArtifact
from zenml.steps.step_interfaces.base_drift_detection_step import (
    BaseDriftDetectionConfig,
    BaseDriftDetectionStep,
)


class DeepchecksProfileConfig(BaseDriftDetectionConfig):
    """Config class for DeepChecks profile steps."""

    column_mapping: Optional[ColumnMapping]
    profile_sections: Sequence[str]


class DeepchecksProfileStep(BaseDriftDetectionStep):
    """Simple step implementation which implements DeepChecks's functionality for
    creating a profile."""

    OUTPUT_SPEC = {
        "check_result": DataAnalysisArtifact,
    }

    def entrypoint(  # type: ignore[override]
        self,
        reference_dataset: pd.DataFrame,
        comparison_dataset: pd.DataFrame,
        config: DeepChecksProfileConfig,
    ) -> SuiteResult:
        """Main entrypoint for the DeepChecks categorical target drift detection
        step.

        Args:
            reference_dataset: a Pandas dataframe
            comparison_dataset: a Pandas dataframe of new data you wish to
                compare against the reference data
            config: the configuration for the step

        Returns:
            profile: dictionary report extracted from an DeepChecks Profile
              generated for the data drift
            dashboard: HTML report extracted from an DeepChecks Dashboard
              generated for the data drift
        """
        sections, tabs = config.get_profile_sections_and_tabs()
        data_drift_dashboard = Dashboard(tabs=tabs)
        data_drift_dashboard.calculate(
            reference_dataset,
            comparison_dataset,
            column_mapping=config.column_mapping or None,
        )
        data_drift_profile = Profile(sections=sections)
        data_drift_profile.calculate(
            reference_dataset,
            comparison_dataset,
            column_mapping=config.column_mapping or None,
        )
        return [data_drift_profile.object(), data_drift_dashboard.html()]
