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
from contextlib import ExitStack as does_not_raise

import pytest

from zenml.enums import StackComponentType
from zenml.exceptions import StackValidationError
from zenml.stack import Stack, StackValidator


def test_validator_with_custom_stack_validation_function():
    """Tests that a validator fails when its custom validation function fails
    to validate the stack."""
    stack = Stack.default_local_stack()

    def failing_validation_function(_: Stack):
        return False, "Custom error"

    failing_validator = StackValidator(
        custom_validation_function=failing_validation_function
    )
    with pytest.raises(StackValidationError):
        failing_validator.validate(stack)

    def successful_validation_function(_: Stack):
        return True, ""

    successful_validator = StackValidator(
        custom_validation_function=successful_validation_function
    )
    with does_not_raise():
        successful_validator.validate(stack)


def test_validator_with_required_components():
    """Tests that a validator fails when one of its required components is
    missing in the stack."""
    stack = Stack.default_local_stack()

    failing_validator = StackValidator(
        required_components={StackComponentType.CONTAINER_REGISTRY}
    )

    with pytest.raises(StackValidationError):
        failing_validator.validate(stack)

    successful_validator = StackValidator(
        required_components={
            StackComponentType.ORCHESTRATOR,
            StackComponentType.METADATA_STORE,
        }
    )
    with does_not_raise():
        successful_validator.validate(stack)
