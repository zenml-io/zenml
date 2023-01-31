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

from contextlib import ExitStack as does_not_raise
from datetime import datetime
from uuid import uuid4

import pytest
from click.testing import CliRunner

from zenml.cli.cli import cli
from zenml.enums import StackComponentType
from zenml.stack.stack_component import StackComponent

NOT_STACK_COMPONENTS = ["abc", "my_other_cat_is_called_blupus", "stack123"]


def test_update_stack_component_succeeds(clean_workspace) -> None:
    """Test that valid stack component update succeeds."""
    register_command = cli.commands["container-registry"].commands["register"]
    update_command = cli.commands["container-registry"].commands["update"]

    runner = CliRunner()
    register_result = runner.invoke(
        register_command,
        [
            "new_container_registry",
            "--flavor",
            "default",
            "--uri=some_random_uri.com",
        ],
    )
    assert register_result.exit_code == 0
    assert (
        StackComponent.from_model(
            clean_workspace.get_stack_component(
                name_id_or_prefix="new_container_registry",
                component_type=StackComponentType.CONTAINER_REGISTRY,
            )
        ).config.uri
        == "some_random_uri.com"
    )

    update_result = runner.invoke(
        update_command,
        [
            "new_container_registry",
            "--uri=another_random_uri.com",
        ],
    )
    assert update_result.exit_code == 0
    assert (
        StackComponent.from_model(
            clean_workspace.get_stack_component(
                name_id_or_prefix="new_container_registry",
                component_type=StackComponentType.CONTAINER_REGISTRY,
            )
        ).config.uri
        == "another_random_uri.com"
    )


def test_update_stack_component_for_nonexistent_component_fails(
    clean_workspace,
) -> None:
    """Test stack update of nonexistent stack fails."""
    update_command = cli.commands["orchestrator"].commands["update"]
    runner = CliRunner()
    result = runner.invoke(
        update_command,
        ["not_an_orchestrator", "--some_property=123"],
    )
    assert result.exit_code == 1


def test_update_stack_component_with_name_or_uuid_fails(
    clean_workspace,
) -> None:
    """Test that updating stack component name or uuid fails."""
    register_container_registry_command = cli.commands[
        "container-registry"
    ].commands["register"]

    runner = CliRunner()
    register_result = runner.invoke(
        register_container_registry_command,
        [
            "new_container_registry",
            "--flavor",
            "default",
            "--uri=some_random_uri.com",
        ],
    )
    assert register_result.exit_code == 0

    update_container_registry_command = cli.commands[
        "container-registry"
    ].commands["update"]
    update_result1 = runner.invoke(
        update_container_registry_command,
        [
            "new_container_registry",
            "--name=aria",
        ],
    )
    assert update_result1.exit_code == 1
    with does_not_raise():
        clean_workspace.get_stack_component(
            name_id_or_prefix="new_container_registry",
            component_type=StackComponentType.CONTAINER_REGISTRY,
        )

    update_result2 = runner.invoke(
        update_container_registry_command,
        [
            "new_container_registry",
            "--uuid=aria_uuid",
        ],
    )
    assert update_result2.exit_code == 1
    with does_not_raise():
        clean_workspace.get_stack_component(
            name_id_or_prefix="new_container_registry",
            component_type=StackComponentType.CONTAINER_REGISTRY,
        )


def test_update_stack_component_with_non_configured_property_fails(
    clean_workspace,
) -> None:
    """Updating stack component with aa non-configured property fails."""
    register_container_registry_command = cli.commands[
        "container-registry"
    ].commands["register"]

    runner = CliRunner()
    register_result = runner.invoke(
        register_container_registry_command,
        [
            "new_container_registry",
            "--flavor",
            "default",
            "--uri=some_random_uri.com",
        ],
    )
    assert register_result.exit_code == 0

    update_container_registry_command = cli.commands[
        "container-registry"
    ].commands["update"]
    update_result = runner.invoke(
        update_container_registry_command,
        [
            "new_container_registry",
            "--favorite_cat=aria",
        ],
    )
    assert update_result.exit_code == 1
    with pytest.raises(AttributeError):
        clean_workspace.get_stack_component(
            name_id_or_prefix="new_container_registry",
            component_type=StackComponentType.CONTAINER_REGISTRY,
        ).__getattribute__("favorite_cat")


