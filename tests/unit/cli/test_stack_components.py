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

import pytest
from click.testing import CliRunner

from zenml.cli.cli import cli
from zenml.enums import StackComponentType
from zenml.stack.stack_component import StackComponent

NOT_STACK_COMPONENTS = ["abc", "my_other_cat_is_called_blupus", "stack123"]

# TODO [ENG-829]: Add tests for these commands using REST, SQL and local options


def test_stack_component_update_for_nonexistent_stack_fails(
    clean_repo,
) -> None:
    """Test stack update of nonexistent stack fails."""
    orchestrator_update_command = cli.commands["orchestrator"].commands[
        "update"
    ]
    runner = CliRunner()
    result = runner.invoke(
        orchestrator_update_command,
        ["not_an_orchestrator", "--some_property=123"],
    )
    assert result.exit_code == 1


def test_valid_stack_component_update_succeeds(clean_repo) -> None:
    """Test that valid stack component update succeeds."""
    register_container_registry_command = cli.commands[
        "container-registry"
    ].commands["register"]

    runner = CliRunner()
    register_result = runner.invoke(
        register_container_registry_command,
        [
            "new_container_registry",
            "-t",
            "default",
            "--uri=some_random_uri.com",
        ],
    )
    assert register_result.exit_code == 0
    assert (
        clean_repo.get_stack_component(
            StackComponentType.CONTAINER_REGISTRY, "new_container_registry"
        ).uri
        == "some_random_uri.com"
    )

    update_container_registry_command = cli.commands[
        "container-registry"
    ].commands["update"]
    update_result = runner.invoke(
        update_container_registry_command,
        [
            "new_container_registry",
            "--uri=another_random_uri.com",
        ],
    )
    assert update_result.exit_code == 0
    assert (
        clean_repo.get_stack_component(
            StackComponentType.CONTAINER_REGISTRY, "new_container_registry"
        ).uri
        == "another_random_uri.com"
    )


def test_updating_stack_component_name_or_uuid_fails(clean_repo) -> None:
    """Test that updating stack component name or uuid fails."""
    register_container_registry_command = cli.commands[
        "container-registry"
    ].commands["register"]

    runner = CliRunner()
    register_result = runner.invoke(
        register_container_registry_command,
        [
            "new_container_registry",
            "-t",
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
        clean_repo.get_stack_component(
            StackComponentType.CONTAINER_REGISTRY, "new_container_registry"
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
        clean_repo.get_stack_component(
            StackComponentType.CONTAINER_REGISTRY, "new_container_registry"
        )


def test_updating_stack_component_with_unconfigured_property_fails(
    clean_repo,
) -> None:
    """Test that updating stack component with an unconfigured property fails."""
    register_container_registry_command = cli.commands[
        "container-registry"
    ].commands["register"]

    runner = CliRunner()
    register_result = runner.invoke(
        register_container_registry_command,
        [
            "new_container_registry",
            "-t",
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
        clean_repo.get_stack_component(
            StackComponentType.CONTAINER_REGISTRY, "new_container_registry"
        ).favorite_cat


def test_renaming_stack_component_to_preexisting_name_fails(
    clean_repo,
) -> None:
    """Test that renaming a component to a name that already is occupied
    fails."""
    register_orchestrator_command = cli.commands["orchestrator"].commands[
        "register"
    ]

    runner = CliRunner()
    register_result = runner.invoke(
        register_orchestrator_command,
        [
            "new_orchestrator",
            "-t",
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
    try:
        clean_repo.get_stack_component(
            StackComponentType.ORCHESTRATOR, "new_orchestrator"
        )
    except KeyError:
        assert (
            False
        ), "Stack component was renamed to a name that already exists"


def test_renaming_nonexistent_stack_component_fails(clean_repo) -> None:
    """Test that renaming nonexistent stack component fails."""
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
        clean_repo.get_stack_component(
            StackComponentType.CONTAINER_REGISTRY, "arias_container_registry"
        )
    with pytest.raises(KeyError):
        clean_repo.get_stack_component(
            StackComponentType.CONTAINER_REGISTRY, "not_a_container_registry"
        )


def test_renaming_non_core_component_succeeds(clean_repo) -> None:
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
            "-t",
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
        clean_repo.get_stack_component(
            StackComponentType.CONTAINER_REGISTRY, "some_container_registry"
        )
    assert isinstance(
        clean_repo.get_stack_component(
            StackComponentType.CONTAINER_REGISTRY, new_component_name
        ),
        StackComponent,
    )
    assert (
        clean_repo.get_stack_component(
            StackComponentType.CONTAINER_REGISTRY, new_component_name
        ).name
        == new_component_name
    )


def test_renaming_core_component_succeeds(clean_repo) -> None:
    """Test renaming a core stack component succeeds."""
    new_component_name = "arias_orchestrator"

    rename_orchestrator_command = cli.commands["orchestrator"].commands[
        "rename"
    ]
    runner = CliRunner()
    result = runner.invoke(
        rename_orchestrator_command,
        ["default", new_component_name],
    )
    assert result.exit_code == 0
    with pytest.raises(KeyError):
        clean_repo.get_stack_component(
            StackComponentType.ORCHESTRATOR, "default"
        )
    assert isinstance(
        clean_repo.get_stack_component(
            StackComponentType.ORCHESTRATOR, new_component_name
        ),
        StackComponent,
    )
    assert (
        clean_repo.get_stack_component(
            StackComponentType.ORCHESTRATOR, new_component_name
        ).name
        == new_component_name
    )
    assert (
        clean_repo.get_stack("default").orchestrator.name == new_component_name
    )
