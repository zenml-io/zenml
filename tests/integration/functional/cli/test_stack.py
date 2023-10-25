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
from zenml.cli.cli import cli
from zenml.client import Client
from zenml.enums import StackComponentType
from zenml.orchestrators.base_orchestrator import BaseOrchestratorConfig
from zenml.orchestrators.local.local_orchestrator import LocalOrchestrator
from zenml.secrets_managers.local.local_secrets_manager import (
    LocalSecretsManager,
    LocalSecretsManagerConfig,
)

NOT_STACKS = ["abc_def", "my_other_cat_is_called_blupus", "stack123"]


def _create_local_orchestrator(
    repo: Client, user: Optional[UUID] = None, workspace: Optional[UUID] = None
):
    """Returns a local orchestrator."""
    return LocalOrchestrator(
        name="arias_orchestrator",
        id=uuid4(),
        config=BaseOrchestratorConfig(),
        flavor="local",
        type=StackComponentType.ORCHESTRATOR,
        user=user or repo.active_user.id,
        workspace=workspace or repo.active_workspace.id,
        created=datetime.now(),
        updated=datetime.now(),
    )


def _create_local_artifact_store(
    repo: Client, user: Optional[UUID] = None, workspace: Optional[UUID] = None
):
    """Fixture that creates a local artifact store for testing."""
    return LocalArtifactStore(
        name="arias_artifact_store",
        id=uuid4(),
        config=LocalArtifactStoreConfig(),
        flavor="local",
        type=StackComponentType.ARTIFACT_STORE,
        user=user or repo.active_user.id,
        workspace=workspace or repo.active_workspace.id,
        created=datetime.now(),
        updated=datetime.now(),
    )


def _create_local_secrets_manager(client: Client):
    return LocalSecretsManager(
        name="arias_secrets_manager",
        id=uuid4(),
        config=LocalSecretsManagerConfig(),
        flavor="local",
        type=StackComponentType.SECRETS_MANAGER,
        user=client.active_user.id,
        workspace=client.active_workspace.id,
        created=datetime.now(),
        updated=datetime.now(),
    )


def test_describe_stack_contains_local_stack() -> None:
    """Test that the stack describe command contains the default local stack."""
    runner = CliRunner()
    describe_command = cli.commands["stack"].commands["describe"]
    result = runner.invoke(describe_command)
    assert result.exit_code == 0
    assert "default" in result.output


@pytest.mark.parametrize("not_a_stack", NOT_STACKS)
def test_describe_stack_bad_input_fails(
    not_a_stack: str,
) -> None:
    """Test if the stack describe fails when passing in bad parameters."""
    runner = CliRunner()
    describe_command = cli.commands["stack"].commands["describe"]
    result = runner.invoke(describe_command, [not_a_stack])
    assert result.exit_code == 1


def test_update_stack_update_on_default_fails(clean_workspace) -> None:
    """Test stack update of default stack is prohibited."""
    # first we set the active stack to a non-default stack
    original_stack = clean_workspace.active_stack_model

    new_artifact_store = _create_local_artifact_store(clean_workspace)

    clean_workspace.create_stack_component(
        name=new_artifact_store.name,
        flavor=new_artifact_store.flavor,
        component_type=new_artifact_store.type,
        configuration=new_artifact_store.config.dict(),
    )

    runner = CliRunner()
    update_command = cli.commands["stack"].commands["update"]
    result = runner.invoke(
        update_command, ["default", "-a", new_artifact_store.name]
    )
    assert result.exit_code == 1

    default_stack = clean_workspace.get_stack("default")
    assert (
        default_stack.components[StackComponentType.ARTIFACT_STORE][0].id
        == original_stack.components[StackComponentType.ARTIFACT_STORE][0].id
    )


