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
from typing import TYPE_CHECKING, ClassVar, Type

from pydantic import BaseModel, Extra

from zenml.config.global_config import GlobalConfiguration
from zenml.enums import PluginSubType, PluginType

if TYPE_CHECKING:
    from zenml.zen_stores.base_zen_store import BaseZenStore


class BasePluginConfig(BaseModel, ABC):
    """Allows configuring of Event Source and Filter configuration."""

    class Config:
        """Pydantic configuration class."""

        # public attributes are immutable
        allow_mutation = True
        # all attributes with leading underscore are private and therefore
        # are mutable and not included in serialization
        underscore_attrs_are_private = True
        # prevent extra attributes during model initialization
        extra = Extra.forbid


class BasePlugin(ABC):
    """Base Class for all Plugins."""

    @property
    def zen_store(self) -> "BaseZenStore":
        """Returns the `BasePluginConfig` config.

        Returns:
            The configuration.
        """
        return GlobalConfiguration().zen_store

    @property
    @abstractmethod
    def config_class(self) -> Type[BasePluginConfig]:
        """Returns the `BasePluginConfig` config.

        Returns:
            The configuration.
        """


class BasePluginFlavorResponse(BaseModel):
    """Base response for all Plugin Flavors."""

    flavor_name: str
    plugin_type: PluginType


class BasePluginFlavor(ABC):
    """Base Class for all PluginFlavors."""

    TYPE: ClassVar[PluginType]
    SUBTYPE: ClassVar[PluginSubType]
    FLAVOR: ClassVar[str]
    PLUGIN_CLASS: ClassVar[Type[BasePlugin]]

    @classmethod
    @abstractmethod
    def get_plugin_flavor_response_model(cls) -> BasePluginFlavorResponse:
        """Convert the Flavor into a Response Model."""
