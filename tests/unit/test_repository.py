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
import os
import random
import string
from contextlib import ExitStack as does_not_raise
from typing import Optional

import pytest

from zenml.artifact_stores import LocalArtifactStore
from zenml.enums import StackComponentType
from zenml.exceptions import (
    ForbiddenRepositoryAccessError,
    InitializationException,
    StackComponentExistsError,
    StackExistsError,
)
from zenml.io import fileio, utils
from zenml.metadata_stores import MySQLMetadataStore, SQLiteMetadataStore
from zenml.orchestrators import LocalOrchestrator
from zenml.repository import Repository
from zenml.stack import Stack


def _create_local_stack(
    stack_name: str,
    orchestrator_name: Optional[str] = None,
    metadata_store_name: Optional[str] = None,
    artifact_store_name: Optional[str] = None,
):
    """Creates a local stack with components with the given names. If the
    names are not given, a random string is used instead."""

    def _random_name():
        return "".join(random.choices(string.ascii_letters, k=10))

    orchestrator_name = orchestrator_name or _random_name()
    metadata_store_name = metadata_store_name or _random_name()
    artifact_store_name = artifact_store_name or _random_name()

    orchestrator = LocalOrchestrator(name=orchestrator_name)
    artifact_store = LocalArtifactStore(name=artifact_store_name, path="stack")
    metadata_store = SQLiteMetadataStore(
        name=metadata_store_name, uri="./metadata.db"
    )

    return Stack(
        name=stack_name,
        orchestrator=orchestrator,
        metadata_store=metadata_store,
        artifact_store=artifact_store,
    )


def test_repository_detection(tmp_path):
    """Tests detection of ZenML repositories in a directory."""
    assert Repository.is_repository_directory(tmp_path) is False
    Repository.initialize(tmp_path)
    assert Repository.is_repository_directory(tmp_path) is True


def test_initializing_repo_creates_directory_and_uses_default_stack(
    tmp_path, clean_repo
):
    """Tests that repo initialization creates a .zen directory and uses the
    default local stack."""
    Repository.initialize(tmp_path)
    assert fileio.exists(str(tmp_path / ".zen"))

    repo = Repository()
    # switch to the new repo root
    repo.activate_root(tmp_path)

    assert len(repo.stacks) == 1

    stack = repo.active_stack
    assert isinstance(stack.orchestrator, LocalOrchestrator)
    assert isinstance(stack.metadata_store, SQLiteMetadataStore)
    assert isinstance(stack.artifact_store, LocalArtifactStore)
    assert stack.container_registry is None


def test_initializing_repo_twice_fails(tmp_path):
    """Tests that initializing a repo in a directory where another repo already
    exists fails."""
    Repository.initialize(tmp_path)
    with pytest.raises(InitializationException):
        Repository.initialize(tmp_path)


def test_freshly_initialized_repo_attributes(tmp_path):
    """Tests that the attributes of a new repository are set correctly."""
    Repository.initialize(tmp_path)
    repo = Repository(tmp_path)

    assert repo.root == tmp_path


def test_finding_repository_directory_with_explicit_path(tmp_path, clean_repo):
    """Tests that a repository can be found using an explicit path, an
    environment variable and the current working directory."""
    subdirectory_path = tmp_path / "some_other_directory"
    utils.create_dir_recursive_if_not_exists(str(subdirectory_path))
    os.chdir(str(subdirectory_path))

    # no repo exists and explicit path passed
    assert Repository.find_repository(tmp_path) is None
    assert Repository(tmp_path).root is None

    # no repo exists and no path passed (=uses current working directory)
    assert Repository.find_repository() is None
    Repository._reset_instance()
    assert Repository().root is None

    # no repo exists and explicit path set via environment variable
    os.environ["ZENML_REPOSITORY_PATH"] = str(tmp_path)
    assert Repository.find_repository() is None
    Repository._reset_instance()
    assert Repository().root is None

    del os.environ["ZENML_REPOSITORY_PATH"]

    # initializing the repo
    Repository.initialize(tmp_path)

    # repo exists and explicit path passed
    assert Repository.find_repository(tmp_path) == tmp_path
    assert Repository(tmp_path).root == tmp_path

    # repo exists and explicit path to subdirectory passed
    assert Repository.find_repository(subdirectory_path) is None
    assert Repository(subdirectory_path).root is None

    # repo exists and no path passed (=uses current working directory)
    assert Repository.find_repository() == tmp_path
    Repository._reset_instance()
    assert Repository().root == tmp_path

    # repo exists and explicit path set via environment variable
    os.environ["ZENML_REPOSITORY_PATH"] = str(tmp_path)
    assert Repository.find_repository() == tmp_path
    Repository._reset_instance()
    assert Repository().root == tmp_path

    # repo exists and explicit path to subdirectory set via environment variable
    os.environ["ZENML_REPOSITORY_PATH"] = str(subdirectory_path)
    assert Repository.find_repository() is None
    Repository._reset_instance()
    assert Repository().root is None

    del os.environ["ZENML_REPOSITORY_PATH"]


