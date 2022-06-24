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

from zenml.environment import Environment
from zenml.integrations.great_expectations.data_validators.ge_data_validator import (
    GreatExpectationsDataValidator,
)
from zenml.integrations.great_expectations.steps.utils import (
    create_batch_request,
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
    """Standard Great Expectations data validation step implementation.

    Use this standard Great Expectations data validation step to run an
    existing Expectation Suite on an input dataset [as covered in the official GE documentation](https://docs.greatexpectations.io/docs/guides/validation/how_to_validate_data_by_running_a_checkpoint).
    """

    def entrypoint(  # type: ignore[override]
        self,
        dataset: pd.DataFrame,
        condition: bool,
        config: GreatExpectationsValidatorConfig,
    ) -> CheckpointResult:
        """Standard Great Expectations data validation step entrypoint.

        Args:
            dataset: The dataset to run the expectation suite on.
            condition: This dummy argument can be used as a condition to enforce
                that this step is only run after another step has completed. This
                is useful for example if the Expectation Suite used to validate
                the data is computed in a `GreatExpectationsProfilerStep` that
                is part of the same pipeline.
            config: The configuration for the step.

        Returns:
            The Great Expectations validation (checkpoint) result.
        """
        # get pipeline name, step name and run id
        step_env = cast(StepEnvironment, Environment()[STEP_ENVIRONMENT_NAME])
        run_id = step_env.pipeline_run_id
        step_name = step_env.step_name

        context = GreatExpectationsDataValidator.get_data_context()

        checkpoint_name = f"{run_id}_{step_name}"

        batch_request = create_batch_request(
            context, dataset, config.data_asset_name
        )

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
        context.add_checkpoint(**checkpoint_config)

        try:
            results = context.run_checkpoint(
                checkpoint_name=checkpoint_name,
                validations=[{"batch_request": batch_request}],
            )
        finally:
            context.delete_datasource(batch_request.datasource_name)
            context.delete_checkpoint(checkpoint_name)

        return results
