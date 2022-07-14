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
"""Implementation of the Evidently data validator."""

from evidently.dashboard import Dashboard  # type: ignore
from evidently.dashboard.tabs import (  # type: ignore
    CatTargetDriftTab,
    ClassificationPerformanceTab,
    DataDriftTab,
    DataQualityTab,
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
    DataQualityProfileSection,
    NumTargetDriftProfileSection,
    ProbClassificationPerformanceProfileSection,
    RegressionPerformanceProfileSection,
)
from evidently.model_profile.sections.base_profile_section import (  # type: ignore
    ProfileSection,
)
from evidently.pipeline.column_mapping import ColumnMapping  # type: ignore
from typing import Any, ClassVar, List, Optional, Sequence, Tuple

import pandas as pd

from zenml.data_validators import BaseDataValidator
from zenml.integrations.evidently import EVIDENTLY_DATA_VALIDATOR_FLAVOR
from zenml.logger import get_logger

logger = get_logger(__name__)


profile_mapper = {
    "datadrift": DataDriftProfileSection,
    "categoricaltargetdrift": CatTargetDriftProfileSection,
    "numericaltargetdrift": NumTargetDriftProfileSection,
    "dataquality": DataQualityProfileSection,
    "classificationmodelperformance": ClassificationPerformanceProfileSection,
    "regressionmodelperformance": RegressionPerformanceProfileSection,
    "probabilisticmodelperformance": ProbClassificationPerformanceProfileSection,
}

dashboard_mapper = {
    "dataquality": DataQualityTab,
    "datadrift": DataDriftTab,
    "categoricaltargetdrift": CatTargetDriftTab,
    "numericaltargetdrift": NumTargetDriftTab,
    "classificationmodelperformance": ClassificationPerformanceTab,
    "regressionmodelperformance": RegressionPerformanceTab,
    "probabilisticmodelperformance": ProbClassificationPerformanceTab,
}


def get_profile_sections_and_tabs(
    profile_list: Optional[Sequence[str]],
    verbose_level: int,
) -> Tuple[List[ProfileSection], List[Tab]]:
    """Get the profile sections and dashboard tabs for a profile list.

    Args:
        profile_list: List of identifiers for Evidently profiles.

    Returns:
        A tuple of two lists of profile sections and tabs.

    Raises:
        ValueError: if the profile_section is not supported.
    """
    profile_list = profile_list or list(profile_mapper.keys())
    try:
        return (
            [profile_mapper[profile]() for profile in profile_list],
            [
                dashboard_mapper[profile](verbose_level=verbose_level)
                for profile in profile_list
            ],
        )
    except KeyError as e:
        nl = "\n"
        raise ValueError(
            f"Invalid profile sections: {profile_list} \n\n"
            f"Valid and supported options are: {nl}- "
            f'{f"{nl}- ".join(list(profile_mapper.keys()))}'
        ) from e


class EvidentlyDataValidator(BaseDataValidator):
    """Evidently data validator stack component."""

    # Class Configuration
    FLAVOR: ClassVar[str] = EVIDENTLY_DATA_VALIDATOR_FLAVOR
    NAME: ClassVar[str] = "Evidently"

    def data_profiling(
        self,
        dataset: pd.DataFrame,
        comparison_dataset: Optional[pd.DataFrame] = None,
        profile_list: Optional[Sequence[str]] = None,
        column_mapping: Optional[ColumnMapping] = None,
        verbose_level: int = 1,
        **kwargs: Any,
    ) -> Tuple[Profile, Dashboard]:
        """Analyze a dataset and generate a data profile with Evidently.

        Args:
            dataset: Target dataset to be profiled.
            comparison_dataset: Optional dataset to be used for data profiles
                that require a baseline for comparison (e.g data drift profiles).
            profile_list: Optional list identifying the categories of Evidently
                data profiles to be generated.
            verbose_level: Level of verbosity for the Evidently dashboards.
            **kwargs: Extra keyword arguments (unused).

        Returns:
            The Evidently Profile and Dashboard objects corresponding to the set
            of generated profiles.
        """
        sections, tabs = get_profile_sections_and_tabs(
            profile_list, verbose_level
        )
        dashboard = Dashboard(tabs=tabs)
        dashboard.calculate(
            reference_data=dataset,
            current_data=comparison_dataset,
            column_mapping=column_mapping,
        )
        profile = Profile(sections=sections)
        profile.calculate(
            reference_data=dataset,
            current_data=comparison_dataset,
            column_mapping=column_mapping,
        )
        return profile, dashboard
