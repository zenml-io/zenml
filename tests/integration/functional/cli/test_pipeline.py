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

import pytest
from click.testing import CliRunner

from zenml.cli.cli import cli
from zenml.pipelines import pipeline
from zenml.steps import step


def test_pipeline_list(clean_workspace_with_run):
    """Test that zenml pipeline list does not fail."""
    runner = CliRunner()
    list_command = cli.commands["pipeline"].commands["list"]
    result = runner.invoke(list_command)
    assert result.exit_code == 0


def test_pipeline_delete(clean_workspace_with_run):
    """Test that zenml pipeline delete works as expected."""
    existing_pipelines = clean_workspace_with_run.list_pipelines()
    assert len(existing_pipelines) == 1
    pipeline_name = existing_pipelines[0].name
    runner = CliRunner()
    delete_command = cli.commands["pipeline"].commands["delete"]
    result = runner.invoke(delete_command, [pipeline_name, "-y"])
    assert result.exit_code == 0
    with pytest.raises(KeyError):
        clean_workspace_with_run.get_pipeline(name=pipeline_name)
    existing_pipelines = clean_workspace_with_run.list_pipelines()
    assert len(existing_pipelines) == 0


def test_pipeline_run_list(clean_workspace_with_run):
    """Test that zenml pipeline runs list does not fail."""
    runner = CliRunner()
    list_command = cli.commands["pipeline"].commands["runs"].commands["list"]
    result = runner.invoke(list_command)
    assert result.exit_code == 0


def test_pipeline_run_delete(clean_workspace_with_run):
    """Test that zenml pipeline runs delete works as expected."""
    existing_runs = clean_workspace_with_run.list_runs()
    assert len(existing_runs) == 1
    run_name = existing_runs[0].name
    runner = CliRunner()
    delete_command = (
        cli.commands["pipeline"].commands["runs"].commands["delete"]
    )
    result = runner.invoke(delete_command, [run_name, "-y"])
    assert result.exit_code == 0
    with pytest.raises(KeyError):
        clean_workspace_with_run.get_pipeline_run(run_name)
    existing_runs = clean_workspace_with_run.list_runs()
    assert len(existing_runs) == 0


def test_pipeline_schedule_list(clean_workspace_with_scheduled_run):
    """Test that `zenml pipeline schedules list` does not fail."""
    runner = CliRunner()
    list_command = (
        cli.commands["pipeline"].commands["schedule"].commands["list"]
    )
    result = runner.invoke(list_command)
    assert result.exit_code == 0


def test_pipeline_schedule_delete(clean_workspace_with_scheduled_run):
    """Test that `zenml pipeline schedules delete` works as expected."""
    existing_schedules = clean_workspace_with_scheduled_run.list_schedules()
    assert len(existing_schedules) == 1
    schedule_name = existing_schedules[0].name
    runner = CliRunner()
    delete_command = (
        cli.commands["pipeline"].commands["schedule"].commands["delete"]
    )
    result = runner.invoke(delete_command, [schedule_name, "-y"])
    assert result.exit_code == 0
    with pytest.raises(KeyError):
        clean_workspace_with_scheduled_run.get_schedule(schedule_name)
    existing_schedules = clean_workspace_with_scheduled_run.list_schedules()
    assert len(existing_schedules) == 0


@step
def s() -> None:
    pass


@pipeline
def p(s1):
    s1()


step_instance = s()
pipeline_instance = p(step_instance)


def test_pipeline_registration_without_repo():
    """Tests that the register command outside of a repo fails."""
    runner = CliRunner()
    register_command = cli.commands["pipeline"].commands["register"]

    result = runner.invoke(
        register_command, [f"{pipeline_instance.__module__}.pipeline_instance"]
    )
    assert result.exit_code == 1


def test_pipeline_registration_with_repo(clean_workspace):
    """Tests the register command inside a repo."""
    runner = CliRunner()
    register_command = cli.commands["pipeline"].commands["register"]

    # Invalid source string
    result = runner.invoke(register_command, ["INVALID_SOURCE"])
    assert result.exit_code == 1

    # Invalid module
    result = runner.invoke(
        register_command, ["invalid_module.pipeline_instance"]
    )
    assert result.exit_code == 1

    # Not a pipeline instance
    result = runner.invoke(
        register_command, [f"{pipeline_instance.__module__}.step_instace"]
    )
    assert result.exit_code == 1

    # Correct source
    result = runner.invoke(
        register_command, [f"{pipeline_instance.__module__}.pipeline_instance"]
    )
    assert result.exit_code == 0
    assert clean_workspace.list_pipelines(name="p").total == 1
