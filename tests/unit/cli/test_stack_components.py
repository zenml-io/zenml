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
from typing import Iterator
from uuid import uuid4

import pytest
from click.testing import CliRunner

from tests.unit.test_flavor import AriaOrchestratorFlavor
from zenml.cli.cli import cli
from zenml.enums import StackComponentType
from zenml.models import FlavorModel
from zenml.stack.flavor_registry import flavor_registry
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
            "--flavor",
            "default",
            "--uri=some_random_uri.com",
        ],
    )
    assert register_result.exit_code == 0
    assert (
        StackComponent.from_model(
            clean_repo.get_stack_component_by_name_and_type(
                type=StackComponentType.CONTAINER_REGISTRY,
                name="new_container_registry",
            )
        ).config.uri
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
        StackComponent.from_model(
            clean_repo.get_stack_component_by_name_and_type(
                type=StackComponentType.CONTAINER_REGISTRY,
                name="new_container_registry",
            )
        ).config.uri
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
        clean_repo.get_stack_component_by_name_and_type(
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
        clean_repo.get_stack_component_by_name_and_type(
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
        clean_repo.get_stack_component_by_name_and_type(
            StackComponentType.CONTAINER_REGISTRY, "new_container_registry"
        ).favorite_cat


@pytest.fixture
def test_flavor() -> Iterator[FlavorModel]:
    """Create a flavor for testing."""

    aria_flavor = AriaOrchestratorFlavor()
    flavor_registry._register_flavor(aria_flavor.to_model())
    yield aria_flavor
    flavor_registry._flavors[aria_flavor.type].pop(aria_flavor.name)


def test_removing_attributes_from_stack_component_works(
    clean_repo, test_flavor
) -> None:
    """Test that removing an optional attribute from a stack component succeeds."""

    new_orchestrator = test_flavor.implementation_class(
        name="arias_orchestrator",
        id=uuid4(),
        config=test_flavor.config_class(
            favorite_orchestration_language="arn:arias:aws:iam",
            favorite_orchestration_language_version="a1.big.cat",
        ),
        flavor=test_flavor.name,
        type=test_flavor.type,
        user=clean_repo.active_user.id,
        project=clean_repo.active_project.id,
        created=datetime.now(),
        updated=datetime.now(),
    )
    clean_repo.register_stack_component(new_orchestrator.to_model())
    orchestrator = clean_repo.get_stack_component_by_name_and_type(
        StackComponentType.ORCHESTRATOR, f"{new_orchestrator.name}"
    )
    orchestrator = StackComponent.from_model(orchestrator.to_hydrated_model())
    assert (
        orchestrator.config.favorite_orchestration_language_version is not None
    )

    runner = CliRunner()
    remove_attribute_command = cli.commands["orchestrator"].commands[
        "remove-attribute"
    ]
    remove_attribute = runner.invoke(
        remove_attribute_command,
        [
            f"{new_orchestrator.name}",
            "--favorite_orchestration_language_version",
        ],
    )
    assert remove_attribute.exit_code == 0
    orchestrator = clean_repo.get_stack_component_by_name_and_type(
        StackComponentType.ORCHESTRATOR, f"{new_orchestrator.name}"
    )
    orchestrator = StackComponent.from_model(orchestrator.to_hydrated_model())
    assert orchestrator.config.favorite_orchestration_language_version is None


def test_removing_nonexistent_component_attributes_fails(clean_repo) -> None:
    """Test that removing a a nonexistent component attribute fails."""
    runner = CliRunner()

    remove_attribute_command = cli.commands["orchestrator"].commands[
        "remove-attribute"
    ]
    remove_attribute = runner.invoke(
        remove_attribute_command,
        [
            "default",
            "--something_that_is_not_an_existing_attribute",
        ],
    )
    assert remove_attribute.exit_code != 0


def test_removing_attribute_from_nonexistent_component_fails(
    clean_repo,
) -> None:
    """Test that removing an attribute from a nonexistent stack component fails."""
    runner = CliRunner()

    remove_attribute_command = cli.commands["orchestrator"].commands[
        "remove-attribute"
    ]
    remove_attribute = runner.invoke(
        remove_attribute_command,
        [
            "some_nonexistent_aria_orchestrator",
            "--cat-size",
        ],
    )
    assert remove_attribute.exit_code != 0


def test_removing_required_attribute_fails(clean_repo) -> None:
    """Test that removing a required attribute from a stack component fails."""
    runner = CliRunner()

    remove_attribute_command = cli.commands["artifact-store"].commands[
        "remove-attribute"
    ]
    remove_attribute = runner.invoke(
        remove_attribute_command,
        [
            "default",
            "--uri",
        ],
    )
    assert remove_attribute.exit_code != 0


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
        clean_repo.get_stack_component_by_name_and_type(
            StackComponentType.ORCHESTRATOR, "new_orchestrator"
        )


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
        clean_repo.get_stack_component_by_name_and_type(
            StackComponentType.CONTAINER_REGISTRY, "arias_container_registry"
        )
    with pytest.raises(KeyError):
        clean_repo.get_stack_component_by_name_and_type(
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
        clean_repo.get_stack_component_by_name_and_type(
            StackComponentType.CONTAINER_REGISTRY,
            "some_container_registry",
        )
    with does_not_raise():
        clean_repo.get_stack_component_by_name_and_type(
            StackComponentType.CONTAINER_REGISTRY, new_component_name
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
        clean_repo.get_stack_component_by_name_and_type(
            StackComponentType.ORCHESTRATOR, "default"
        )
    with does_not_raise():
        clean_repo.get_stack_component_by_name_and_type(
            type=StackComponentType.ORCHESTRATOR, name=new_component_name
        )
