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

import os
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

import pytest
from click.testing import CliRunner

from zenml.artifact_stores.local_artifact_store import (
    LocalArtifactStore,
    LocalArtifactStoreConfig,
)
from zenml.cli.stack import (
    delete_stack,
    describe_stack,
    export_stack,
    import_stack,
    register_stack,
    remove_stack_component,
    rename_stack,
    share_stack,
    update_stack,
)
from zenml.client import Client
from zenml.enums import StackComponentType
from zenml.models import UserModel
from zenml.orchestrators.base_orchestrator import BaseOrchestratorConfig
from zenml.orchestrators.local.local_orchestrator import LocalOrchestrator
from zenml.secrets_managers.local.local_secrets_manager import (
    LocalSecretsManager,
    LocalSecretsManagerConfig,
)
from zenml.stack import Stack

NOT_STACKS = ["abc", "my_other_cat_is_called_blupus", "stack123"]

# TODO [ENG-828]: Add tests for these commands using REST, SQL and local options


def _create_local_orchestrator(
    repo: Client, user: Optional[UUID] = None, project: Optional[UUID] = None
):
    """Returns a local orchestrator."""
    return LocalOrchestrator(
        name="arias_orchestrator",
        id=uuid4(),
        config=BaseOrchestratorConfig(),
        flavor="local",
        type=StackComponentType.ORCHESTRATOR,
        user=user or repo.active_user.id,
        project=project or repo.active_project.id,
        created=datetime.now(),
        updated=datetime.now(),
    )


def _create_local_artifact_store(
    repo: Client, user: Optional[UUID] = None, project: Optional[UUID] = None
):
    """Fixture that creates a local artifact store for testing."""
    return LocalArtifactStore(
        name="arias_artifact_store",
        id=uuid4(),
        config=LocalArtifactStoreConfig(),
        flavor="local",
        type=StackComponentType.ARTIFACT_STORE,
        user=user or repo.active_user.id,
        project=project or repo.active_project.id,
        created=datetime.now(),
        updated=datetime.now(),
    )


def _create_local_secrets_manager(repo: Client):
    return LocalSecretsManager(
        name="arias_secrets_manager",
        id=uuid4(),
        config=LocalSecretsManagerConfig(),
        flavor="local",
        type=StackComponentType.SECRETS_MANAGER,
        user=repo.active_user.id,
        project=repo.active_project.id,
        share_stack=False,
        created=datetime.now(),
        updated=datetime.now(),
    )


def test_stack_describe_contains_local_stack() -> None:
    """Test that the stack describe command contains the default local stack"""
    runner = CliRunner()
    result = runner.invoke(describe_stack)
    assert result.exit_code == 0
    assert "default" in result.output


@pytest.mark.parametrize("not_a_stack", NOT_STACKS)
def test_stack_describe_fails_for_bad_input(
    not_a_stack: str,
) -> None:
    """Test that the stack describe command fails when passing in bad parameters"""
    runner = CliRunner()
    result = runner.invoke(describe_stack, [not_a_stack])
    assert result.exit_code == 1


def test_updating_default_stack_fails(clean_client) -> None:
    """Test stack update of default stack is prohibited."""
    # first we set the active stack to a non-default stack
    original_stack = clean_client.active_stack

    new_artifact_store = _create_local_artifact_store(clean_client)
    clean_client.register_stack_component(new_artifact_store.to_model())

    runner = CliRunner()
    result = runner.invoke(
        update_stack, ["default", "-a", new_artifact_store.name]
    )
    assert result.exit_code == 1

    default_stack = [s for s in clean_client.stacks if s.name == "default"][0]
    assert (
        default_stack.components[StackComponentType.ARTIFACT_STORE][0].id
        == original_stack.artifact_store.id
    )


def test_updating_active_stack_succeeds(clean_client) -> None:
    """Test stack update of active stack succeeds."""
    # first we set the active stack to a non-default stack
    registered_stack = clean_client.active_stack
    new_stack = Stack(
        id=uuid4(),
        name="arias_new_stack",
        orchestrator=registered_stack.orchestrator,
        artifact_store=registered_stack.artifact_store,
    )
    stack_model = new_stack.to_model(
        user=clean_client.active_user.id, project=clean_client.active_project.id
    )
    clean_client.register_stack(stack_model)
    clean_client.activate_stack(new_stack)

    new_artifact_store = _create_local_artifact_store(clean_client)
    clean_client.register_stack_component(new_artifact_store.to_model())

    runner = CliRunner()
    result = runner.invoke(update_stack, ["-a", new_artifact_store.name])
    assert result.exit_code == 0
    assert clean_client.active_stack.artifact_store == new_artifact_store


