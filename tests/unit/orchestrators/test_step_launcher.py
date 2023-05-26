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
from uuid import uuid4

import pytest

from zenml.enums import StackComponentType
from zenml.orchestrators.step_launcher import (
    _get_step_operator,
)
from zenml.stack import Stack


def test_step_operator_validation(local_stack, sample_step_operator):
    """Tests that the step operator gets correctly extracted and validated
    from the stack."""

    with pytest.raises(RuntimeError):
        _get_step_operator(
            stack=local_stack, step_operator_name="step_operator"
        )

    components = local_stack.components
    components[StackComponentType.STEP_OPERATOR] = sample_step_operator
    stack_with_step_operator = Stack.from_components(
        id=uuid4(), name="", components=components
    )
    with pytest.raises(RuntimeError):
        _get_step_operator(
            stack=stack_with_step_operator,
            step_operator_name="not_the_step_operator_name",
        )

    with does_not_raise():
        _get_step_operator(
            stack=stack_with_step_operator,
            step_operator_name=sample_step_operator.name,
        )
