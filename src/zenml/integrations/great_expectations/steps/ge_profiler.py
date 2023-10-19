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
"""Great Expectations data profiling standard step."""

from typing import Any, Dict, Optional

import pandas as pd
from great_expectations.core import (  # type: ignore[import-untyped]
    ExpectationSuite,
)

from zenml import step
from zenml.integrations.great_expectations.data_validators.ge_data_validator import (
    GreatExpectationsDataValidator,
)


@step
def great_expectations_profiler_step(
    dataset: pd.DataFrame,
    expectation_suite_name: str,
    data_asset_name: Optional[str] = None,
    profiler_kwargs: Optional[Dict[str, Any]] = None,
    overwrite_existing_suite: bool = True,
) -> ExpectationSuite:
    """Infer data validation rules from a pandas dataset.

    Args:
        dataset: The dataset from which the expectation suite will be inferred.
        expectation_suite_name: The name of the expectation suite to infer.
        data_asset_name: The name of the data asset to profile.
        profiler_kwargs: A dictionary of keyword arguments to pass to the
            profiler.
        overwrite_existing_suite: Whether to overwrite an existing expectation
            suite.

    Returns:
        The generated Great Expectations suite.
    """
    data_validator = GreatExpectationsDataValidator.get_active_data_validator()

    return data_validator.data_profiling(
        dataset,
        expectation_suite_name=expectation_suite_name,
        data_asset_name=data_asset_name,
        profiler_kwargs=profiler_kwargs or {},
        overwrite_existing_suite=overwrite_existing_suite,
    )
