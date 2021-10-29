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

from git.repo.base import Repo

from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
from zenml.core.repo import Repository
from zenml.metadata.base_metadata_store import BaseMetadataStore
from zenml.orchestrators.base_orchestrator import BaseOrchestrator


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
        local_service.metadata_stores["local_metadata_store"],
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
        local_service.artifact_stores["local_artifact_store"],
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
        local_service.orchestrators["local_orchestrator"],
        BaseOrchestrator,
    )


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
