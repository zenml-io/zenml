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
"""Great Expectations data validation standard step."""

from typing import Any, Dict, List, Optional

import pandas as pd
from great_expectations.checkpoint.checkpoint import (  # type: ignore[import-untyped]
    CheckpointResult,
)

from zenml import step
from zenml.integrations.great_expectations.data_validators.expectations import GreatExpectationExpectationConfig
from zenml.integrations.great_expectations.data_validators.ge_data_validator import (
    GreatExpectationsDataValidator,
)
import great_expectations as ge

@step
def great_expectations_validator_step(
    dataset: pd.DataFrame,
    expectation_suite_name: Optional[str] = None,
    data_asset_name: Optional[str] = None,
    action_list: Optional[List[ge.checkpoint.actions.ValidationAction]] = None,
    expectation_parameters: Optional[Dict[str, Any]] = None,
    expectations_list: Optional[List[GreatExpectationExpectationConfig]] = None,
    result_format: str = "SUMMARY",
    exit_on_error: bool = False,
) -> CheckpointResult:
    """Shortcut function to create a new instance of the GreatExpectationsValidatorStep step.

    The returned GreatExpectationsValidatorStep can be used in a pipeline to
    validate an input pd.DataFrame dataset and return the result as a Great
    Expectations CheckpointResult object. The validation results are also
    persisted in the Great Expectations validation store.

    Args:
        dataset: The dataset to run the expectation suite on.
        expectation_suite_name: The name of the expectation suite to use to
            validate the dataset.
        data_asset_name: The name of the data asset to use to identify the
            dataset in the Great Expectations docs.
        action_list: A list of additional Great Expectations actions to run
            after the validation check.
        exit_on_error: Set this flag to raise an error and exit the pipeline
            early if the validation fails.
        expectation_parameters: Additional parameters to pass to the
            expectation suite.
        expectations_list: A list of expectations to run.
        result_format: The format of the validation results.
            validator.

    Returns:
        The Great Expectations validation (checkpoint) result.

    Raises:
        RuntimeError: if the step is configured to exit on error and the
            data validation failed.
    """
    data_validator = GreatExpectationsDataValidator.get_active_data_validator()

    results = data_validator.data_validation(
        dataset,
        expectation_suite_name=expectation_suite_name,
        data_asset_name=data_asset_name,
        action_list=action_list,
        expectation_parameters=expectation_parameters,
        expectations_list=expectations_list,
        result_format=result_format,
    )

    if exit_on_error and not results.success:
        raise RuntimeError(
            "The Great Expectations validation failed. Check "
            "the logs or the Great Expectations data docs for more "
            "information."
        )

    return results