def test_update_stack_active_stack_succeeds(clean_workspace) -> None:
    """Test stack update of active stack succeeds."""
    # first we set the active stack to a non-default stack
    registered_stack = clean_workspace.active_stack_model

    artifact_store_name = registered_stack.components[
        StackComponentType.ARTIFACT_STORE
    ][0].name

    orchestrator_name = registered_stack.components[
        StackComponentType.ORCHESTRATOR
    ][0].name
    new_stack = clean_workspace.create_stack(
        name="arias_new_stack",
        components={
            StackComponentType.ARTIFACT_STORE: artifact_store_name,
            StackComponentType.ORCHESTRATOR: orchestrator_name,
        },
    )

    clean_workspace.activate_stack(stack_name_id_or_prefix=new_stack.id)

    new_artifact_store = _create_local_artifact_store(clean_workspace)

    clean_workspace.create_stack_component(
        name=new_artifact_store.name,
        flavor=new_artifact_store.flavor,
        component_type=new_artifact_store.type,
        configuration=new_artifact_store.config.dict(),
    )
    runner = CliRunner()

    update_command = cli.commands["stack"].commands["update"]

    result = runner.invoke(update_command, ["-a", new_artifact_store.name])
    assert result.exit_code == 0

    assert (
        clean_workspace.active_stack_model.components[
            StackComponentType.ARTIFACT_STORE
        ][0].name
        == new_artifact_store.name
    )


def test_updating_non_active_stack_succeeds(clean_workspace) -> None:
    """Test if stack update of existing stack of non-active stack succeeds."""
    registered_stack = clean_workspace.active_stack_model

    artifact_store_name = registered_stack.components[
        StackComponentType.ARTIFACT_STORE
    ][0].name

    orchestrator_name = registered_stack.components[
        StackComponentType.ORCHESTRATOR
    ][0].name

    new_stack = clean_workspace.create_stack(
        name="arias_new_stack",
        components={
            StackComponentType.ARTIFACT_STORE: artifact_store_name,
            StackComponentType.ORCHESTRATOR: orchestrator_name,
        },
    )

    orchestrator = _create_local_orchestrator(clean_workspace)

    new_orchestrator = clean_workspace.create_stack_component(
        name=orchestrator.name,
        flavor=orchestrator.flavor,
        component_type=orchestrator.type,
        configuration=orchestrator.config.dict(),
    )

    runner = CliRunner()

    stack_update_command = cli.commands["stack"].commands["update"]

    result = runner.invoke(
        stack_update_command, [new_stack.name, "-o", new_orchestrator.name]
    )
    assert result.exit_code == 0

    assert (
        clean_workspace.get_stack(str(new_stack.id))
        .components.get(StackComponentType.ORCHESTRATOR)[0]
        .name
        == new_orchestrator.name
    )


def test_update_stack_adding_component_succeeds(clean_workspace) -> None:
    """Test stack update by adding a new component to a stack succeeds."""
    # first we create and activate a non-default stack
    registered_stack = clean_workspace.active_stack_model

    artifact_store_name = registered_stack.components[
        StackComponentType.ARTIFACT_STORE
    ][0].name

    orchestrator_name = registered_stack.components[
        StackComponentType.ORCHESTRATOR
    ][0].name

    new_stack = clean_workspace.create_stack(
        name="arias_new_stack",
        components={
            StackComponentType.ARTIFACT_STORE: artifact_store_name,
            StackComponentType.ORCHESTRATOR: orchestrator_name,
        },
    )
    clean_workspace.activate_stack(new_stack.id)

    local_secrets_manager = _create_local_secrets_manager(clean_workspace)

    local_secrets_manager_model = clean_workspace.create_stack_component(
        name=local_secrets_manager.name,
        flavor=local_secrets_manager.flavor,
        component_type=local_secrets_manager.type,
        configuration=local_secrets_manager.config.dict(),
    )

    runner = CliRunner()
    update_command = cli.commands["stack"].commands["update"]
    result = runner.invoke(update_command, ["-x", local_secrets_manager.name])

    new_stack = clean_workspace.get_stack(new_stack.id)

    assert result.exit_code == 0
    assert StackComponentType.SECRETS_MANAGER in new_stack.components.keys()
    assert new_stack.components[StackComponentType.SECRETS_MANAGER] is not None
    assert (
        new_stack.components[StackComponentType.SECRETS_MANAGER][0].id
        == local_secrets_manager_model.id
    )


