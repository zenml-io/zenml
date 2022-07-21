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

import pytest
from click.testing import CliRunner

from zenml.artifact_stores import LocalArtifactStore
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
from zenml.metadata_stores import SQLiteMetadataStore
from zenml.orchestrators import LocalOrchestrator
from zenml.secrets_managers.local.local_secrets_manager import (
    LocalSecretsManager,
)
from zenml.stack import Stack

NOT_STACKS = ["abc", "my_other_cat_is_called_blupus", "stack123"]

# TODO [ENG-828]: Add tests for these commands using REST, SQL and local options


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
    new_artifact_store = LocalArtifactStore(name="arias_store", path="/meow")
    clean_repo.register_stack_component(new_artifact_store)

    runner = CliRunner()
    result = runner.invoke(
        update_stack, ["default", "--decouple_stores", "-a", "arias_store"]
    )
    assert result.exit_code == 0
    assert clean_repo.active_stack.artifact_store == new_artifact_store


def test_updating_non_active_stack_succeeds(clean_repo) -> None:
    """Test stack update of pre-existing component of non-active stack succeeds."""
    new_orchestrator = LocalOrchestrator(name="arias_orchestrator")
    clean_repo.register_stack_component(new_orchestrator)

    registered_stack = clean_repo.active_stack
    new_stack = Stack(
        name="arias_new_stack",
        orchestrator=registered_stack.orchestrator,
        metadata_store=registered_stack.metadata_store,
        artifact_store=registered_stack.artifact_store,
    )
    clean_repo.register_stack(new_stack)

    runner = CliRunner()
    result = runner.invoke(
        update_stack, ["arias_new_stack", "-o", "arias_orchestrator"]
    )
    assert result.exit_code == 0
    assert (
        clean_repo.get_stack("arias_new_stack").orchestrator == new_orchestrator
    )


def test_adding_to_stack_succeeds(clean_repo) -> None:
    """Test stack update by adding a new component to a stack
    succeeds."""
    local_secrets_manager = LocalSecretsManager(name="arias_secrets_manager")
    clean_repo.register_stack_component(local_secrets_manager)

    runner = CliRunner()
    result = runner.invoke(
        update_stack, ["default", "-x", "arias_secrets_manager"]
    )

    assert result.exit_code == 0
    assert clean_repo.get_stack("default").secrets_manager is not None
    assert (
        clean_repo.get_stack("default").secrets_manager == local_secrets_manager
    )


def test_updating_nonexistent_stack_fails(clean_repo) -> None:
    """Test stack update of nonexistent stack fails."""
    local_secrets_manager = LocalSecretsManager(name="arias_secrets_manager")
    clean_repo.register_stack_component(local_secrets_manager)

    runner = CliRunner()
    result = runner.invoke(
        update_stack, ["not_a_stack", "-x", "arias_secrets_manager"]
    )

    assert result.exit_code == 1
    assert clean_repo.get_stack("default").secrets_manager is None


def test_renaming_nonexistent_stack_fails(clean_repo) -> None:
    """Test stack rename of nonexistent stack fails."""
    runner = CliRunner()
    result = runner.invoke(rename_stack, ["not_a_stack", "a_new_stack"])
    assert result.exit_code == 1
    with pytest.raises(KeyError):
        clean_repo.get_stack("not_a_stack")


def test_renaming_stack_to_same_name_as_existing_stack_fails(
    clean_repo,
) -> None:
    runner = CliRunner()
    result = runner.invoke(rename_stack, ["not_a_stack", "default"])
    assert result.exit_code == 1
    with pytest.raises(KeyError):
        clean_repo.get_stack("not_a_stack")


def test_renaming_active_stack_succeeds(clean_repo) -> None:
    """Test stack rename of active stack fails."""
    runner = CliRunner()
    result = runner.invoke(rename_stack, ["default", "arias_default"])
    assert result.exit_code == 0
    assert clean_repo.get_stack("arias_default") is not None
    assert clean_repo.get_stack("arias_default").name == "arias_default"


