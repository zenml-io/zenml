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
from typing import DefaultDict, Dict, List

from zenml.enums import StackComponentType
from zenml.logger import get_logger
from zenml.zen_stores.models import FlavorWrapper

logger = get_logger(__name__)


class FlavorRegistry:
    """Registry for stack component flavor.

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
        from zenml.container_registries import BaseContainerRegistry
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
            BaseContainerRegistry,
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

    def get_flavor(
        self,
        component_type: StackComponentType,
        name: str,
    ) -> FlavorWrapper:
        """Returns the flavor wrapper for the given type and name.

        Args:
            component_type: The type of the component class to return.
            name: The flavor of the component class to return.
        Raises:
            KeyError: If no component class is registered for the given type
                and flavor.
        """

        available_flavors = self._flavors[component_type]
        try:
            return available_flavors[name]
        except KeyError:
            raise KeyError(
                f"No flavor with the name {name} found for type "
                f"{component_type}. Registered flavors for this "
                f"type: {set(available_flavors)}. If your stack "
                f"component class is part of a ZenML integration, make "
                f"sure the corresponding integration is installed by "
                f"running `zenml integration install INTEGRATION_NAME`."
            ) from None

    def get_flavors_by_type(
        self, component_type: StackComponentType
    ) -> Dict[str, FlavorWrapper]:
        """Return the list of flavors with given type."""
        return self._flavors[component_type]

    def get_flavors_by_type_and_name(
        self, name: str, component_type: StackComponentType
    ) -> FlavorWrapper:
        """Returns the flavor with the given name and type."""
        try:
            return self._flavors[component_type][name]
        except KeyError:
            raise KeyError(
                f"There is no default or integrated flavor '{name}' for the "
                f"type '{component_type}' within the registry."
            )

    def list_flavors(self) -> List[FlavorWrapper]:
        """Returns a list of all FlavorWrappers."""
        return [
            self._flavors[t][f] for t in self._flavors for f in self._flavors[t]
        ]


# Create the instance of the registry
flavor_registry = FlavorRegistry()
