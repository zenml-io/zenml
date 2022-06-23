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

from typing import Any, Dict, List, Optional, cast

import pandas as pd
from great_expectations.checkpoint.types.checkpoint_result import (  # type: ignore[import]
    CheckpointResult,
)
from great_expectations.core.batch import (  # type: ignore[import]
    RuntimeBatchRequest,
)
from great_expectations.data_context.data_context import (  # type: ignore[import]
    DataContext,
)

from zenml.environment import Environment
from zenml.integrations.great_expectations.data_validators.ge_data_validator import (
    GreatExpectationsDataValidator,
)
from zenml.steps import (
    STEP_ENVIRONMENT_NAME,
    BaseStep,
    BaseStepConfig,
    StepEnvironment,
)


class GreatExpectationsValidatorConfig(BaseStepConfig):
    """Config class for a Great Expectations checkpoint step."""

    expectation_suite_name: str
    data_asset_name: Optional[str] = None
    action_list: Optional[List[Dict[str, Any]]] = None
    exit_on_error: bool = False


class GreatExpectationsValidatorStep(BaseStep):
    """Standard Great Expectation data validation step implementation.

    Use this standard Great Expectations data validation step to run an
    existing Expectation Suite on an input dataset [as covered in the official GE documentation](https://docs.greatexpectations.io/docs/guides/validation/how_to_validate_data_by_running_a_checkpoint).
    """

    def entrypoint(  # type: ignore[override]
        self,
        dataset: pd.DataFrame,
        condition: bool,
        config: GreatExpectationsValidatorConfig,
    ) -> CheckpointResult:
        """Standard Great Expectation data validation step entrypoint.

        Args:
            dataset: The dataset to run the expectation suite on.
            condition: This dummy argument can be used as a condition to enforce
                that this step is only run after another step has completed. This
                is useful for example if the Expectation Suite used to validate
                the data is computed in a `GreatExpectationsProfilerStep` that
                is part of the same pipeline.
            config: The configuration for the step.

        Returns:
            The Great Expectation validation (checkpoint) result.
        """
        # get pipeline name, step name and run id
        step_env = cast(StepEnvironment, Environment()[STEP_ENVIRONMENT_NAME])
        pipeline_name = step_env.pipeline_name
        run_id = step_env.pipeline_run_id
        step_name = step_env.step_name

        context = GreatExpectationsDataValidator.get_data_context()

        datasource_name = f"{run_id}_{step_name}"
        data_connector_name = datasource_name
        checkpoint_name = datasource_name
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

        action_list = config.action_list or [
            {
                "name": "store_validation_result",
                "action": {"class_name": "StoreValidationResultAction"},
            },
            {
                "name": "store_evaluation_params",
                "action": {"class_name": "StoreEvaluationParametersAction"},
            },
            {
                "name": "update_data_docs",
                "action": {"class_name": "UpdateDataDocsAction"},
            },
        ]

        checkpoint_config = {
            "name": checkpoint_name,
            "run_name_template": f"{run_id}",
            "config_version": 1,
            "class_name": "Checkpoint",
            "expectation_suite_name": config.expectation_suite_name,
            "action_list": action_list,
        }
        batch_request = RuntimeBatchRequest(
            datasource_name=datasource_name,
            data_connector_name=data_connector_name,
            data_asset_name=data_asset_name,
            runtime_parameters={"batch_data": dataset},
            batch_identifiers={batch_identifier: batch_identifier},
        )

        context.add_checkpoint(**checkpoint_config)

        try:
            results = context.run_checkpoint(
                checkpoint_name=checkpoint_name,
                validations=[{"batch_request": batch_request}],
            )
        finally:
            try:
                context.delete_datasource(datasource_name)
            except AttributeError:
                # this is required to account for a bug in the BaseDataContext
                # class that doesn't account for the fact that an in-memory
                # data context doesn't have a `_save_project_config` method.
                # see: https://github.com/great-expectations/great_expectations/issues/5373
                pass

            context.delete_checkpoint(checkpoint_name)

        return results
