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
"""Regression tests for SDK project updates."""

from typing import Any, Dict, cast

import pytest
from pydantic import ValidationError
from pytest_mock import MockerFixture

from zenml.client import Client
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import DEFAULT_PROJECT_NAME, ENV_ZENML_ACTIVE_PROJECT_ID
from zenml.exceptions import EntityExistsError, IllegalOperationError


@pytest.mark.parametrize(
    "updates, expected_fields",
    [
        ({"new_name": "renamed-project"}, {"name": "renamed-project"}),
        (
            {"new_display_name": "New display name"},
            {"display_name": "New display name"},
        ),
        (
            {"new_description": "New description"},
            {"description": "New description"},
        ),
        ({"new_display_name": ""}, {"display_name": ""}),
        ({"new_description": ""}, {"description": ""}),
        ({"project_metadata": {}}, {"project_metadata": {}}),
        ({}, {}),
    ],
    ids=[
        "slug",
        "display-name",
        "description",
        "clear-display-name",
        "clear-description",
        "clear-metadata",
        "omitted-fields",
    ],
)
def test_update_project_only_sends_explicit_fields(
    clean_client: Client,
    mocker: MockerFixture,
    updates: Dict[str, Any],
    expected_fields: Dict[str, Any],
) -> None:
    """Partial updates preserve every omitted field and permit empty values.

    Args:
        clean_client: Client backed by an isolated SQLite database.
        mocker: Fixture for observing the store update request.
        updates: SDK keyword arguments for this update.
        expected_fields: Fields that should be sent to the store.
    """
    original_fields: Dict[str, Any] = {
        "name": "editable-project",
        "display_name": "Original display name",
        "description": "Original description",
        "project_metadata": {"owner": "original-owner"},
    }
    project = clean_client.create_project(**original_fields)
    update_project = mocker.spy(type(clean_client.zen_store), "update_project")

    updated = clean_client.update_project(project.name, **updates)

    update_project.assert_called_once()
    assert update_project.call_args.kwargs["project_id"] == project.id
    assert (
        update_project.call_args.kwargs["project_update"].model_dump(
            exclude_unset=True
        )
        == expected_fields
    )
    expected = {**original_fields, **expected_fields}
    stored = clean_client.get_project(project.id)
    for response in (updated, stored):
        assert response.id == project.id
        assert response.name == expected["name"]
        assert response.display_name == expected["display_name"]
        assert response.description == expected["description"]
        assert response.project_metadata == expected["project_metadata"]


@pytest.mark.parametrize(
    "client_fixture, use_environment_override, save_project_globally",
    [
        ("clean_client", False, True),
        ("clean_client_with_repo", False, False),
        ("clean_client", True, False),
        ("clean_client", True, True),
    ],
    ids=[
        "global-selection",
        "repository-selection",
        "environment-with-different-global-selection",
        "environment-with-matching-global-selection",
    ],
)
def test_rename_project_preserves_selection_and_resources(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
    client_fixture: str,
    use_environment_override: bool,
    save_project_globally: bool,
) -> None:
    """Renaming refreshes the selected project while retaining resource IDs.

    Args:
        request: Fixture request used to select the client configuration.
        monkeypatch: Fixture for setting the project environment override.
        client_fixture: Name of the isolated client fixture.
        use_environment_override: Whether to select the project via environment.
        save_project_globally: Whether to save the project selection globally
            before setting the environment override.
    """
    client = cast(Client, request.getfixturevalue(client_fixture))
    project = client.create_project("editable-project", "Description")
    if not use_environment_override or save_project_globally:
        client.set_active_project(project.id)
    selected_project = client.active_project
    global_config = GlobalConfiguration()
    global_project = global_config.get_active_project()
    global_project_id = global_config.active_project_id
    global_stack_id = global_config.active_stack_id
    if use_environment_override:
        monkeypatch.setenv(ENV_ZENML_ACTIVE_PROJECT_ID, str(project.id))
    assert client.active_project.name == project.name
    model = client.create_model("existing-model")

    updated = client.update_project(project.id, new_name="renamed-project")

    assert updated.id == project.id
    assert client.active_project.id == project.id
    assert client.active_project.name == "renamed-project"
    assert client.get_project("renamed-project").id == project.id
    assert client.get_model(model.id).project_id == project.id
    assert client.get_model("existing-model").id == model.id
    assert client.create_model("new-model").project_id == project.id
    with pytest.raises(KeyError):
        client.get_project("editable-project", allow_name_prefix_match=False)

    if use_environment_override:
        monkeypatch.delenv(ENV_ZENML_ACTIVE_PROJECT_ID)
    assert global_config.active_project_id == global_project_id
    assert global_config.active_stack_id == global_stack_id
    assert global_config.get_active_project().id == global_project.id
    assert global_config.get_active_project().name == (
        updated.name
        if global_project.id == project.id
        else global_project.name
    )
    assert client.active_project.id == selected_project.id
    assert client.active_project.name == (
        updated.name
        if selected_project.id == project.id
        else selected_project.name
    )