def test_repo_without_configuration_file_falls_back_to_empty_config(tmp_path):
    """Tests that the repo uses an empty configuration if the config file was
    deleted."""
    utils.create_dir_recursive_if_not_exists(str(tmp_path / ".zen"))
    repo = Repository(tmp_path)

    assert len(repo.stacks) == 1
    assert repo.active_stack_name == "default"
    assert repo.active_stack is not None


def test_creating_repository_instance_during_step_execution_fails(mocker):
    """Tests that creating a Repository instance while a step is being executed
    fails."""
    mocker.patch(
        "zenml.environment.Environment.step_is_running",
        return_value=True,
    )
    with pytest.raises(ForbiddenRepositoryAccessError):
        Repository()


def test_activating_nonexisting_stack_fails(clean_repo):
    """Tests that activating a stack name that isn't registered fails."""
    with pytest.raises(KeyError):
        clean_repo.activate_stack("stack_name_that_hopefully_does_not_exist")


def test_activating_a_stack_updates_the_config_file(clean_repo):
    """Tests that the newly active stack name gets persisted."""
    stack = clean_repo.active_stack
    stack._name = "new_stack"

    clean_repo.register_stack(stack)
    clean_repo.activate_stack(stack.name)

    assert Repository(clean_repo.root).active_stack_name == stack.name


def test_getting_a_stack(clean_repo):
    """Tests that getting a stack succeeds if the stack name exists and fails
    otherwise."""
    existing_stack_name = clean_repo.active_stack_name

    with does_not_raise():
        stack = clean_repo.get_stack(existing_stack_name)
        assert isinstance(stack, Stack)

    with pytest.raises(KeyError):
        clean_repo.get_stack("stack_name_that_hopefully_does_not_exist")


def test_registering_a_stack(clean_repo):
    """Tests that registering a stack works and the stack gets persisted."""
    stack = _create_local_stack(stack_name="some_new_stack_name")
    clean_repo.register_stack(stack)

    new_repo = Repository(clean_repo.root)
    with does_not_raise():
        new_repo.get_stack("some_new_stack_name")


def test_registering_a_stack_with_existing_name(clean_repo):
    """Tests that registering a stack for an existing name fails."""
    stack = _create_local_stack(stack_name=clean_repo.active_stack_name)

    with pytest.raises(StackExistsError):
        clean_repo.register_stack(stack)


def test_registering_a_new_stack_with_already_registered_components(clean_repo):
    """Tests that registering a new stack with already registered components
    registers the stacks and does NOT register the components."""
    stack = clean_repo.active_stack
    stack._name = "some_new_stack_name"

    registered_orchestrators = clean_repo.get_stack_components(
        StackComponentType.ORCHESTRATOR
    )
    registered_metadata_stores = clean_repo.get_stack_components(
        StackComponentType.METADATA_STORE
    )
    registered_artifact_stores = clean_repo.get_stack_components(
        StackComponentType.ARTIFACT_STORE
    )

    with does_not_raise():
        clean_repo.register_stack(stack)

    # the same exact components were already registered in the repo, so no
    # new component should have been registered
    assert registered_orchestrators == clean_repo.get_stack_components(
        StackComponentType.ORCHESTRATOR
    )
    assert registered_metadata_stores == clean_repo.get_stack_components(
        StackComponentType.METADATA_STORE
    )
    assert registered_artifact_stores == clean_repo.get_stack_components(
        StackComponentType.ARTIFACT_STORE
    )


def test_registering_a_stack_registers_unregistered_components(clean_repo):
    """Tests that registering a stack with an unregistered component registers
    the component."""
    registered_stack = clean_repo.active_stack

    new_orchestrator = LocalOrchestrator(name="new_orchestrator_name")
    new_stack = Stack(
        name="new_stack_name",
        orchestrator=new_orchestrator,
        metadata_store=registered_stack.metadata_store,
        artifact_store=registered_stack.artifact_store,
    )

    registered_orchestrators = clean_repo.get_stack_components(
        StackComponentType.ORCHESTRATOR
    )

    with does_not_raise():
        clean_repo.register_stack(new_stack)

    updated_registered_orchestrators = clean_repo.get_stack_components(
        StackComponentType.ORCHESTRATOR
    )

    assert (
        len(updated_registered_orchestrators)
        == len(registered_orchestrators) + 1
    )
    assert any(c == new_orchestrator for c in updated_registered_orchestrators)

    # if one of the components has a name that is already registered, but it's
    # not the exact registered component then the stack registration should fail
    another_new_orchestrator = LocalOrchestrator(name=new_orchestrator.name)
    another_new_stack = Stack(
        name="another_new_stack_name",
        orchestrator=another_new_orchestrator,
        metadata_store=registered_stack.metadata_store,
        artifact_store=registered_stack.artifact_store,
    )

    with pytest.raises(StackComponentExistsError):
        clean_repo.register_stack(another_new_stack)


def test_deregistering_the_active_stack(clean_repo):
    """Tests that deregistering the active stack fails."""
    with pytest.raises(ValueError):
        clean_repo.deregister_stack(clean_repo.active_stack_name)