def test_updating_non_active_stack_succeeds(clean_client) -> None:
    """Test stack update of pre-existing component of non-active stack succeeds."""
    registered_stack = clean_client.active_stack
    new_stack = Stack(
        id=uuid4(),
        name="arias_new_stack",
        orchestrator=registered_stack.orchestrator,
        artifact_store=registered_stack.artifact_store,
    )
    stack_model = new_stack.to_model(
        user=clean_client.active_user.id, project=clean_client.active_project.id
    )
    clean_client.register_stack(stack_model)

    new_orchestrator = _create_local_orchestrator(clean_client)
    clean_client.register_stack_component(new_orchestrator.to_model())

    runner = CliRunner()
    result = runner.invoke(
        update_stack, ["arias_new_stack", "-o", new_orchestrator.name]
    )
    assert result.exit_code == 0

    updated_stack = Stack.from_model(
        clean_client.zen_store.get_stack(stack_model.id).to_hydrated_model()
    )
    assert updated_stack.orchestrator == new_orchestrator


def test_adding_to_stack_succeeds(clean_client) -> None:
    """Test stack update by adding a new component to a stack
    succeeds."""
    # first we create and activate a non-default stack
    registered_stack = clean_client.active_stack
    new_stack = Stack(
        id=uuid4(),
        name="arias_new_stack",
        orchestrator=registered_stack.orchestrator,
        artifact_store=registered_stack.artifact_store,
    )
    stack_model = new_stack.to_model(
        user=clean_client.active_user.id, project=clean_client.active_project.id
    )
    clean_client.register_stack(stack_model)
    clean_client.activate_stack(new_stack)

    local_secrets_manager = _create_local_secrets_manager(clean_client)
    clean_client.register_stack_component(local_secrets_manager.to_model())

    runner = CliRunner()
    result = runner.invoke(update_stack, ["-x", local_secrets_manager.name])

    active_stack = clean_client.active_stack_model

    assert result.exit_code == 0
    assert StackComponentType.SECRETS_MANAGER in active_stack.components.keys()
    assert (
        active_stack.components[StackComponentType.SECRETS_MANAGER] is not None
    )
    assert (
        active_stack.components[StackComponentType.SECRETS_MANAGER][0].id
        == local_secrets_manager.id
    )


def test_adding_to_default_stack_fails(clean_client) -> None:
    """Test stack update by adding a new component to the default stack
    is prohibited."""
    # first we set the active stack to a non-default stack
    registered_stack = clean_client.active_stack
    new_stack = Stack(
        id=uuid4(),
        name="arias_new_stack",
        orchestrator=registered_stack.orchestrator,
        artifact_store=registered_stack.artifact_store,
    )
    stack_model = new_stack.to_model(
        user=clean_client.active_user.id, project=clean_client.active_project.id
    )
    clean_client.register_stack(stack_model)
    clean_client.activate_stack(new_stack)

    local_secrets_manager = _create_local_secrets_manager(clean_client)
    clean_client.register_stack_component(local_secrets_manager.to_model())

    runner = CliRunner()
    result = runner.invoke(
        update_stack, ["default", "-x", local_secrets_manager.name]
    )
    assert result.exit_code == 1

    default_stack = [s for s in clean_client.stacks if s.name == "default"][0]
    assert (
        StackComponentType.SECRETS_MANAGER
        not in default_stack.components.keys()
    )


def test_updating_nonexistent_stack_fails(clean_client) -> None:
    """Test stack update of nonexistent stack fails."""
    local_secrets_manager = _create_local_secrets_manager(clean_client)
    clean_client.register_stack_component(local_secrets_manager.to_model())

    runner = CliRunner()
    result = runner.invoke(
        update_stack, ["not_a_stack", "-x", local_secrets_manager.name]
    )

    assert result.exit_code == 1
    assert clean_client.active_stack.secrets_manager is None


