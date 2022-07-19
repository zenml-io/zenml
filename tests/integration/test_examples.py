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
import logging
import os
import platform
import shutil
from pathlib import Path
from typing import Callable, NamedTuple, Optional

import pytest

from zenml.cli import EXAMPLES_RUN_SCRIPT, SHELL_EXECUTABLE, LocalExample
from zenml.repository import Repository

from .example_validations import (
    generate_basic_validation_function,
    mlflow_tracking_example_validation,
)


def copy_example_files(example_dir: str, dst_dir: str) -> None:
    for item in os.listdir(example_dir):
        if item == ".zen":
            # don't copy any existing ZenML repository
            continue

        s = os.path.join(example_dir, item)
        d = os.path.join(dst_dir, item)
        if os.path.isdir(s):
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)


def example_runner(examples_dir):
    """Get the executable that runs examples.

    By default, returns the path to an executable .sh file in the
    repository, but can also prefix that with the path to a shell
    / interpreter when the file is not executable on its own. The
    latter option is needed for Windows compatibility.
    """
    return (
        [os.environ[SHELL_EXECUTABLE]] if SHELL_EXECUTABLE in os.environ else []
    ) + [str(examples_dir / EXAMPLES_RUN_SCRIPT)]


class ExampleIntegrationTestConfiguration(NamedTuple):
    """Configuration options for testing a ZenML example.

    Attributes:
        name: The name (=directory name) of the example
        validation_function: A function that validates that this example ran
            correctly.
        setup_function: Optional function that performs any additional setup
            (e.g. modifying the stack) before the example is run.
        skip_on_windows: If `True`, this example will not run on windows.
        prevent_stack_setup: If `True` this example will not set up a custom
            stack.
    """

    name: str
    validation_function: Callable[[Repository], None]
    setup_function: Optional[Callable[[Repository], None]] = None
    skip_on_windows: bool = False
    prevent_stack_setup: bool = True


examples = [
    ExampleIntegrationTestConfiguration(
        name="airflow_orchestration",
        validation_function=generate_basic_validation_function(
            pipeline_name="airflow_example_pipeline", step_count=3
        ),
    ),
    # TODO: re-add data validation test when we understand why they
    # intermittently break some of the other test cases
    # ExampleIntegrationTestConfiguration(
    #     name="evidently_drift_detection",
    #     validation_function=drift_detection_example_validation,
    #     prevent_stack_setup=False,
    # ),
    # ExampleIntegrationTestConfiguration(
    #     name="deepchecks_data_validation",
    #     validation_function=generate_basic_validation_function(
    #         pipeline_name="data_validation_pipeline", step_count=6
    #     ),
    #     prevent_stack_setup=False,
    # ),
    # ExampleIntegrationTestConfiguration(
    #     name="great_expectations_data_validation",
    #     validation_function=generate_basic_validation_function(
    #         pipeline_name="validation_pipeline", step_count=6
    #     ),
    #     prevent_stack_setup=False,
    # ),
    # TODO [ENG-708]: Enable running the whylogs example on kubeflow
    # ExampleIntegrationTestConfiguration(
    #     name="whylogs_data_profiling",
    #     validation_function=whylogs_example_validation,
    #     prevent_stack_setup=False,
    # ),
    ExampleIntegrationTestConfiguration(
        name="kubeflow_pipelines_orchestration",
        validation_function=generate_basic_validation_function(
            pipeline_name="mnist_pipeline", step_count=4
        ),
    ),
    # TODO [ENG-858]: Create Integration tests for lightgbm
    # TODO [ENG-859]: Create Integration tests for MLflow Deployment
    ExampleIntegrationTestConfiguration(
        name="mlflow_tracking",
        validation_function=mlflow_tracking_example_validation,
        skip_on_windows=True,
        prevent_stack_setup=False,
    ),
    ExampleIntegrationTestConfiguration(
        name="neural_prophet",
        validation_function=generate_basic_validation_function(
            pipeline_name="neural_prophet_pipeline", step_count=3
        ),
    ),
    ExampleIntegrationTestConfiguration(
        name="xgboost",
        validation_function=generate_basic_validation_function(
            pipeline_name="xgboost_pipeline", step_count=3
        ),
        skip_on_windows=True,
    ),
    # TODO [ENG-860]: Investigate why xgboost test doesn't work on windows
    # TODO [ENG-861]: Investigate why huggingface test throws pip error on
    #  dill<0.3.2,>=0.3.1.1, but you have dill 0.3.4
    ExampleIntegrationTestConfiguration(
        name="pytorch",
        validation_function=generate_basic_validation_function(
            pipeline_name="fashion_mnist_pipeline", step_count=3
        ),
    ),
]


@pytest.mark.parametrize(
    "example_configuration",
    [pytest.param(example, id=example.name) for example in examples],
)
def test_run_example(
    example_configuration: ExampleIntegrationTestConfiguration,
    tmp_path_factory: pytest.TempPathFactory,
    repo_fixture_name: str,
    request: pytest.FixtureRequest,
    virtualenv: str,
) -> None:
    """Runs the given examples and validates they ran correctly.

    Args:
        example_configuration: Configuration of the example to run.
        tmp_path_factory: Factory to generate temporary test paths.
        repo_fixture_name: Name of a fixture that returns a ZenML repository.
            This fixture will be executed and the example will run on the
            active stack of the repository given by the fixture.
        request: Pytest fixture needed to run the fixture given in the
            `repo_fixture_name` argument
        virtualenv: Either a separate cloned environment for each test, or an
                    empty string.
    """
    if example_configuration.skip_on_windows and platform.system() == "Windows":
        logging.info(
            f"Skipping example {example_configuration.name} on windows."
        )
        return

    # run the fixture given by repo_fixture_name
    repo = request.getfixturevalue(repo_fixture_name)

    tmp_path = tmp_path_factory.mktemp("tmp")

    # Root directory of all checked out examples
    examples_directory = Path(repo.original_cwd) / "examples"

    # Copy all example files into the repository directory
    copy_example_files(
        str(examples_directory / example_configuration.name), str(tmp_path)
    )

    # allow any additional setup that the example might need
    if example_configuration.setup_function:
        example_configuration.setup_function(repo)

    # Run the example
    example = LocalExample(name=example_configuration.name, path=tmp_path)
    example.run_example(
        example_runner(examples_directory),
        force=True,
        prevent_stack_setup=example_configuration.prevent_stack_setup,
    )

    # Validate the result
    example_configuration.validation_function(repo)

    # clean up
    try:
        shutil.rmtree(tmp_path)
    except PermissionError:
        # Windows does not have the concept of unlinking a file and deleting
        # once all processes that are accessing the resource are done
        # instead windows tries to delete immediately and fails with a
        # PermissionError: [WinError 32] The process cannot access the
        # file because it is being used by another process
        logging.debug(
            "Skipping deletion of temp dir at teardown, due to "
            "Windows Permission error"
        )
