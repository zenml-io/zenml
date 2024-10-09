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
    """Test that `zenml artifact list` does not fail."""
    runner = CliRunner()
    list_command = cli.commands["pipeline"].commands["list"]
    result = runner.invoke(list_command)
    assert result.exit_code == 0


def test_artifact_version_list(clean_client_with_run):
    """Test that `zenml artifact version list` does not fail."""
    runner = CliRunner()
    list_command = (
        cli.commands["artifact"].commands["version"].commands["list"]
    )
    result = runner.invoke(list_command)
    assert result.exit_code == 0


def test_artifact_update(clean_client_with_run):
    """Test `zenml artifact update`."""
    runner = CliRunner()
    update_command = cli.commands["artifact"].commands["update"]
    new_name = "new_name"
    tags = ["tag1", "tag2"]

    # Initially there should be no tags
    artifact_response = clean_client_with_run.list_artifacts()[0]
    assert artifact_response.name != new_name
    for tag in tags:
        assert tag not in [t.name for t in artifact_response.tags]

    # After updating, the tags should be there and the name should be changed
    result = runner.invoke(
        update_command,
        [
            artifact_response.name,
            "-n",
            new_name,
            "-t",
            tags[0],
            "-t",
            tags[1],
        ],
    )
    assert result.exit_code == 0
    artifact_response = clean_client_with_run.get_artifact(new_name)
    assert artifact_response.name == new_name
    for tag in tags:
        assert tag in [t.name for t in artifact_response.tags]

    # Tags should also be removable
    result = runner.invoke(
        update_command,
        [
            artifact_response.name,
            "-r",
            tags[0],
        ],
    )
    assert result.exit_code == 0
    artifact_response = clean_client_with_run.get_artifact(new_name)
    existing_tags = [t.name for t in artifact_response.tags]
    assert tags[0] not in existing_tags
    assert tags[1] in existing_tags


def test_artifact_version_update(clean_client_with_run):
    """Test `zenml artifact version update`."""
    runner = CliRunner()
    update_command = (
        cli.commands["artifact"].commands["version"].commands["update"]
    )
    tags = ["tag1", "tag2"]

    # Initially there should be no tags
    artifact_version_response = clean_client_with_run.list_artifact_versions()[
        0
    ]
    for tag in tags:
        assert tag not in [t.name for t in artifact_version_response.tags]

    # After updating, the tags should be there
    result = runner.invoke(
        update_command,
        [
            artifact_version_response.name,
            "-v",
            artifact_version_response.version,
            "-t",
            tags[0],
            "-t",
            tags[1],
        ],
    )
    assert result.exit_code == 0
    artifact_version_response = clean_client_with_run.get_artifact_version(
        artifact_version_response.name, artifact_version_response.version
    )
    for tag in tags:
        assert tag in [t.name for t in artifact_version_response.tags]

    # Tags should also be removable
    result = runner.invoke(
        update_command,
        [
            artifact_version_response.name,
            "-v",
            artifact_version_response.version,
            "-r",
            tags[0],
        ],
    )
    assert result.exit_code == 0
    artifact_version_response = clean_client_with_run.get_artifact_version(
        artifact_version_response.name, artifact_version_response.version
    )
    existing_tags = [t.name for t in artifact_version_response.tags]
    assert tags[0] not in existing_tags
    assert tags[1] in existing_tags


def test_artifact_prune(clean_client_with_run):
    """Test that `zenml artifact prune` deletes all unused artifacts."""

    # Initially there should be two artifacts with one version each
    existing_artifacts = clean_client_with_run.list_artifacts()
    assert len(existing_artifacts) == 2
    existing_artifact_versions = clean_client_with_run.list_artifact_versions()
    assert len(existing_artifact_versions) == 2

    # After pruning, nothing should change since the artifacts are still used
    runner = CliRunner()
    prune_command = cli.commands["artifact"].commands["prune"]
    result = runner.invoke(prune_command, ["-y"])
    assert result.exit_code == 0
    existing_artifacts = clean_client_with_run.list_artifacts()
    assert len(existing_artifacts) == 2
    existing_artifact_versions = clean_client_with_run.list_artifact_versions()
    assert len(existing_artifact_versions) == 2

    # After deleting the run, the artifacts should still exist
    existing_runs = clean_client_with_run.list_pipeline_runs()
    assert len(existing_runs) == 1
    run_name = existing_runs[0].name
    clean_client_with_run.delete_pipeline_run(run_name)
    existing_runs = clean_client_with_run.list_pipeline_runs()
    assert len(existing_runs) == 0
    existing_artifacts = clean_client_with_run.list_artifacts()
    assert len(existing_artifacts) == 2
    existing_artifact_versions = clean_client_with_run.list_artifact_versions()
    assert len(existing_artifact_versions) == 2

    # After deleting the run, the artifacts should now get pruned
    result = runner.invoke(prune_command, ["-y"])
    assert result.exit_code == 0
    existing_artifacts = clean_client_with_run.list_artifacts()
    assert len(existing_artifacts) == 0
    existing_artifact_versions = clean_client_with_run.list_artifact_versions()
    assert len(existing_artifact_versions) == 0