def test_deregistering_a_non_active_stack(clean_repo):
    """Tests that deregistering a non-active stack works."""
    stack = _create_local_stack("some_new_stack_name")
    clean_repo.register_stack(stack)

    with does_not_raise():
        clean_repo.deregister_stack(stack.name)


def test_getting_a_stack_component(clean_repo):
    """Tests that getting a stack component returns the correct component."""
    component = clean_repo.active_stack.orchestrator

    with does_not_raise():
        registered_component = clean_repo.get_stack_component(
            component_type=component.TYPE, name=component.name
        )

    assert component == registered_component


def test_getting_a_nonexisting_stack_component(clean_repo):
    """Tests that getting a stack component for a name that isn't registered
    fails."""
    with pytest.raises(KeyError):
        clean_repo.get_stack_component(
            component_type=StackComponentType.ORCHESTRATOR,
            name="definitely_not_a_registered_orchestrator",
        )


def test_getting_all_stack_components_of_a_type(clean_repo):
    """Tests that getting all components of a certain type includes newly
    registered components."""
    components = clean_repo.get_stack_components(
        StackComponentType.ORCHESTRATOR
    )

    new_orchestrator = LocalOrchestrator(name="new_orchestrator")
    clean_repo.register_stack_component(new_orchestrator)

    new_components = clean_repo.get_stack_components(
        StackComponentType.ORCHESTRATOR
    )

    assert len(new_components) == len(components) + 1
    assert any(c == new_orchestrator for c in new_components)


def test_registering_a_stack_component_with_existing_name(clean_repo):
    """Tests that registering a stack component for an existing name fails."""
    with pytest.raises(StackComponentExistsError):
        clean_repo.register_stack_component(
            clean_repo.active_stack.orchestrator
        )


def test_registering_a_new_stack_component(clean_repo):
    """Tests that registering a stack component works and is persisted."""
    new_artifact_store = LocalArtifactStore(name="arias_store", path="/meow")
    clean_repo.register_stack_component(new_artifact_store)

    new_repo = Repository(clean_repo.root)

    with does_not_raise():
        registered_artifact_store = new_repo.get_stack_component(
            component_type=new_artifact_store.TYPE, name=new_artifact_store.name
        )

    assert registered_artifact_store == new_artifact_store


def test_deregistering_a_stack_component(clean_repo):
    """Tests that deregistering a stack component works and is persisted."""
    component = LocalOrchestrator(name="unregistered_orchestrator")
    clean_repo.register_stack_component(component)

    clean_repo.deregister_stack_component(
        component_type=component.TYPE, name=component.name
    )

    with pytest.raises(KeyError):
        clean_repo.get_stack_component(
            component_type=component.TYPE, name=component.name
        )

    new_repo = Repository(clean_repo.root)

    with pytest.raises(KeyError):
        new_repo.get_stack_component(
            component_type=component.TYPE, name=component.name
        )


def test_deregistering_a_stack_component_that_is_part_of_a_registered_stack(
    clean_repo,
):
    """Tests that deregistering a stack component that is part of a registered
    stack fails."""
    component = clean_repo.active_stack.orchestrator

    with pytest.raises(ValueError):
        clean_repo.deregister_stack_component(
            component_type=component.TYPE, name=component.name
        )


def test_get_pipelines_forwards_to_metadata_store(clean_repo, mocker):
    """Tests that getting post-execution pipelines forwards calls to the
    metadata store of the (active) stack."""
    # register a stack with a mysql metadata store
    active_stack = clean_repo.active_stack
    new_metadata_store = MySQLMetadataStore(
        name="new_metadata_store_name",
        host="",
        port=0,
        database="",
        username="",
        password="",
    )
    new_stack = Stack(
        name="new_stack_name",
        orchestrator=active_stack.orchestrator,
        metadata_store=new_metadata_store,
        artifact_store=active_stack.artifact_store,
    )
    clean_repo.register_stack(new_stack)

    mocker.patch.object(SQLiteMetadataStore, "get_pipelines", return_value=[])
    mocker.patch.object(SQLiteMetadataStore, "get_pipeline", return_value=None)

    mocker.patch.object(MySQLMetadataStore, "get_pipelines", return_value=[])
    mocker.patch.object(MySQLMetadataStore, "get_pipeline", return_value=None)

    # calling without a stack name calls the metadata store of the active stack
    clean_repo.get_pipelines()
    clean_repo.get_pipeline(pipeline_name="whatever")
    SQLiteMetadataStore.get_pipelines.assert_called_once()
    SQLiteMetadataStore.get_pipeline.assert_called_once()
    assert not MySQLMetadataStore.get_pipelines.called
    assert not MySQLMetadataStore.get_pipeline.called

    clean_repo.get_pipeline(pipeline_name="whatever", stack_name=new_stack.name)
    clean_repo.get_pipelines(stack_name=new_stack.name)
    MySQLMetadataStore.get_pipelines.assert_called_once()
    MySQLMetadataStore.get_pipeline.assert_called_once()
