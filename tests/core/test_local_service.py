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

from zenml.artifact_stores.local_artifact_store import LocalArtifactStore
from zenml.core.local_service import LocalService
from zenml.metadata.sqlite_metadata_wrapper import SQLiteMetadataStore
from zenml.stacks.base_stack import BaseStack


def test_service_crud():
    """Test basic service crud."""
    # TODO [LOW] [TEST]: Need to improve this logic, potentially with
    #  physically checking the FS us `path_utils`.

    ls = LocalService()
    METADATA_KEY = "metadata local"
    ARTIFACT_KEY = "artifact_local"
    STACK_KEY = "stack_local"
    ORCHESTRATOR_KEY = "orchestrator_local"
    local_artifact_store = LocalArtifactStore()
    local_metadata_store = SQLiteMetadataStore()
    local_stack = BaseStack(
        metadata_store_name=METADATA_KEY,
        artifact_store_name=ARTIFACT_KEY,
        orchestrator_name=ORCHESTRATOR_KEY,
    )

    ls.register_artifact_store(ARTIFACT_KEY, local_artifact_store)
    ls.register_metadata_store(METADATA_KEY, local_metadata_store)
    ls.register_stack(STACK_KEY, local_stack)

    assert ls.get_metadata_store(METADATA_KEY) == local_metadata_store
    assert ls.get_artifact_store(ARTIFACT_KEY) == local_artifact_store
    assert ls.get_stack(STACK_KEY) == local_stack

    ls.delete_artifact_store(ARTIFACT_KEY)
    ls.delete_metadata_store(METADATA_KEY)
    ls.delete_stack(STACK_KEY)

    ls.delete()