def test_update_stack_adding_to_default_stack_fails(clean_workspace) -> None:
    """Test stack update by adding a new component to the default stack is prohibited."""
    # first we set the active stack to a non-default stack
    registered_stack = clean_workspace.active_stack_model

    artifact_store_name = registered_stack.components[
        StackComponentType.ARTIFACT_STORE
    ][0].name

    orchestrator_name = registered_stack.components[
        StackComponentType.ORCHESTRATOR
    ][0].name

    new_stack = clean_workspace.create_stack(
        name="arias_new_stack",
        components={
            StackComponentType.ARTIFACT_STORE: artifact_store_name,
            StackComponentType.ORCHESTRATOR: orchestrator_name,
        },
    )
    clean_workspace.activate_stack(new_stack.id)

    local_secrets_manager = _create_local_secrets_manager(clean_workspace)

    local_secrets_manager_model = clean_workspace.create_stack_component(
        name=local_secrets_manager.name,
        flavor=local_secrets_manager.flavor,
        component_type=local_secrets_manager.type,
        configuration=local_secrets_manager.config.dict(),
    )

    runner = CliRunner()
    update_command = cli.commands["stack"].commands["update"]
    result = runner.invoke(
        update_command, ["default", "-x", local_secrets_manager_model.name]
    )
    assert result.exit_code == 1

    default_stack = clean_workspace.get_stack("default")
    assert (
        StackComponentType.SECRETS_MANAGER
        not in default_stack.components.keys()
    )


def test_update_stack_nonexistent_stack_fails(clean_workspace) -> None:
    """Test stack update of nonexistent stack fails."""
    local_secrets_manager = _create_local_secrets_manager(clean_workspace)

    local_secrets_manager_model = clean_workspace.create_stack_component(
        name=local_secrets_manager.name,
        flavor=local_secrets_manager.flavor,
        component_type=local_secrets_manager.type,
        configuration=local_secrets_manager.config.dict(),
    )

    runner = CliRunner()
    update_command = cli.commands["stack"].commands["update"]
    result = runner.invoke(
        update_command, ["not_a_stack", "-x", local_secrets_manager_model.name]
    )

    assert result.exit_code == 1
    assert clean_workspace.active_stack.secrets_manager is None


def test_rename_stack_nonexistent_stack_fails(clean_workspace) -> None:
    """Test stack rename of nonexistent stack fails."""
    runner = CliRunner()
    rename_command = cli.commands["stack"].commands["rename"]
    result = runner.invoke(rename_command, ["not_a_stack", "a_new_stack"])
    assert result.exit_code == 1


def test_rename_stack_new_name_with_existing_name_fails(
    clean_workspace,
) -> None:
    runner = CliRunner()
    rename_command = cli.commands["stack"].commands["rename"]
    result = runner.invoke(rename_command, ["not_a_stack", "default"])
    assert result.exit_code == 1


def test_rename_stack_default_stack_fails(clean_workspace) -> None:
    """Test stack rename of default stack fails."""
    runner = CliRunner()
    rename_command = cli.commands["stack"].commands["rename"]
    result = runner.invoke(rename_command, ["default", "axls_new_stack"])
    assert result.exit_code == 1
    assert clean_workspace.get_stack("default")


def test_rename_stack_active_stack_succeeds(clean_workspace) -> None:
    """Test stack rename of active stack fails."""
    # first we set the active stack to a non-default stack
    registered_stack = clean_workspace.active_stack_model

    artifact_store_name = registered_stack.components[
        StackComponentType.ARTIFACT_STORE
    ][0].name

    orchestrator_name = registered_stack.components[
        StackComponentType.ORCHESTRATOR
    ][0].name

    new_stack = clean_workspace.create_stack(
        name="arias_stack",
        components={
            StackComponentType.ARTIFACT_STORE: artifact_store_name,
            StackComponentType.ORCHESTRATOR: orchestrator_name,
        },
    )
    clean_workspace.activate_stack(new_stack.id)

    runner = CliRunner()
    rename_command = cli.commands["stack"].commands["rename"]
    result = runner.invoke(rename_command, ["arias_stack", "axls_stack"])
    assert result.exit_code == 0
    assert clean_workspace.active_stack_model.name == "axls_stack"


