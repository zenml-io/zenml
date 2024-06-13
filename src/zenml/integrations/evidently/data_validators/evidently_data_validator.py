#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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

import os
from typing import (
    Any,
    ClassVar,
    Dict,
    Optional,
    Sequence,
    Tuple,
    Type,
)

import pandas as pd
from evidently.pipeline.column_mapping import ColumnMapping  # type: ignore
from evidently.report import Report  # type: ignore
from evidently.test_suite import TestSuite  # type: ignore

from zenml.data_validators import BaseDataValidator, BaseDataValidatorFlavor
from zenml.integrations.evidently.flavors.evidently_data_validator_flavor import (
    EvidentlyDataValidatorFlavor,
)
from zenml.integrations.evidently.metrics import EvidentlyMetricConfig
from zenml.integrations.evidently.tests import EvidentlyTestConfig
from zenml.logger import get_logger
from zenml.utils import source_utils

logger = get_logger(__name__)


class EvidentlyDataValidator(BaseDataValidator):
    """Evidently data validator stack component."""

    NAME: ClassVar[str] = "Evidently"
    FLAVOR: ClassVar[Type[BaseDataValidatorFlavor]] = (
        EvidentlyDataValidatorFlavor
    )

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
                option_cls = source_utils.load(option_clspath)
            except AttributeError:
                raise ValueError(
                    f"Could not map the `{option_clspath}` Evidently option "
                    f"class path to a valid class."
                )
            option = option_cls(**option_args)
            options.append(option)

        return options

    @staticmethod
    def _set_nltk_data_path() -> None:
        """Set the NLTK data path to the current working directory.

        This is necessary because the default download directory is not writable
        in some Docker containers.
        
        Raises:
            ImportError: if NLTK is not installed.
        """
        try:
            from nltk.data import (  # type: ignore[import-untyped]
                path as nltk_path,
            )
        except ImportError:
            raise ImportError(
                "NLTK is not installed. Please install NLTK to use "
                "Evidently text metrics and tests."
            )

        # Configure NLTK to use the current working directory to download and
        # lookup data. This is necessary because the default download directory
        # is not writable in some Docker containers.
        os.environ["NLTK_DATA"] = os.getcwd()
        nltk_path.append(os.getcwd())

    @staticmethod
    def _download_nltk_data() -> None:
        """Download NLTK data for text metrics and tests.

        Raises:
            ImportError: if NLTK is not installed.
        """
        try:
            import nltk  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError(
                "NLTK is not installed. Please install NLTK to use "
                "Evidently text metrics and tests."
            )
        # Download NLTK data. We need this later on for the Evidently text report.
        nltk.download("words", download_dir=os.getcwd())
        nltk.download("wordnet", download_dir=os.getcwd())
        nltk.download("omw-1.4", download_dir=os.getcwd())

    def data_profiling(
        self,
        dataset: pd.DataFrame,
        comparison_dataset: Optional[pd.DataFrame] = None,
        profile_list: Optional[Sequence[EvidentlyMetricConfig]] = None,
        column_mapping: Optional[ColumnMapping] = None,
        report_options: Sequence[Tuple[str, Dict[str, Any]]] = [],
        download_nltk_data: bool = False,
        **kwargs: Any,
    ) -> Report:
        """Analyze a dataset and generate a data report with Evidently.

        The method takes in an optional list of Evidently options to be passed
        to the report constructor (`report_options`). Each element in the list must be
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
            dataset: Target dataset to be profiled. When a comparison dataset
                is provided, this dataset is considered the reference dataset.
            comparison_dataset: Optional dataset to be used for data profiles
                that require a current dataset for comparison (e.g data drift
                profiles).
            profile_list: List of Evidently metric configurations to
                be included in the report. If not provided, all available
                metric presets will be included.
            column_mapping: Properties of the DataFrame columns used
            report_options: List of Evidently options to be passed to the
                report constructor.
            download_nltk_data: Whether to download NLTK data for text metrics.
                Defaults to False.
            **kwargs: Extra keyword arguments (unused).

        Returns:
            The Evidently Report as JSON object and as HTML.
        """
        self._set_nltk_data_path()
        if download_nltk_data:
            self._download_nltk_data()

        profile_list = profile_list or EvidentlyMetricConfig.default_metrics()
        metrics = [metric.to_evidently_metric() for metric in profile_list]

        unpacked_report_options = self._unpack_options(report_options)

        report = Report(metrics=metrics, options=unpacked_report_options)

        report.run(
            reference_data=dataset,
            current_data=comparison_dataset,
            column_mapping=column_mapping,
        )

        return report

    def data_validation(
        self,
        dataset: Any,
        comparison_dataset: Optional[Any] = None,
        check_list: Optional[Sequence[EvidentlyTestConfig]] = None,
        test_options: Sequence[Tuple[str, Dict[str, Any]]] = [],
        column_mapping: Optional[ColumnMapping] = None,
        download_nltk_data: bool = False,
        **kwargs: Any,
    ) -> TestSuite:
        """Validate a dataset with Evidently.

        Args:
            dataset: Target dataset to be validated.
            comparison_dataset: Optional dataset to be used for data validation
                that require a baseline for comparison (e.g data drift
                validation).
            check_list: List of Evidently test configurations to be
                included in the test suite. If not provided, all available
                test presets will be included.
            test_options: List of Evidently options to be passed to the
                test suite constructor.
            column_mapping: Properties of the DataFrame columns used
            download_nltk_data: Whether to download NLTK data for text tests.
                Defaults to False.
            **kwargs: Extra keyword arguments (unused).

        Returns:
            The Evidently Test Suite as JSON object and as HTML.
        """
        if download_nltk_data:
            self._download_nltk_data()

        check_list = check_list or EvidentlyTestConfig.default_tests()
        tests = [test.to_evidently_test() for test in check_list]

        unpacked_test_options = self._unpack_options(test_options)

        test_suite = TestSuite(tests=tests, options=unpacked_test_options)
        test_suite.run(
            reference_data=dataset,
            current_data=comparison_dataset,
            column_mapping=column_mapping,
        )

        return test_suite