def test_renaming_non_active_stack_succeeds(clean_repo) -> None:
    """Test stack rename of non-active stack succeeds."""
    registered_stack = clean_repo.active_stack
    new_stack = Stack(
        name="arias_stack",
        orchestrator=registered_stack.orchestrator,
        metadata_store=registered_stack.metadata_store,
        artifact_store=registered_stack.artifact_store,
    )
    clean_repo.register_stack(new_stack)

    runner = CliRunner()
    result = runner.invoke(rename_stack, ["arias_stack", "arias_renamed_stack"])
    assert result.exit_code == 0
    assert clean_repo.get_stack("arias_renamed_stack") is not None
    assert (
        clean_repo.get_stack("arias_renamed_stack").name
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
    local_secrets_manager = LocalSecretsManager(name="arias_secrets_manager")
    clean_repo.register_stack_component(local_secrets_manager)
    runner = CliRunner()
    runner.invoke(
        update_stack,
        [clean_repo.active_stack.name, "-x", "arias_secrets_manager"],
    )
    assert clean_repo.active_stack.secrets_manager is not None
    assert (
        clean_repo.get_stack(clean_repo.active_stack.name).secrets_manager
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
        name="arias_new_stack",
        orchestrator=clean_repo.active_stack.orchestrator,
        metadata_store=clean_repo.active_stack.metadata_store,
        artifact_store=clean_repo.active_stack.artifact_store,
    )
    clean_repo.register_stack(new_stack)
    runner = CliRunner()
    result = runner.invoke(delete_stack, ["arias_new_stack", "-y"])
    assert result.exit_code == 0
    with pytest.raises(KeyError):
        clean_repo.get_stack("arias_new_stack")


def test_stack_export(clean_repo) -> None:
    """Test exporting default stack succeeds."""
    runner = CliRunner()
    result = runner.invoke(export_stack, ["default", "default.yaml"])
    assert result.exit_code == 0
    assert os.path.exists("default.yaml")


def test_stack_export_delete_import(clean_repo) -> None:
    """Test exporting, deleting, then importing a stack succeeds."""
    # create new stack
    artifact_store_name = "arias_artifact_store"
    artifact_store = LocalArtifactStore(name=artifact_store_name, path="path/")
    clean_repo.register_stack_component(artifact_store)
    metadata_store_name = "arias_metadata_store"
    metadata_store = SQLiteMetadataStore(name=metadata_store_name, uri="uri")
    clean_repo.register_stack_component(metadata_store)
    orchestrator_name = "arias_orchestrator"
    orchestrator = LocalOrchestrator(name=orchestrator_name)
    clean_repo.register_stack_component(orchestrator)
    stack_name = "arias_new_stack"
    stack = Stack(
        name=stack_name,
        orchestrator=orchestrator,
        metadata_store=metadata_store,
        artifact_store=artifact_store,
    )
    clean_repo.register_stack(stack)

    # export stack
    runner = CliRunner()
    export_import_args = ["arias_new_stack", "arias_new_stack.yaml"]
    result = runner.invoke(export_stack, export_import_args)
    assert result.exit_code == 0
    assert os.path.exists("arias_new_stack.yaml")

    # delete stack and corresponding components
    clean_repo.deregister_stack(stack_name)
    clean_repo.deregister_stack_component(
        StackComponentType.ARTIFACT_STORE, artifact_store_name
    )
    clean_repo.deregister_stack_component(
        StackComponentType.METADATA_STORE, metadata_store_name
    )
    clean_repo.deregister_stack_component(
        StackComponentType.ORCHESTRATOR, orchestrator_name
    )
    with pytest.raises(KeyError):
        clean_repo.get_stack("arias_new_stack")

    # import stack
    result = runner.invoke(import_stack, export_import_args)
    assert result.exit_code == 0
    assert clean_repo.get_stack("arias_new_stack") is not None


def test_stack_update_and_register_couples_stores(clean_repo):
    """Tests if the artifact- and metadata store coupling works as intended."""
    # First, check if default association exists.
    default_stack = clean_repo.active_stack

    existing_association = clean_repo.zen_store.get_store_associations_for_artifact_and_metadata_store(
        artifact_store_uuid=default_stack.artifact_store.uuid,
        metadata_store_uuid=default_stack.metadata_store.uuid,
    )

    assert len(existing_association) == 1

    # Second, create another stack with the same association successfully.
    new_orchestrator_name = "new_orchestrator"
    new_orchestrator = LocalOrchestrator(name=new_orchestrator_name)
    clean_repo.register_stack_component(new_orchestrator)

    stack = Stack(
        name="new_stack_with_existing_association",
        orchestrator=new_orchestrator,
        metadata_store=default_stack.metadata_store,
        artifact_store=default_stack.artifact_store,
    )
    clean_repo.register_stack(stack)
    assert len(existing_association) == 1

    # Third, create a stack with the wrong association which should fail.
    new_artifact_store_name = "new_artifact_store"
    new_artifact_store = LocalArtifactStore(
        name=new_artifact_store_name, path="path/"
    )
    clean_repo.register_stack_component(new_artifact_store)

    from zenml.exceptions import StackValidationError

    with pytest.raises(StackValidationError):
        stack = Stack(
            name="new_stack_with_wrong_association",
            orchestrator=default_stack.orchestrator,
            metadata_store=default_stack.metadata_store,
            artifact_store=new_artifact_store,
        )
        clean_repo.register_stack(stack)

    # Fourth, successfully create the faulty stack by resetting the coupling.
    stack = Stack(
        name="new_stack_with_wrong_association",
        orchestrator=default_stack.orchestrator,
        metadata_store=default_stack.metadata_store,
        artifact_store=new_artifact_store,
    )
    clean_repo.register_stack(stack, decouple_stores=True)

    # Finally, due to the fourth step resetting the coupling, default stack
    # should fail.
    with pytest.raises(StackValidationError):
        default_stack.validate()
