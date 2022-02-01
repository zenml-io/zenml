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

from zenml.enums import (
    ArtifactStoreFlavor,
    ContainerRegistryFlavor,
    MetadataStoreFlavor,
    OrchestratorFlavor,
    StackComponentType,
)
from zenml.integrations.registry import integration_registry
from zenml.stack.stack_component_class_registry import (
    StackComponentClassRegistry,
)


def test_registration_of_integration_stack_components():
    """Tests that activating the integrations registers all available stack
    components."""
    integration_registry.activate_integrations()

    for flavor in OrchestratorFlavor:
        assert StackComponentClassRegistry.get_class(
            component_type=StackComponentType.ORCHESTRATOR,
            component_flavor=flavor,
        )

    for flavor in MetadataStoreFlavor:
        assert StackComponentClassRegistry.get_class(
            component_type=StackComponentType.METADATA_STORE,
            component_flavor=flavor,
        )

    for flavor in ArtifactStoreFlavor:
        assert StackComponentClassRegistry.get_class(
            component_type=StackComponentType.ARTIFACT_STORE,
            component_flavor=flavor,
        )

    for flavor in ContainerRegistryFlavor:
        assert StackComponentClassRegistry.get_class(
            component_type=StackComponentType.CONTAINER_REGISTRY,
            component_flavor=flavor,
        )
