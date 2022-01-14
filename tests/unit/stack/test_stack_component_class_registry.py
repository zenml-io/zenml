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
from contextlib import ExitStack as does_not_raise

import pytest

from zenml.artifact_stores import LocalArtifactStore
from zenml.container_registries import BaseContainerRegistry
from zenml.enums import (
    ArtifactStoreFlavor,
    ContainerRegistryFlavor,
    MetadataStoreFlavor,
    OrchestratorFlavor,
    StackComponentType,
)
from zenml.metadata_stores import SQLiteMetadataStore
from zenml.orchestrators import LocalOrchestrator
from zenml.stack.stack_component_class_registry import (
    StackComponentClassRegistry,
    register_stack_component_class,
)


def test_stack_component_class_registry_has_local_classes_registered():
    """Tests that the local stack component classes are already registered
    when importing the StackComponentClassRegistry."""
    assert (
        StackComponentClassRegistry.get_class(
            component_type=StackComponentType.ORCHESTRATOR,
            component_flavor=OrchestratorFlavor.LOCAL,
        )
        is LocalOrchestrator
    )
    assert (
        StackComponentClassRegistry.get_class(
            component_type=StackComponentType.METADATA_STORE,
            component_flavor=MetadataStoreFlavor.SQLITE,
        )
        is SQLiteMetadataStore
    )
    assert (
        StackComponentClassRegistry.get_class(
            component_type=StackComponentType.ARTIFACT_STORE,
            component_flavor=ArtifactStoreFlavor.LOCAL,
        )
        is LocalArtifactStore
    )
    assert (
        StackComponentClassRegistry.get_class(
            component_type=StackComponentType.CONTAINER_REGISTRY,
            component_flavor=ContainerRegistryFlavor.DEFAULT,
        )
        is BaseContainerRegistry
    )


def test_stack_component_class_registration(stub_component):
    """Tests that stack component classes are available after registration."""

    with pytest.raises(KeyError):
        StackComponentClassRegistry.get_class(
            component_type=stub_component.type,
            component_flavor=stub_component.flavor,
        )

    StackComponentClassRegistry.register_class(
        component_type=stub_component.type,
        component_flavor=stub_component.flavor,
        component_class=type(stub_component),
    )

    with does_not_raise():
        returned_class = StackComponentClassRegistry.get_class(
            component_type=stub_component.type,
            component_flavor=stub_component.flavor,
        )

    assert returned_class is type(stub_component)
    # remove the registered component class so other tests aren't affected
    StackComponentClassRegistry.component_classes[stub_component.type].pop(
        stub_component.flavor.value
    )


def test_stack_component_class_registration_decorator(stub_component):
    """Tests that stack component classes can be registered using the
    decorator."""
    register_stack_component_class(
        component_type=stub_component.type,
        component_flavor=stub_component.flavor,
    )(type(stub_component))

    with does_not_raise():
        StackComponentClassRegistry.get_class(
            component_type=stub_component.type,
            component_flavor=stub_component.flavor,
        )

    # remove the registered component class so other tests aren't affected
    StackComponentClassRegistry.component_classes[stub_component.type].pop(
        stub_component.flavor.value
    )
