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


def test_artifact_list(clean_client_with_run):
    """Test that zenml artifact list does not fail."""
    runner = CliRunner()
    list_command = cli.commands["pipeline"].commands["list"]
    result = runner.invoke(list_command)
    assert result.exit_code == 0


def test_artifact_delete(clean_client_with_run):
    """Test that zenml artifact delete works for unused artifacts."""
    existing_runs = clean_client_with_run.list_runs()
    existing_artifacts = clean_client_with_run.list_artifacts()
    assert len(existing_runs) == 1
    assert len(existing_artifacts) == 2
    run_name = existing_runs[0].name
    clean_client_with_run.delete_pipeline_run(run_name)
    existing_runs = clean_client_with_run.list_runs()
    existing_artifacts = clean_client_with_run.list_artifacts()
    assert len(existing_runs) == 0
    assert len(existing_artifacts) == 2
    artifact_id = existing_artifacts[0].id
    runner = CliRunner()
    delete_command = cli.commands["artifact"].commands["delete"]
    result = runner.invoke(delete_command, [str(artifact_id), "-y"])
    assert result.exit_code == 0
    existing_artifacts = clean_client_with_run.list_artifacts()
    assert len(existing_artifacts) == 1


def test_artifact_delete_fails_if_artifact_still_used(
    clean_client_with_run,
):
    """Test that zenml artifact delete fails if artifact is still used."""
    existing_artifacts = clean_client_with_run.list_artifacts()
    assert len(existing_artifacts) == 2
    artifact_id = existing_artifacts[0].id
    runner = CliRunner()
    delete_command = cli.commands["artifact"].commands["delete"]
    result = runner.invoke(delete_command, [artifact_id, "-y"])
    assert result.exit_code == 1
    existing_artifacts = clean_client_with_run.list_artifacts()
    assert len(existing_artifacts) == 2


def test_artifact_prune(clean_client_with_run):
    """Test that zenml artifact prune deletes unused artifacts."""
    existing_artifacts = clean_client_with_run.list_artifacts()
    assert len(existing_artifacts) == 2
    runner = CliRunner()
    prune_command = cli.commands["artifact"].commands["prune"]
    result = runner.invoke(prune_command, ["-y"])
    assert result.exit_code == 0
    existing_artifacts = clean_client_with_run.list_artifacts()
    assert len(existing_artifacts) == 2
    existing_runs = clean_client_with_run.list_runs()
    assert len(existing_runs) == 1
    run_name = existing_runs[0].name
    clean_client_with_run.delete_pipeline_run(run_name)
    existing_runs = clean_client_with_run.list_runs()
    existing_artifacts = clean_client_with_run.list_artifacts()
    assert len(existing_runs) == 0
    assert len(existing_artifacts) == 2
    result = runner.invoke(prune_command, ["-y"])
    assert result.exit_code == 0
    existing_artifacts = clean_client_with_run.list_artifacts()
    assert len(existing_artifacts) == 0
