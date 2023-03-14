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
"""Implementation of the Evidently Profile Step."""

from typing import Any, Dict, List, Optional, Sequence, Tuple, cast

import pandas as pd
from evidently.model_profile import Profile  # type: ignore[import]
from pydantic import Field

from zenml.integrations.evidently.column_mapping import (
    EvidentlyColumnMapping,
)
from zenml.integrations.evidently.data_validators import EvidentlyDataValidator
from zenml.steps import Output
from zenml.steps.base_parameters import BaseParameters
from zenml.steps.base_step import BaseStep


class EvidentlyProfileParameters(BaseParameters):
    """Parameters class for Evidently profile steps.

    Attributes:
        column_mapping: properties of the DataFrame columns used
        ignored_cols: columns to ignore during the Evidently profile step
        profile_sections: a list identifying the Evidently profile sections to be
            used. The following are valid options supported by Evidently:
            - "datadrift"
            - "categoricaltargetdrift"
            - "numericaltargetdrift"
            - "classificationmodelperformance"
            - "regressionmodelperformance"
            - "probabilisticmodelperformance"
        verbose_level: Verbosity level for the Evidently dashboards. Use
            0 for a brief dashboard, 1 for a detailed dashboard.
        profile_options: Optional list of options to pass to the
            profile constructor. See `EvidentlyDataValidator._unpack_options`.
        dashboard_options: Optional list of options to pass to the
            dashboard constructor. See `EvidentlyDataValidator._unpack_options`.
    """

    column_mapping: Optional[EvidentlyColumnMapping] = None
    ignored_cols: Optional[List[str]] = None
    profile_sections: Optional[Sequence[str]] = None
    verbose_level: int = 1
    profile_options: Sequence[Tuple[str, Dict[str, Any]]] = Field(
        default_factory=list
    )
    dashboard_options: Sequence[Tuple[str, Dict[str, Any]]] = Field(
        default_factory=list
    )


class EvidentlyProfileStep(BaseStep):
    """Step implementation implementing an Evidently Profile Step."""

    def entrypoint(
        self,
        reference_dataset: pd.DataFrame,
        comparison_dataset: pd.DataFrame,
        params: EvidentlyProfileParameters,
    ) -> Output(  # type:ignore[valid-type]
        profile=Profile, dashboard=str
    ):
        """Main entrypoint for the Evidently categorical target drift detection step.

        Args:
            reference_dataset: a Pandas DataFrame
            comparison_dataset: a Pandas DataFrame of new data you wish to
                compare against the reference data
            params: the parameters for the step

        Returns:
            profile: Evidently Profile generated for the data drift
            dashboard: HTML report extracted from an Evidently Dashboard
              generated for the data drift.

        Raises:
            ValueError: If ignored_cols is an empty list
            ValueError: If column is not found in reference or comparison
                dataset
        """
        data_validator = cast(
            EvidentlyDataValidator,
            EvidentlyDataValidator.get_active_data_validator(),
        )
        column_mapping = None

        if params.ignored_cols is None:
            pass

        elif not params.ignored_cols:
            raise ValueError(
                f"Expects None or list of columns in strings, but got {params.ignored_cols}"
            )

        elif not (
            set(params.ignored_cols).issubset(set(reference_dataset.columns))
        ) or not (
            set(params.ignored_cols).issubset(set(comparison_dataset.columns))
        ):
            raise ValueError(
                "Column is not found in reference or comparison datasets"
            )

        else:
            reference_dataset = reference_dataset.drop(
                labels=list(params.ignored_cols), axis=1
            )
            comparison_dataset = comparison_dataset.drop(
                labels=list(params.ignored_cols), axis=1
            )

        if params.column_mapping:
            column_mapping = (
                params.column_mapping.to_evidently_column_mapping()
            )
        profile, dashboard = data_validator.legacy_data_profiling(
            dataset=reference_dataset,
            comparison_dataset=comparison_dataset,
            profile_list=params.profile_sections,
            column_mapping=column_mapping,
            verbose_level=params.verbose_level,
            profile_options=params.profile_options,
            dashboard_options=params.dashboard_options,
        )
        return [profile, dashboard.html()]


def evidently_profile_step(
    step_name: str,
    params: EvidentlyProfileParameters,
) -> BaseStep:
    """Shortcut function to create a new instance of the EvidentlyProfileConfig step.

    The returned EvidentlyProfileStep can be used in a pipeline to
    run model drift analyses on two input pd.DataFrame datasets and return the
    results as an Evidently profile object and a rendered dashboard object.

    Args:
        step_name: The name of the step
        params: The parameters for the step

    Returns:
        a EvidentlyProfileStep step instance.
    """
    return EvidentlyProfileStep(name=step_name, params=params)