def test_updating_another_project_preserves_active_selection(
    clean_client: Client,
) -> None:
    """Updating another project leaves the selected project's identity intact.

    Args:
        clean_client: Client backed by an isolated SQLite database.
    """
    selected = clean_client.active_project
    project = clean_client.create_project("other-project", "Description")

    clean_client.update_project(project.id, new_name="renamed-project")

    assert clean_client.active_project.id == selected.id
    assert clean_client.active_project.name == selected.name


@pytest.mark.parametrize("new_name", ["", "Has Spaces", "UPPERCASE", "x" * 51])
def test_update_project_rejects_invalid_slug(
    clean_client: Client, new_name: str
) -> None:
    """Invalid slugs fail without changing the existing project.

    Args:
        clean_client: Client backed by an isolated SQLite database.
        new_name: Invalid project slug to reject.
    """
    project = clean_client.create_project("editable-project", "Description")

    with pytest.raises(ValidationError):
        clean_client.update_project(project.id, new_name=new_name)

    assert clean_client.get_project(project.id).name == project.name


def test_default_project_slug_remains_protected(clean_client: Client) -> None:
    """The default slug is protected while its descriptive fields are editable.

    Args:
        clean_client: Client backed by an isolated SQLite database.
    """
    project = clean_client.get_project(DEFAULT_PROJECT_NAME)

    with pytest.raises(IllegalOperationError, match="default project"):
        clean_client.update_project(project.id, new_name="renamed-default")

    updated = clean_client.update_project(
        project.id,
        new_display_name="Default display name",
        new_description="Default description",
    )

    assert updated.id == project.id
    assert updated.name == DEFAULT_PROJECT_NAME
    assert updated.display_name == "Default display name"
    assert updated.description == "Default description"


def test_update_project_rejects_name_prefix(clean_client: Client) -> None:
    """Project updates require an exact name rather than a name prefix.

    Args:
        clean_client: Client backed by an isolated SQLite database.
    """
    project = clean_client.create_project("editable-project", "Description")

    with pytest.raises(KeyError):
        clean_client.update_project("editable", new_name="renamed-project")

    assert clean_client.get_project(project.id).name == project.name


def test_update_project_rejects_duplicate_slug(clean_client: Client) -> None:
    """A conflicting slug fails without changing either project's identity.

    Args:
        clean_client: Client backed by an isolated SQLite database.
    """
    original = clean_client.create_project("original-project", "Original")
    existing = clean_client.create_project("existing-project", "Existing")

    with pytest.raises(EntityExistsError):
        clean_client.update_project(original.id, new_name=existing.name)

    assert clean_client.get_project(original.id).name == original.name
    assert clean_client.get_project(original.name).id == original.id
    assert clean_client.get_project(existing.id).name == existing.name
    assert clean_client.get_project(existing.name).id == existing.id
