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
from collections import defaultdict
from typing import DefaultDict, Dict

from zenml.enums import StackComponentType
from zenml.logger import get_logger
from zenml.zen_stores.models import FlavorWrapper

logger = get_logger(__name__)


class FlavorRegistry:
    """Registry for stack component flavors.

    The flavors defined by ZenML must be registered here.
    """

    def __init__(self) -> None:
        """Initialization of the flavors."""
        self._flavors: DefaultDict[
            StackComponentType, Dict[str, FlavorWrapper]
        ] = defaultdict(dict)

        self.register_default_flavors()
        self.register_integration_flavors()

    def register_default_flavors(self) -> None:
        """Registers the default built-in flavors."""
        from zenml.artifact_stores import LocalArtifactStore
        from zenml.container_registries import (
            AzureContainerRegistry,
            DefaultContainerRegistry,
            DockerHubContainerRegistry,
            GCPContainerRegistry,
            GitHubContainerRegistry,
            GitLabContainerRegistry,
        )
        from zenml.metadata_stores import (
            MySQLMetadataStore,
            SQLiteMetadataStore,
        )
        from zenml.orchestrators import LocalOrchestrator
        from zenml.secrets_managers import LocalSecretsManager

        default_flavors = [
            LocalOrchestrator,
            SQLiteMetadataStore,
            MySQLMetadataStore,
            LocalArtifactStore,
            DefaultContainerRegistry,
            AzureContainerRegistry,
            DockerHubContainerRegistry,
            GCPContainerRegistry,
            GitHubContainerRegistry,
            GitLabContainerRegistry,
            LocalSecretsManager,
        ]
        for flavor in default_flavors:
            self._register_flavor(
                FlavorWrapper(
                    name=flavor.FLAVOR,  # type: ignore[attr-defined]
                    type=flavor.TYPE,  # type: ignore[attr-defined]
                    source=flavor.__module__ + "." + flavor.__name__,
                    integration="built-in",
                )
            )

    def register_integration_flavors(self) -> None:
        """Registers the flavors implemented by integrations."""
        from zenml.integrations.registry import integration_registry

        for integration in integration_registry.integrations.values():
            integrated_flavors = integration.flavors()
            if integrated_flavors:
                for flavor in integrated_flavors:
                    self._register_flavor(flavor)

    def _register_flavor(
        self,
        flavor: FlavorWrapper,
    ) -> None:
        """Registers a stack component flavor."""
        flavors = self._flavors[flavor.type]

        if flavor.name in flavors:
            raise KeyError(
                f"There is already a {flavor.type} with the flavor "
                f"`{flavor.name}`. Please select another name for the flavor."
            )

        flavors[flavor.name] = flavor
        logger.debug(
            f"Registered flavor for '{flavor.name}' and type '{flavor.type}'.",
        )

    def get_flavors_by_type(
        self, component_type: StackComponentType
    ) -> Dict[str, FlavorWrapper]:
        """Return the list of flavors with given type."""
        return self._flavors[component_type]


# Create the instance of the registry
flavor_registry = FlavorRegistry()
