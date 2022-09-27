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
from uuid import uuid4

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
    remove_stack_component,
    rename_stack,
    update_stack,
)
from zenml.enums import StackComponentType
from zenml.orchestrators.base_orchestrator import BaseOrchestratorConfig
from zenml.orchestrators.local.local_orchestrator import LocalOrchestrator
from zenml.repository import Repository
from zenml.secrets_managers.local.local_secrets_manager import (
    LocalSecretsManager,
    LocalSecretsManagerConfig,
)
from zenml.stack import Stack

NOT_STACKS = ["abc", "my_other_cat_is_called_blupus", "stack123"]

# TODO [ENG-828]: Add tests for these commands using REST, SQL and local options


def _create_local_orchestrator(repo: Repository):
    """Returns a local orchestrator."""
    return LocalOrchestrator(
        name="arias_orchestrator",
        id=uuid4(),
        config=BaseOrchestratorConfig(),
        flavor="local",
        type=StackComponentType.ORCHESTRATOR,
        user=repo.active_user.id,
        project=repo.active_project.id,
        created=datetime.now(),
        updated=datetime.now(),
    )


def _create_local_artifact_store(repo: Repository):
    """Fixture that creates a local artifact store for testing."""
    return LocalArtifactStore(
        name="arias_artifact_store",
        id=uuid4(),
        config=LocalArtifactStoreConfig(),
        flavor="local",
        type=StackComponentType.ARTIFACT_STORE,
        user=repo.active_user.id,
        project=repo.active_project.id,
        created=datetime.now(),
        updated=datetime.now(),
    )


