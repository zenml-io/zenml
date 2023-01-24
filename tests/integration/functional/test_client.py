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
from uuid import uuid4

import pytest

from zenml.client import Client
from zenml.enums import StackComponentType
from zenml.exceptions import (
    IllegalOperationError,
    InitializationException,
    StackComponentExistsError,
    StackExistsError,
)
from zenml.io import fileio
from zenml.metadata.metadata_types import MetadataTypeEnum
from zenml.models import ComponentResponseModel, StackResponseModel
from zenml.utils import io_utils


def _create_local_orchestrator(
    client: Client,
    orchestrator_name: str = "OrchesTraitor",
) -> ComponentResponseModel:
    return client.create_stack_component(
        name=orchestrator_name,
        flavor="local",
        component_type=StackComponentType.ORCHESTRATOR,
        configuration={},
        is_shared=False,
    )


def _create_local_artifact_store(
    client: Client,
    artifact_store_name: str = "Art-E-Fact",
) -> ComponentResponseModel:
    return client.create_stack_component(
        name=artifact_store_name,
        flavor="local",
        component_type=StackComponentType.ARTIFACT_STORE,
        configuration={},
        is_shared=False,
    )


def _create_local_stack(
    client: Client,
    stack_name: str,
    orchestrator_name: Optional[str] = None,
    artifact_store_name: Optional[str] = None,
) -> StackResponseModel:
    """Creates a local stack with components with the given names. If the names are not given, a random string is used instead."""

    def _random_name():
        return "".join(random.choices(string.ascii_letters, k=10))

    orchestrator = _create_local_orchestrator(
        client=client, orchestrator_name=orchestrator_name or _random_name()
    )

    artifact_store = _create_local_artifact_store(
        client=client,
        artifact_store_name=artifact_store_name or _random_name(),
    )

    return client.create_stack(
        name=stack_name,
        components={
            StackComponentType.ORCHESTRATOR: str(orchestrator.id),
            StackComponentType.ARTIFACT_STORE: str(artifact_store.id),
        },
    )


def test_repository_detection(tmp_path):
    """Tests detection of ZenML repositories in a directory."""
    assert Client.is_repository_directory(tmp_path) is False
    Client.initialize(tmp_path)
    assert Client.is_repository_directory(tmp_path) is True


def test_initializing_repo_creates_directory_and_uses_default_stack(
    tmp_path, clean_client
):
    """Tests that repo initialization creates a .zen directory and uses the default local stack."""
    Client.initialize(tmp_path)
    assert fileio.exists(str(tmp_path / ".zen"))

    client = Client()
    # switch to the new repo root
    client.activate_root(tmp_path)

    stack = client.active_stack_model
    assert isinstance(
        stack.components[StackComponentType.ORCHESTRATOR][0],
        ComponentResponseModel,
    )
    assert isinstance(
        stack.components[StackComponentType.ARTIFACT_STORE][0],
        ComponentResponseModel,
    )
    with pytest.raises(KeyError):
        assert stack.components[StackComponentType.CONTAINER_REGISTRY]


def test_initializing_repo_twice_fails(tmp_path):
    """Tests that initializing a repo in a directory where another repo already exists fails."""
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
    """Tests that a repository can be found using an explicit path, an environment variable and the current working directory."""
    subdirectory_path = tmp_path / "some_other_directory"
    io_utils.create_dir_recursive_if_not_exists(str(subdirectory_path))
    os.chdir(str(subdirectory_path))

    # no repo exists and explicit path passed
    assert Client.find_repository(tmp_path) is None
    assert Client(tmp_path).root is None

    # no repo exists and no path passed (=uses current working directory)
    assert Client.find_repository() is None
    Client._reset_instance()
    assert Client().root is None

    # no repo exists and explicit path set via environment variable
    os.environ["ZENML_REPOSITORY_PATH"] = str(tmp_path)
    assert Client.find_repository() is None
    Client._reset_instance()
    assert Client().root is None

    del os.environ["ZENML_REPOSITORY_PATH"]

    # initializing the repo
    Client.initialize(tmp_path)

    # repo exists and explicit path passed
    assert Client.find_repository(tmp_path) == tmp_path
    assert Client(tmp_path).root == tmp_path

    # repo exists and explicit path to subdirectory passed
    assert Client.find_repository(subdirectory_path) is None
    assert Client(subdirectory_path).root is None

    # repo exists and no path passed (=uses current working directory)
    assert Client.find_repository() == tmp_path
    Client._reset_instance()
    assert Client().root == tmp_path

    # repo exists and explicit path set via environment variable
    os.environ["ZENML_REPOSITORY_PATH"] = str(tmp_path)
    assert Client.find_repository() == tmp_path
    Client._reset_instance()
    assert Client().root == tmp_path

    # repo exists and explicit path to subdirectory set via environment variable
    os.environ["ZENML_REPOSITORY_PATH"] = str(subdirectory_path)
    assert Client.find_repository() is None
    Client._reset_instance()
    assert Client().root is None

    del os.environ["ZENML_REPOSITORY_PATH"]


