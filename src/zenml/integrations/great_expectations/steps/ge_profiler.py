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

from typing import Any, Dict, Optional, cast

import great_expectations as ge  # type: ignore[import]
import great_expectations.exceptions as ge_exceptions  # type: ignore[import]
import pandas as pd
from great_expectations.core import ExpectationSuite  # type: ignore[import]
from great_expectations.core.batch import (  # type: ignore[import]
    RuntimeBatchRequest,
)
from great_expectations.profile.user_configurable_profiler import (  # type: ignore[import]
    UserConfigurableProfiler,
)
from pydantic import Field

from zenml.environment import Environment
from zenml.integrations.great_expectations.data_validators.ge_data_validator import (
    GreatExpectationsDataValidator,
)
from zenml.logger import get_logger
from zenml.steps import (
    STEP_ENVIRONMENT_NAME,
    BaseStep,
    BaseStepConfig,
    StepEnvironment,
)

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
    """Standard Great Expectation profiling step implementation.

    Use this standard Great Expectations profiling step to build an Expectation
    Suite automatically by running a UserConfigurableProfiler on an input
    dataset [as covered in the official GE documentation](https://docs.greatexpectations.io/docs/guides/expectations/how_to_create_and_edit_expectations_with_a_profiler).
    """

    def entrypoint(  # type: ignore[override]
        self,
        dataset: pd.DataFrame,
        config: GreatExpectationsProfilerConfig,
    ) -> ExpectationSuite:
        """Standard Great Expectation data profiling step entrypoint.

        Args:
            dataset: The dataset from which the expectation suite will be inferred.
            config: The configuration for the step.

        Returns:
            The generated Great Expectation suite.
        """
        # get pipeline name, step name and run id
        step_env = cast(StepEnvironment, Environment()[STEP_ENVIRONMENT_NAME])
        pipeline_name = step_env.pipeline_name
        run_id = step_env.pipeline_run_id
        step_name = step_env.step_name

        context = GreatExpectationsDataValidator.get_data_context()

        suite_exists = False
        try:
            suite = context.get_expectation_suite(config.expectation_suite_name)
            if not config.overwrite_existing_suite:
                logger.info(
                    f"Expectation Suite `{config.expectation_suite_name}` "
                    f"already exists and `overwrite_existing_suite` is not set "
                    f"in the step configuration. Skipping re-running the "
                    f"profiler."
                )
                return suite
            suite_exists = True
        except ge_exceptions.DataContextError:
            pass

        datasource_name = f"{run_id}_{step_name}"
        data_connector_name = datasource_name
        data_asset_name = (
            config.data_asset_name or f"{pipeline_name}_{step_name}"
        )
        batch_identifier = "default"

        datasource_config = {
            "name": datasource_name,
            "class_name": "Datasource",
            "module_name": "great_expectations.datasource",
            "execution_engine": {
                "module_name": "great_expectations.execution_engine",
                "class_name": "PandasExecutionEngine",
            },
            "data_connectors": {
                data_connector_name: {
                    "class_name": "RuntimeDataConnector",
                    "batch_identifiers": [batch_identifier],
                },
            },
        }

        context.add_datasource(**datasource_config)

        try:
            batch_request = RuntimeBatchRequest(
                datasource_name=datasource_name,
                data_connector_name=data_connector_name,
                data_asset_name=data_asset_name,
                runtime_parameters={"batch_data": dataset},
                batch_identifiers={batch_identifier: batch_identifier},
            )

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
            context.delete_datasource(datasource_name)

        return suite
