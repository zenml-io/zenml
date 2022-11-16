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
"""Base ZenML Flavor implementation."""

from abc import abstractmethod
from typing import Optional, Type, cast

from zenml.enums import StackComponentType
from zenml.models import FlavorRequestModel, FlavorResponseModel
from zenml.stack.stack_component import StackComponent, StackComponentConfig
from zenml.utils.source_utils import load_source_path_class, resolve_class


class Flavor:
    """Class for ZenML Flavors."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The flavor name.

        Returns:
            The flavor name.
        """

    @property
    @abstractmethod
    def type(self) -> StackComponentType:
        """The stack component type.

        Returns:
            The stack component type.
        """

    @property
    @abstractmethod
    def implementation_class(self) -> Type[StackComponent]:
        """Implementation class for this flavor.

        Returns:
            The implementation class for this flavor.
        """

    @property
    @abstractmethod
    def config_class(self) -> Type[StackComponentConfig]:
        """Returns `StackComponentConfig` config class.

        Returns:
            The config class.
        """

    @property
    def config_schema(self) -> str:
        """The config schema for a flavor.

        Returns:
            The config schema.
        """
        return self.config_class.schema_json()

    @classmethod
    def from_model(cls, flavor_model: FlavorResponseModel) -> "Flavor":
        """Loads a flavor from a model.

        Args:
            flavor_model: The model to load from.

        Returns:
            The loaded flavor.
        """
        flavor = load_source_path_class(flavor_model.source)()  # noqa
        return cast(Flavor, flavor)

    def to_model(self, integration: Optional[str] = None) -> FlavorRequestModel:
        """Converts a flavor to a model.

        Args:
            integration: The integration to use for the model.

        Returns:
            The model.
        """
        from zenml.client import Client

        client = Client()
        model = FlavorRequestModel(
            user=client.active_user.id,
            project=client.active_project.id,
            name=self.name,
            type=self.type,
            source=resolve_class(self.__class__),  # noqa
            config_schema=self.config_schema,
            integration=integration,
        )
        return model
