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
from datetime import datetime
from typing import Optional
from uuid import uuid4

import pytest

from zenml.artifact_stores.local_artifact_store import (
    LocalArtifactStore,
    LocalArtifactStoreConfig,
)
from zenml.client import Client
from zenml.enums import StackComponentType
from zenml.exceptions import (
    IllegalOperationError,
    InitializationException,
    StackComponentExistsError,
    StackExistsError,
)
from zenml.io import fileio
from zenml.models.stack_models import StackModel
from zenml.orchestrators.base_orchestrator import BaseOrchestratorConfig
from zenml.orchestrators.local.local_orchestrator import LocalOrchestrator
from zenml.stack import Stack
from zenml.utils import io_utils


def _create_local_stack(
    repo: Client,
    stack_name: str,
    orchestrator_name: Optional[str] = None,
    artifact_store_name: Optional[str] = None,
) -> Stack:
    """Creates a local stack with components with the given names. If the
    names are not given, a random string is used instead."""

    def _random_name():
        return "".join(random.choices(string.ascii_letters, k=10))

    orchestrator_name = orchestrator_name or _random_name()
    artifact_store_name = artifact_store_name or _random_name()
    user = repo.active_user
    project = repo.active_project

    orchestrator = LocalOrchestrator(
        name=orchestrator_name,
        id=uuid4(),
        config=BaseOrchestratorConfig(),
        flavor="local",
        type=StackComponentType.ORCHESTRATOR,
        user=user.id,
        project=project.id,
        created=datetime.now(),
        updated=datetime.now(),
    )
    artifact_store = LocalArtifactStore(
        name=artifact_store_name,
        id=uuid4(),
        config=LocalArtifactStoreConfig(),
        flavor="local",
        type=StackComponentType.ARTIFACT_STORE,
        user=user.id,
        project=project.id,
        created=datetime.now(),
        updated=datetime.now(),
    )

    return Stack(
        id=uuid4(),
        name=stack_name,
        orchestrator=orchestrator,
        artifact_store=artifact_store,
    )


def test_repository_detection(tmp_path):
    """Tests detection of ZenML repositories in a directory."""
    assert Client.is_client_directory(tmp_path) is False
    Client.initialize(tmp_path)
    assert Client.is_client_directory(tmp_path) is True


def test_initializing_repo_creates_directory_and_uses_default_stack(
    tmp_path, clean_client
):
    """Tests that repo initialization creates a .zen directory and uses the
    default local stack."""
    Client.initialize(tmp_path)
    assert fileio.exists(str(tmp_path / ".zen"))

    client = Client()
    # switch to the new repo root
    client.activate_root(tmp_path)

    assert len(client.stacks) == 1

    stack = client.active_stack
    assert isinstance(stack.orchestrator, LocalOrchestrator)
    assert isinstance(stack.artifact_store, LocalArtifactStore)
    assert stack.container_registry is None


def test_initializing_repo_twice_fails(tmp_path):
    """Tests that initializing a repo in a directory where another repo already
    exists fails."""
    Client.initialize(tmp_path)
    with pytest.raises(InitializationException):
        Client.initialize(tmp_path)


def test_freshly_initialized_repo_attributes(tmp_path):
    """Tests that the attributes of a new repository are set correctly."""
    Client.initialize(tmp_path)
    client = Client(tmp_path)

    assert client.root == tmp_path


def test_finding_repository_directory_with_explicit_path(
    tmp_path, clean_client
):
    """Tests that a repository can be found using an explicit path, an
    environment variable and the current working directory."""
    subdirectory_path = tmp_path / "some_other_directory"
    io_utils.create_dir_recursive_if_not_exists(str(subdirectory_path))
    os.chdir(str(subdirectory_path))

    # no repo exists and explicit path passed
    assert Client.find_client(tmp_path) is None
    assert Client(tmp_path).root is None

    # no repo exists and no path passed (=uses current working directory)
    assert Client.find_client() is None
    Client._reset_instance()
    assert Client().root is None

    # no repo exists and explicit path set via environment variable
    os.environ["ZENML_REPOSITORY_PATH"] = str(tmp_path)
    assert Client.find_client() is None
    Client._reset_instance()
    assert Client().root is None

    del os.environ["ZENML_REPOSITORY_PATH"]

    # initializing the repo
    Client.initialize(tmp_path)

    # repo exists and explicit path passed
    assert Client.find_client(tmp_path) == tmp_path
    assert Client(tmp_path).root == tmp_path

    # repo exists and explicit path to subdirectory passed
    assert Client.find_client(subdirectory_path) is None
    assert Client(subdirectory_path).root is None

    # repo exists and no path passed (=uses current working directory)
    assert Client.find_client() == tmp_path
    Client._reset_instance()
    assert Client().root == tmp_path

    # repo exists and explicit path set via environment variable
    os.environ["ZENML_REPOSITORY_PATH"] = str(tmp_path)
    assert Client.find_client() == tmp_path
    Client._reset_instance()
    assert Client().root == tmp_path

    # repo exists and explicit path to subdirectory set via environment variable
    os.environ["ZENML_REPOSITORY_PATH"] = str(subdirectory_path)
    assert Client.find_client() is None
    Client._reset_instance()
    assert Client().root is None

    del os.environ["ZENML_REPOSITORY_PATH"]