def test_renaming_nonexistent_stack_fails(clean_client) -> None:
    """Test stack rename of nonexistent stack fails."""
    runner = CliRunner()
    result = runner.invoke(rename_stack, ["not_a_stack", "a_new_stack"])
    assert result.exit_code == 1


def test_renaming_stack_to_same_name_as_existing_stack_fails(
    clean_client,
) -> None:
    runner = CliRunner()
    result = runner.invoke(rename_stack, ["not_a_stack", "default"])
    assert result.exit_code == 1


def test_renaming_default_stack_fails(clean_client) -> None:
    """Test stack rename of default stack fails."""
    runner = CliRunner()
    result = runner.invoke(rename_stack, ["default", "axls_new_stack"])
    assert result.exit_code == 1
    assert len([s for s in clean_client.stacks if s.name == "default"]) == 1


def test_renaming_active_stack_succeeds(clean_client) -> None:
    """Test stack rename of active stack fails."""
    # first we set the active stack to a non-default stack
    registered_stack = clean_client.active_stack
    new_stack = Stack(
        id=uuid4(),
        name="arias_new_stack",
        orchestrator=registered_stack.orchestrator,
        artifact_store=registered_stack.artifact_store,
    )
    stack_model = new_stack.to_model(
        user=clean_client.active_user.id, project=clean_client.active_project.id
    )
    clean_client.register_stack(stack_model)
    clean_client.activate_stack(new_stack)

    runner = CliRunner()
    result = runner.invoke(rename_stack, ["arias_new_stack", "axls_new_stack"])
    assert result.exit_code == 0
    assert clean_client.active_stack_model.name == "axls_new_stack"


def test_renaming_non_active_stack_succeeds(clean_client) -> None:
    """Test stack rename of non-active stack succeeds."""
    registered_stack = clean_client.active_stack
    new_stack = Stack(
        id=uuid4(),
        name="arias_stack",
        orchestrator=registered_stack.orchestrator,
        artifact_store=registered_stack.artifact_store,
    )
    stack_model = new_stack.to_model(
        user=clean_client.active_user.id, project=clean_client.active_project.id
    )
    clean_client.register_stack(stack_model)

    runner = CliRunner()
    result = runner.invoke(rename_stack, ["arias_stack", "arias_renamed_stack"])
    assert result.exit_code == 0
    assert (
        clean_client.zen_store.get_stack(stack_model.id).name
        == "arias_renamed_stack"
    )


def test_sharing_nonexistent_stack_fails(clean_client: Client) -> None:
    """Test stack rename of nonexistent stack fails."""
    runner = CliRunner()
    result = runner.invoke(share_stack, ["not_a_stack"])
    assert result.exit_code == 1


def test_sharing_default_stack_fails(
    clean_client: Client,
) -> None:
    runner = CliRunner()
    result = runner.invoke(share_stack, ["default"])
    assert result.exit_code == 1

    default_stack = [s for s in clean_client.stacks if s.name == "default"][0]
    assert default_stack.is_shared is False


def test_share_stack_that_is_already_shared_by_other_user_fails(
    clean_client: Client,
) -> None:
    # first we create a new non-default stack
    new_orchestrator = _create_local_orchestrator(clean_client)
    clean_client.register_stack_component(new_orchestrator.to_model())
    new_artifact_store = _create_local_artifact_store(clean_client)
    clean_client.register_stack_component(new_artifact_store.to_model())

    new_stack = Stack(
        id=uuid4(),
        name="arias_new_stack",
        orchestrator=new_orchestrator,
        artifact_store=new_artifact_store,
    )
    stack_model = new_stack.to_model(
        user=clean_client.active_user.id, project=clean_client.active_project.id
    )
    clean_client.register_stack(stack_model)

    other_user = UserModel(name="Arias_Evil_Twin")
    other_user = clean_client.zen_store.create_user(other_user)

    other_orchestrator = _create_local_orchestrator(
        clean_client, user=other_user.id
    )
    clean_client.register_stack_component(other_orchestrator.to_model())
    other_artifact_store = _create_local_artifact_store(
        clean_client, user=other_user.id
    )
    clean_client.register_stack_component(other_artifact_store.to_model())

    other_stack = Stack(
        id=uuid4(),
        name="arias_new_stack",
        orchestrator=other_orchestrator,
        artifact_store=other_artifact_store,
    )
    other_stack_model = other_stack.to_model(
        user=other_user.id, project=clean_client.active_project.id
    )
    other_stack_model.is_shared = True
    clean_client.register_stack(other_stack_model)

    runner = CliRunner()

    result = runner.invoke(share_stack, ["arias_new_stack"])
    assert result.exit_code == 1

    arias_stack = [
        s for s in clean_client.stacks if s.name == "arias_new_stack"
    ][0]
    assert arias_stack.is_shared is False