def test_creating_repository_instance_during_step_execution(mocker):
    """Tests that creating a Repository instance while a step is being executed does not fail."""
    mocker.patch(
        "zenml.environment.Environment.step_is_running",
        return_value=True,
    )
    with does_not_raise():
        Client()


def test_activating_nonexisting_stack_fails(clean_client):
    """Tests that activating a stack name that isn't registered fails."""
    with pytest.raises(KeyError):
        clean_client.activate_stack(str(uuid4()))


def test_activating_a_stack_updates_the_config_file(clean_client):
    """Tests that the newly active stack name gets persisted."""
    stack = _create_local_stack(client=clean_client, stack_name="new_stack")
    clean_client.activate_stack(stack.id)

    assert Client(clean_client.root).active_stack_model.name == stack.name


def test_registering_a_stack(clean_client):
    """Tests that registering a stack works and the stack gets persisted."""
    orch = _create_local_orchestrator(
        client=clean_client,
    )
    art = _create_local_artifact_store(
        client=clean_client,
    )
    new_stack_name = "some_new_stack_name"
    new_stack = clean_client.create_stack(
        name=new_stack_name,
        components={
            StackComponentType.ORCHESTRATOR: str(orch.id),
            StackComponentType.ARTIFACT_STORE: str(art.id),
        },
    )

    Client(clean_client.root)
    with does_not_raise():
        clean_client.zen_store.get_stack(new_stack.id)


def test_registering_a_stack_with_existing_name(clean_client):
    """Tests that registering a stack for an existing name fails."""
    _create_local_stack(
        client=clean_client,
        stack_name="axels_super_awesome_stack_of_fluffyness",
    )
    orchestrator = _create_local_orchestrator(clean_client)
    artifact_store = _create_local_artifact_store(clean_client)

    with pytest.raises(StackExistsError):
        clean_client.create_stack(
            name="axels_super_awesome_stack_of_fluffyness",
            components={
                StackComponentType.ORCHESTRATOR: str(orchestrator.id),
                StackComponentType.ARTIFACT_STORE: str(artifact_store.id),
            },
        )


def test_updating_a_stack_with_new_component_succeeds(clean_client):
    """Tests that updating a new stack with already registered components updates the stack with the new or altered components passed in."""
    stack = _create_local_stack(
        client=clean_client, stack_name="some_new_stack_name"
    )
    clean_client.activate_stack(stack_name_id_or_prefix=stack.name)

    old_orchestrator = stack.components[StackComponentType.ORCHESTRATOR][0]
    old_artifact_store = stack.components[StackComponentType.ARTIFACT_STORE][0]
    orchestrator = _create_local_orchestrator(
        client=clean_client, orchestrator_name="different_orchestrator"
    )

    with does_not_raise():
        updated_stack = clean_client.update_stack(
            name_id_or_prefix=stack.name,
            component_updates={
                StackComponentType.ORCHESTRATOR: [str(orchestrator.id)],
            },
        )

    active_orchestrator = updated_stack.components[
        StackComponentType.ORCHESTRATOR
    ][0]
    active_artifact_store = updated_stack.components[
        StackComponentType.ARTIFACT_STORE
    ][0]
    assert active_orchestrator != old_orchestrator
    assert active_orchestrator == orchestrator
    assert active_artifact_store == old_artifact_store


