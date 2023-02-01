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

from typing import Any, ClassVar, Dict, List, Optional, Sequence, Tuple, Type, Union

import pandas as pd
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
from evidently.base_metric import Metric
from evidently.metric_preset.metric_preset import MetricPreset
from evidently.utils.generators import BaseGenerator
from evidently.report import Report  # type: ignore
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

from zenml.data_validators import BaseDataValidator, BaseDataValidatorFlavor
from zenml.integrations.evidently.flavors.evidently_data_validator_flavor import (
    EvidentlyDataValidatorFlavor,
)
from zenml.logger import get_logger
from zenml.utils.source_utils import load_source_path_class

logger = get_logger(__name__)


class EvidentlyDataValidator(BaseDataValidator):
    """Evidently data validator stack component."""

    NAME: ClassVar[str] = "Evidently"
    FLAVOR: ClassVar[
        Type[BaseDataValidatorFlavor]
    ] = EvidentlyDataValidatorFlavor

    @classmethod
    def _unpack_options(
        cls, option_list: Sequence[Tuple[str, Dict[str, Any]]]
    ) -> Sequence[Any]:
        """Unpack Evidently options.

        Implements de-serialization for [Evidently options](https://docs.evidentlyai.com/user-guide/customization)
        that can be passed as constructor arguments when creating Profile and
        Dashboard objects. The convention used is that each item in the list
        consists of two elements:

        * a string containing the full class path of a `dataclass` based
        class with Evidently options
        * a dictionary with kwargs used as parameters for the option instance

        For example,

        ```python
            options = [
                (
                    "evidently.options.ColorOptions",{
                        "primary_color": "#5a86ad",
                        "fill_color": "#fff4f2",
                        "zero_line_color": "#016795",
                        "current_data_color": "#c292a1",
                        "reference_data_color": "#017b92",
                    }
                ),
            ]
        ```

        This is the same as saying:

        ```python
        from evidently.options import ColorOptions

        color_scheme = ColorOptions()
        color_scheme.primary_color = "#5a86ad"
        color_scheme.fill_color = "#fff4f2"
        color_scheme.zero_line_color = "#016795"
        color_scheme.current_data_color = "#c292a1"
        color_scheme.reference_data_color = "#017b92"
        ```

        Args:
            option_list: list of packed Evidently options

        Returns:
            A list of unpacked Evidently options

        Raises:
            ValueError: if one of the passed Evidently class paths cannot be
                resolved to an actual class.
        """
        options = []
        for option_clspath, option_args in option_list:
            try:
                option_cls = load_source_path_class(option_clspath)
            except AttributeError:
                raise ValueError(
                    f"Could not map the `{option_clspath}` Evidently option "
                    f"class path to a valid class."
                )
            option = option_cls(**option_args)
            options.append(option)

        return options

    def data_profiling(
        self,
        dataset: pd.DataFrame,
        comparison_dataset: Optional[pd.DataFrame] = None,
        metric_list: List[Union[Metric, MetricPreset, BaseGenerator]] = None,
        column_mapping: Optional[ColumnMapping] = None,
        report_options: Sequence[Tuple[str, Dict[str, Any]]] = [],
        **kwargs: Any,
    ) -> Report:
        """Analyze a dataset and generate a data profile with Evidently.

        The method takes in an optional list of Evidently options to be passed
        to the profile constructor (`profile_options`) and the dashboard
        constructor (`dashboard_options`). Each element in the list must be
        composed of two items: the first is a full class path of an Evidently
        option `dataclass`, the second is a dictionary of kwargs with the actual
        option parameters, e.g.:

        ```python
        options = [
            (
                "evidently.options.ColorOptions",{
                    "primary_color": "#5a86ad",
                    "fill_color": "#fff4f2",
                    "zero_line_color": "#016795",
                    "current_data_color": "#c292a1",
                    "reference_data_color": "#017b92",
                }
            ),
        ]
        ```

        Args:
            dataset: Target dataset to be profiled.
            comparison_dataset: Optional dataset to be used for data profiles
                that require a baseline for comparison (e.g data drift profiles).
            metric_list: Optional list identifying the categories of Evidently
                data profiles to be generated.
            column_mapping: Properties of the DataFrame columns used
            report_options: List of Evidently options to be passed to the
                report constructor.
            **kwargs: Extra keyword arguments (unused).

        Returns:
            The Evidently Report as JSON object and as HTML.
        """
        unpacked_report_options = self._unpack_options(report_options)

        report = Report(metrics=metric_list, options=unpacked_report_options)
        report.run(
            reference_data=dataset,
            current_data=comparison_dataset,
            column_mapping=column_mapping,
        )

        return report