def test_rename_stack_non_active_stack_succeeds(clean_workspace) -> None:
    """Test stack rename of non-active stack succeeds."""
    registered_stack = clean_workspace.active_stack_model

    artifact_store_name = registered_stack.components[
        StackComponentType.ARTIFACT_STORE
    ][0].name

    orchestrator_name = registered_stack.components[
        StackComponentType.ORCHESTRATOR
    ][0].name

    new_stack = clean_workspace.create_stack(
        name="arias_stack",
        components={
            StackComponentType.ARTIFACT_STORE: artifact_store_name,
            StackComponentType.ORCHESTRATOR: orchestrator_name,
        },
    )

    runner = CliRunner()
    rename_command = cli.commands["stack"].commands["rename"]
    result = runner.invoke(rename_command, ["arias_stack", "axls_stack"])
    assert result.exit_code == 0
    assert clean_workspace.get_stack(new_stack.id).name == "axls_stack"


def test_remove_component_from_nonexistent_stack_fails(
    clean_workspace,
) -> None:
    """Test stack remove-component of nonexistent stack fails."""
    runner = CliRunner()
    remove_command = cli.commands["stack"].commands["remove-component"]
    result = runner.invoke(remove_command, ["not_a_stack", "-x"])
    assert result.exit_code == 1


def test_remove_component_core_component_fails(clean_workspace) -> None:
    """Test stack remove-component of core component fails."""
    # first we create a non-default stack
    new_artifact_store = _create_local_artifact_store(clean_workspace)

    new_artifact_store_model = clean_workspace.create_stack_component(
        name=new_artifact_store.name,
        flavor=new_artifact_store.flavor,
        component_type=new_artifact_store.type,
        configuration=new_artifact_store.config.dict(),
    )

    new_orchestrator = _create_local_orchestrator(clean_workspace)

    new_orchestrator_model = clean_workspace.create_stack_component(
        name=new_orchestrator.name,
        flavor=new_orchestrator.flavor,
        component_type=new_orchestrator.type,
        configuration=new_orchestrator.config.dict(),
    )

    new_stack = clean_workspace.create_stack(
        name="arias_new_stack",
        components={
            StackComponentType.ARTIFACT_STORE: new_artifact_store_model.name,
            StackComponentType.ORCHESTRATOR: new_orchestrator_model.name,
        },
    )

    runner = CliRunner()
    remove_command = cli.commands["stack"].commands["remove-component"]
    result = runner.invoke(remove_command, [new_stack.name, "-o"])
    assert result.exit_code != 0

    arias_stack = clean_workspace.get_stack(new_stack.name)
    assert StackComponentType.ORCHESTRATOR in arias_stack.components


def test_remove_component_non_core_component_succeeds(clean_workspace) -> None:
    """Test stack remove-component of non-core component succeeds."""
    # first we create a non-default stack
    new_artifact_store = _create_local_artifact_store(clean_workspace)

    new_artifact_store_model = clean_workspace.create_stack_component(
        name=new_artifact_store.name,
        flavor=new_artifact_store.flavor,
        component_type=new_artifact_store.type,
        configuration=new_artifact_store.config.dict(),
    )

    new_orchestrator = _create_local_orchestrator(clean_workspace)

    new_orchestrator_model = clean_workspace.create_stack_component(
        name=new_orchestrator.name,
        flavor=new_orchestrator.flavor,
        component_type=new_orchestrator.type,
        configuration=new_orchestrator.config.dict(),
    )

    new_secrets_manager = _create_local_secrets_manager(clean_workspace)

    new_secrets_manager_model = clean_workspace.create_stack_component(
        name=new_secrets_manager.name,
        flavor=new_secrets_manager.flavor,
        component_type=new_secrets_manager.type,
        configuration=new_secrets_manager.config.dict(),
    )
    new_stack = clean_workspace.create_stack(
        name="arias_new_stack",
        components={
            StackComponentType.ARTIFACT_STORE: new_artifact_store_model.name,
            StackComponentType.ORCHESTRATOR: new_orchestrator_model.name,
            StackComponentType.SECRETS_MANAGER: new_secrets_manager_model.name,
        },
    )
    clean_workspace.activate_stack(new_stack.id)

    runner = CliRunner()
    remove_command = cli.commands["stack"].commands["remove-component"]
    result = runner.invoke(remove_command, [new_stack.name, "-x"])
    assert result.exit_code == 0
    assert (
        StackComponentType.SECRETS_MANAGER
        not in clean_workspace.active_stack_model.components
    )


