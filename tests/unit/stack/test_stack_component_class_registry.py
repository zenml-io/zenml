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
from zenml.enums import StackComponentType
from zenml.integrations.registry import integration_registry
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
            component_flavor="local",
        )
        is LocalOrchestrator
    )
    assert (
        StackComponentClassRegistry.get_class(
            component_type=StackComponentType.METADATA_STORE,
            component_flavor="sqlite",
        )
        is SQLiteMetadataStore
    )
    assert (
        StackComponentClassRegistry.get_class(
            component_type=StackComponentType.ARTIFACT_STORE,
            component_flavor="local",
        )
        is LocalArtifactStore
    )
    assert (
        StackComponentClassRegistry.get_class(
            component_type=StackComponentType.CONTAINER_REGISTRY,
            component_flavor="default",
        )
        is BaseContainerRegistry
    )


def test_stack_component_class_registration(stub_component):
    """Tests that stack component classes are available after registration."""

    with pytest.raises(KeyError):
        StackComponentClassRegistry.get_class(
            component_type=stub_component.TYPE,
            component_flavor=stub_component.FLAVOR,
        )

    StackComponentClassRegistry.register_class(
        component_class=type(stub_component),
    )

    with does_not_raise():
        returned_class = StackComponentClassRegistry.get_class(
            component_type=stub_component.TYPE,
            component_flavor=stub_component.FLAVOR,
        )

    assert returned_class is type(stub_component)
    # remove the registered component class so other tests aren't affected
    StackComponentClassRegistry.component_classes[stub_component.TYPE].pop(
        stub_component.FLAVOR
    )


def test_stack_component_class_registration_decorator(stub_component):
    """Tests that stack component classes can be registered using the
    decorator."""
    register_stack_component_class(type(stub_component))

    with does_not_raise():
        StackComponentClassRegistry.get_class(
            component_type=stub_component.TYPE,
            component_flavor=stub_component.FLAVOR,
        )

    # remove the registered component class so other tests aren't affected
    StackComponentClassRegistry.component_classes[stub_component.TYPE].pop(
        stub_component.FLAVOR
    )


def test_stack_component_class_registry_activates_integrations_if_necessary(
    stub_component, mocker
):
    """Tests that the stack component class registry tries activating
    integrations as a fallback if no registered class can be found."""

    def _activate_integrations():
        StackComponentClassRegistry.register_class(
            component_class=type(stub_component),
        )

    mocker.patch.object(
        integration_registry,
        "activate_integrations",
        side_effect=_activate_integrations,
    )

    # getting the local orchestrator should not require activating integrations
    StackComponentClassRegistry.get_class(
        component_type=StackComponentType.ORCHESTRATOR,
        component_flavor="local",
    )
    integration_registry.activate_integrations.assert_not_called()

    # trying to get an unregistered component should activate the integrations
    stub_component_class = StackComponentClassRegistry.get_class(
        component_type=stub_component.TYPE,
        component_flavor=stub_component.FLAVOR,
    )
    assert stub_component_class is type(stub_component)
    integration_registry.activate_integrations.assert_called_once()

    # remove the registered component class so other tests aren't affected
    StackComponentClassRegistry.component_classes[stub_component.TYPE].pop(
        stub_component.FLAVOR
    )
