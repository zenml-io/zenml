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
from great_expectations.core import ExpectationSuite  # type: ignore[import]
from pydantic import Field

from zenml.integrations.great_expectations.data_validators.ge_data_validator import (
    GreatExpectationsDataValidator,
)
from zenml.logger import get_logger
from zenml.steps import BaseParameters, BaseStep

logger = get_logger(__name__)


class GreatExpectationsProfilerParameters(BaseParameters):
    """Parameters class for a Great Expectations profiler step.

    Attributes:
        expectation_suite_name: The name of the expectation suite to create
            or update.
        data_asset_name: The name of the data asset to run the expectation suite on.
        profiler_kwargs: A dictionary of keyword arguments to pass to the profiler.
        overwrite_existing_suite: Whether to overwrite an existing expectation suite.
    """

    expectation_suite_name: str
    data_asset_name: Optional[str] = None
    profiler_kwargs: Optional[Dict[str, Any]] = Field(default_factory=dict)
    overwrite_existing_suite: bool = True


class GreatExpectationsProfilerStep(BaseStep):
    """Standard Great Expectations profiling step implementation.

    Use this standard Great Expectations profiling step to build an Expectation
    Suite automatically by running a UserConfigurableProfiler on an input
    dataset [as covered in the official GE documentation](https://docs.greatexpectations.io/docs/guides/expectations/how_to_create_and_edit_expectations_with_a_profiler).
    """

    def entrypoint(
        self,
        dataset: pd.DataFrame,
        params: GreatExpectationsProfilerParameters,
    ) -> ExpectationSuite:
        """Standard Great Expectations data profiling step entrypoint.

        Args:
            dataset: The dataset from which the expectation suite will be inferred.
            params: The parameters for the step.

        Returns:
            The generated Great Expectations suite.
        """
        data_validator = (
            GreatExpectationsDataValidator.get_active_data_validator()
        )

        return data_validator.data_profiling(
            dataset,
            expectation_suite_name=params.expectation_suite_name,
            data_asset_name=params.data_asset_name,
            profiler_kwargs=params.profiler_kwargs,
            overwrite_existing_suite=params.overwrite_existing_suite,
        )


def great_expectations_profiler_step(
    step_name: str,
    params: GreatExpectationsProfilerParameters,
) -> BaseStep:
    """Shortcut function to create a new instance of the GreatExpectationsProfilerStep step.

    The returned GreatExpectationsProfilerStep can be used in a pipeline to
    infer data validation rules from an input pd.DataFrame dataset and return
    them as an Expectation Suite. The Expectation Suite is also persisted in the
    Great Expectations expectation store.

    Args:
        step_name: The name of the step
        params: The parameters for the step

    Returns:
        a GreatExpectationsProfilerStep step instance
    """
    return GreatExpectationsProfilerStep(name=step_name, params=params)
