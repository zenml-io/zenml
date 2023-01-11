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
"""Implementation of the ZenML flavor registry."""

from collections import defaultdict
from datetime import datetime
from typing import DefaultDict, Dict, List
from uuid import UUID

from zenml.client import Client
from zenml.enums import StackComponentType
from zenml.integrations.registry import integration_registry
from zenml.logger import get_logger
from zenml.models import FlavorRequestModel, FlavorResponseModel

logger = get_logger(__name__)


class FlavorRegistry:
    """Registry for stack component flavors.

    The flavors defined by ZenML must be registered here.
    """

    def __init__(self) -> None:
        """Initialization of the flavors."""
        self._flavors: DefaultDict[
            StackComponentType, Dict[str, FlavorResponseModel]
        ] = defaultdict(dict)

        self.register_default_flavors()
        self.register_integration_flavors()

    def register_default_flavors(self) -> None:
        """Registers the default built-in flavors."""
        from zenml.artifact_stores import LocalArtifactStoreFlavor
        from zenml.container_registries import (
            AzureContainerRegistryFlavor,
            DefaultContainerRegistryFlavor,
            DockerHubContainerRegistryFlavor,
            GCPContainerRegistryFlavor,
            GitHubContainerRegistryFlavor,
        )
        from zenml.orchestrators import (
            LocalDockerOrchestratorFlavor,
            LocalOrchestratorFlavor,
        )
        from zenml.secrets_managers import LocalSecretsManagerFlavor

        default_flavors = (
            LocalArtifactStoreFlavor,
            LocalOrchestratorFlavor,
            LocalDockerOrchestratorFlavor,
            DefaultContainerRegistryFlavor,
            AzureContainerRegistryFlavor,
            DockerHubContainerRegistryFlavor,
            GCPContainerRegistryFlavor,
            GitHubContainerRegistryFlavor,
            LocalSecretsManagerFlavor,
        )
        for flavor in default_flavors:
            flavor_instance = flavor()  # type: ignore[abstract]
            self._register_flavor(
                flavor_instance.to_model(integration="built-in")
            )

    def register_integration_flavors(self) -> None:
        """Registers the flavors implemented by integrations."""
        for name, integration in integration_registry.integrations.items():
            integrated_flavors = integration.flavors()
            if integrated_flavors:
                for flavor in integrated_flavors:
                    self._register_flavor(flavor().to_model(integration=name))

    def _register_flavor(
        self,
        flavor: FlavorRequestModel,
    ) -> None:
        """Registers a stack component flavor.

        Args:
            flavor: The flavor to register.

        Raises:
            KeyError: If the flavor is already registered.
        """
        flavors = self._flavors[flavor.type]

        if flavor.name in flavors:
            raise KeyError(
                f"There is already a {flavor.type} with the flavor "
                f"`{flavor.name}`. Please select another name for the flavor."
            )

        client = Client()

        flavor_response_model = FlavorResponseModel(
            name=flavor.name,
            type=flavor.type,
            config_schema=flavor.config_schema,
            source=flavor.source,
            integration=flavor.integration,
            # This is a small trick to convert the request to response
            id=UUID(int=0),
            user=client.active_user,
            project=client.active_project,
            created=datetime.utcnow(),
            updated=datetime.utcnow(),
        )

        flavors[flavor.name] = flavor_response_model
        logger.debug(
            f"Registered flavor for '{flavor.name}' and type '{flavor.type}'.",
        )

    @property
    def flavors(self) -> List[FlavorResponseModel]:
        """Returns all registered flavors.

        Returns:
            The list of all registered flavors.
        """
        flavors = list()
        for flavors_by_type in self._flavors.values():
            for flavor in flavors_by_type.values():
                flavors.append(flavor)
        return flavors

    def get_flavors_by_type(
        self, component_type: StackComponentType
    ) -> List[FlavorResponseModel]:
        """Return the list of flavors with given type.

        Args:
            component_type: The type of the stack component.

        Returns:
            The list of flavors with the given type.
        """
        return list(self._flavors[component_type].values())

    def get_flavor_by_name_and_type(
        self, name: str, component_type: StackComponentType
    ) -> FlavorResponseModel:
        """Gets the flavor for a given name and type.

        Args:
            name: The name of the flavor.
            component_type: The type of the stack component.

        Returns:
            The flavor with the given name and type.
        """
        return self._flavors[component_type][name]


# Create the instance of the registry
flavor_registry = FlavorRegistry()
