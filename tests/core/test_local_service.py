#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import os

import pytest
from git.repo.base import Repo

from zenml.artifact_stores import BaseArtifactStore, LocalArtifactStore
from zenml.core.repo import Repository
from zenml.exceptions import AlreadyExistsException, DoesNotExistException
from zenml.metadata import BaseMetadataStore
from zenml.metadata.sqlite_metadata_store import SQLiteMetadataStore
from zenml.orchestrators import BaseOrchestrator, LocalOrchestrator
from zenml.stacks import BaseStack

LOCAL_STACK_NAME = "local_stack"
LOCAL_ORCHESTRATOR_NAME = "local_orchestrator"
LOCAL_METADATA_STORE_NAME = "local_metadata_store"
LOCAL_ARTIFACT_STORE_NAME = "local_artifact_store"


def test_local_service_file_name_exists(tmp_path: str) -> None:
    """Local Service contains reference to a local service file name."""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    local_service = repo.get_service()
    assert local_service.get_serialization_file_name is not None


def test_local_service_can_access_metadata_stores(tmp_path: str) -> None:
    """Local Service can access metadata stores."""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    local_service = repo.get_service()
    assert local_service.metadata_stores is not None
    assert isinstance(local_service.metadata_stores, dict)
    assert isinstance(
        local_service.metadata_stores[LOCAL_METADATA_STORE_NAME],
        BaseMetadataStore,
    )


def test_local_service_can_access_artifact_stores(tmp_path: str) -> None:
    """Local Service can access artifact stores."""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    local_service = repo.get_service()
    assert local_service.artifact_stores is not None
    assert isinstance(local_service.artifact_stores, dict)
    assert isinstance(
        local_service.artifact_stores[LOCAL_ARTIFACT_STORE_NAME],
        BaseArtifactStore,
    )


def test_local_service_can_access_orchestrators(tmp_path: str) -> None:
    """Local Service can access orchestrators."""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    local_service = repo.get_service()
    assert local_service.orchestrators is not None
    assert isinstance(local_service.orchestrators, dict)
    assert isinstance(
        local_service.orchestrators[LOCAL_ORCHESTRATOR_NAME],
        BaseOrchestrator,
    )


def test_get_stack_returns_a_stack_when_provided_a_key(tmp_path: str) -> None:
    """Check get_stack returns a stack with its expected components."""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    local_service = repo.get_service()
    stack = local_service.get_stack("local_stack")
    assert stack is not None
    assert isinstance(stack, BaseStack)
    assert (
        stack.orchestrator
        == local_service.orchestrators[LOCAL_ORCHESTRATOR_NAME]
    )
    assert (
        stack.artifact_store
        == local_service.artifact_stores[LOCAL_ARTIFACT_STORE_NAME]
    )
    assert (
        stack.metadata_store
        == local_service.metadata_stores[LOCAL_METADATA_STORE_NAME]
    )


def test_register_stack_works_as_expected(tmp_path: str) -> None:
    """Test register_stack method registers a stack as expected."""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    local_service = repo.get_service()
    local_stack1 = local_service.get_stack("local_stack")
    local_service.register_stack("local_stack_2", local_stack1)
    local_stack2 = local_service.get_stack("local_stack_2")
    assert local_stack2 is not None
    assert local_stack2.orchestrator == local_stack1.orchestrator
    assert local_stack2.artifact_store == local_stack1.artifact_store
    assert local_stack2.metadata_store == local_stack1.metadata_store
    # TODO [MEDIUM]: rework this as a fixture to be run after the test completes
    local_service.delete_stack("local_stack_2")


def test_get_stack_raises_exception_when_key_does_not_exist(
    tmp_path: str,
) -> None:
    """Test get_stack raises exception when key does not exist."""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    local_service = repo.get_service()
    with pytest.raises(DoesNotExistException):
        local_service.get_stack("made_up_stack")


