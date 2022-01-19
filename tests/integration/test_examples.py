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
import shutil
from os import environ
from pathlib import Path
from typing import Dict

import pytest

from zenml.cli import EXAMPLES_RUN_SCRIPT, SHELL_EXECUTABLE, LocalExample
from zenml.enums import ExecutionStatus
from zenml.repository import Repository

QUICKSTART = "quickstart"
NOT_SO_QUICKSTART = "not_so_quickstart"
CACHING = "caching"
DRIFT_DETECTION = "drift_detection"
MLFLOW = "mlflow_tracking"


@pytest.fixture
def examples_dir(clean_repo):
    # TODO [high]: tests should store zenml artifacts in a new temp directory
    examples_path = Path(clean_repo.root) / "zenml_examples"
    source_path = Path(clean_repo.original_cwd) / "examples"
    shutil.copytree(source_path, examples_path)
    yield examples_path


def example_runner(examples_dir):
    """Get the executable that runs examples.

    By default returns the path to an executable .sh file in the
    repository, but can also prefix that with the path to a shell
    / interpreter when the file is not executable on its own. The
    latter option is needed for windows compatibility.
    """
    return (
        [environ[SHELL_EXECUTABLE]] if SHELL_EXECUTABLE in environ else []
    ) + [str(examples_dir / EXAMPLES_RUN_SCRIPT)]


def test_run_quickstart(examples_dir: Path):
    """Testing the functionality of the quickstart example

    Args:
        Temporary folder containing all examples including the run_examples
        bash script.
    """
    local_example = LocalExample(examples_dir / QUICKSTART, name=QUICKSTART)

    local_example.run_example(example_runner(examples_dir), force=True)

    # Verify the example run was successful
    repo = Repository(local_example.path)
    pipeline = repo.get_pipelines()[0]
    assert pipeline.name == "mnist_pipeline"

    pipeline_run = pipeline.runs[-1]

    assert pipeline_run.status == ExecutionStatus.COMPLETED

    for step in pipeline_run.steps:
        assert step.status == ExecutionStatus.COMPLETED


def test_run_not_so_quickstart(examples_dir: Path):
    """Testing the functionality of the not_so_quickstart example

    Args:
        Temporary folder containing all examples including the run_examples
        bash script.
    """
    local_example = LocalExample(
        examples_dir / NOT_SO_QUICKSTART, name=NOT_SO_QUICKSTART
    )
    local_example.run_example(example_runner(examples_dir), force=True)

    # Verify the example run was successful
    repo = Repository(local_example.path)
    pipeline = repo.get_pipelines()[0]
    assert pipeline.name == "mnist_pipeline"

    first_run = pipeline.runs[-3]
    second_run = pipeline.runs[-2]
    third_run = pipeline.runs[-1]

    assert first_run.status == ExecutionStatus.COMPLETED
    assert second_run.status == ExecutionStatus.COMPLETED
    assert third_run.status == ExecutionStatus.COMPLETED


def test_run_drift_detection(examples_dir: Path):
    """Testing the functionality of the drift_detection example

    Args:
        Temporary folder containing all examples including the run_examples
        bash script.
    """
    local_example = LocalExample(
        examples_dir / DRIFT_DETECTION, name=DRIFT_DETECTION
    )

    local_example.run_example(example_runner(examples_dir), force=True)

    # Verify the example run was successful
    repo = Repository(local_example.path)
    pipeline = repo.get_pipelines()[0]
    assert pipeline.name == "drift_detection_pipeline"

    run = pipeline.runs[0]

    # Run should be completed
    assert run.status == ExecutionStatus.COMPLETED

    # The first run should not have any cached steps
    for step in run.steps:
        assert not step.is_cached

    # Final step should have output a data drift report
    output_obj = run.steps[3].outputs["profile"].read()
    assert isinstance(output_obj, Dict)
    assert output_obj.get("data_drift") is not None


def test_run_caching(examples_dir: Path):
    """Testing the functionality of the caching example

    Args:
        Temporary folder containing all examples including the run_examples
        bash script.
    """
    local_example = LocalExample(examples_dir / CACHING, name=CACHING)
    local_example.run_example(example_runner(examples_dir), force=True)

    # Verify the example run was successful
    repo = Repository(local_example.path)
    pipeline = repo.get_pipelines()[0]
    assert pipeline.name == "mnist_pipeline"

    first_run = pipeline.runs[-2]
    second_run = pipeline.runs[-1]

    # Both runs should be completed
    assert first_run.status == ExecutionStatus.COMPLETED
    assert second_run.status == ExecutionStatus.COMPLETED

    # The first run should not have any cached steps
    for step in first_run.steps:
        assert not step.is_cached

    # The second run should have two cached steps (chronologically first 2)
    assert second_run.steps[0].is_cached
    assert second_run.steps[1].is_cached
    assert not second_run.steps[2].is_cached
    assert not second_run.steps[3].is_cached


def test_run_mlflow(examples_dir: Path):
    """Testing the functionality of the quickstart example

    Args:
        Temporary folder containing all examples including the run_examples
        bash script.
    """
    local_example = LocalExample(examples_dir / MLFLOW, name=MLFLOW)
    local_example.run_example(example_runner(examples_dir), force=True)

    # Verify the example run was successful
    repo = Repository(local_example.path)
    pipeline = repo.get_pipelines()[0]
    assert pipeline.name == "mlflow_example_pipeline"

    first_run = pipeline.runs[-2]
    second_run = pipeline.runs[-1]

    # Both runs should be completed
    assert first_run.status == ExecutionStatus.COMPLETED
    assert second_run.status == ExecutionStatus.COMPLETED

    for step in first_run.steps:
        assert step.status == ExecutionStatus.COMPLETED
    for step in second_run.steps:
        assert step.status == ExecutionStatus.COMPLETED

    # TODO [ENG-359]: Add some mlflow specific assertions.
    #  Currently this is a bit difficult as the mlruns do not end up in the
    #  expected location within the temporary fixtures. This needs to be
    #  investigated
