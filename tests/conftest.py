#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
import logging
import os

import pytest

from zenml.artifacts.base_artifact import BaseArtifact
from zenml.constants import ENV_ZENML_DEBUG
from zenml.core.repo import Repository
from zenml.exceptions import InitializationException
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.pipelines import pipeline
from zenml.steps import StepContext, step


def pytest_sessionstart(session):
    """Called after the Session object has been created and
    before performing collection and entering the run test loop.
    """
    os.environ[ENV_ZENML_DEBUG] = "true"
    try:
        Repository.init_repo()
    except InitializationException:
        # already initialized
        logging.info("Repo already initialized for testing.")


def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run finished, right before
    returning the exit status to the system.
    """


@pytest.fixture
def empty_step():
    """Pytest fixture that returns an empty (no input, no output) step."""

    @step
    def _empty_step():
        pass

    return _empty_step


@pytest.fixture
def multiple_empty_steps():
    """Pytest fixture that returns multiple unique empty step functions."""

    def _multiple_empty_steps():
        @step
        def _empty_step_1():
            pass

        @step
        def _empty_step_2():
            pass

        @step
        def _empty_step_3():
            pass

        output = [_empty_step_1, _empty_step_2, _empty_step_3]

        return output

    return _multiple_empty_steps


@pytest.fixture
def one_step_pipeline():
    """Pytest fixture that returns a pipeline which takes a single step
    named `step_`."""

    @pipeline
    def _pipeline(step_):
        pass

    return _pipeline


@pytest.fixture
def unconnected_two_step_pipeline():
    """Pytest fixture that returns a pipeline which takes two steps
    `step_1` and `step_2`. The steps are not connected to each other."""

    @pipeline
    def _pipeline(step_1, step_2):
        pass

    return _pipeline


@pytest.fixture
def int_step_output():
    @step
    def _step() -> int:
        return 1

    return _step()()


@pytest.fixture
def step_with_two_int_inputs():
    @step
    def _step(input_1: int, input_2: int):
        pass

    return _step


@pytest.fixture
def step_context_with_no_output():
    return StepContext(
        step_name="", output_materializers={}, output_artifacts={}
    )


@pytest.fixture
def step_context_with_single_output():
    materializers = {"output_1": BaseMaterializer}
    artifacts = {"output_1": BaseArtifact()}

    return StepContext(
        step_name="",
        output_materializers=materializers,
        output_artifacts=artifacts,
    )


@pytest.fixture
def step_context_with_two_outputs():
    materializers = {"output_1": BaseMaterializer, "output_2": BaseMaterializer}
    artifacts = {"output_1": BaseArtifact(), "output_2": BaseArtifact()}

    return StepContext(
        step_name="",
        output_materializers=materializers,
        output_artifacts=artifacts,
    )
