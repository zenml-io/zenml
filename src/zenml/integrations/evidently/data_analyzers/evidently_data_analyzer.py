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
from typing import Any, ClassVar, List, Optional, Sequence, Tuple

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

from zenml.data_analyzer.base_data_analyzer import (
    BaseDataAnalyzer,
    BaseDataAnalyzerConfig,
)
from zenml.integrations.evidently import EVIDENTLY_DATA_ANALYZER_FLAVOR
from zenml.steps import Output

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


class EvidentlyDataAnalyzerConfig(BaseDataAnalyzerConfig):
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

    def get_column_mapping(self) -> Optional[ColumnMapping]:
        return ColumnMapping(
            target=self.target,
            prediction=self.prediction,
            datetime=self.datetime,
            id=self.id,
            numerical_features=self.numerical_features,
            categorical_features=self.categorical_features,
            target_names=self.target_names,
        )

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

    profile_sections: Sequence[str]


class EvidentlyDataAnalyzer(BaseDataAnalyzer):
    """Stores evidently configuration options."""

    # Class Configuration
    FLAVOR: ClassVar[str] = EVIDENTLY_DATA_ANALYZER_FLAVOR

    def analyze_tabular(
        self,
        analysis: pd.DataFrame,
        reference: Optional[pd.DataFrame] = None,
        model: Optional[Any] = None,
        config: Optional[EvidentlyDataAnalyzerConfig] = None,
    ) -> Output(  # type:ignore[valid-type]
        profile=dict, dashboard=str
    ):
        """Generic method for analyzing pandas dataframe with Evidently.

        Args:
            config: configuration of the analysis.
            analysis: dataframe to be analyzed.
            reference: optional dataframe which is the reference.
            model: optional model to aid in analysis. In this case, not used.
        Returns:
            profile: dictionary report extracted from an Evidently Profile
              generated for the data drift
            dashboard: HTML report extracted from an Evidently Dashboard
              generated for the data drift
        """
        sections, tabs = config.get_profile_sections_and_tabs()
        data_drift_dashboard = Dashboard(tabs=tabs)
        data_drift_dashboard.calculate(
            reference,
            analysis,
            column_mapping=config.get_column_mapping(),
        )
        data_profile = Profile(sections=sections)
        data_profile.calculate(
            reference,
            analysis,
            column_mapping=config.get_column_mapping(),
        )
        return [data_profile.object(), data_drift_dashboard.html()]
