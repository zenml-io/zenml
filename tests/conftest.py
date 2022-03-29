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
from pathlib import Path
from typing import Generator

import pytest
from py._builtin import execfile
from pytest_mock import MockerFixture

from tests.venv_clone_utils import clone_virtualenv
from zenml.artifacts.base_artifact import BaseArtifact
from zenml.config.global_config import GlobalConfiguration
from zenml.config.profile_config import ProfileConfiguration
from zenml.constants import ENV_ZENML_DEBUG
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.pipelines import pipeline
from zenml.repository import Repository
from zenml.steps import StepContext, step


@pytest.fixture(scope="session", autouse=True)
def base_repo(
    tmp_path_factory: pytest.TempPathFactory,
    session_mocker: MockerFixture,
    request: pytest.FixtureRequest,
):
    """Fixture to get a base clean global configuration and repository for all
    tests."""

    # the global configuration and repository must not have been instantiated
    # yet, otherwise the current working configuration might be affected
    assert GlobalConfiguration.get_instance() is None
    assert Repository.get_instance() is None

    # original working directory
    orig_cwd = os.getcwd()

    # set env variables
    os.environ[ENV_ZENML_DEBUG] = "true"
    os.environ["ZENML_ANALYTICS_OPT_IN"] = "false"
    os.environ["ZENML_DEFAULT_STORE_TYPE"] = request.config.getoption(
        "store_type"
    )

    # change the working directory to a fresh temp path
    tmp_path = tmp_path_factory.mktemp("tmp")
    os.chdir(tmp_path)

    # patch the global dir just within the scope of this function
    logging.info(f"Tests are running in path: {tmp_path}")

    # set the ZENML_CONFIG_PATH environment variable to ensure that the global
    # configuration, the configuration profiles and the local stacks used during
    # testing are separate from those used in the current environment
    os.environ["ZENML_CONFIG_PATH"] = str(tmp_path / "zenml")

    session_mocker.patch("analytics.track")

    # initialize repo at the new path
    repo = Repository()

    # monkey patch original cwd in for later use and yield
    repo.original_cwd = orig_cwd
    yield repo

    # clean up
    os.chdir(orig_cwd)
    shutil.rmtree(tmp_path)

    # reset the global configuration and the repository
    GlobalConfiguration._reset_instance()
    Repository._reset_instance()


@pytest.fixture(scope="module", autouse=True)
def base_profile(
    base_repo: Repository,
    request: pytest.FixtureRequest,
) -> Generator[Repository, None, None]:
    """Creates and activates a clean profile with a fresh default stack for all
    tests in a module.

    Args:
        base_repo: The base ZenML repository for tests.
        request: Pytest FixtureRequest object

    Yields:
        The input repository with a provisioned profile.
    """
    gc = GlobalConfiguration()

    profile_name = request.node.name
    profile_name = profile_name.replace(".", "_")
    profile = ProfileConfiguration(name=profile_name)

    gc.add_or_update_profile(profile)

    original_profile = base_repo.active_profile_name

    base_repo.activate_profile(profile_name)

    logging.info(
        f"Tests are running in clean profile '{profile_name}' with store type "
        f"'{profile.store_type.value}'"
    )

    yield base_repo

    base_repo.activate_profile(original_profile)
    gc.delete_profile(profile_name)


@pytest.fixture
def clean_repo(
    request: pytest.FixtureRequest,
    tmp_path_factory: pytest.TempPathFactory,
    base_repo: Repository,
) -> Repository:
    """Fixture to get a clean global configuration and repository for an
    individual test.

    Args:
        request: Pytest FixtureRequest object
        tmp_path_factory: Pytest TempPathFactory in order to create a new
                          temporary directory
        mocker: Pytest mocker to patch away the
                zenml.io.utils.get_global_config_directory
        base_repo: Fixture that returns the base_repo that all tests use
    """
    orig_cwd = os.getcwd()
    orig_config_path = os.getenv("ZENML_CONFIG_PATH")

    # change the working directory to a fresh temp path
    test_name = request.node.name
    test_name = test_name.replace("[", "-").replace("]", "-")
    tmp_path = tmp_path_factory.mktemp(test_name)

    os.chdir(tmp_path)

    logging.info(f"Tests are running in clean environment: {tmp_path}")

    # save the current global configuration and repository singleton instances
    # to restore them later, then reset them
    original_config = GlobalConfiguration.get_instance()
    original_repository = Repository.get_instance()
    GlobalConfiguration._reset_instance()
    Repository._reset_instance()

    # set the ZENML_CONFIG_PATH environment variable to ensure that the global
    # configuration, the configuration profiles and the local stacks used in
    # the scope of this function are separate from those used in the global
    # testing environment
    os.environ["ZENML_CONFIG_PATH"] = str(tmp_path / "zenml")

    # initialize repo with new tmp path
    repo = Repository()

    # monkey patch base repo cwd for later user and yield
    repo.original_cwd = base_repo.original_cwd
    yield repo

    # remove all traces, and change working directory back to base path
    os.chdir(orig_cwd)
    try:
        shutil.rmtree(tmp_path)
    except PermissionError:
        # Windows does not have the concept of unlinking a file and deleting
        #  once all processes that are accessing the resource are done
        #  instead windows tries to delete immediately and fails with a
        #  PermissionError: [WinError 32] The process cannot access the
        #  file because it is being used by another process
        logging.debug(
            "Skipping deletion of temp dir at teardown, due to "
            "Windows Permission error"
        )
        # Todo[HIGH]: Implement fixture cleanup for Windows where shutil.rmtree
        #  fails on files that are in use on python 3.7

    # restore the global configuration path
    os.environ["ZENML_CONFIG_PATH"] = orig_config_path

    # restore the original global configuration and the repository singleton
    GlobalConfiguration._reset_instance(original_config)
    Repository._reset_instance(original_repository)


