#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

from zenml.pipelines.new import pipeline
from zenml.steps import step


@step
def step_with_int_input(input_: int) -> int:
    return input_


def test_input_validation_outside_of_pipeline():
    step_instance = step_with_int_input()

    with pytest.raises(Exception):
        # Missing input
        step_instance()

    with pytest.raises(Exception):
        # Wrong type
        step_instance(input_="wrong_type")

    output = step_instance(input_=1)
    assert output == 1
    assert type(output) is int

    output = step_instance(input_=3.0)
    assert output == 3
    assert type(output) is int


def test_input_validation_inside_pipeline():
    @pipeline
    def test_pipeline(step_input):
        return step_with_int_input(step_input)

    with pytest.raises(Exception):
        test_pipeline(step_input="wrong_type")

    with does_not_raise():
        test_pipeline(step_input=1)
        test_pipeline(step_input=3.0)
