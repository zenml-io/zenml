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

import pytest
from git.repo.base import Repo

from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
from zenml.core.repo import Repository
from zenml.metadata.base_metadata_store import BaseMetadataStore
from zenml.orchestrators.base_orchestrator import BaseOrchestrator
from zenml.stacks.base_stack import BaseStack

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
    """Check get_stack returns a stack with expected properties."""
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


def test_register_stack_works_as_expected(tmp_path) -> None:
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
    # TODO: [Medium] rework this as a fixture to be run after the test completes
    local_service.delete_stack("local_stack_2")


def test_get_stack_raises_exception_when_key_does_not_exist(tmp_path) -> None:
    """Test get_stack raises exception when key does not exist."""
    Repo.init(tmp_path)
    repo = Repository(str(tmp_path))
    local_service = repo.get_service()
    with pytest.raises(Exception):
        local_service.get_stack("made_up_stack")


# def test_service_crud(tmp_path):
#     """Test basic service crud."""
#     # TODO [LOW] [TEST]: Need to improve this logic, potentially with
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
