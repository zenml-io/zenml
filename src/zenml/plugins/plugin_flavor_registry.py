#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Registry all event source configurations."""
from typing import TYPE_CHECKING, Dict, List, Optional, Type

from pydantic import BaseModel

from zenml.enums import PluginType
from zenml.integrations.registry import integration_registry
from zenml.logger import get_logger
from zenml.plugins.base_plugin_flavor import BasePlugin, BasePluginFlavor

logger = get_logger(__name__)
if TYPE_CHECKING:
    from zenml.zen_stores.base_zen_store import BaseZenStore


class RegistryEntry(BaseModel):
    """Registry Entry Class for the Plugin Registry."""

    flavor_class: Type["BasePluginFlavor"]
    plugin_instance: Optional[BasePlugin]

    class Config:
        """Pydantic configuration class."""

        arbitrary_types_allowed = True


class PluginFlavorRegistry:
    """Registry for plugin flavors."""

    def __init__(self) -> None:
        """Initialize the event flavor registry."""
        self.plugin_flavors: Dict[str, Dict[str, RegistryEntry]] = {}
        self.register_plugin_flavors()

    @property
    def available_flavors(self) -> List[str]:
        """Returns all available flavors."""
        return list(self.plugin_flavors.keys())

    def available_types_for_flavor(self, flavor_name) -> List[str]:
        """Returns all available types for a given flavor.

        Args:
            flavor_name: The name of the flavor

        Returns:
            A list of available plugin types for this flavor.


        Raises:
            KeyError: If the flavor has no registry entries.
        """
        return list(self.plugin_flavors[flavor_name].keys())

    def available_flavors_for_type(self, type_name: str) -> List[str]:
        """Returns all available flavors for a given type.

        Args:
            type_name: The type_name.

        Returns:
            A list of available plugin flavors for this type.
        """
        return [
            flavor
            for flavor, types in self.plugin_flavors.items()
            if type_name in types
        ]

    @property
    def _builtin_flavors(self) -> List[Type["BasePluginFlavor"]]:
        """A list of all default in-built flavors.

        Returns:
            A list of builtin flavors.
        """
        flavors = []
        return flavors

    @property
    def _integration_flavors(self) -> List[Type["BasePluginFlavor"]]:
        """A list of all integration event flavors.

        Returns:
            A list of integration flavors.
        """
        # TODO: Only load active integrations
        integrated_flavors = []
        for _, integration in integration_registry.integrations.items():
            for flavor in integration.plugin_flavors():
                integrated_flavors.append(flavor)

        return integrated_flavors

    def register_plugin_flavors(self) -> None:
        """Registers all flavors."""
        for flavor in self._builtin_flavors:
            self.register_plugin_flavor(flavor_class=flavor)
        for flavor in self._integration_flavors:
            self.register_plugin_flavor(flavor_class=flavor)

    def register_plugin_flavor(
        self, flavor_class: Type["BasePluginFlavor"]
    ) -> None:
        """Registers a new event_source.

        Args:
            flavor_class: The flavor to register
        """
        if flavor_class.FLAVOR not in self.plugin_flavors.keys():
            self.plugin_flavors[flavor_class.FLAVOR] = {}
        if (
            flavor_class.TYPE
            not in self.plugin_flavors[flavor_class.FLAVOR].keys()
        ):
            self.plugin_flavors[flavor_class.FLAVOR] = {
                flavor_class.TYPE: RegistryEntry(flavor_class=flavor_class)
            }
            logger.debug(
                f"Registered built in plugin {flavor_class.FLAVOR} for plugin type {flavor_class.TYPE} {flavor_class}"
            )
        else:
            logger.debug(
                f"Found existing type {flavor_class.TYPE} for Flavor {flavor_class.FLAVOR} already "
                f"registered. Skipping registration for {flavor_class}."
            )

    def get_flavor_class(
        self, name: str, _type: PluginType
    ) -> Type["BasePluginFlavor"]:
        """Get a single event_source based on the key.

        Args:
            name: Indicates the name of the plugin flavor.
            _type: The type of plugin.

        Returns:
            `BaseEventConfiguration` subclass that was registered for this key.
        """
        all_types_of_flavor = self.plugin_flavors.get(name, None)
        if all_types_of_flavor:
            registry_entry = all_types_of_flavor.get(_type, None)
            if registry_entry:
                return registry_entry.flavor_class

        raise KeyError(
            f"No flavor class found for flavor name {name} and type {_type}"
        )

    def get_plugin_implementation(
        self, name: str, _type: PluginType
    ) -> "BasePlugin":
        """Get a single event_source based on the key.

        Args:
            name: The name of the plugin flavor.
            _type: The type of plugin.

        Returns:
            `BaseEventConfiguration` subclass that was registered for this key.
        """
        all_types_of_flavor = self.plugin_flavors.get(name, None)
        if all_types_of_flavor:
            registry_entry = all_types_of_flavor.get(_type, None)
            if registry_entry:
                if registry_entry.plugin_instance:
                    return registry_entry.plugin_instance

        raise KeyError(
            f"No plugin instance found for flavor name {name} and type {_type}"
        )

    def initialize_plugins(self, zen_store: "BaseZenStore"):
        """Initializes an instance of the plugin class and stores it in the registry."""
        for flavor, types_dict in self.plugin_flavors.items():
            for type_, registry_entry in types_dict.items():
                # TODO: Only initialize if the integration is active
                registry_entry.plugin_instance = (
                    registry_entry.flavor_class.PLUGIN_CLASS(
                        zen_store=zen_store
                    )
                )
