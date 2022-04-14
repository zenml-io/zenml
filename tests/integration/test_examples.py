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
import shutil
from pathlib import Path
from typing import Callable, NamedTuple, TypeVar

import pytest

from zenml.cli import EXAMPLES_RUN_SCRIPT, SHELL_EXECUTABLE, LocalExample
from zenml.repository import Repository

from .example_validations import (
    caching_example_validation,
    drift_detection_example_validation,
    generate_basic_validation_function,
    mlflow_tracking_example_validation,
    whylogs_example_validation,
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


ExampleValidationFunction = TypeVar(
    "ExampleValidationFunction", bound=Callable[[Repository], None]
)


class ExampleIntegrationTestConfiguration(NamedTuple):
    """Configuration options for testing a ZenML example.

    Attributes:
        name: The name (=directory name) of the example
        validation_function: A function that validates that this example ran
            correctly.
    """

    name: str
    validation_function: ExampleValidationFunction


examples = [
    ExampleIntegrationTestConfiguration(
        name="quickstart",
        validation_function=generate_basic_validation_function(
            pipeline_name="mnist_pipeline", step_count=3
        ),
    ),
    ExampleIntegrationTestConfiguration(
        name="not_so_quickstart",
        validation_function=generate_basic_validation_function(
            pipeline_name="mnist_pipeline", step_count=4, run_count=3
        ),
    ),
    ExampleIntegrationTestConfiguration(
        name="caching", validation_function=caching_example_validation
    ),
    ExampleIntegrationTestConfiguration(
        name="custom_materializer",
        validation_function=generate_basic_validation_function(
            pipeline_name="pipe", step_count=2
        ),
    ),
    ExampleIntegrationTestConfiguration(
        name="fetch_historical_runs",
        validation_function=generate_basic_validation_function(
            pipeline_name="mnist_pipeline", step_count=3
        ),
    ),
    ExampleIntegrationTestConfiguration(
        name="kubeflow",
        validation_function=generate_basic_validation_function(
            pipeline_name="mnist_pipeline", step_count=4
        ),
    ),
    ExampleIntegrationTestConfiguration(
        name="drift_detection",
        validation_function=drift_detection_example_validation,
    ),
    ExampleIntegrationTestConfiguration(
        name="mlflow_tracking",
        validation_function=mlflow_tracking_example_validation,
    ),
    # TODO [ENG-708]: Enable running the whylogs example on kubeflow
    ExampleIntegrationTestConfiguration(
        name="whylogs", validation_function=whylogs_example_validation
    ),
    ExampleIntegrationTestConfiguration(
        name="statistics",
        validation_function=generate_basic_validation_function(
            pipeline_name="boston_housing_pipeline",
            step_count=3,
        ),
    ),
    ExampleIntegrationTestConfiguration(
        name="lineage",
        validation_function=generate_basic_validation_function(
            pipeline_name="boston_housing_pipeline",
            step_count=4,
        ),
    ),
    ExampleIntegrationTestConfiguration(
        name="dag_visualizer",
        validation_function=generate_basic_validation_function(
            pipeline_name="boston_housing_pipeline",
            step_count=3,
        ),
    ),
    ExampleIntegrationTestConfiguration(
        name="standard_interfaces",
        validation_function=generate_basic_validation_function(
            pipeline_name="TrainingPipeline",
            step_count=6,
        ),
    ),
    ExampleIntegrationTestConfiguration(
        name="airflow_local",
        validation_function=generate_basic_validation_function(
            pipeline_name="mnist_pipeline",
            step_count=4,
        ),
    ),
    ExampleIntegrationTestConfiguration(
        name="class_based_api",
        validation_function=generate_basic_validation_function(
            pipeline_name="TrainingPipeline",
            step_count=6,
        ),
    ),
    ExampleIntegrationTestConfiguration(
        name="functional_api",
        validation_function=generate_basic_validation_function(
            pipeline_name="mnist_pipeline",
            step_count=4,
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
    # run the fixture given by repo_fixture_name
    repo = request.getfixturevalue(repo_fixture_name)

    tmp_path = tmp_path_factory.mktemp("tmp")

    # Root directory of all checked out examples
    examples_directory = Path(repo.original_cwd) / "examples"

    # Copy all example files into the repository directory
    copy_example_files(
        str(examples_directory / example_configuration.name), str(tmp_path)
    )

    # Run the example
    example = LocalExample(name=example_configuration.name, path=tmp_path)
    example.run_example(
        example_runner(examples_directory),
        force=True,
        prevent_stack_setup=True,
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
