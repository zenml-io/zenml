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
import logging
import os
import shutil
import sys

import pytest

from zenml.artifacts.base_artifact import BaseArtifact
from zenml.constants import ENV_ZENML_DEBUG
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.pipelines import pipeline
from zenml.repository import Repository
from zenml.steps import StepContext, step


@pytest.fixture(scope="session", autouse=True)
def base_repo(tmp_path_factory, session_mocker):
    """Fixture to get a base clean repository for all tests."""
    # original working directory
    orig_cwd = os.getcwd()

    # set env variables
    os.environ[ENV_ZENML_DEBUG] = "true"
    os.environ["ZENML_ANALYTICS_OPT_IN"] = "false"

    # change the working directory to a fresh temp path
    tmp_path = tmp_path_factory.mktemp("tmp")
    os.chdir(tmp_path)

    # patch the global dir just within the scope of this function
    logging.info(f"Tests are running in repo path: {tmp_path}")
    session_mocker.patch.object(
        sys.modules["zenml.io.utils"],
        "get_global_config_directory",
        return_value=str(tmp_path / "zenml"),
    )

    session_mocker.patch(
        "zenml.config.global_config.GlobalConfig.config_directory",
        return_value=str(tmp_path / "zenml"),
    )
    session_mocker.patch("analytics.track")

    # initialize repo at path
    Repository.initialize(root=tmp_path)
    repo = Repository(root=tmp_path)

    # monkey patch original cwd in for later use and yield
    repo.original_cwd = orig_cwd
    yield repo

    # clean up
    os.chdir(orig_cwd)
    shutil.rmtree(tmp_path)


@pytest.fixture
def clean_repo(tmp_path_factory, mocker, base_repo: Repository):
    """Fixture to get a clean repository for an individual test."""
    # change the working directory to a fresh temp path
    tmp_path = tmp_path_factory.mktemp("tmp")
    os.chdir(tmp_path)

    # patch the global dir just within the scope of this function
    mocker.patch.object(
        sys.modules["zenml.io.utils"],
        "get_global_config_directory",
        return_value=str(tmp_path / "zenml"),
    )

    # initialize repo with new tmp path
    Repository.initialize(root=tmp_path)
    repo = Repository(root=tmp_path)

    # monkey patch base repo cwd for later user and yield
    repo.original_cwd = base_repo.original_cwd
    yield repo

    # remove all traces, and change working directory back to base path
    os.chdir(str(base_repo.root))
    shutil.rmtree(tmp_path)


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
        step_()

    return _pipeline


@pytest.fixture
def unconnected_two_step_pipeline():
    """Pytest fixture that returns a pipeline which takes two steps
    `step_1` and `step_2`. The steps are not connected to each other."""

    @pipeline
    def _pipeline(step_1, step_2):
        step_1()
        step_2()

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
