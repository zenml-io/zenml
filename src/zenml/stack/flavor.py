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
import json
from abc import abstractmethod
from typing import Any, Dict, Optional, Type, cast

from zenml.enums import StackComponentType
from zenml.models import FlavorRequestModel, FlavorResponseModel
from zenml.stack.stack_component import StackComponent, StackComponentConfig
from zenml.utils.source_utils import load_source_path, resolve_class


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
    def docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return None

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A url to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return None

    @property
    def logo_url(self) -> Optional[str]:
        """A url to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return None

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
    def config_schema(self) -> Dict[str, Any]:
        """The config schema for a flavor.

        Returns:
            The config schema.
        """
        config_schema: Dict[str, Any] = json.loads(
            self.config_class.schema_json()
        )
        return config_schema

    @classmethod
    def from_model(cls, flavor_model: FlavorResponseModel) -> "Flavor":
        """Loads a flavor from a model.

        Args:
            flavor_model: The model to load from.

        Returns:
            The loaded flavor.
        """
        flavor = load_source_path(flavor_model.source)()  # noqa
        return cast(Flavor, flavor)

    def to_model(
        self,
        integration: Optional[str] = None,
        scoped_by_workspace: bool = True,
        is_custom: bool = True,
    ) -> FlavorRequestModel:
        """Converts a flavor to a model.

        Args:
            integration: The integration to use for the model.
            scoped_by_workspace: Whether this flavor should live in the scope
                of the active workspace
            is_custom: Whether the flavor is a custom flavor. Custom flavors
                are then scoped by user and workspace

        Returns:
            The model.
        """
        from zenml.client import Client

        client = Client()
        model = FlavorRequestModel(
            user=client.active_user.id if is_custom else None,
            workspace=client.active_workspace.id if is_custom else None,
            name=self.name,
            type=self.type,
            source=resolve_class(self.__class__),  # noqa
            config_schema=self.config_schema,
            integration=integration,
            logo_url=self.logo_url,
            docs_url=self.docs_url,
            sdk_docs_url=self.sdk_docs_url,
            is_custom=is_custom,
        )
        return model

    def generate_default_docs_url(self, component_name: str = "") -> str:
        """Generate the doc urls for all inbuilt and integration flavors.

        Note that this method is not going to be useful for custom flavors,
        which do not have any docs in the main zenml docs.

        Args:
            component_name: The name of the component for docs generation. Used
                for legacy documentation before ZenML v0.34.0.

        Returns:
            The complete url to the zenml documentation
        """
        from zenml import __version__

        component_type = self.type.plural.replace("_", "-")
        name = self.name.replace("_", "-")
        docs_component_name = component_name or name
        base = f"https://docs.zenml.io/v/{__version__}"
        return (
            f"{base}/component-gallery/{component_type}/{docs_component_name}"
        )

    def generate_default_sdk_docs_url(self) -> str:
        """Generate SDK docs url for a flavor.

        Returns:
            The complete url to the zenml SDK docs
        """
        from zenml import __version__

        base = f"https://apidocs.zenml.io/{__version__}"

        component_type = self.type.plural

        if "zenml.integrations" in self.__module__:
            # Get integration name out of module path which will look something
            #  like this "zenml.integrations.<integration>....
            integration = self.__module__.split(
                "zenml.integrations.", maxsplit=1
            )[1].split(".")[0]

            return (
                f"{base}/integration_code_docs"
                f"/integrations-{integration}/#{self.__module__}"
            )

        else:
            return (
                f"{base}/core_code_docs/core-{component_type}/"
                f"#{self.__module__}"
            )
