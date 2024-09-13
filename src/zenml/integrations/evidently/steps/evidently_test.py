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
from typing_extensions import Annotated

from zenml import step
from zenml.integrations.evidently.column_mapping import (
    EvidentlyColumnMapping,
)
from zenml.integrations.evidently.data_validators import EvidentlyDataValidator
from zenml.integrations.evidently.tests import EvidentlyTestConfig
from zenml.types import HTMLString


@step
def evidently_test_step(
    reference_dataset: pd.DataFrame,
    comparison_dataset: Optional[pd.DataFrame],
    column_mapping: Optional[EvidentlyColumnMapping] = None,
    ignored_cols: Optional[List[str]] = None,
    tests: Optional[List[EvidentlyTestConfig]] = None,
    test_options: Optional[Sequence[Tuple[str, Dict[str, Any]]]] = None,
    download_nltk_data: bool = False,
) -> Tuple[Annotated[str, "test_json"], Annotated[HTMLString, "test_html"]]:
    """Run an Evidently test suite on one or two pandas datasets.

    Args:
        reference_dataset: a Pandas DataFrame
        comparison_dataset: a Pandas DataFrame of new data you wish to
            compare against the reference data
        column_mapping: properties of the DataFrame columns used
        ignored_cols: columns to ignore during the Evidently profile step
        tests: a list of Evidently test configuration to use for the test suite.
        test_options: a list of tuples containing the name of the test
            and a dictionary of options for the test.
        download_nltk_data: whether to download the NLTK data for the report
            step. Defaults to False.

    Returns:
        A tuple containing the TestSuite in JSON and HTML formats.

    Raises:
        ValueError: If ignored_cols is an empty list or if any column in
            ignored_cols is not found in the reference or comparison dataset.
    """
    if not tests:
        tests = EvidentlyTestConfig.default_tests()

    data_validator = cast(
        EvidentlyDataValidator,
        EvidentlyDataValidator.get_active_data_validator(),
    )

    if ignored_cols:
        extra_cols = set(ignored_cols) - set(reference_dataset.columns)
        if extra_cols:
            raise ValueError(
                f"Columns {extra_cols} configured in the ignored_cols "
                "parameter are not found in the reference dataset."
            )
        reference_dataset = reference_dataset.drop(
            labels=list(ignored_cols), axis=1
        )

        if comparison_dataset is not None:
            extra_cols = set(ignored_cols) - set(comparison_dataset.columns)
            if extra_cols:
                raise ValueError(
                    f"Columns {extra_cols} configured in the ignored_cols "
                    "parameter are not found in the comparison dataset."
                )

            comparison_dataset = comparison_dataset.drop(
                labels=list(ignored_cols), axis=1
            )

    if column_mapping:
        evidently_column_mapping = column_mapping.to_evidently_column_mapping()
    else:
        evidently_column_mapping = None
    test_suite = data_validator.data_validation(
        dataset=reference_dataset,
        comparison_dataset=comparison_dataset,
        check_list=tests,
        column_mapping=evidently_column_mapping,
        test_options=test_options or [],
        download_nltk_data=download_nltk_data,
    )
    return (
        test_suite.json(),
        HTMLString(test_suite.show(mode="inline").data),
    )