def test_renaming_stack_with_update_method_succeeds(clean_client):
    """Tests that renaming a stack with the update method succeeds."""
    stack = _create_local_stack(
        client=clean_client, stack_name="some_new_stack_name"
    )
    clean_client.activate_stack(stack.id)

    new_stack_name = "new_stack_name"

    with does_not_raise():
        clean_client.update_stack(
            name_id_or_prefix=stack.id, name=new_stack_name
        )
    assert clean_client.get_stack(name_id_or_prefix=new_stack_name)


def test_register_a_stack_with_unregistered_component_fails(clean_client):
    """Tests that registering a stack with an unregistered component fails."""
    with pytest.raises(KeyError):
        clean_client.create_stack(
            name="axels_empty_stack_of_disappoint",
            components={
                StackComponentType.ORCHESTRATOR: "orchestrator_doesnt_exist",
                StackComponentType.ARTIFACT_STORE: "this_also_doesnt",
            },
        )


def test_deregistering_the_active_stack(clean_client):
    """Tests that deregistering the active stack fails."""
    with pytest.raises(ValueError):
        clean_client.delete_stack(clean_client.active_stack_model.id)


def test_deregistering_a_non_active_stack(clean_client):
    """Tests that deregistering a non-active stack works."""
    stack = _create_local_stack(
        client=clean_client, stack_name="some_new_stack_name"
    )

    with does_not_raise():
        clean_client.delete_stack(name_id_or_prefix=stack.id)


def test_getting_a_stack_component(clean_client):
    """Tests that getting a stack component returns the correct component."""
    component = clean_client.active_stack_model.components[
        StackComponentType.ORCHESTRATOR
    ][0]
    with does_not_raise():
        registered_component = clean_client.get_stack_component(
            component_type=component.type, name_id_or_prefix=component.id
        )

    assert component == registered_component


def test_getting_a_nonexisting_stack_component(clean_client):
    """Tests that getting a stack component for a name that isn't registered fails."""
    with pytest.raises(KeyError):
        clean_client.get_stack(name_id_or_prefix=str(uuid4()))


def test_registering_a_stack_component_with_existing_name(clean_client):
    """Tests that registering a stack component for an existing name fails."""
    _create_local_orchestrator(
        client=clean_client, orchestrator_name="axels_orchestration_laboratory"
    )
    with pytest.raises(StackComponentExistsError):
        clean_client.create_stack_component(
            name="axels_orchestration_laboratory",
            flavor="local",
            component_type=StackComponentType.ORCHESTRATOR,
            configuration={},
            is_shared=False,
        )


def test_registering_a_new_stack_component_succeeds(clean_client):
    """Tests that registering a stack component works and is persisted."""
    new_artifact_store = _create_local_artifact_store(client=clean_client)

    new_client = Client(clean_client.root)

    with does_not_raise():
        registered_artifact_store = new_client.get_stack_component(
            component_type=new_artifact_store.type,
            name_id_or_prefix=new_artifact_store.id,
        )

    assert registered_artifact_store == new_artifact_store


def test_deregistering_a_stack_component_in_stack_fails(clean_client):
    """Tests that deregistering a stack component works and is persisted."""
    component = _create_local_stack(
        clean_client, "", orchestrator_name="unregistered_orchestrator"
    ).components[StackComponentType.ORCHESTRATOR][0]

    with pytest.raises(IllegalOperationError):
        clean_client.deregister_stack_component(
            component_type=StackComponentType.ORCHESTRATOR,
            name_id_or_prefix=str(component.id),
        )


def test_deregistering_a_stack_component_that_is_part_of_a_registered_stack(
    clean_client,
):
    """Tests that deregistering a stack component that is part of a registered stack fails."""
    component = clean_client.active_stack_model.components[
        StackComponentType.ORCHESTRATOR
    ][0]

    with pytest.raises(IllegalOperationError):
        clean_client.deregister_stack_component(
            name_id_or_prefix=component.id,
            component_type=StackComponentType.ORCHESTRATOR,
        )