def test_share_stack_when_component_is_already_shared_by_other_user_fails(
    clean_client: Client,
) -> None:
    """When sharing a stack all the components are also shared, so if a
    component with the same name is already shared this should fail."""
    # first we create a new non-default stack
    new_orchestrator = _create_local_orchestrator(clean_client)
    clean_client.register_stack_component(new_orchestrator.to_model())
    new_artifact_store = _create_local_artifact_store(clean_client)
    clean_client.register_stack_component(new_artifact_store.to_model())

    new_stack = Stack(
        id=uuid4(),
        name="arias_new_stack",
        orchestrator=new_orchestrator,
        artifact_store=new_artifact_store,
    )
    stack_model = new_stack.to_model(
        user=clean_client.active_user.id, project=clean_client.active_project.id
    )
    clean_client.register_stack(stack_model)

    other_user = UserModel(name="Arias_Evil_Twin")
    other_user = clean_client.zen_store.create_user(other_user)

    other_orchestrator = _create_local_orchestrator(
        clean_client, user=other_user.id
    )
    orchestrator_model = other_orchestrator.to_model()
    orchestrator_model.is_shared = True
    clean_client.register_stack_component(orchestrator_model)

    runner = CliRunner()

    result = runner.invoke(share_stack, ["arias_new_stack"])
    assert result.exit_code == 1

    arias_stack = [
        s for s in clean_client.stacks if s.name == "arias_new_stack"
    ][0]
    assert arias_stack.is_shared is False


def test_create_shared_stack_when_component_is_private_fails(
    clean_client: Client,
) -> None:
    """When sharing a stack all the components should also be shared, so if a
    component is not shared this should fail."""
    runner = CliRunner()
    result = runner.invoke(
        register_stack,
        ["default2", "-o", "default", "-a", "default", "--share"],
    )
    assert result.exit_code == 1


def test_add_private_component_to_shared_stack_fails(
    clean_client: Client,
) -> None:
    """When sharing a stack all the components are also shared, so if a
    component with the same name is already shared this should fail."""
    runner = CliRunner()
    local_secrets_manager = _create_local_secrets_manager(clean_client)
    clean_client.register_stack_component(local_secrets_manager.to_model())
    result = runner.invoke(share_stack, ["default", "-r"])
    assert result.exit_code == 0
    result = runner.invoke(
        update_stack, ["default", "-x", "arias_secrets_manager"]
    )
    assert result.exit_code == 1


def test_share_stack_when_component_is_private_fails(
    clean_client: Client,
) -> None:
    """When sharing a stack all the components are also shared, so if a
    component with the same name is already shared this should fail."""
    runner = CliRunner()
    result = runner.invoke(share_stack, ["default"])
    assert result.exit_code == 1


def test_remove_component_from_nonexistent_stack_fails(clean_client) -> None:
    """Test stack remove-component of nonexistent stack fails."""
    runner = CliRunner()
    result = runner.invoke(remove_stack_component, ["not_a_stack", "-x"])
    assert result.exit_code == 1


def test_remove_core_component_from_stack_fails(clean_client) -> None:
    """Test stack remove-component of core component fails."""
    # first we create a non-default stack
    registered_stack = clean_client.active_stack
    new_stack = Stack(
        id=uuid4(),
        name="arias_new_stack",
        orchestrator=registered_stack.orchestrator,
        artifact_store=registered_stack.artifact_store,
    )
    stack_model = new_stack.to_model(
        user=clean_client.active_user.id, project=clean_client.active_project.id
    )
    clean_client.register_stack(stack_model)

    runner = CliRunner()
    result = runner.invoke(remove_stack_component, ["arias_new_stack", "-o"])
    assert result.exit_code != 0
    arias_stack = [
        s for s in clean_client.stacks if s.name == "arias_new_stack"
    ][0]

    assert StackComponentType.ORCHESTRATOR in arias_stack.components