def test_repo_without_configuration_file_falls_back_to_empty_config(tmp_path):
    """Tests that the repo uses an empty configuration if the config file was
    deleted."""
    io_utils.create_dir_recursive_if_not_exists(str(tmp_path / ".zen"))
    client = Client(tmp_path)

    assert len(client.stacks) == 1
    assert client.active_stack_model.name == "default"
    assert client.active_stack is not None


def test_creating_repository_instance_during_step_execution(mocker):
    """Tests that creating a Repository instance while a step is being executed
    does not fail."""
    mocker.patch(
        "zenml.environment.Environment.step_is_running",
        return_value=True,
    )
    with does_not_raise():
        Client()


def test_activating_nonexisting_stack_fails(clean_client):
    """Tests that activating a stack name that isn't registered fails."""
    stack = _create_local_stack(
        repo=clean_client, stack_name="stack_name_that_hopefully_does_not_exist"
    )

    with pytest.raises(KeyError):
        clean_client.activate_stack(
            stack.to_model(
                user=clean_client.active_user.id,
                project=clean_client.active_project.id,
            )
        )


def test_activating_a_stack_updates_the_config_file(clean_client):
    """Tests that the newly active stack name gets persisted."""
    stack = _create_local_stack(repo=clean_client, stack_name="new_stack")
    stack_model = stack.to_model(
        user=clean_client.active_user.id, project=clean_client.active_project.id
    )

    clean_client.register_stack_component(stack.orchestrator.to_model())
    clean_client.register_stack_component(stack.artifact_store.to_model())

    clean_client.register_stack(stack_model)
    clean_client.activate_stack(stack_model)

    assert Client(clean_client.root).active_stack_model.name == stack.name


def test_getting_a_stack(clean_client):
    """Tests that getting a stack succeeds if the stack name exists and fails
    otherwise."""
    existing_stack_name = clean_client.active_stack.name

    with does_not_raise():
        stack = clean_client.get_stack_by_name_or_partial_id(
            existing_stack_name
        )
        assert isinstance(stack, StackModel)

    with pytest.raises(KeyError):
        clean_client.get_stack_by_name_or_partial_id(
            "stack_name_that_hopefully_does_not_exist"
        )


def test_registering_a_stack(clean_client):
    """Tests that registering a stack works and the stack gets persisted."""
    stack = _create_local_stack(
        repo=clean_client, stack_name="some_new_stack_name"
    )
    stack_model = stack.to_model(
        user=clean_client.active_user.id, project=clean_client.active_project.id
    )
    clean_client.register_stack_component(stack.orchestrator.to_model())
    clean_client.register_stack_component(stack.artifact_store.to_model())
    clean_client.register_stack(stack_model)

    Client(clean_client.root)
    with does_not_raise():
        clean_client.zen_store.get_stack(stack_model.id)


def test_registering_a_stack_with_existing_name(clean_client):
    """Tests that registering a stack for an existing name fails."""
    stack = _create_local_stack(
        repo=clean_client, stack_name=clean_client.active_stack_model.name
    )
    clean_client.register_stack_component(stack.orchestrator.to_model())
    clean_client.register_stack_component(stack.artifact_store.to_model())

    with pytest.raises(StackExistsError):
        clean_client.register_stack(
            stack.to_model(
                user=clean_client.active_user.id,
                project=clean_client.active_project.id,
            )
        )


def test_registering_a_new_stack_with_already_registered_components(
    clean_client,
):
    """Tests that registering a new stack with already registered components
    registers the stacks and does NOT register the components."""
    stack = clean_client.active_stack.to_model(
        user=clean_client.active_user.id,
        project=clean_client.active_project.id,
    )
    stack.id = uuid4()
    stack.name = "some_new_stack_name"

    registered_orchestrators = clean_client.list_stack_components_by_type(
        StackComponentType.ORCHESTRATOR
    )
    registered_artifact_stores = clean_client.list_stack_components_by_type(
        StackComponentType.ARTIFACT_STORE
    )

    with does_not_raise():
        clean_client.register_stack(stack)

    # the same exact components were already registered in the repo, so no
    # new component should have been registered
    assert (
        registered_orchestrators
        == clean_client.list_stack_components_by_type(
            StackComponentType.ORCHESTRATOR
        )
    )
    assert (
        registered_artifact_stores
        == clean_client.list_stack_components_by_type(
            StackComponentType.ARTIFACT_STORE
        )
    )


