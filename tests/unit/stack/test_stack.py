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

import pytest

from zenml.artifact_stores import LocalArtifactStore
from zenml.container_registries import BaseContainerRegistry
from zenml.enums import StackComponentType
from zenml.io.utils import get_global_config_directory
from zenml.metadata_stores import SQLiteMetadataStore
from zenml.orchestrators import LocalOrchestrator
from zenml.stack import Stack


def test_default_local_stack():
    """Tests that the default_local_stack method returns a stack with local
    components."""
    stack = Stack.default_local_stack()

    assert isinstance(stack.orchestrator, LocalOrchestrator)
    assert isinstance(stack.metadata_store, SQLiteMetadataStore)
    assert isinstance(stack.artifact_store, LocalArtifactStore)
    assert stack.container_registry is None

    expected_artifact_store_path = os.path.join(
        get_global_config_directory(),
        "local_stores",
        str(stack.artifact_store.uuid),
    )
    expected_metadata_store_uri = os.path.join(
        expected_artifact_store_path, "metadata.db"
    )

    assert stack.artifact_store.path == expected_artifact_store_path
    assert stack.metadata_store.uri == expected_metadata_store_uri


def test_initializing_a_stack_from_components():
    """Tests that a stack can be initialized from a dict of components."""
    orchestrator = LocalOrchestrator(name="")
    metadata_store = SQLiteMetadataStore(name="", uri="")
    artifact_store = LocalArtifactStore(name="", path="")

    components = {
        StackComponentType.ORCHESTRATOR: orchestrator,
        StackComponentType.METADATA_STORE: metadata_store,
        StackComponentType.ARTIFACT_STORE: artifact_store,
    }

    stack = Stack.from_components(name="", components=components)

    assert stack.orchestrator is orchestrator
    assert stack.metadata_store is metadata_store
    assert stack.artifact_store is artifact_store
    assert stack.container_registry is None

    # check that it also works with optional container registry
    container_registry = BaseContainerRegistry(name="", uri="")
    components[StackComponentType.CONTAINER_REGISTRY] = container_registry

    stack = Stack.from_components(name="", components=components)
    assert stack.container_registry is container_registry


def test_initializing_a_stack_with_missing_components():
    """Tests that initializing a stack with missing components fails."""
    with pytest.raises(TypeError):
        Stack.from_components(name="", components={})


def test_initializing_a_stack_with_wrong_components():
    """Tests that initializing a stack with wrong component classes fails."""
    orchestrator = LocalOrchestrator(name="")

    # orchestrators for all component types
    components = {
        StackComponentType.ORCHESTRATOR: orchestrator,
        StackComponentType.METADATA_STORE: orchestrator,
        StackComponentType.ARTIFACT_STORE: orchestrator,
    }

    with pytest.raises(TypeError):
        Stack.from_components(name="", components=components)


def test_stack_validates_when_initialized(mocker):
    """Tests that a stack is validated when it's initialized."""
    mocker.patch.object(Stack, "validate")
    Stack.default_local_stack()
    Stack.validate.assert_called_once()


def test_stack_runtime_options_combines_runtime_options_of_components():
    """"""


def test_stack_requirements():
    """"""


def test_stack_validation():
    """"""


def test_stack_deployment():
    """"""