def test_create_run_metadata_for_pipeline_run(clean_client_with_run):
    """Test creating run metadata linked only to a pipeline run."""
    pipeline_run = clean_client_with_run.list_runs()[0]
    existing_metadata = clean_client_with_run.list_run_metadata(
        pipeline_run_id=pipeline_run.id
    )

    # Assert that the created metadata is correct
    new_metadata = clean_client_with_run.create_run_metadata(
        metadata={"axel": "is awesome"}, pipeline_run_id=pipeline_run.id
    )
    assert len(new_metadata) == 1
    assert new_metadata[0].key == "axel"
    assert new_metadata[0].value == "is awesome"
    assert new_metadata[0].type == MetadataTypeEnum.STRING
    assert new_metadata[0].pipeline_run_id == pipeline_run.id
    assert new_metadata[0].step_run_id is None
    assert new_metadata[0].artifact_id is None
    assert new_metadata[0].stack_component_id is None

    # Assert new metadata is linked to the pipeline run
    all_metadata = clean_client_with_run.list_run_metadata(
        pipeline_run_id=pipeline_run.id
    )
    assert len(all_metadata) == len(existing_metadata) + 1


def test_create_run_metadata_for_pipeline_run_and_component(
    clean_client_with_run,
):
    """Test creating metadata linked to a pipeline run and a stack component"""
    pipeline_run = clean_client_with_run.list_runs()[0]
    orchestrator_id = clean_client_with_run.active_stack_model.components[
        "orchestrator"
    ][0].id
    existing_metadata = clean_client_with_run.list_run_metadata(
        pipeline_run_id=pipeline_run.id
    )
    existing_component_metadata = clean_client_with_run.list_run_metadata(
        stack_component_id=orchestrator_id
    )

    # Assert that the created metadata is correct
    new_metadata = clean_client_with_run.create_run_metadata(
        metadata={"aria": "is awesome too"},
        pipeline_run_id=pipeline_run.id,
        stack_component_id=orchestrator_id,
    )
    assert len(new_metadata) == 1
    assert new_metadata[0].key == "aria"
    assert new_metadata[0].value == "is awesome too"
    assert new_metadata[0].type == MetadataTypeEnum.STRING
    assert new_metadata[0].pipeline_run_id == pipeline_run.id
    assert new_metadata[0].step_run_id is None
    assert new_metadata[0].artifact_id is None
    assert new_metadata[0].stack_component_id == orchestrator_id

    # Assert new metadata is linked to the pipeline run
    registered_metadata = clean_client_with_run.list_run_metadata(
        pipeline_run_id=pipeline_run.id
    )
    assert len(registered_metadata) == len(existing_metadata) + 1

    # Assert new metadata is linked to the stack component
    registered_component_metadata = clean_client_with_run.list_run_metadata(
        stack_component_id=orchestrator_id
    )
    assert (
        len(registered_component_metadata)
        == len(existing_component_metadata) + 1
    )


def test_create_run_metadata_for_step_run(clean_client_with_run):
    """Test creating run metadata linked only to a step run."""
    step_run = clean_client_with_run.list_run_steps()[0]
    existing_metadata = clean_client_with_run.list_run_metadata(
        step_run_id=step_run.id
    )

    # Assert that the created metadata is correct
    new_metadata = clean_client_with_run.create_run_metadata(
        metadata={"axel": "is awesome"}, step_run_id=step_run.id
    )
    assert len(new_metadata) == 1
    assert new_metadata[0].key == "axel"
    assert new_metadata[0].value == "is awesome"
    assert new_metadata[0].type == MetadataTypeEnum.STRING
    assert new_metadata[0].pipeline_run_id is None
    assert new_metadata[0].step_run_id == step_run.id
    assert new_metadata[0].artifact_id is None
    assert new_metadata[0].stack_component_id is None

    # Assert new metadata is linked to the step run
    registered_metadata = clean_client_with_run.list_run_metadata(
        step_run_id=step_run.id
    )
    assert len(registered_metadata) == len(existing_metadata) + 1


