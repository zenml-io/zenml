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
"""Registry for all plugins."""
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence, Type

from pydantic import BaseModel

from zenml.enums import PluginSubType, PluginType
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
        self.plugin_flavors: Dict[
            str, Dict[str, Dict[str, RegistryEntry]]
        ] = {}
        self.register_plugin_flavors()

    @property
    def available_flavors(self) -> List[str]:
        """Returns all available flavors."""
        return list(self.plugin_flavors.keys())

    def get_available_types_for_flavor(self, flavor_name) -> List[str]:
        """Returns all available types for a given flavor.

        Args:
            flavor_name: The name of the flavor

        Returns:
            A list of available plugin types for this flavor.

        Raises:
            KeyError: If the flavor has no registry entries.
        """
        return list(self.plugin_flavors[flavor_name].keys())

    def get_available_flavors_for_type(self, _type: str) -> List[str]:
        """Returns all available flavors for a given type.

        Args:
            _type: The type_name.

        Returns:
            A list of available plugin flavors for this type.
        """
        return [
            flavor
            for flavor, types in self.plugin_flavors.items()
            if _type in types
        ]

    def get_available_subtypes_for_flavor_and_type(
        self, flavor: str, _type: str
    ) -> List[str]:
        """Get a list of all subtypes for a specific flavor and type."""
        if (
            flavor in self.plugin_flavors
            and _type in self.plugin_flavors[flavor]
        ):
            return list(self.plugin_flavors[flavor][_type].keys())
        return []

    @property
    def _builtin_flavors(self) -> Sequence[Type["BasePluginFlavor"]]:
        """A list of all default in-built flavors.

        Returns:
            A list of builtin flavors.
        """
        from zenml.scheduler.scheduler_event_source_flavor import (
            SchedulerEventSourceFlavor,
        )

        flavors = [SchedulerEventSourceFlavor]
        return flavors

    @property
    def _integration_flavors(self) -> Sequence[Type["BasePluginFlavor"]]:
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

    def _get_registry_entry(
        self, flavor: str, _type: str, subtype: str
    ) -> RegistryEntry:
        """Get registry entry.

        Args:
            flavor: Flavor of the entry.
            _type: Type of the entry.
            subtype: Subtype of the entry.

        Returns:
            The registry entry.

        Raises:
            KeyError: In case no entry exists.
        """
        return self.plugin_flavors[flavor][_type][subtype]

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
        try:
            self._get_registry_entry(
                flavor=flavor_class.FLAVOR,
                _type=flavor_class.TYPE,
                subtype=flavor_class.SUBTYPE,
            )
        except KeyError:
            (
                self.plugin_flavors.setdefault(flavor_class.FLAVOR, {})
                .setdefault(flavor_class.TYPE, {})
                .setdefault(
                    flavor_class.SUBTYPE,
                    RegistryEntry(flavor_class=flavor_class),
                )
            )
            logger.debug(
                f"Registered built in plugin {flavor_class.FLAVOR} for plugin type {flavor_class.TYPE} and "
                f"subtype {flavor_class.SUBTYPE}: {flavor_class}"
            )
        else:
            logger.debug(
                f"Found existing type {flavor_class.TYPE} for Flavor {flavor_class.FLAVOR} already "
                f"registered. Skipping registration for {flavor_class}."
            )

    def get_flavor_class(
        self, flavor: str, _type: PluginType, subtype: PluginSubType
    ) -> Type["BasePluginFlavor"]:
        """Get a single event_source based on the key.

        Args:
            flavor: Indicates the name of the plugin flavor.
            _type: The type of plugin.
            subtype: The subtype of plugin.

        Returns:
            `BaseEventConfiguration` subclass that was registered for this key.
        """
        try:
            return self._get_registry_entry(
                flavor=flavor, _type=_type, subtype=subtype
            ).flavor_class
        except KeyError:
            raise KeyError(
                f"No flavor class found for flavor name {flavor} and type {_type} and subtype {subtype}."
            )

    def get_plugin(
        self, flavor: str, _type: PluginType, subtype: PluginSubType
    ) -> "BasePlugin":
        """Get the plugin based on the flavor, type and subtype.

        Args:
            flavor: The name of the plugin flavor.
            _type: The type of plugin.
            subtype: The subtype of plugin.

        Returns:
            Plugin instance associated with the flavor, type and subtype.
        """
        try:
            return self._get_registry_entry(
                flavor=flavor, _type=_type, subtype=subtype
            ).plugin_instance
        except KeyError:
            raise KeyError(
                f"No flavor class found for flavor name {flavor} and type "
                f"{_type} and subtype {subtype}."
            )

    def initialize_plugins(self, zen_store: "BaseZenStore"):
        """Initializes an instance of the plugin class and stores it in the registry."""
        for flavor, types_dict in self.plugin_flavors.items():
            for type_, subtype_dict in types_dict.items():
                for subtype, registry_entry in subtype_dict.items():
                    # TODO: Only initialize if the integration is active
                    registry_entry.plugin_instance = (
                        registry_entry.flavor_class.PLUGIN_CLASS()
                    )


plugin_flavor_registry = PluginFlavorRegistry()