def test_delete_stack_with_flag_succeeds(clean_workspace) -> None:
    """Test stack delete with flag succeeds."""
    registered_stack = clean_workspace.active_stack_model

    artifact_store_name = registered_stack.components[
        StackComponentType.ARTIFACT_STORE
    ][0].name

    orchestrator_name = registered_stack.components[
        StackComponentType.ORCHESTRATOR
    ][0].name

    new_stack = clean_workspace.create_stack(
        name="arias_new_stack",
        components={
            StackComponentType.ARTIFACT_STORE: artifact_store_name,
            StackComponentType.ORCHESTRATOR: orchestrator_name,
        },
    )
    runner = CliRunner()
    delete_command = cli.commands["stack"].commands["delete"]
    result = runner.invoke(delete_command, [new_stack.name, "-y"])
    assert result.exit_code == 0
    with pytest.raises(KeyError):
        clean_workspace.get_stack(new_stack.id)


def test_delete_stack_default_stack_fails(clean_workspace) -> None:
    """Test stack delete default stack fails."""
    # first we set the active stack to a non-default stack
    registered_stack = clean_workspace.active_stack_model

    artifact_store_name = registered_stack.components[
        StackComponentType.ARTIFACT_STORE
    ][0].name

    orchestrator_name = registered_stack.components[
        StackComponentType.ORCHESTRATOR
    ][0].name

    new_stack = clean_workspace.create_stack(
        name="arias_new_stack",
        components={
            StackComponentType.ARTIFACT_STORE: artifact_store_name,
            StackComponentType.ORCHESTRATOR: orchestrator_name,
        },
    )
    clean_workspace.activate_stack(new_stack.name)

    runner = CliRunner()
    delete_command = cli.commands["stack"].commands["delete"]
    result = runner.invoke(delete_command, ["default", "-y"])
    assert result.exit_code == 1
    assert clean_workspace.get_stack("default")


def test_delete_stack_recursively_with_flag_succeeds(clean_workspace) -> None:
    """Test recursively delete stack delete with flag succeeds."""
    registered_stack = clean_workspace.active_stack_model

    artifact_store_name = registered_stack.components[
        StackComponentType.ARTIFACT_STORE
    ][0].name

    orchestrator_name = registered_stack.components[
        StackComponentType.ORCHESTRATOR
    ][0].name

    new_secrets_manager = _create_local_secrets_manager(clean_workspace)

    new_secrets_manager_model = clean_workspace.create_stack_component(
        name=new_secrets_manager.name,
        flavor=new_secrets_manager.flavor,
        component_type=new_secrets_manager.type,
        configuration=new_secrets_manager.config.dict(),
    )
    new_stack = clean_workspace.create_stack(
        name="arias_new_stack",
        components={
            StackComponentType.ARTIFACT_STORE: artifact_store_name,
            StackComponentType.ORCHESTRATOR: orchestrator_name,
            StackComponentType.SECRETS_MANAGER: new_secrets_manager_model.name,
        },
    )

    runner = CliRunner()
    delete_command = cli.commands["stack"].commands["delete"]
    result = runner.invoke(delete_command, [new_stack.name, "-y", "-r"])
    assert result.exit_code == 0
    with pytest.raises(KeyError):
        clean_workspace.get_stack(new_stack.id)
    with pytest.raises(KeyError):
        clean_workspace.get_stack_component(
            StackComponentType.SECRETS_MANAGER, new_secrets_manager_model.name
        )
    assert clean_workspace.get_stack_component(
        StackComponentType.ARTIFACT_STORE, artifact_store_name
    )
    assert clean_workspace.get_stack_component(
        StackComponentType.ORCHESTRATOR, orchestrator_name
    )


def test_stack_export(clean_workspace) -> None:
    """Test exporting default stack succeeds."""
    runner = CliRunner()
    export_command = cli.commands["stack"].commands["export"]
    result = runner.invoke(export_command, ["default", "default.yaml"])
    assert result.exit_code == 0
    assert os.path.exists("default.yaml")


