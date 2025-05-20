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

import logging

import pytest

from zenml.pipelines import pipeline
from zenml.steps import step
from zenml.types import HTMLString


@pytest.fixture
def one_step_pipeline() -> Callable:
    """Pytest fixture that returns a pipeline generator function.

    The returned function (`_wrapper`) takes a single ZenML step function
    as an argument and, when called, defines and returns a ZenML pipeline
    composed of that single step.

    Returns:
        A function that generates a one-step ZenML pipeline.
    """

    def _wrapper(step_: Callable) -> Callable:
        """Defines and returns a one-step ZenML pipeline.

        Args:
            step_: A ZenML step function to be included in the pipeline.

        Returns:
            A ZenML pipeline function.
        """
        @pipeline
        def _pipeline():
            step_()

        return _pipeline

    return _wrapper


@pytest.fixture
def connected_two_step_pipeline() -> Callable:
    """Pytest fixture that returns a pipeline generator function for a two-step pipeline.

    The returned function (`_wrapper`) takes two ZenML step functions
    as arguments. When called, it defines and returns a ZenML pipeline where
    the output of the first step (`step_1`) is passed as input to the
    second step (`step_2`).

    Returns:
        A function that generates a connected two-step ZenML pipeline.
    """

    def _wrapper(step_1: Callable, step_2: Callable) -> Callable:
        """Defines and returns a connected two-step ZenML pipeline.

        Args:
            step_1: The first ZenML step function in the sequence.
            step_2: The second ZenML step function, which takes the output of
                `step_1` as input.

        Returns:
            A ZenML pipeline function.
        """
        @pipeline(name="connected_two_step_pipeline")
        def _pipeline():
            step_2(step_1())

        return _pipeline

    return _wrapper


@step
def constant_int_output_test_step() -> int:
    """A simple ZenML step that returns a constant integer value (7)."""
    return 7


@step
def int_plus_one_test_step(input: int) -> int:
    """A simple ZenML step that takes an integer and returns that integer plus one.

    Args:
        input: An integer to which one will be added.

    Returns:
        The input integer incremented by one.
    """
    return input + 1


@step
def int_plus_two_test_step(input: int) -> int:
    """A simple ZenML step that takes an integer and returns that integer plus two.

    Args:
        input: An integer to which two will be added.

    Returns:
        The input integer incremented by two.
    """
    return input + 2


@step
def visualizable_step() -> HTMLString:
    """A ZenML step that returns an HTMLString artifact for visualization.

    Returns:
        An HTMLString containing a simple HTML header.
    """
    return HTMLString("<h1>Test</h1>")


@step
def step_with_logs() -> int:
    """A ZenML step that logs a message and returns an integer.

    This step demonstrates logging within a ZenML step.

    Returns:
        An integer value (1).
    """
    logging.info("Hello World!")
    return 1


@pytest.fixture
def clean_client_with_run(clean_client: "Client", connected_two_step_pipeline: Callable) -> "Client":
    """Pytest fixture that provides a clean ZenML client with a pre-existing pipeline run.

    This fixture initializes a clean ZenML client environment and then runs a
    sample two-step pipeline (`connected_two_step_pipeline` with
    `constant_int_output_test_step` and `int_plus_one_test_step`).
    This is useful for tests that need to operate on an existing pipeline run
    without the overhead of running the pipeline within the test function itself.

    Args:
        clean_client: A pytest fixture that provides a clean ZenML client instance.
        connected_two_step_pipeline: A pytest fixture that provides a function
            to generate a connected two-step pipeline.

    Returns:
        A ZenML client instance with a completed pipeline run.
    """
    connected_two_step_pipeline(
        step_1=constant_int_output_test_step,
        step_2=int_plus_one_test_step,
    )()
    return clean_client