def test_register_stack_raises_exception_when_key_already_exists(
    tmp_path: str,
) -> None:
    """Test register_stack raises exception when key already exists."""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    local_service = repo.get_service()
    local_stack1 = local_service.get_stack("local_stack")
    with pytest.raises(AlreadyExistsException):
        local_service.register_stack("local_stack", local_stack1)


def test_delete_stack_deletes_the_stack(tmp_path: str) -> None:
    """Test delete_stack deletes the stack."""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    local_service = repo.get_service()
    local_stack1 = local_service.get_stack("local_stack")
    local_service.register_stack("local_stack_2", local_stack1)
    local_stack2 = local_service.get_stack("local_stack_2")
    assert local_stack2 is not None
    local_service.delete_stack("local_stack_2")
    with pytest.raises(DoesNotExistException):
        local_service.get_stack("local_stack_2")


def test_get_artifact_store_returns_artifact_store(tmp_path: str) -> None:
    """Test get_artifact_store returns artifact store."""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    local_service = repo.get_service()
    artifact_store = local_service.get_artifact_store(LOCAL_ARTIFACT_STORE_NAME)
    assert artifact_store is not None
    assert isinstance(artifact_store, BaseArtifactStore)


def test_register_artifact_store_works_as_expected(tmp_path: str) -> None:
    """Test register_artifact_store method registers an artifact store as expected."""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    local_service = repo.get_service()
    artifact_store_dir = os.path.join(tmp_path, "test_store")
    local_artifact_store = LocalArtifactStore(path=artifact_store_dir)
    local_service.register_artifact_store(
        "local_artifact_store_2", local_artifact_store
    )
    assert (
        local_service.get_artifact_store("local_artifact_store_2") is not None
    )
    local_service.delete_artifact_store("local_artifact_store_2")


def test_register_artifact_store_with_existing_key_fails(tmp_path: str) -> None:
    """Test register_artifact_store with existing key fails."""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    local_service = repo.get_service()
    with pytest.raises(AlreadyExistsException):
        local_service.register_artifact_store(
            LOCAL_ARTIFACT_STORE_NAME,
            local_service.get_artifact_store(LOCAL_ARTIFACT_STORE_NAME),
        )


def test_delete_artifact_store_works(tmp_path: str) -> None:
    """Test delete_artifact_store works as expected."""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    local_service = repo.get_service()
    artifact_store_dir = os.path.join(tmp_path, "test_store")
    local_artifact_store = LocalArtifactStore(path=artifact_store_dir)
    local_service.register_artifact_store(
        "local_artifact_store_2", local_artifact_store
    )
    local_service.delete_artifact_store("local_artifact_store_2")
    with pytest.raises(DoesNotExistException):
        local_service.get_artifact_store("local_artifact_store_2")


def test_get_metadata_store_returns_metadata_store(tmp_path: str) -> None:
    """Test get_metadata_store returns metadata store."""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    local_service = repo.get_service()
    metadata_store = local_service.get_metadata_store(LOCAL_METADATA_STORE_NAME)
    assert metadata_store is not None
    assert isinstance(metadata_store, BaseMetadataStore)


def test_register_metadata_store_works_as_expected(tmp_path: str) -> None:
    """Test register_metadata_store method registers an metadata store as expected."""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    local_service = repo.get_service()
    artifact_store_dir = os.path.join(tmp_path, "test_store")
    metadata_file = os.path.join(artifact_store_dir, "metadata.db")
    metadata_store = SQLiteMetadataStore(uri=metadata_file)
    local_service.register_metadata_store(
        "local_metadata_store_2", metadata_store
    )
    assert (
        local_service.get_metadata_store("local_metadata_store_2") is not None
    )
    local_service.delete_metadata_store("local_metadata_store_2")


