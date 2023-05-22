#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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

import pytest

from zenml import pipeline, step
from zenml.types import HTMLString


@pytest.fixture
def one_step_pipeline():
    """Pytest fixture that returns a pipeline which takes a single step named `step_`."""

    @pipeline
    def _pipeline(step_):
        step_()

    return _pipeline


@pytest.fixture
def connected_two_step_pipeline():
    """Pytest fixture that returns a pipeline which takes two steps
    `step_1` and `step_2` that are connected."""

    @pipeline(name="connected_two_step_pipeline")
    def _pipeline(step_1, step_2):
        step_2(step_1())

    return _pipeline


@step
def constant_int_output_test_step() -> int:
    return 7


@step
def int_plus_one_test_step(input: int) -> int:
    return input + 1


@step
def int_plus_two_test_step(input: int) -> int:
    return input + 2


@step
def visualizable_step() -> HTMLString:
    """A step that returns a visualizable artifact."""
    return HTMLString("<h1>Test</h1>")


@pytest.fixture
def clean_client_with_run(clean_client, connected_two_step_pipeline):
    """Fixture to get a clean client with an existing pipeline run in it."""
    connected_two_step_pipeline(
        step_1=constant_int_output_test_step(),
        step_2=int_plus_one_test_step(),
    ).run()
    return clean_client