def test_remove_non_core_component_from_stack_succeeds(clean_client) -> None:
    """Test stack remove-component of non-core component succeeds."""
    # first we create a non-default stack
    local_secrets_manager = _create_local_secrets_manager(clean_client)
    clean_client.register_stack_component(local_secrets_manager.to_model())

    registered_stack = clean_client.active_stack
    new_stack = Stack(
        id=uuid4(),
        name="arias_new_stack",
        orchestrator=registered_stack.orchestrator,
        artifact_store=registered_stack.artifact_store,
        secrets_manager=local_secrets_manager,
    )
    stack_model = new_stack.to_model(
        user=clean_client.active_user.id, project=clean_client.active_project.id
    )
    clean_client.register_stack(stack_model)

    runner = CliRunner()

    result = runner.invoke(remove_stack_component, ["arias_new_stack", "-x"])
    assert result.exit_code == 0
    assert clean_client.active_stack.secrets_manager is None


def test_deleting_stack_with_flag_succeeds(clean_client) -> None:
    """Test stack delete with flag succeeds."""
    new_stack = Stack(
        id=uuid4(),
        name="arias_new_stack",
        orchestrator=clean_client.active_stack.orchestrator,
        artifact_store=clean_client.active_stack.artifact_store,
    )
    stack_model = new_stack.to_model(
        user=clean_client.active_user.id, project=clean_client.active_project.id
    )
    clean_client.register_stack(stack_model)
    runner = CliRunner()
    result = runner.invoke(delete_stack, ["arias_new_stack", "-y"])
    assert result.exit_code == 0
    with pytest.raises(KeyError):
        clean_client.zen_store.get_stack(stack_model.id)


def test_deleting_default_stack_fails(clean_client) -> None:
    """Test stack delete default stack fails."""
    # first we set the active stack to a non-default stack
    registered_stack = clean_client.active_stack
    new_stack = Stack(
        id=uuid4(),
        name="arias_new_stack",
        orchestrator=registered_stack.orchestrator,
        artifact_store=registered_stack.artifact_store,
    )
    stack_model = new_stack.to_model(
        user=clean_client.active_user.id, project=clean_client.active_project.id
    )
    clean_client.register_stack(stack_model)
    clean_client.activate_stack(new_stack)

    runner = CliRunner()
    result = runner.invoke(delete_stack, ["default", "-y"])
    assert result.exit_code == 1
    assert len([s for s in clean_client.stacks if s.name == "default"]) == 1


def test_stack_export(clean_client) -> None:
    """Test exporting default stack succeeds."""
    runner = CliRunner()
    result = runner.invoke(export_stack, ["default", "default.yaml"])
    assert result.exit_code == 0
    assert os.path.exists("default.yaml")


def test_stack_export_delete_import(clean_client) -> None:
    """Test exporting, deleting, then importing a stack succeeds."""
    # create new stack
    artifact_store = _create_local_artifact_store(clean_client)

    clean_client.register_stack_component(artifact_store.to_model())
    orchestrator = _create_local_orchestrator(clean_client)

    clean_client.register_stack_component(orchestrator.to_model())
    stack_name = "arias_new_stack"
    stack = Stack(
        id=uuid4(),
        name=stack_name,
        orchestrator=orchestrator,
        artifact_store=artifact_store,
    )
    stack_model = stack.to_model(
        user=clean_client.active_user.id, project=clean_client.active_project.id
    )
    clean_client.register_stack(stack_model)

    # export stack
    runner = CliRunner()
    file_name = "arias_new_stack.yaml"
    result = runner.invoke(export_stack, [stack_name, file_name])
    assert result.exit_code == 0
    assert os.path.exists("arias_new_stack.yaml")

    # delete stack and corresponding components
    clean_client.deregister_stack(stack_model)
    clean_client.deregister_stack_component(orchestrator.to_model())
    clean_client.deregister_stack_component(artifact_store.to_model())
    with pytest.raises(KeyError):
        clean_client.zen_store.get_stack(stack_model.id)

    # import stack
    result = runner.invoke(import_stack, [stack_name, "--filename", file_name])
    assert result.exit_code == 0
    assert len(clean_client.zen_store.list_stacks(name="arias_new_stack")) > 0