def test_create_run_metadata_for_step_run_and_component(clean_client_with_run):
    """Test creating metadata linked to a step run and a stack component"""
    step_run = clean_client_with_run.list_run_steps()[0]
    orchestrator_id = clean_client_with_run.active_stack_model.components[
        "orchestrator"
    ][0].id
    existing_metadata = clean_client_with_run.list_run_metadata(
        step_run_id=step_run.id
    )
    existing_component_metadata = clean_client_with_run.list_run_metadata(
        stack_component_id=orchestrator_id
    )

    # Assert that the created metadata is correct
    new_metadata = clean_client_with_run.create_run_metadata(
        metadata={"aria": "is awesome too"},
        step_run_id=step_run.id,
        stack_component_id=orchestrator_id,
    )
    assert len(new_metadata) == 1
    assert new_metadata[0].key == "aria"
    assert new_metadata[0].value == "is awesome too"
    assert new_metadata[0].type == MetadataTypeEnum.STRING
    assert new_metadata[0].pipeline_run_id is None
    assert new_metadata[0].step_run_id == step_run.id
    assert new_metadata[0].artifact_id is None
    assert new_metadata[0].stack_component_id == orchestrator_id

    # Assert new metadata is linked to the step run
    registered_metadata = clean_client_with_run.list_run_metadata(
        step_run_id=step_run.id
    )
    assert len(registered_metadata) == len(existing_metadata) + 1

    # Assert new metadata is linked to the stack component
    registered_component_metadata = clean_client_with_run.list_run_metadata(
        stack_component_id=orchestrator_id
    )
    assert (
        len(registered_component_metadata)
        == len(existing_component_metadata) + 1
    )


def test_create_run_metadata_for_artifact(clean_client_with_run):
    """Test creating run metadata linked to an artifact."""
    artifact = clean_client_with_run.list_artifacts()[0]
    existing_metadata = clean_client_with_run.list_run_metadata(
        artifact_id=artifact.id
    )

    # Assert that the created metadata is correct
    new_metadata = clean_client_with_run.create_run_metadata(
        metadata={"axel": "is awesome"}, artifact_id=artifact.id
    )
    assert len(new_metadata) == 1
    assert new_metadata[0].key == "axel"
    assert new_metadata[0].value == "is awesome"
    assert new_metadata[0].type == MetadataTypeEnum.STRING
    assert new_metadata[0].pipeline_run_id is None
    assert new_metadata[0].step_run_id is None
    assert new_metadata[0].artifact_id == artifact.id
    assert new_metadata[0].stack_component_id is None

    # Assert new metadata is linked to the artifact
    registered_metadata = clean_client_with_run.list_run_metadata(
        artifact_id=artifact.id
    )
    assert len(registered_metadata) == len(existing_metadata) + 1


def test_create_run_metadata_fails_if_not_linked_to_any_entity(
    clean_client_with_run,
):
    """Test that creating metadata without linking it to any entity fails."""
    with pytest.raises(ValueError):
        clean_client_with_run.create_run_metadata(
            metadata={"axel": "is awesome"}
        )


def test_create_run_metadata_fails_if_linked_to_multiple_entities(
    clean_client_with_run,
):
    """Test that creating metadata fails when linking to multiple entities."""
    metadata = {"axel": "is awesome"}
    pipeline_run = clean_client_with_run.list_runs()[0]
    step_run = clean_client_with_run.list_run_steps()[0]
    artifact = clean_client_with_run.list_artifacts()[0]

    with pytest.raises(ValueError):
        clean_client_with_run.create_run_metadata(
            metadata=metadata,
            pipeline_run_id=pipeline_run.id,
            step_run_id=step_run.id,
            artifact_id=artifact.id,
        )

    with pytest.raises(ValueError):
        clean_client_with_run.create_run_metadata(
            metadata=metadata,
            pipeline_run_id=pipeline_run.id,
            step_run_id=step_run.id,
        )

    with pytest.raises(ValueError):
        clean_client_with_run.create_run_metadata(
            metadata=metadata,
            pipeline_run_id=pipeline_run.id,
            artifact_id=artifact.id,
        )

    with pytest.raises(ValueError):
        clean_client_with_run.create_run_metadata(
            metadata=metadata,
            step_run_id=step_run.id,
            artifact_id=artifact.id,
        )
