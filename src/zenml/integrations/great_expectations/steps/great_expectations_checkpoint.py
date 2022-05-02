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
from typing import Optional

import great_expectations as ge  # type: ignore[import]
import pandas as pd

from zenml.steps import Output
from zenml.steps.base_step import BaseStep
from zenml.steps.base_step_config import BaseStepConfig


class GreatExpectationsCheckpointConfig(BaseStepConfig):
    """Config class for a Great Expectations checkpoint step."""

    context_path: str
    datasource_name: str
    expectation_suite_name: str
    data_asset_name: Optional[str] = "zenml_step_data_asset"


class GreatExpectationsCheckpointStep(BaseStep):
    """Simple step implementation which implements Great Expectations
    functionality for running a Checkpoint."""

    def entrypoint(  # type: ignore[override]
        self,
        validation_dataset: pd.DataFrame,
        config: GreatExpectationsCheckpointConfig,
    ) -> Output(  # type:ignore[valid-type]
        results=dict, data_doc=str
    ):
        context = ge.get_context()

        checkpoint_config = {
            "name": "example_checkpoint",
            "config_version": 1,
            "class_name": "SimpleCheckpoint",
            "validations": [
                {
                    "batch_request": {
                        "datasource_name": config.datasource_name,
                        "data_connector_name": "default_runtime_data_connector_name",
                        "data_asset_name": config.data_asset_name,
                    },
                    "expectation_suite_name": config.expectation_suite_name,
                }
            ],
        }
        context.add_checkpoint(**checkpoint_config)
        results = context.run_checkpoint(
            checkpoint_name="example_checkpoint",
            batch_request={
                "runtime_parameters": {"batch_data": validation_dataset},
                "batch_identifiers": {
                    "default_identifier_name": "default_identifier"
                },
            },
        )
        docs = context.build_data_docs()["local_site"]

        return [results.to_json_dict(), docs]
