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

from zenml.integrations.great_expectations.steps import (
    GreatExpectationsValidatorConfig,
    GreatExpectationsValidatorStep,
)
from zenml.steps.utils import clone_step

ge_validate_train_config = GreatExpectationsValidatorConfig(
    expectation_suite_name="steel_plates_suite",
    data_asset_name="steel_plates_train_df",
)
ge_validate_test_config = GreatExpectationsValidatorConfig(
    expectation_suite_name="steel_plates_suite",
    data_asset_name="steel_plates_test_df",
)

# We clone the builtin step by calling the `clone_step` utility to use it twice
# in our pipeline: on the training set and on the validation set.
# This is necessary because a step cannot be used twice in the same pipeline.
ge_validate_train_step = clone_step(
    GreatExpectationsValidatorStep, "ge_validate_train_step_class"
)(config=ge_validate_train_config)
ge_validate_test_step = clone_step(
    GreatExpectationsValidatorStep, "ge_validate_test_step_class"
)(config=ge_validate_test_config)
