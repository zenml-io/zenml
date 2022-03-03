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
from typing import List, Optional, Sequence, Tuple

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
from zenml.steps import Output
from zenml.steps.step_interfaces.base_drift_detection_step import (
    BaseDriftDetectionConfig,
    BaseDriftDetectionStep,
)

profile_mapper = {
    "datadrift": DataDriftProfileSection,
    "categoricaltargetdrift": CatTargetDriftProfileSection,
    "numericaltargetdrift": NumTargetDriftProfileSection,
    "classificationmodelperformance": ClassificationPerformanceProfileSection,
    "regressionmodelperformance": RegressionPerformanceProfileSection,
    "probabilisticmodelperformance": ProbClassificationPerformanceProfileSection,
}

dashboard_mapper = {
    "datadrift": DataDriftTab,
    "categoricaltargetdrift": CatTargetDriftTab,
    "numericaltargetdrift": NumTargetDriftTab,
    "classificationmodelperformance": ClassificationPerformanceTab,
    "regressionmodelperformance": RegressionPerformanceTab,
    "probabilisticmodelperformance": ProbClassificationPerformanceTab,
}


class EvidentlyProfileConfig(BaseDriftDetectionConfig):
    """Config class for Evidently profile steps.

    column_mapping: properties of the dataframe's columns used
    profile_section: a string that identifies the profile section to be used.
        The following are valid options supported by Evidently:
        - "datadrift"
        - "categoricaltargetdrift"
        - "numericaltargetdrift"
        - "classificationmodelperformance"
        - "regressionmodelperformance"
        - "probabilisticmodelperformance"
    """

    def get_profile_sections_and_tabs(
        self,
    ) -> Tuple[List[ProfileSection], List[Tab]]:
        try:
            return (
                [
                    profile_mapper[profile]()
                    for profile in self.profile_sections
                ],
                [
                    dashboard_mapper[profile]()
                    for profile in self.profile_sections
                ],
            )
        except KeyError:
            nl = "\n"
            raise ValueError(
                f"Invalid profile section: {self.profile_sections} \n\n"
                f"Valid and supported options are: {nl}- "
                f'{f"{nl}- ".join(list(profile_mapper.keys()))}'
            )

    column_mapping: Optional[ColumnMapping]
    profile_sections: Sequence[str]


class EvidentlyProfileStep(BaseDriftDetectionStep):
    """Simple step implementation which implements Evidently's functionality for
    creating a profile."""

    OUTPUT_SPEC = {
        "profile": DataAnalysisArtifact,
        "dashboard": DataAnalysisArtifact,
    }

    def entrypoint(  # type: ignore[override]
        self,
        reference_dataset: pd.DataFrame,
        comparison_dataset: pd.DataFrame,
        config: EvidentlyProfileConfig,
    ) -> Output(  # type:ignore[valid-type]
        profile=dict, dashboard=str
    ):
        """Main entrypoint for the Evidently categorical target drift detection
        step.

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
