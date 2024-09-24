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
"""Base implementation for all Plugin Flavors."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, Type

from pydantic import BaseModel, ConfigDict

from zenml.config.global_config import GlobalConfiguration
from zenml.enums import PluginSubType, PluginType
from zenml.models import BasePluginFlavorResponse

if TYPE_CHECKING:
    from zenml.zen_stores.base_zen_store import BaseZenStore


class BasePluginConfig(BaseModel, ABC):
    """Allows configuring of Event Source and Filter configuration."""

    model_config = ConfigDict(
        # public attributes are mutable
        frozen=False,
        # ignore extra attributes during model initialization
        extra="ignore",
    )


class BasePlugin(ABC):
    """Base Class for all Plugins."""

    @property
    def zen_store(self) -> "BaseZenStore":
        """Returns the active zen store.

        Returns:
            The active zen store.
        """
        return GlobalConfiguration().zen_store

    @property
    @abstractmethod
    def config_class(self) -> Type[BasePluginConfig]:
        """Returns the `BasePluginConfig` config.

        Returns:
            The configuration.
        """

    @property
    @abstractmethod
    def flavor_class(self) -> "Type[BasePluginFlavor]":
        """Returns the flavor class of the plugin.

        Returns:
            The flavor class of the plugin.
        """


class BasePluginFlavor(ABC):
    """Base Class for all PluginFlavors."""

    TYPE: ClassVar[PluginType]
    SUBTYPE: ClassVar[PluginSubType]
    FLAVOR: ClassVar[str]
    PLUGIN_CLASS: ClassVar[Type[BasePlugin]]

    @classmethod
    @abstractmethod
    def get_flavor_response_model(
        cls, hydrate: bool
    ) -> BasePluginFlavorResponse[Any, Any, Any]:
        """Convert the Flavor into a Response Model.

        Args:
            hydrate: Whether the model should be hydrated.

        Returns:
            The flavor response model.
        """
