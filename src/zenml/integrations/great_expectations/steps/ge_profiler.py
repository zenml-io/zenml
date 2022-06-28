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
from great_expectations.data_context.types.resource_identifiers import (  # type: ignore[import]
    ExpectationSuiteIdentifier,
)
from great_expectations.profile.user_configurable_profiler import (  # type: ignore[import]
    UserConfigurableProfiler,
)
from pydantic import Field

from zenml.integrations.great_expectations.data_validators.ge_data_validator import (
    GreatExpectationsDataValidator,
)
from zenml.integrations.great_expectations.steps.utils import (
    create_batch_request,
)
from zenml.logger import get_logger
from zenml.steps import BaseStep, BaseStepConfig

logger = get_logger(__name__)


class GreatExpectationsProfilerConfig(BaseStepConfig):
    """Config class for a Great Expectations profiler step.

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

    def entrypoint(  # type: ignore[override]
        self,
        dataset: pd.DataFrame,
        config: GreatExpectationsProfilerConfig,
    ) -> ExpectationSuite:
        """Standard Great Expectations data profiling step entrypoint.

        Args:
            dataset: The dataset from which the expectation suite will be inferred.
            config: The configuration for the step.

        Returns:
            The generated Great Expectations suite.
        """
        context = GreatExpectationsDataValidator.get_data_context()

        suite_exists = False
        if context.expectations_store.has_key(  # noqa
            ExpectationSuiteIdentifier(config.expectation_suite_name)
        ):
            suite_exists = True
            suite = context.get_expectation_suite(config.expectation_suite_name)
            if not config.overwrite_existing_suite:
                logger.info(
                    f"Expectation Suite `{config.expectation_suite_name}` "
                    f"already exists and `overwrite_existing_suite` is not set "
                    f"in the step configuration. Skipping re-running the "
                    f"profiler."
                )
                return suite

        batch_request = create_batch_request(
            context, dataset, config.data_asset_name
        )

        try:
            if suite_exists:
                validator = context.get_validator(
                    batch_request=batch_request,
                    expectation_suite_name=config.expectation_suite_name,
                )
            else:
                validator = context.get_validator(
                    batch_request=batch_request,
                    create_expectation_suite_with_name=config.expectation_suite_name,
                )

            profiler = UserConfigurableProfiler(
                profile_dataset=validator, **config.profiler_kwargs
            )

            suite = profiler.build_suite()
            context.save_expectation_suite(
                expectation_suite=suite,
                expectation_suite_name=config.expectation_suite_name,
            )

            context.build_data_docs()
        finally:
            context.delete_datasource(batch_request.datasource_name)

        return suite
