#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Tests for project update commands."""

from importlib import import_module

import pytest
from click.testing import CliRunner

from zenml.client import Client

project_module = import_module("zenml.cli.project")


def test_update_project_renames_by_uuid(
    clean_client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both names and description can change without recreating a project."""
    project = clean_client.create_project("original-project", "Original")
    clean_client.set_active_project(project.id)
    monkeypatch.setattr(project_module, "Client", lambda: clean_client)

    result = CliRunner().invoke(
        project_module.project,
        [
            "update",
            str(project.id),
            "--name",
            "renamed-project",
            "--display-name",
            "Renamed Project",
            "--description",
            "Updated description",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Project 'renamed-project' updated successfully" in result.output
    updated = clean_client.get_project(project.id)
    assert updated.name == "renamed-project"
    assert updated.display_name == "Renamed Project"
    assert updated.description == "Updated description"
    assert clean_client.active_project.id == project.id
    assert clean_client.active_project.name == "renamed-project"


@pytest.mark.parametrize(
    "option, value, field",
    [
        ("--name", "renamed-project", "name"),
        ("--display-name", "Updated display name", "display_name"),
        ("--description", "Updated description", "description"),
        ("--display-name", "", "display_name"),
        ("--description", "", "description"),
    ],
)
def test_update_project_changes_only_requested_field(
    clean_client: Client,
    monkeypatch: pytest.MonkeyPatch,
    option: str,
    value: str,
    field: str,
) -> None:
    """Each option works independently, including explicitly empty values."""
    original = {
        "name": "original-project",
        "display_name": "Original display name",
        "description": "Original description",
    }
    project = clean_client.create_project(
        name=original["name"],
        description=original["description"],
        display_name=original["display_name"],
    )
    monkeypatch.setattr(project_module, "Client", lambda: clean_client)

    result = CliRunner().invoke(
        project_module.project, ["update", project.name, option, value]
    )

    assert result.exit_code == 0, result.output
    expected = {**original, field: value}
    updated = clean_client.get_project(project.id)
    assert updated.name == expected["name"]
    assert updated.display_name == expected["display_name"]
    assert updated.description == expected["description"]


@pytest.mark.parametrize("arguments", [["update"], ["update", "some-project"]])
def test_update_project_requires_target_and_changes(
    monkeypatch: pytest.MonkeyPatch, arguments: list[str]
) -> None:
    """Incomplete commands fail before constructing a client."""

    def unexpected_client() -> None:
        pytest.fail("Incomplete update must not construct a client.")

    monkeypatch.setattr(project_module, "Client", unexpected_client)

    result = CliRunner().invoke(project_module.project, arguments)

    assert result.exit_code == 2, result.output
    if len(arguments) == 1:
        assert "Missing argument 'PROJECT_NAME_OR_ID'" in result.output
    else:
        assert "Provide at least one of" in result.output


@pytest.mark.parametrize(
    "target, name",
    [("missing-project", "new-name"), ("original-project", "Invalid Name")],
)
def test_update_project_reports_failure(
    clean_client: Client,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    name: str,
) -> None:
    """Missing projects and invalid names produce errors without success text."""
    project = clean_client.create_project("original-project", "Original")
    monkeypatch.setattr(project_module, "Client", lambda: clean_client)

    result = CliRunner().invoke(
        project_module.project, ["update", target, "--name", name]
    )

    assert result.exit_code == 1, result.output
    assert "Error:" in result.output
    assert "updated successfully" not in result.output
    assert clean_client.get_project(project.id).name == project.name
