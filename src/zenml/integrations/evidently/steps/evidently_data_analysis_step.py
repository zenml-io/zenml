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
from evidently.dashboard import Dashboard  # type: ignore
from evidently.dashboard.tabs import (  # type: ignore
    CatTargetDriftTab,
    ClassificationPerformanceTab,
    DataDriftTab,
    NumTargetDriftTab,
    ProbClassificationPerformanceTab,
    RegressionPerformanceTab,
)
from evidently.dashboard.tabs.base_tab import Tab  # type: ignore
from evidently.model_profile import Profile  # type: ignore
from evidently.model_profile.sections import (  # type: ignore
    CatTargetDriftProfileSection,
    ClassificationPerformanceProfileSection,
    DataDriftProfileSection,
    NumTargetDriftProfileSection,
    ProbClassificationPerformanceProfileSection,
    RegressionPerformanceProfileSection,
)
from evidently.model_profile.sections.base_profile_section import (  # type: ignore
    ProfileSection,
)
from evidently.pipeline.column_mapping import ColumnMapping  # type: ignore

from zenml.artifacts import DataAnalysisArtifact
from zenml.integrations.evidently.data_analyzers.evidently_data_analyzer import (
    EvidentlyDataAnalyzer,
    EvidentlyDataAnalyzerConfig,
)
from zenml.steps import Output
from zenml.steps.step_context import StepContext
from zenml.steps.step_interfaces.base_drift_detection_step import (
    BaseDriftDetectionStep,
)


class EvidentlyDataAnalysisStep(BaseDriftDetectionStep):
    """Simple step implementation which implements Evidently's functionality for
    creating a profile."""

    OUTPUT_SPEC = {
        "profile": DataAnalysisArtifact,
        "dashboard": DataAnalysisArtifact,
    }

    def entrypoint(  # type: ignore[override]
        self,
        context: StepContext,
        reference_dataset: pd.DataFrame,
        comparison_dataset: pd.DataFrame,
        config: EvidentlyDataAnalyzerConfig,
    ) -> Output(  # type:ignore[valid-type]
        profile=dict, dashboard=str
    ):
        """Main entrypoint for the Evidently data analysis step.

        Args:
            reference_dataset: a Pandas dataframe
            comparison_dataset: a Pandas dataframe of new data you wish to
                compare against the reference data
            config: the configuration for the step

        Returns:
            profile: dictionary report extracted from an Evidently Profile
              generated for the data drift
            dashboard: HTML report extracted from an Evidently Dashboard
              generated for the data drift
        """
        data_analyzer = context.stack.data_analyzer
        if not isinstance(data_analyzer, EvidentlyDataAnalyzer):
            raise ValueError(
                "The active stack needs to have a Evidently data analyzer component registered "
                "to be able to use `evidently_data_analyzer` step. "
                "You can create a new stack with a Data Analyzer component or update "
                "your existing stack to add this component, e.g.:\n\n"
                "  'zenml data-analyzer register evidently_data_analyzer --flavor=evidently' ...\n"
                "  'zenml stack register stack-name -dd evidently_data_analyzer ...'\n"
            )
        data_profile, data_drift_dashboard = data_analyzer.analyze_tabular(
            reference_dataset, comparison_dataset, config=config
        )
        return [data_profile.object(), data_drift_dashboard.html()]
