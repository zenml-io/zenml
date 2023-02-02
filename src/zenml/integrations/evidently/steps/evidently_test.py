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

from typing import Any, Dict, List, Optional, Sequence, Tuple, Union, cast

import pandas as pd
from evidently.pipeline.column_mapping import (  # type: ignore[import]
    ColumnMapping,
)
from pydantic import Field

from zenml.integrations.evidently.data_validators import EvidentlyDataValidator
from zenml.integrations.evidently.steps.evidently_report import (
    EvidentlyColumnMapping,
)
from zenml.steps import Output
from zenml.steps.base_parameters import BaseParameters
from zenml.steps.base_step import BaseStep


class EvidentlyTestParameters(BaseParameters):
    """Parameters class for Evidently profile steps.

    Attributes:
        column_mapping: properties of the DataFrame columns used
        ignored_cols: columns to ignore during the Evidently profile step
        tests: a list of tests, test presets or a dictionary of
            tests to use with the gnerate_column_tests method.

            The tests and the test presets should be strings with the exact
            names as in the evidently library. The dictionary should be used when
            you want to choose a test for more than one columns. The structure
            of the dictionary should be as follows:
            {
                "test": "test_name",
                "parameters": {},
                "columns": ["column1", "column2"]
            }
        test_options: a list of tuples containing the name of the test
            and a dictionary of options for the test.
    """

    column_mapping: Optional[EvidentlyColumnMapping] = None
    ignored_cols: Optional[List[str]] = None
    tests: List[Union[str, Dict[str, Any]]] = None
    test_options: Sequence[Tuple[str, Dict[str, Any]]] = Field(
        default_factory=list
    )

    class Config:
        """Pydantic config class."""

        arbitrary_types_allowed = True


class EvidentlyTestStep(BaseStep):
    """Step implementation implementing an Evidently Test Step."""

    def entrypoint(
        self,
        reference_dataset: pd.DataFrame,
        comparison_dataset: pd.DataFrame,
        params: EvidentlyTestParameters,
    ) -> Output(  # type:ignore[valid-type]
        test_json=str, test_html=str
    ):
        """Main entrypoint for the Evidently test step.

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
            A tuple containing the test json and html
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
        test_suite = data_validator.data_validation(
            dataset=reference_dataset,
            comparison_dataset=comparison_dataset,
            check_list=params.tests,
            column_mapping=column_mapping,
            test_options=params.test_options,
        )
        return [test_suite.json(), test_suite.show().data]


def evidently_test_step(
    step_name: str,
    params: EvidentlyTestParameters,
) -> BaseStep:
    """Shortcut function to create a new instance of the EvidentlyTestStep.

    The returned EvidentlyTestStep can be used in a pipeline to
    run model tests on two input pd.DataFrame datasets and return the
    results as an Evidently TestSuite object in JSON and HTML formats.

    Args:
        step_name: The name of the step
        params: The parameters for the step

    Returns:
        a EvidentlyTestStep step instance
    """
    return EvidentlyTestStep(name=step_name, params=params)