def test_remove_attribute_component_succeeds(
    clean_workspace, test_flavor
) -> None:
    """Removing an optional attribute from a stack component succeeds."""
    orchestrator = test_flavor.implementation_class(
        name="arias_orchestrator",
        id=uuid4(),
        config=test_flavor.config_class(
            favorite_orchestration_language="arn:arias:aws:iam",
            favorite_orchestration_language_version="a1.big.cat",
        ),
        flavor=test_flavor.name,
        type=test_flavor.type,
        user=clean_workspace.active_user.id,
        workspace=clean_workspace.active_workspace.id,
        created=datetime.now(),
        updated=datetime.now(),
    )

    orchestrator_response = clean_workspace.create_stack_component(
        name=orchestrator.name,
        component_type=orchestrator.type,
        flavor=orchestrator.flavor,
        configuration=orchestrator.config.dict(),
    )

    assert (
        "favorite_orchestration_language_version"
        in orchestrator_response.configuration
    )

    runner = CliRunner()
    remove_attribute_command = cli.commands["orchestrator"].commands[
        "remove-attribute"
    ]
    remove_attribute = runner.invoke(
        remove_attribute_command,
        [
            f"{orchestrator_response.name}",
            "favorite_orchestration_language_version",
        ],
    )
    assert remove_attribute.exit_code == 0

    orchestrator_response = clean_workspace.get_stack_component(
        name_id_or_prefix=orchestrator_response.id,
        component_type=StackComponentType.ORCHESTRATOR,
    )

    assert (
        "favorite_orchestration_language_version"
        not in orchestrator_response.configuration
    )


def test_remove_attribute_component_non_existent_attributes_fail(
    clean_workspace,
) -> None:
    """Removing a nonexistent component attribute fails."""
    runner = CliRunner()

    remove_attribute_command = cli.commands["orchestrator"].commands[
        "remove-attribute"
    ]
    remove_attribute = runner.invoke(
        remove_attribute_command,
        [
            "default",
            "something_that_is_not_an_existing_attribute",
        ],
    )
    assert remove_attribute.exit_code != 0


def test_remove_attribute_component_nonexistent_component_fails(
    clean_workspace,
) -> None:
    """Removing an attribute from a nonexistent stack component fails."""
    runner = CliRunner()

    remove_attribute_command = cli.commands["orchestrator"].commands[
        "remove-attribute"
    ]
    remove_attribute = runner.invoke(
        remove_attribute_command,
        [
            "some_nonexistent_aria_orchestrator",
            "cat-size",
        ],
    )
    assert remove_attribute.exit_code != 0


def test_remove_attribute_component_required_attribute_fails(
    clean_workspace, test_flavor
) -> None:
    """Removing a required attribute from a stack component fails."""
    orchestrator = test_flavor.implementation_class(
        name="arias_orchestrator",
        id=uuid4(),
        config=test_flavor.config_class(
            favorite_orchestration_language="arn:arias:aws:iam",
            favorite_orchestration_language_version="a1.big.cat",
        ),
        flavor=test_flavor.name,
        type=test_flavor.type,
        user=clean_workspace.active_user.id,
        workspace=clean_workspace.active_workspace.id,
        created=datetime.now(),
        updated=datetime.now(),
    )

    orchestrator_response = clean_workspace.create_stack_component(
        name=orchestrator.name,
        component_type=orchestrator.type,
        flavor=orchestrator.flavor,
        configuration=orchestrator.config.dict(),
    )

    runner = CliRunner()
    remove_attribute_command = cli.commands["orchestrator"].commands[
        "remove-attribute"
    ]
    remove_attribute = runner.invoke(
        remove_attribute_command,
        [
            f"{orchestrator_response.name}",
            "favorite_orchestration_language",
        ],
    )
    assert remove_attribute.exit_code != 0


def test_rename_stack_component_to_preexisting_name_fails(
    clean_workspace,
) -> None:
    """Renaming a component to a name that already is occupied fails."""
    register_orchestrator_command = cli.commands["orchestrator"].commands[
        "register"
    ]

    runner = CliRunner()
    register_result = runner.invoke(
        register_orchestrator_command,
        [
            "new_orchestrator",
            "--flavor",
            "local",
        ],
    )
    assert register_result.exit_code == 0

    rename_orchestrator_command = cli.commands["orchestrator"].commands[
        "rename"
    ]
    runner = CliRunner()
    result = runner.invoke(
        rename_orchestrator_command,
        ["new_orchestrator", "default"],
    )
    assert result.exit_code == 1
    with does_not_raise():
        clean_workspace.get_stack_component(
            name_id_or_prefix="new_orchestrator",
            component_type=StackComponentType.ORCHESTRATOR,
        )


def test_rename_stack_component_nonexistent_component_fails(
    clean_workspace,
) -> None:
    """Renaming nonexistent stack component fails."""
    rename_container_registry_command = cli.commands[
        "container-registry"
    ].commands["rename"]
    runner = CliRunner()
    result = runner.invoke(
        rename_container_registry_command,
        ["not_a_container_registry", "arias_container_registry"],
    )
    assert result.exit_code == 1
    with pytest.raises(KeyError):
        clean_workspace.get_stack_component(
            name_id_or_prefix="arias_container_registry",
            component_type=StackComponentType.ORCHESTRATOR,
        )
    with pytest.raises(KeyError):
        clean_workspace.get_stack_component(
            name_id_or_prefix="arias_container_registry",
            component_type=StackComponentType.ORCHESTRATOR,
        )