def test_register_metadata_store_with_existing_key_fails(tmp_path: str) -> None:
    """Test register_metadata_store with existing key fails."""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    local_service = repo.get_service()
    with pytest.raises(AlreadyExistsException):
        local_service.register_metadata_store(
            LOCAL_METADATA_STORE_NAME,
            local_service.get_metadata_store(LOCAL_METADATA_STORE_NAME),
        )


def test_delete_metadata_store_works(tmp_path: str) -> None:
    """Test delete_metadata_store works as expected"""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    local_service = repo.get_service()
    artifact_store_dir = os.path.join(tmp_path, "test_store")
    metadata_file = os.path.join(artifact_store_dir, "metadata.db")
    metadata_store = SQLiteMetadataStore(uri=metadata_file)
    local_service.register_metadata_store(
        "local_metadata_store_2", metadata_store
    )
    local_service.delete_metadata_store("local_metadata_store_2")
    with pytest.raises(DoesNotExistException):
        local_service.get_metadata_store("local_metadata_store_2")


def test_get_orchestrator_returns_orchestrator(tmp_path: str) -> None:
    """Test get_orchestrator returns orchestrator"""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    local_service = repo.get_service()
    orchestrator = local_service.get_orchestrator(LOCAL_ORCHESTRATOR_NAME)
    assert orchestrator is not None
    assert isinstance(orchestrator, BaseOrchestrator)


def test_register_orchestrator_works_as_expected(tmp_path: str) -> None:
    """Test register_orchestrator method registers an orchestrator as expected."""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    local_service = repo.get_service()
    orchestrator = LocalOrchestrator()
    local_service.register_orchestrator("local_orchestrator_2", orchestrator)
    assert local_service.get_orchestrator("local_orchestrator_2") is not None
    local_service.delete_orchestrator("local_orchestrator_2")


def test_register_orchestrator_with_existing_key_fails(tmp_path: str) -> None:
    """Test register_orchestrator with existing key fails."""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    local_service = repo.get_service()
    with pytest.raises(AlreadyExistsException):
        local_service.register_orchestrator(
            LOCAL_ORCHESTRATOR_NAME,
            local_service.get_orchestrator(LOCAL_ORCHESTRATOR_NAME),
        )


def test_delete_orchestrator_works(tmp_path: str) -> None:
    """Test delete_orchestrator works as expected."""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    local_service = repo.get_service()
    orchestrator = LocalOrchestrator()
    local_service.register_orchestrator("local_orchestrator_2", orchestrator)
    local_service.delete_orchestrator("local_orchestrator_2")
    with pytest.raises(DoesNotExistException):
        local_service.get_orchestrator("local_orchestrator_2")


# TODO [LOW]: remove this legacy test code if we don't need it anymore
# def test_service_crud(tmp_path):
#     """Test basic service crud."""
#     # TODO [LOW]: Need to improve this logic, potentially with
#     #  physically checking the FS us `path_utils`.
#     ls = LocalService()
#     METADATA_KEY = "metadata_test_local"
#     ARTIFACT_KEY = "artifact_test_local"
#     STACK_KEY = "stack_test_local"
#     ORCHESTRATOR_KEY = "orchestrator_test_local"
#     local_artifact_store = LocalArtifactStore(
#         path=str(tmp_path / "local_store")
#     )
#     local_metadata_store = SQLiteMetadataStore(
#         uri=str(tmp_path / "local_store" / "metadata.db")
#     )
#     local_stack = BaseStack(
#         metadata_store_name=METADATA_KEY,
#         artifact_store_name=ARTIFACT_KEY,
#         orchestrator_name=ORCHESTRATOR_KEY,
#     )

#     ls.register_artifact_store(ARTIFACT_KEY, local_artifact_store)
#     ls.register_metadata_store(METADATA_KEY, local_metadata_store)
#     ls.register_stack(STACK_KEY, local_stack)

#     ls.delete_artifact_store(ARTIFACT_KEY)
#     ls.delete_metadata_store(METADATA_KEY)
#     ls.delete_stack(STACK_KEY)
