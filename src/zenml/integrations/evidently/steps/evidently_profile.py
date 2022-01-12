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
from typing import Optional, cast

from evidently.model_profile import Profile  # type: ignore
from evidently.pipeline.column_mapping import ColumnMapping  # type: ignore
from evidently.profile_sections import (  # type: ignore
    CatTargetDriftProfileSection,
    ClassificationPerformanceProfileSection,
    DataDriftProfileSection,
    NumTargetDriftProfileSection,
    ProbClassificationPerformanceProfileSection,
    RegressionPerformanceProfileSection,
)
from evidently.profile_sections.base_profile_section import (  # type: ignore
    ProfileSection,
)

from zenml.artifacts import DataArtifact
from zenml.steps import StepContext
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

    def get_profile_section(self) -> ProfileSection:
        try:
            return profile_mapper[self.profile_section]()
        except KeyError:
            raise ValueError(
                f"Invalid profile section: {self.profile_section}"
                "\n\n"
                "Valid and supported options are: \n"
                "- datadrift, \n"
                "- categoricaltargetdrift, \n"
                "- numericaltargetdrift, \n"
                "- classificationmodelperformance, \n"
                "- regressionmodelperformance, \n"
                "- probabilisticmodelperformance \n"
            )

    column_mapping: Optional[ColumnMapping]
    profile_section: str


class EvidentlyProfileStep(BaseDriftDetectionStep):
    """Simple step implementation which implements Evidently's functionality for
    creating a profile."""

    def entrypoint(  # type: ignore[override]
        self,
        reference_dataset: DataArtifact,
        comparison_dataset: DataArtifact,
        config: EvidentlyProfileConfig,
        context: StepContext,
    ) -> dict:  # type: ignore[type-arg]
        """Main entrypoint for the Evidently categorical target drift detection
        step.

        Args:
            reference_dataset: a Pandas dataframe
            comparison_dataset: a Pandas dataframe of new data you wish to
                compare against the reference data
            config: the configuration for the step
            context: the context of the step

        Returns:
            a dict containing the results of the drift detection
        """

        data_drift_profile = Profile(sections=[config.get_profile_section()])
        data_drift_profile.calculate(
            reference_dataset,
            comparison_dataset,
            column_mapping=config.column_mapping or None,
        )
        return cast(dict, data_drift_profile.object())  # type: ignore[type-arg]