def test_updating_a_stack_with_new_components(clean_client):
    """Tests that updating a new stack with already registered components
    updates the stack with the new or altered components passed in."""
    current_stack = clean_client.active_stack
    old_orchestrator = current_stack.orchestrator
    new_orchestrator = _create_local_stack(
        clean_client, "", orchestrator_name="new_orchestrator"
    ).orchestrator
    updated_stack = Stack(
        id=current_stack.id,
        name=current_stack.name,
        orchestrator=new_orchestrator,
        artifact_store=current_stack.artifact_store,
    )

    with does_not_raise():
        clean_client.register_stack_component(new_orchestrator.to_model())

        clean_client.update_stack(
            updated_stack.to_model(
                user=clean_client.active_user.id,
                project=clean_client.active_project.id,
            )
        )

    active_orchestrator = clean_client.active_stack.orchestrator.to_model()
    assert active_orchestrator != old_orchestrator.to_model()
    assert active_orchestrator == new_orchestrator.to_model()


def test_renaming_stack_with_update_method_succeeds(clean_client):
    """Tests that renaming a stack with the update method succeeds."""
    current_stack = clean_client.active_stack
    new_stack_name = "new_stack_name"
    updated_stack = Stack(
        id=current_stack.id,
        name=new_stack_name,
        orchestrator=current_stack.orchestrator,
        artifact_store=current_stack.artifact_store,
    )

    with does_not_raise():
        clean_client.update_stack(
            updated_stack.to_model(
                user=clean_client.active_user.id,
                project=clean_client.active_project.id,
            )
        )
    assert new_stack_name == clean_client.active_stack_model.name


def test_register_a_stack_with_unregistered_component_fails(clean_client):
    """Tests that registering a stack with an unregistered component fails."""

    new_stack = _create_local_stack(
        repo=clean_client, stack_name="some_new_stack_name"
    )
    # Don't register orchestrator or artifact store

    with pytest.raises(KeyError):
        clean_client.register_stack(
            new_stack.to_model(
                user=clean_client.active_user.id,
                project=clean_client.active_project.id,
            )
        )


def test_deregistering_the_active_stack(clean_client):
    """Tests that deregistering the active stack fails."""
    with pytest.raises(ValueError):
        clean_client.deregister_stack(
            clean_client.active_stack.to_model(
                user=clean_client.active_user.id,
                project=clean_client.active_project.id,
            )
        )


def test_deregistering_a_non_active_stack(clean_client):
    """Tests that deregistering a non-active stack works."""
    stack = _create_local_stack(
        repo=clean_client, stack_name="some_new_stack_name"
    )
    stack_model = stack.to_model(
        user=clean_client.active_user.id, project=clean_client.active_project.id
    )
    clean_client.register_stack_component(stack.orchestrator.to_model())
    clean_client.register_stack_component(stack.artifact_store.to_model())
    clean_client.register_stack(stack_model)

    with does_not_raise():
        clean_client.deregister_stack(stack_model)


def test_getting_a_stack_component(clean_client):
    """Tests that getting a stack component returns the correct component."""
    component = clean_client.active_stack.orchestrator.to_model()

    with does_not_raise():
        registered_component = clean_client.get_stack_component_by_id(
            component.id
        )

    assert component == registered_component


def test_getting_a_nonexisting_stack_component(clean_client):
    """Tests that getting a stack component for a name that isn't registered
    fails."""
    with pytest.raises(KeyError):
        clean_client.get_stack_component_by_id(uuid4())


def test_registering_a_stack_component_with_existing_name(clean_client):
    """Tests that registering a stack component for an existing name fails."""
    with pytest.raises(StackComponentExistsError):
        clean_client.register_stack_component(
            clean_client.active_stack.orchestrator.to_model()
        )


def test_registering_a_new_stack_component(clean_client):
    """Tests that registering a stack component works and is persisted."""
    new_artifact_store = _create_local_stack(
        clean_client, "", artifact_store_name="arias_store"
    ).artifact_store.to_model()
    clean_client.register_stack_component(new_artifact_store)

    new_client = Client(clean_client.root)

    with does_not_raise():
        registered_artifact_store = new_client.get_stack_component_by_id(
            new_artifact_store.id
        )

    assert registered_artifact_store == new_artifact_store


def test_deregistering_a_stack_component(clean_client):
    """Tests that deregistering a stack component works and is persisted."""
    component = _create_local_stack(
        clean_client, "", orchestrator_name="unregistered_orchestrator"
    ).orchestrator.to_model()

    clean_client.register_stack_component(component)
    clean_client.deregister_stack_component(component)

    with pytest.raises(KeyError):
        clean_client.get_stack_component_by_id(component.id)

    Client(clean_client.root)

    with pytest.raises(KeyError):
        clean_client.get_stack_component_by_id(component.id)


def test_deregistering_a_stack_component_that_is_part_of_a_registered_stack(
    clean_client,
):
    """Tests that deregistering a stack component that is part of a registered
    stack fails."""
    component = clean_client.active_stack.orchestrator.to_model()

    with pytest.raises(IllegalOperationError):
        clean_client.deregister_stack_component(component)
