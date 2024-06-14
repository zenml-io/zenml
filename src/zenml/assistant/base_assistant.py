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
"""Base implementation of actions."""

from abc import ABC, abstractmethod
from typing import ClassVar, Type

from zenml.enums import PluginType
from zenml.logger import get_logger
from zenml.models.v2.core.assistant import AssistantRequest, AssistantResponse
from zenml.models.v2.core.assistant_flavor import (
    AssistantFlavorResponse,
    AssistantFlavorResponseBody,
)
from zenml.plugins.base_plugin_flavor import (
    BasePlugin,
    BasePluginConfig,
    BasePluginFlavor,
)

logger = get_logger(__name__)


# -------------------- Flavors ---------------------------------------------


class BaseAssistantFlavor(BasePluginFlavor, ABC):
    """Base Action Flavor to register Action Configurations."""

    TYPE: ClassVar[PluginType] = PluginType.ASSISTANT

    @classmethod
    def get_flavor_response_model(
        cls, hydrate: bool
    ) -> AssistantFlavorResponse:
        """Convert the Flavor into a Response Model.

        Args:
            hydrate: Whether the model should be hydrated.

        Returns:
            The response model.
        """
        metadata = None
        return AssistantFlavorResponse(
            body=AssistantFlavorResponseBody(),
            metadata=metadata,
            name=cls.FLAVOR,
            type=cls.TYPE,
            subtype=cls.SUBTYPE,
        )


# -------------------- Plugin -----------------------------------


class BaseAssistantHandler(BasePlugin, ABC):
    """Implementation for an assistant handler."""

    def __init__(self) -> None:
        """Assistant handler initialization."""
        super().__init__()

    @property
    def config_class(self) -> Type[BasePluginConfig]:
        """Assistants do not support a config."""
        pass

    @property
    @abstractmethod
    def flavor_class(self) -> Type[AssistantFlavorResponse]:
        """Returns the flavor class of the plugin.

        Returns:
            The flavor class of the plugin.
        """

    @abstractmethod
    def make_assistant_call(
        self, assistant_request: AssistantRequest
    ) -> AssistantResponse:
        """Make call to assistant backend.

        Args:
            assistant_request: Request to forward to the backend.

        Returns:
            The response from the backend.
        """
