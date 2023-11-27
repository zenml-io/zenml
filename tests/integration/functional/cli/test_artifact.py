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
"""Test zenml artifact CLI commands."""

from click.testing import CliRunner

from zenml.cli.cli import cli


def test_artifact_list(clean_workspace_with_run):
    """Test that zenml artifact list does not fail."""
    runner = CliRunner()
    list_command = cli.commands["pipeline"].commands["list"]
    result = runner.invoke(list_command)
    assert result.exit_code == 0


def test_artifact_prune(clean_workspace_with_run):
    """Test that zenml artifact prune deletes unused artifacts."""
    existing_artifacts = clean_workspace_with_run.list_artifact_versions()
    assert len(existing_artifacts) == 2
    runner = CliRunner()
    prune_command = cli.commands["artifact"].commands["prune"]
    result = runner.invoke(prune_command, ["-y"])
    assert result.exit_code == 0
    existing_artifacts = clean_workspace_with_run.list_artifact_versions()
    assert len(existing_artifacts) == 2
    existing_runs = clean_workspace_with_run.list_runs()
    assert len(existing_runs) == 1
    run_name = existing_runs[0].name
    clean_workspace_with_run.delete_pipeline_run(run_name)
    existing_runs = clean_workspace_with_run.list_runs()
    existing_artifacts = clean_workspace_with_run.list_artifact_versions()
    assert len(existing_runs) == 0
    assert len(existing_artifacts) == 2
    result = runner.invoke(prune_command, ["-y"])
    assert result.exit_code == 0
    existing_artifacts = clean_workspace_with_run.list_artifact_versions()
    assert len(existing_artifacts) == 0
