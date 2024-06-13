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
from typing import Any, Dict, Optional, Type, cast

from zenml.enums import StackComponentType
from zenml.models import (
    FlavorRequest,
    FlavorResponse,
    ServiceConnectorRequirements,
)
from zenml.models.v2.core.flavor import InternalFlavorRequest
from zenml.stack.stack_component import StackComponent, StackComponentConfig
from zenml.utils import source_utils
from zenml.utils.package_utils import is_latest_zenml_version


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
        return self.config_class.model_json_schema()

    @property
    def service_connector_requirements(
        self,
    ) -> Optional[ServiceConnectorRequirements]:
        """Service connector resource requirements for service connectors.

        Specifies resource requirements that are used to filter the available
        service connector types that are compatible with this flavor.

        Returns:
            Requirements for compatible service connectors, if a service
            connector is required for this flavor.
        """
        return None

    @classmethod
    def from_model(cls, flavor_model: FlavorResponse) -> "Flavor":
        """Loads a flavor from a model.

        Args:
            flavor_model: The model to load from.

        Returns:
            The loaded flavor.
        """
        flavor = source_utils.load(flavor_model.source)()
        return cast(Flavor, flavor)

    def to_model(
        self,
        integration: Optional[str] = None,
        is_custom: bool = True,
    ) -> FlavorRequest:
        """Converts a flavor to a model.

        Args:
            integration: The integration to use for the model.
            is_custom: Whether the flavor is a custom flavor. Custom flavors
                are then scoped by user and workspace

        Returns:
            The model.
        """
        from zenml.client import Client

        client = Client()
        connector_requirements = self.service_connector_requirements
        connector_type = (
            connector_requirements.connector_type
            if connector_requirements
            else None
        )
        resource_type = (
            connector_requirements.resource_type
            if connector_requirements
            else None
        )
        resource_id_attr = (
            connector_requirements.resource_id_attr
            if connector_requirements
            else None
        )
        model_class = FlavorRequest if is_custom else InternalFlavorRequest
        model = model_class(
            user=client.active_user.id if is_custom else None,
            workspace=client.active_workspace.id if is_custom else None,
            name=self.name,
            type=self.type,
            source=source_utils.resolve(self.__class__).import_path,
            config_schema=self.config_schema,
            connector_type=connector_type,
            connector_resource_type=resource_type,
            connector_resource_id_attr=resource_id_attr,
            integration=integration,
            logo_url=self.logo_url,
            docs_url=self.docs_url,
            sdk_docs_url=self.sdk_docs_url,
            is_custom=is_custom,
        )
        return model

    def generate_default_docs_url(self) -> str:
        """Generate the doc urls for all inbuilt and integration flavors.

        Note that this method is not going to be useful for custom flavors,
        which do not have any docs in the main zenml docs.

        Returns:
            The complete url to the zenml documentation
        """
        from zenml import __version__

        component_type = self.type.plural.replace("_", "-")
        name = self.name.replace("_", "-")

        try:
            is_latest = is_latest_zenml_version()
        except RuntimeError:
            # We assume in error cases that we are on the latest version
            is_latest = True

        if is_latest:
            base = "https://docs.zenml.io/"
        else:
            base = f"https://zenml-io.gitbook.io/zenml-legacy-documentation/v/{__version__}"
        return f"{base}/stack-components/{component_type}/{name}"

    def generate_default_sdk_docs_url(self) -> str:
        """Generate SDK docs url for a flavor.

        Returns:
            The complete url to the zenml SDK docs
        """
        from zenml import __version__

        base = f"https://sdkdocs.zenml.io/{__version__}"

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


def validate_flavor_source(
    source: str, component_type: StackComponentType
) -> Type["Flavor"]:
    """Import a StackComponent class from a given source and validate its type.

    Args:
        source: source path of the implementation
        component_type: the type of the stack component

    Returns:
        the imported class

    Raises:
        ValueError: If ZenML cannot find the given module path
        TypeError: If the given module path does not point to a subclass of a
            StackComponent which has the right component type.
    """
    from zenml.stack.stack_component import (
        StackComponent,
        StackComponentConfig,
    )
    from zenml.utils import source_utils

    try:
        flavor_class = source_utils.load(source)
    except (ValueError, AttributeError, ImportError) as e:
        raise ValueError(
            f"ZenML can not import the flavor class '{source}': {e}"
        )

    if not (
        isinstance(flavor_class, type) and issubclass(flavor_class, Flavor)
    ):
        raise TypeError(
            f"The source '{source}' does not point to a subclass of the ZenML"
            f"Flavor."
        )

    flavor = flavor_class()
    try:
        impl_class = flavor.implementation_class
    except (ModuleNotFoundError, ImportError, NotImplementedError) as e:
        raise ValueError(
            f"The implementation class defined within the "
            f"'{flavor_class.__name__}' can not be imported: {e}"
        )

    if not issubclass(impl_class, StackComponent):
        raise TypeError(
            f"The implementation class '{impl_class.__name__}' of a flavor "
            f"needs to be a subclass of the ZenML StackComponent."
        )

    if flavor.type != component_type:  # noqa
        raise TypeError(
            f"The source points to a {impl_class.type}, not a "  # noqa
            f"{component_type}."
        )

    try:
        conf_class = flavor.config_class
    except (ModuleNotFoundError, ImportError, NotImplementedError) as e:
        raise ValueError(
            f"The config class defined within the "
            f"'{flavor_class.__name__}' can not be imported: {e}"
        )

    if not issubclass(conf_class, StackComponentConfig):
        raise TypeError(
            f"The config class '{conf_class.__name__}' of a flavor "
            f"needs to be a subclass of the ZenML StackComponentConfig."
        )

    return flavor_class