def test_stack_export_delete_import(clean_workspace) -> None:
    """Test exporting, deleting, then importing a stack succeeds."""
    # create new stack
    new_artifact_store = _create_local_artifact_store(clean_workspace)

    new_artifact_store_model = clean_workspace.create_stack_component(
        name=new_artifact_store.name,
        flavor=new_artifact_store.flavor,
        component_type=new_artifact_store.type,
        configuration=new_artifact_store.config.dict(),
    )

    new_orchestrator = _create_local_orchestrator(clean_workspace)

    new_orchestrator_model = clean_workspace.create_stack_component(
        name=new_orchestrator.name,
        flavor=new_orchestrator.flavor,
        component_type=new_orchestrator.type,
        configuration=new_orchestrator.config.dict(),
    )

    new_stack_model = clean_workspace.create_stack(
        name="arias_new_stack",
        components={
            StackComponentType.ARTIFACT_STORE: new_artifact_store_model.name,
            StackComponentType.ORCHESTRATOR: new_orchestrator_model.name,
        },
    )

    # export stack
    file_name = "arias_new_stack.yaml"

    runner = CliRunner()
    export_command = cli.commands["stack"].commands["export"]
    result = runner.invoke(export_command, [new_stack_model.name, file_name])
    assert result.exit_code == 0
    assert os.path.exists("arias_new_stack.yaml")

    # delete stack and corresponding components
    clean_workspace.delete_stack(name_id_or_prefix=new_stack_model.name)
    clean_workspace.delete_stack_component(
        name_id_or_prefix=new_orchestrator_model.name,
        component_type=StackComponentType.ORCHESTRATOR,
    )
    clean_workspace.delete_stack_component(
        name_id_or_prefix=new_artifact_store_model.name,
        component_type=StackComponentType.ARTIFACT_STORE,
    )
    with pytest.raises(KeyError):
        clean_workspace.get_stack(new_stack_model.id)

    # import stack
    import_command = cli.commands["stack"].commands["import"]
    result = runner.invoke(
        import_command, [new_stack_model.name, "--filename", file_name]
    )
    assert result.exit_code == 0
    assert clean_workspace.get_stack(new_stack_model.name)


def test_stack_export_import_reuses_components(clean_workspace) -> None:
    """Test exporting and then importing a stack reuses existing components."""
    # create new stack
    new_artifact_store = _create_local_artifact_store(clean_workspace)

    new_artifact_store_model = clean_workspace.create_stack_component(
        name=new_artifact_store.name,
        flavor=new_artifact_store.flavor,
        component_type=new_artifact_store.type,
        configuration=new_artifact_store.config.dict(),
    )

    new_orchestrator = _create_local_orchestrator(clean_workspace)

    new_orchestrator_model = clean_workspace.create_stack_component(
        name=new_orchestrator.name,
        flavor=new_orchestrator.flavor,
        component_type=new_orchestrator.type,
        configuration=new_orchestrator.config.dict(),
    )

    stack_name = "arias_new_stack"
    old_stack_model = clean_workspace.create_stack(
        name=stack_name,
        components={
            StackComponentType.ARTIFACT_STORE: new_artifact_store_model.name,
            StackComponentType.ORCHESTRATOR: new_orchestrator_model.name,
        },
    )

    # export stack
    file_name = "arias_new_stack.yaml"

    runner = CliRunner()
    export_command = cli.commands["stack"].commands["export"]
    result = runner.invoke(export_command, [stack_name, file_name])
    assert result.exit_code == 0
    assert os.path.exists("arias_new_stack.yaml")

    # delete stack but no components
    clean_workspace.delete_stack(name_id_or_prefix=stack_name)

    # import stack
    import_command = cli.commands["stack"].commands["import"]
    result = runner.invoke(import_command, [stack_name])
    assert result.exit_code == 0
    new_stack_model = clean_workspace.get_stack(stack_name)

    # new stack but with the same, reused components
    assert old_stack_model.id != new_stack_model.id
    assert old_stack_model.components == new_stack_model.components