def _create_local_secrets_manager(repo: Repository):
    return LocalSecretsManager(
        name="arias_secrets_manager",
        id=uuid4(),
        config=LocalSecretsManagerConfig(),
        flavor="local",
        type=StackComponentType.SECRETS_MANAGER,
        user=repo.active_user.id,
        project=repo.active_project.id,
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


def test_updating_active_stack_succeeds(clean_repo) -> None:
    """Test stack update of active stack succeeds."""
    new_artifact_store = _create_local_artifact_store(clean_repo)
    clean_repo.register_stack_component(new_artifact_store.to_model())

    runner = CliRunner()
    result = runner.invoke(
        update_stack, ["default", "-a", new_artifact_store.name]
    )
    assert result.exit_code == 0
    assert clean_repo.active_stack.artifact_store == new_artifact_store


def test_updating_non_active_stack_succeeds(clean_repo) -> None:
    """Test stack update of pre-existing component of non-active stack succeeds."""
    new_orchestrator = _create_local_orchestrator(clean_repo)
    clean_repo.register_stack_component(new_orchestrator.to_model())

    registered_stack = clean_repo.active_stack
    new_stack = Stack(
        id=uuid4(),
        name="arias_new_stack",
        orchestrator=registered_stack.orchestrator,
        artifact_store=registered_stack.artifact_store,
    )
    stack_model = new_stack.to_model(
        user=clean_repo.active_user.id, project=clean_repo.active_project.id
    )
    clean_repo.register_stack(stack_model)

    runner = CliRunner()
    result = runner.invoke(
        update_stack, ["arias_new_stack", "-o", new_orchestrator.name]
    )
    assert result.exit_code == 0

    updated_stack = Stack.from_model(
        clean_repo.get_stack_by_name_or_partial_id(
            "arias_new_stack"
        ).to_hydrated_model()
    )
    assert updated_stack.orchestrator == new_orchestrator


def test_adding_to_stack_succeeds(clean_repo) -> None:
    """Test stack update by adding a new component to a stack
    succeeds."""
    local_secrets_manager = _create_local_secrets_manager(clean_repo)
    clean_repo.register_stack_component(local_secrets_manager.to_model())

    runner = CliRunner()
    result = runner.invoke(
        update_stack, ["default", "-x", local_secrets_manager.name]
    )

    active_stack = Stack.from_model(
        clean_repo.get_stack_by_name_or_partial_id(
            "default"
        ).to_hydrated_model()
    )
    assert result.exit_code == 0
    assert active_stack.secrets_manager is not None
    assert active_stack.secrets_manager == local_secrets_manager


def test_updating_nonexistent_stack_fails(clean_repo) -> None:
    """Test stack update of nonexistent stack fails."""
    local_secrets_manager = _create_local_secrets_manager(clean_repo)
    clean_repo.register_stack_component(local_secrets_manager.to_model())

    runner = CliRunner()
    result = runner.invoke(
        update_stack, ["not_a_stack", "-x", local_secrets_manager.name]
    )

    assert result.exit_code == 1
    assert clean_repo.active_stack.secrets_manager is None


def test_renaming_nonexistent_stack_fails(clean_repo) -> None:
    """Test stack rename of nonexistent stack fails."""
    runner = CliRunner()
    result = runner.invoke(rename_stack, ["not_a_stack", "a_new_stack"])
    assert result.exit_code == 1
    with pytest.raises(KeyError):
        clean_repo.get_stack_by_name_or_partial_id("not_a_stack")


def test_renaming_stack_to_same_name_as_existing_stack_fails(
    clean_repo,
) -> None:
    runner = CliRunner()
    result = runner.invoke(rename_stack, ["not_a_stack", "default"])
    assert result.exit_code == 1
    with pytest.raises(KeyError):
        clean_repo.get_stack_by_name_or_partial_id("not_a_stack")


def test_renaming_active_stack_succeeds(clean_repo) -> None:
    """Test stack rename of active stack fails."""
    runner = CliRunner()
    result = runner.invoke(rename_stack, ["default", "arias_default"])
    assert result.exit_code == 0
    assert (
        clean_repo.get_stack_by_name_or_partial_id("arias_default") is not None
    )
    assert (
        clean_repo.get_stack_by_name_or_partial_id("arias_default").name
        == "arias_default"
    )


def test_renaming_non_active_stack_succeeds(clean_repo) -> None:
    """Test stack rename of non-active stack succeeds."""
    registered_stack = clean_repo.active_stack
    new_stack = Stack(
        id=uuid4(),
        name="arias_stack",
        orchestrator=registered_stack.orchestrator,
        artifact_store=registered_stack.artifact_store,
    )
    stack_model = new_stack.to_model(
        user=clean_repo.active_user.id, project=clean_repo.active_project.id
    )
    clean_repo.register_stack(stack_model)

    runner = CliRunner()
    result = runner.invoke(rename_stack, ["arias_stack", "arias_renamed_stack"])
    assert result.exit_code == 0
    assert (
        clean_repo.get_stack_by_name_or_partial_id("arias_renamed_stack")
        is not None
    )
    assert (
        clean_repo.get_stack_by_name_or_partial_id("arias_renamed_stack").name
        == "arias_renamed_stack"
    )


def test_remove_component_from_nonexistent_stack_fails(clean_repo) -> None:
    """Test stack remove-component of nonexistent stack fails."""
    runner = CliRunner()
    result = runner.invoke(remove_stack_component, ["not_a_stack", "-x"])
    assert result.exit_code == 1


def test_remove_core_component_from_stack_fails(clean_repo) -> None:
    """Test stack remove-component of core component fails."""
    runner = CliRunner()
    result = runner.invoke(
        remove_stack_component, [clean_repo.active_stack.name, "-o"]
    )
    assert result.exit_code != 0
    assert clean_repo.active_stack.orchestrator is not None


def test_remove_non_core_component_from_stack_succeeds(clean_repo) -> None:
    """Test stack remove-component of non-core component succeeds."""
    local_secrets_manager = _create_local_secrets_manager(clean_repo)
    clean_repo.register_stack_component(local_secrets_manager.to_model())
    runner = CliRunner()
    runner.invoke(
        update_stack,
        [clean_repo.active_stack.name, "-x", local_secrets_manager.name],
    )
    assert clean_repo.active_stack.secrets_manager is not None
    assert (
        Stack.from_model(
            clean_repo.get_stack_by_name_or_partial_id(
                clean_repo.active_stack.name
            ).to_hydrated_model()
        ).secrets_manager
        == local_secrets_manager
    )
    result = runner.invoke(
        remove_stack_component, [clean_repo.active_stack.name, "-x"]
    )
    assert result.exit_code == 0
    assert clean_repo.active_stack.secrets_manager is None


def test_deleting_stack_with_flag_succeeds(clean_repo) -> None:
    """Test stack delete with flag succeeds."""
    new_stack = Stack(
        id=uuid4(),
        name="arias_new_stack",
        orchestrator=clean_repo.active_stack.orchestrator,
        artifact_store=clean_repo.active_stack.artifact_store,
    )
    stack_model = new_stack.to_model(
        user=clean_repo.active_user.id, project=clean_repo.active_project.id
    )
    clean_repo.register_stack(stack_model)
    runner = CliRunner()
    result = runner.invoke(delete_stack, ["arias_new_stack", "-y"])
    assert result.exit_code == 0
    with pytest.raises(KeyError):
        clean_repo.get_stack_by_name_or_partial_id("arias_new_stack")


def test_stack_export(clean_repo) -> None:
    """Test exporting default stack succeeds."""
    runner = CliRunner()
    result = runner.invoke(export_stack, ["default", "default.yaml"])
    assert result.exit_code == 0
    assert os.path.exists("default.yaml")


def test_stack_export_delete_import(clean_repo) -> None:
    """Test exporting, deleting, then importing a stack succeeds."""
    # create new stack
    artifact_store = _create_local_artifact_store(clean_repo)
    artifact_store.name
    clean_repo.register_stack_component(artifact_store.to_model())
    orchestrator = _create_local_orchestrator(clean_repo)
    orchestrator.name
    clean_repo.register_stack_component(orchestrator.to_model())
    stack_name = "arias_new_stack"
    stack = Stack(
        id=uuid4(),
        name=stack_name,
        orchestrator=orchestrator,
        artifact_store=artifact_store,
    )
    stack_model = stack.to_model(
        user=clean_repo.active_user.id, project=clean_repo.active_project.id
    )
    clean_repo.register_stack(stack_model)

    # export stack
    runner = CliRunner()
    file_name = "arias_new_stack.yaml"
    result = runner.invoke(export_stack, [stack_name, file_name])
    assert result.exit_code == 0
    assert os.path.exists("arias_new_stack.yaml")

    # delete stack and corresponding components
    clean_repo.deregister_stack(stack_model)
    clean_repo.deregister_stack_component(orchestrator.to_model())
    clean_repo.deregister_stack_component(artifact_store.to_model())
    with pytest.raises(KeyError):
        clean_repo.get_stack_by_name_or_partial_id("arias_new_stack")

    # import stack
    result = runner.invoke(import_stack, [stack_name, "--filename", file_name])
    assert result.exit_code == 0
    assert (
        clean_repo.get_stack_by_name_or_partial_id("arias_new_stack")
        is not None
    )