@pytest.fixture
def empty_step():
    """Pytest fixture that returns an empty (no input, no output) step."""

    @step
    def _empty_step():
        pass

    return _empty_step


@pytest.fixture
def generate_empty_steps():
    """Pytest fixture that returns a function that generates multiple empty
    steps."""

    def _generate_empty_steps(count: int):
        output = []

        for i in range(count):

            @step(name=f"step_{i}")
            def _step_function():
                pass

            output.append(_step_function)

        return output

    return _generate_empty_steps


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


@pytest.fixture
def virtualenv(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> str:
    """Based on the underlying virtual environment a copy of the environment is
    made and used for the test that uses this fixture.

    Args:
        request: Pytest FixtureRequest object used to create unique tmp dir
                 based on the name of the test
        tmp_path_factory: Pytest TempPathFactory in order to create a new
                          temporary directory

    Yields:
        Path to the virtual environment
    """
    if request.config.getoption("use_virtualenv"):
        # Remember the old executable
        orig_sys_executable = Path(sys.executable)

        test_name = request.node.name
        test_name = test_name.replace("[", "-").replace("]", "-")

        # Create temporary venv
        tmp_path = tmp_path_factory.mktemp(test_name) / "venv"
        # TODO[ENG-707]: Implement for use outside of a base virtual environment
        #  If this happens outside of a virtual environment the complete
        #  /usr space is cloned
        clone_virtualenv(
            src_dir=str(orig_sys_executable.parent.parent),
            dst_dir=str(tmp_path),
        )

        env_bin_dir = "bin"
        if sys.platform == "win32":
            env_bin_dir = "Scripts"

        # Activate venv
        activate_this_file = tmp_path / env_bin_dir / "activate_this.py"

        if not activate_this_file.is_file():
            raise FileNotFoundError(
                "Integration tests don't work for some local "
                "virtual environments. Use virtualenv for "
                "your virtual environment to run integration "
                "tests"
            )

        execfile(
            str(activate_this_file), dict(__file__=str(activate_this_file))
        )

        # Set new system executable
        sys.executable = tmp_path / env_bin_dir / "python"

        yield tmp_path
        # Reset system executable
        sys.executable = orig_sys_executable

        # Switch back to original venv
        activate_this_f = Path(orig_sys_executable).parent / "activate_this.py"

        if not activate_this_f.is_file():
            raise FileNotFoundError(
                "Integration tests don't work for some local "
                "virtual environments. Use virtualenv for "
                "your virtual environment to run integration "
                "tests"
            )
        execfile(str(activate_this_f), dict(__file__=str(activate_this_f)))

    else:
        yield ""


def pytest_addoption(parser):
    """Fixture that gets called by pytest ahead of tests. Adds the following cli
    option:

        * an option to enable kubeflow for integration tests
        * an option to disable the use of the virtualenv fixture. This might be
        useful for local integration testing in case you do not care about your
        base environment being affected
        * an option to use a specific store type for the profiles

    How to use this option:

        ```pytest tests/integration/test_examples.py --on-kubeflow```

        ```pytest tests/integration/test_examples.py --use-virtualenv```

        ```pytest tests/integration/test_examples.py --store-type sql```

    """
    parser.addoption(
        "--on-kubeflow",
        action="store_true",
        default=False,
        help="Only run Kubeflow",
    )
    parser.addoption(
        "--use-virtualenv",
        action="store_true",
        default=False,
        help="Run Integration tests in cloned env",
    )
    parser.addoption(
        "--store-type",
        action="store",
        default="local",
        help="The type of store back-end to use for profiles (local, sql, etc)",
    )


def pytest_generate_tests(metafunc):
    """Parametrizes the repo_fixture_name wherever it is imported by a step with
    the cli options."""
    if "repo_fixture_name" in metafunc.fixturenames:
        if metafunc.config.getoption("on_kubeflow"):
            repos = ["clean_kubeflow_profile"]
        else:
            repos = ["clean_base_profile"]
        metafunc.parametrize("repo_fixture_name", repos)
