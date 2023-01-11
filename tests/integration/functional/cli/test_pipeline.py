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
"""Test zenml pipeline CLI commands."""
import os
import subprocess
import sys

import click
import pytest
from click.testing import CliRunner

from zenml.cli.cli import cli
from zenml.client import Client
from zenml.enums import ExecutionStatus
from zenml.post_execution.pipeline import get_pipeline

PIPELINE_NAME = "some_pipe"
STEP_NAME = "some_step"
MATERIALIZER_NAME = "SomeMaterializer"
CUSTOM_OBJ_NAME = "SomeObj"


def test_pipeline_run_single_file(clean_client, files_dir: str) -> None:
    """Test that zenml pipeline run works as expected when the pipeline, its
    steps and materializers are all in the same file."""
    clean_sys_modules = sys.modules

    os.chdir(files_dir)
    clean_client.activate_root()
    Client.initialize(root=files_dir)

    assert os.path.isfile(os.path.join(files_dir, "run.py"))
    assert os.path.isfile(os.path.join(files_dir, "config.yaml"))

    # Run Pipeline using subprocess as runner.invoke seems to have issues with
    #  pytest https://github.com/pallets/click/issues/824,
    #  https://github.com/pytest-dev/pytest/issues/3344
    subprocess.check_call(
        ["zenml", "pipeline", "run", "run.py", "-c", "config.yaml"],
        cwd=files_dir,
        shell=click._compat.WIN,
        env=os.environ.copy(),
    )

    # Assert that the pipeline ran successfully
    historic_pipeline = get_pipeline(pipeline_name=PIPELINE_NAME)

    assert len(historic_pipeline.runs) == 1

    assert historic_pipeline.runs[-1].status == ExecutionStatus.COMPLETED

    # Clean up sys modules that were imported in the course of this test
    for mod in sys.modules:
        if mod not in clean_sys_modules:
            del sys.modules[mod]


def test_pipeline_run_multifile(clean_client, files_dir: str) -> None:
    """Test that zenml pipeline run works as expected when the pipeline, its
    steps and materializers are all in the different files.

    This test creates a project with the following structure.
    |custom_obj_file
    |   |--custom_obj_file.py
    |materializer_file
    |   |--materializer_file.py
    |step_file
    |   |--step_file.py
    |config.yaml
    |run.py
    """
    clean_sys_modules = sys.modules

    os.chdir(files_dir)
    clean_client.activate_root()
    Client.initialize(root=files_dir)

    assert os.path.isfile(os.path.join(files_dir, "pipeline_file/pipeline.py"))
    assert os.path.isfile(os.path.join(files_dir, "config.yaml"))

    # Run Pipeline using subprocess as runner.invoke seems to have issues with
    #  pytest https://github.com/pallets/click/issues/824,
    #  https://github.com/pytest-dev/pytest/issues/3344
    subprocess.check_output(
        [
            "zenml",
            "pipeline",
            "run",
            "pipeline_file/pipeline.py",
            "-c",
            "config.yaml",
        ],
        cwd=files_dir,
        shell=click._compat.WIN,
        env=os.environ.copy(),
    )

    # Assert that pipeline completed successfully
    historic_pipeline = get_pipeline(pipeline_name=PIPELINE_NAME)

    assert len(historic_pipeline.runs) == 1

    assert historic_pipeline.runs[-1].status == ExecutionStatus.COMPLETED

    # Clean up sys modules that were imported in the course of this test
    for mod in sys.modules:
        if mod not in clean_sys_modules:
            del sys.modules[mod]


def test_pipeline_list(clean_project_with_run):
    """Test that zenml pipeline list does not fail."""
    runner = CliRunner()
    list_command = cli.commands["pipeline"].commands["list"]
    result = runner.invoke(list_command)
    assert result.exit_code == 0


def test_pipeline_delete(clean_project_with_run):
    """Test that zenml pipeline delete works as expected."""
    existing_pipelines = clean_project_with_run.list_pipelines()
    assert len(existing_pipelines) == 1
    pipeline_name = existing_pipelines[0].name
    runner = CliRunner()
    delete_command = cli.commands["pipeline"].commands["delete"]
    result = runner.invoke(delete_command, [pipeline_name, "-y"])
    assert result.exit_code == 0
    with pytest.raises(KeyError):
        clean_project_with_run.get_pipeline(pipeline_name)
    existing_pipelines = clean_project_with_run.list_pipelines()
    assert len(existing_pipelines) == 0


def test_pipeline_run_list(clean_project_with_run):
    """Test that zenml pipeline runs list does not fail."""
    runner = CliRunner()
    list_command = cli.commands["pipeline"].commands["runs"].commands["list"]
    result = runner.invoke(list_command)
    assert result.exit_code == 0


def test_pipeline_run_delete(clean_project_with_run):
    """Test that zenml pipeline runs delete works as expected."""
    existing_runs = clean_project_with_run.list_runs()
    assert len(existing_runs) == 1
    run_name = existing_runs[0].name
    runner = CliRunner()
    delete_command = (
        cli.commands["pipeline"].commands["runs"].commands["delete"]
    )
    result = runner.invoke(delete_command, [run_name, "-y"])
    assert result.exit_code == 0
    with pytest.raises(KeyError):
        clean_project_with_run.get_pipeline_run(run_name)
    existing_runs = clean_project_with_run.list_runs()
    assert len(existing_runs) == 0


def test_pipeline_schedule_list(clean_project_with_run):
    """Test that `zenml pipeline schedules list` does not fail."""
    runner = CliRunner()
    list_command = (
        cli.commands["pipeline"].commands["schedule"].commands["list"]
    )
    result = runner.invoke(list_command)
    assert result.exit_code == 0


def test_pipeline_schedule_delete(clean_project_with_run):
    """Test that `zenml pipeline schedules delete` works as expected."""
    existing_schedules = clean_project_with_run.list_schedules()
    assert len(existing_schedules) == 1
    schedule_name = existing_schedules[0].name
    runner = CliRunner()
    delete_command = (
        cli.commands["pipeline"].commands["schedule"].commands["delete"]
    )
    result = runner.invoke(delete_command, [schedule_name, "-y"])
    assert result.exit_code == 0
    with pytest.raises(KeyError):
        clean_project_with_run.get_schedule(schedule_name)
    existing_schedules = clean_project_with_run.list_schedules()
    assert len(existing_schedules) == 0
