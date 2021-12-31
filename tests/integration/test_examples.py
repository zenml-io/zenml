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
import shutil
from pathlib import Path

import pytest

from zenml.cli import EXAMPLES_RUN_SCRIPT, LocalExample
from zenml.core.repo import Repository
from zenml.enums import ExecutionStatus

QUICKSTART = "quickstart"
NOT_SO_QUICKSTART = "not_so_quickstart"
CACHING = "caching"


@pytest.fixture
def examples_dir(clean_repo):
    examples_path = Path(clean_repo.path) / "zenml_examples"
    source_path = Path(clean_repo.original_cwd) / "examples"
    shutil.copytree(source_path, examples_path)
    yield examples_path


def test_run_quickstart(examples_dir: Path):
    """Testing the functionality of the quickstart example

    Args:
        Temporary folder containing all examples including the run_examples
        bash script.
    """
    local_example = LocalExample(examples_dir / QUICKSTART, name=QUICKSTART)

    bash_script_location = examples_dir / EXAMPLES_RUN_SCRIPT
    local_example.run_example(bash_file=str(bash_script_location), force=True)

    # Verify the example run was successful
    repo = Repository(path=str(local_example.path))
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

    bash_script_location = examples_dir / EXAMPLES_RUN_SCRIPT
    local_example.run_example(bash_file=str(bash_script_location), force=True)

    # Verify the example run was successful
    repo = Repository(path=str(local_example.path))
    pipeline = repo.get_pipelines()[0]
    assert pipeline.name == "mnist_pipeline"

    first_run = pipeline.runs[-3]
    second_run = pipeline.runs[-2]
    third_run = pipeline.runs[-1]

    assert first_run.status == ExecutionStatus.COMPLETED
    assert second_run.status == ExecutionStatus.COMPLETED
    assert third_run.status == ExecutionStatus.COMPLETED


def test_run_caching(examples_dir: Path):
    """Testing the functionality of the caching example

    Args:
        Temporary folder containing all examples including the run_examples
        bash script.
    """
    local_example = LocalExample(examples_dir / CACHING, name=CACHING)

    bash_script_location = examples_dir / EXAMPLES_RUN_SCRIPT
    local_example.run_example(bash_file=str(bash_script_location), force=True)

    # Verify the example run was successful
    repo = Repository(path=str(local_example.path))
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