def test_renaming_non_core_component_succeeds(clean_workspace) -> None:
    """Test renaming a non-core stack component succeeds."""
    new_component_name = "arias_container_registry"
    register_container_registry_command = cli.commands[
        "container-registry"
    ].commands["register"]

    runner = CliRunner()
    register_result = runner.invoke(
        register_container_registry_command,
        [
            "some_container_registry",
            "--flavor",
            "default",
            "--uri=some_random_uri.com",
        ],
    )
    assert register_result.exit_code == 0

    rename_container_registry_command = cli.commands[
        "container-registry"
    ].commands["rename"]
    runner = CliRunner()
    result = runner.invoke(
        rename_container_registry_command,
        ["some_container_registry", new_component_name],
    )
    assert result.exit_code == 0
    with pytest.raises(KeyError):
        clean_workspace.get_stack_component(
            name_id_or_prefix="some_container_registry",
            component_type=StackComponentType.CONTAINER_REGISTRY,
        )
    with does_not_raise():
        clean_workspace.get_stack_component(
            name_id_or_prefix=new_component_name,
            component_type=StackComponentType.CONTAINER_REGISTRY,
        )


def test_renaming_core_component_succeeds(clean_workspace) -> None:
    """Test renaming a core stack component succeeds."""
    new_component_name = "arias_orchestrator"
    register_orchestrator_command = cli.commands["orchestrator"].commands[
        "register"
    ]

    runner = CliRunner()
    register_result = runner.invoke(
        register_orchestrator_command,
        [
            "some_orchestrator",
            "--flavor",
            "local",
        ],
    )
    assert register_result.exit_code == 0

    new_component_name = "arias_orchestrator"

    rename_orchestrator_command = cli.commands["orchestrator"].commands[
        "rename"
    ]
    runner = CliRunner()
    result = runner.invoke(
        rename_orchestrator_command,
        ["some_orchestrator", new_component_name],
    )
    assert result.exit_code == 0
    with pytest.raises(KeyError):
        clean_workspace.get_stack_component(
            name_id_or_prefix="some_orchestrator",
            component_type=StackComponentType.ORCHESTRATOR,
        )
    with does_not_raise():
        clean_workspace.get_stack_component(
            name_id_or_prefix=new_component_name,
            component_type=StackComponentType.ORCHESTRATOR,
        )


def test_renaming_default_component_fails(clean_workspace) -> None:
    """Test renaming a default stack component fails."""
    new_component_name = "aria"

    runner = CliRunner()
    rename_command = cli.commands["orchestrator"].commands["rename"]
    result = runner.invoke(
        rename_command,
        ["default", new_component_name],
    )
    assert result.exit_code == 1
    with does_not_raise():
        clean_workspace.get_stack_component(
            name_id_or_prefix="default",
            component_type=StackComponentType.ORCHESTRATOR,
        )
    with pytest.raises(KeyError):
        clean_workspace.get_stack_component(
            name_id_or_prefix=new_component_name,
            component_type=StackComponentType.ORCHESTRATOR,
        )

    rename_command = cli.commands["artifact-store"].commands["rename"]
    result = runner.invoke(
        rename_command,
        ["default", new_component_name],
    )
    assert result.exit_code == 1
    with does_not_raise():
        clean_workspace.get_stack_component(
            name_id_or_prefix="default",
            component_type=StackComponentType.ARTIFACT_STORE,
        )
    with pytest.raises(KeyError):
        clean_workspace.get_stack_component(
            name_id_or_prefix=new_component_name,
            component_type=StackComponentType.ARTIFACT_STORE,
        )


def test_delete_default_component_fails(clean_workspace) -> None:
    """Test deleting a default stack component fails."""
    runner = CliRunner()
    delete_command = cli.commands["orchestrator"].commands["delete"]
    result = runner.invoke(
        delete_command,
        ["default"],
    )
    assert result.exit_code == 1
    with does_not_raise():
        clean_workspace.get_stack_component(
            name_id_or_prefix="default",
            component_type=StackComponentType.ORCHESTRATOR,
        )
    delete_command = cli.commands["artifact-store"].commands["delete"]
    result = runner.invoke(
        delete_command,
        ["default"],
    )
    assert result.exit_code == 1
    with does_not_raise():
        clean_workspace.get_stack_component(
            name_id_or_prefix="default",
            component_type=StackComponentType.ARTIFACT_STORE,
        )
