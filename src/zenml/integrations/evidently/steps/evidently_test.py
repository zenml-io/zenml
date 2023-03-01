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
"""Implementation of the Evidently Test Step."""

from typing import Any, Dict, List, Optional, Sequence, Tuple, cast

import pandas as pd
from pydantic import Field, root_validator

from zenml.integrations.evidently.column_mapping import (
    EvidentlyColumnMapping,
)
from zenml.integrations.evidently.data_validators import EvidentlyDataValidator
from zenml.integrations.evidently.tests import EvidentlyTestConfig
from zenml.steps import Output
from zenml.steps.base_parameters import BaseParameters
from zenml.steps.base_step import BaseStep


class EvidentlyTestParameters(BaseParameters):
    """Parameters class for Evidently profile steps.

    Attributes:
        column_mapping: properties of the DataFrame columns used
        ignored_cols: columns to ignore during the Evidently profile step
        tests: a list of Evidently test configuration to use for the test suite.
        test_options: a list of tuples containing the name of the test
            and a dictionary of options for the test.
        download_nltk_data: whether to download the NLTK data for the report
            step. Defaults to False.
    """

    column_mapping: Optional[EvidentlyColumnMapping] = None
    ignored_cols: Optional[List[str]] = None
    tests: List[EvidentlyTestConfig]
    test_options: Sequence[Tuple[str, Dict[str, Any]]] = Field(
        default_factory=list
    )
    download_nltk_data: bool = False

    @root_validator(pre=True)
    def default_tests(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Default Evidently tests to use if none are provided.

        If no tests are configured, use all available TestPreset tests
        by default.

        Args:
            values: The valued configured for the EvidentlyTestParameters
                instance.

        Returns:
            The values with the default tests added if no tests were
            configured.
        """
        if not values.get("tests"):
            values["tests"] = EvidentlyTestConfig.default_tests()

        return values

    class Config:
        """Pydantic config class."""

        extra = "forbid"


class EvidentlyBaseTestStep:
    """Base implementation for an Evidently Test Step."""

    def _run_entrypoint(
        self,
        reference_dataset: pd.DataFrame,
        comparison_dataset: Optional[pd.DataFrame],
        params: EvidentlyTestParameters,
    ) -> Output(  # type:ignore[valid-type]
        test_json=str, test_html=str
    ):
        """Evidently test step for one or two datasets.

        Args:
            reference_dataset: a Pandas DataFrame
            comparison_dataset: a Pandas DataFrame of new data you wish to
                compare against the reference data
            params: the parameters for the step

        Raises:
            ValueError: If ignored_cols is an empty list
            ValueError: If column is not found in reference or comparison
                dataset

        Returns:
            A tuple containing the TestSuite in JSON and HTML formats.
        """
        data_validator = cast(
            EvidentlyDataValidator,
            EvidentlyDataValidator.get_active_data_validator(),
        )
        column_mapping = None

        if params.ignored_cols:
            extra_cols = set(params.ignored_cols) - set(
                reference_dataset.columns
            )
            if extra_cols:
                raise ValueError(
                    f"Columns {extra_cols} configured in the ignored_cols "
                    "parameter are not found in the reference dataset."
                )
            reference_dataset = reference_dataset.drop(
                labels=list(params.ignored_cols), axis=1
            )

            if comparison_dataset is not None:
                extra_cols = set(params.ignored_cols) - set(
                    comparison_dataset.columns
                )
                if extra_cols:
                    raise ValueError(
                        f"Columns {extra_cols} configured in the ignored_cols "
                        "parameter are not found in the comparison dataset."
                    )

                comparison_dataset = comparison_dataset.drop(
                    labels=list(params.ignored_cols), axis=1
                )

        if params.column_mapping:
            column_mapping = (
                params.column_mapping.to_evidently_column_mapping()
            )
        test_suite = data_validator.data_validation(
            dataset=reference_dataset,
            comparison_dataset=comparison_dataset,
            check_list=params.tests,
            column_mapping=column_mapping,
            test_options=params.test_options,
            download_nltk_data=params.download_nltk_data,
        )
        return [test_suite.json(), test_suite.show(mode="inline").data]


class EvidentlyTestStep(BaseStep, EvidentlyBaseTestStep):
    """Implementation for an Evidently Test Step using two datasets."""

    def entrypoint(
        self,
        reference_dataset: pd.DataFrame,
        comparison_dataset: pd.DataFrame,
        params: EvidentlyTestParameters,
    ) -> Output(  # type:ignore[valid-type]
        test_json=str, test_html=str
    ):
        """Evidently test step for two datasets.

        Args:
            reference_dataset: a Pandas DataFrame
            comparison_dataset: a Pandas DataFrame of new data you wish to
                compare against the reference data
            params: the parameters for the step

        Returns:
            A tuple containing the Evidently TestSuite in JSON and HTML formats.
        """
        return self._run_entrypoint(
            reference_dataset=reference_dataset,
            comparison_dataset=comparison_dataset,
            params=params,
        )


class EvidentlySingleDatasetTestStep(BaseStep, EvidentlyBaseTestStep):
    """Implementation for an Evidently Test Step using a single dataset."""

    def entrypoint(
        self,
        dataset: pd.DataFrame,
        params: EvidentlyTestParameters,
    ) -> Output(  # type:ignore[valid-type]
        test_json=str, test_html=str
    ):
        """Evidently test step for a single dataset.

        Args:
            dataset: a Pandas DataFrame
            params: the parameters for the step

        Returns:
            A tuple containing the Evidently TestSuite in JSON and HTML formats.
        """
        return self._run_entrypoint(
            reference_dataset=dataset, comparison_dataset=None, params=params
        )


def evidently_test_step(
    step_name: str,
    params: EvidentlyTestParameters,
    single_dataset: bool = False,
    **kwargs: Any,
) -> BaseStep:
    """Create an instance of the Evidently test step.

    The returned step can be used in a pipeline to run an Evidently test suite
    on one or two input pd.DataFrame datasets and return the results as an
    Evidently TestSuite object in JSON and HTML formats.

    Args:
        step_name: The name of the step
        params: The parameters for the step
        single_dataset: Whether to use a single dataset or two datasets
            as input.
        **kwargs: Additional keyword arguments to pass to the step constructor.

    Returns:
        a Evidently test step instance
    """
    if single_dataset:
        return EvidentlySingleDatasetTestStep(
            name=step_name, params=params, **kwargs
        )
    return EvidentlyTestStep(name=step_name, params=params, **kwargs)
