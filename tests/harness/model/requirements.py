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
"""ZenML test requirements models."""

import logging
import platform
import shutil
from enum import Enum
from functools import partial
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple
from uuid import UUID

import pkg_resources
from pydantic import ConfigDict, Field

from tests.harness.model.base import BaseTestConfigModel
from tests.harness.model.secret import BaseTestSecretConfigModel
from zenml.client import Client
from zenml.enums import StackComponentType
from zenml.utils.pagination_utils import depaginate

if TYPE_CHECKING:
    from tests.harness.environment import TestEnvironment
    from tests.harness.harness import TestHarness
    from zenml.models import ComponentResponse


class OSType(str, Enum):
    """Enum for the different types of operating systems."""

    LINUX = "linux"
    MACOS = "macos"
    WINDOWS = "windows"


class StackRequirementConfiguration(BaseTestSecretConfigModel):
    """ZenML stack component configuration attributes."""

    model_config = ConfigDict(validate_assignment=True, extra="allow")


class StackRequirement(BaseTestConfigModel):
    """ZenML stack component descriptor."""

    name: str = ""
    description: str = ""
    type: StackComponentType
    flavor: Optional[str] = None
    configuration: Optional[StackRequirementConfiguration] = None
    containerized: bool = False
    external: Optional[bool] = None

    def compile(self, harness: "TestHarness") -> None:
        """Validates and compiles the configuration when part of a test harness.

        Checks that all secrets referenced in the store configuration are
        defined in the test harness.

        Args:
            harness: The test harness to validate against.
        """
        if self.configuration is not None:
            self.configuration.compile(harness)

    def find_stack_component(
        self,
        client: "Client",
        environment: Optional["TestEnvironment"] = None,
    ) -> Optional["ComponentResponse"]:
        """Find a stack component that meets these requirements.

        The current deployment (accessible through the passed client) is
        searched for all components that match the requirements criteria. If
        supplied, the environment is used to filter the components further
        based on the stack configurations mandated by the environment.

        Args:
            client: The ZenML client to be used.
            environment: Optional environment against which to check mandatory
                and tracked stack requirements.

        Returns:
            The stack component or None if no component was found.
        """
        components = depaginate(
            partial(
                client.list_stack_components,
                name=self.name or None,
                type=self.type,
                flavor=self.flavor,
            )
        )

        mandatory_components: List[UUID] = []
        optional_components: List[UUID] = []
        if environment is not None:
            if self.type in environment.mandatory_components:
                mandatory_components = [
                    c.id for c in environment.mandatory_components[self.type]
                ]
            if self.type in environment.optional_components:
                optional_components = [
                    c.id for c in environment.optional_components[self.type]
                ]

        def filter_components(component: "ComponentResponse") -> bool:
            if self.configuration:
                for key, value in self.configuration.model_dump().items():
                    if component.configuration.get(key) != value:
                        logging.debug(
                            f"{component.type.value} '{component.name}' does "
                            f"not match configuration"
                        )
                        return False

            # The component must be one of the components of the same type
            # managed or tracked by the environment. Exceptions are the default
            # components (default artifact store and orchestrator) that are
            # always available.
            if environment is not None:
                # If one or more mandatory components of the same type are
                # enforced, the component must be one of them.
                if len(mandatory_components) > 0:
                    if component.id not in mandatory_components:
                        logging.debug(
                            f"{component.type.value} '{component.name}' does "
                            f"not match mandatory components in the environment"
                        )
                        return False
                    else:
                        logging.debug(
                            f"{component.type.value} '{component.name}' is a "
                            f"mandatory match"
                        )
                        return True

                if (
                    self.type
                    in [
                        StackComponentType.ARTIFACT_STORE,
                        StackComponentType.ORCHESTRATOR,
                    ]
                    and component.name == "default"
                ):
                    return True

                if component.id not in optional_components:
                    logging.debug(
                        f"{component.type.value} '{component.name}' is not "
                        f"tracked by nor managed by the environment"
                    )
                    return False

            logging.debug(
                f"{component.type.value} '{component.name}' is a match"
            )

            return True

        # Filter components further by flavor, configuration and mandatory
        # requirements.
        components = list(filter(filter_components, components))

        if len(components) == 0:
            return None

        if len(components) > 1:
            logging.warning(
                f"found multiple {self.type.value} components that meet the "
                f"test requirements: {', '.join([c.name for c in components])}. "
                f"Using the first one: {components[0].name}"
            )

        return components[0]

    def check_requirements(
        self,
        client: "Client",
        environment: Optional["TestEnvironment"] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Check if the requirements are met.

        Args:
            client: The ZenML client to be used to check ZenML requirements.
            environment: Optional environment against which to check mandatory
                stack requirements.

        Returns:
            The true/false result and a message describing which requirements
            are not met.
        """
        component = self.find_stack_component(client, environment=environment)
        if component is not None:
            return True, None

        msg = f"missing {self.type.value}"
        if self.flavor is not None:
            msg += f" with flavor '{self.flavor}'"
        if self.configuration:
            msg += " with custom configuration"
        return (False, msg)

    def get_integration(self) -> Optional[str]:
        """Get the integration requirement implied by this stack requirement.

        Returns:
            The integration name, if one is implied by this stack requirement.

        Raises:
            RuntimeError: If the configured component flavor is not found in
                ZenML.
        """
        if self.flavor is None:
            return None

        client = Client()
        try:
            flavor = client.get_flavor_by_name_and_type(
                component_type=self.type, name=self.flavor
            )
        except KeyError:
            raise RuntimeError(
                f"cannot find {self.type.value} flavor '{self.flavor}'"
            )

        if flavor.integration == "built-in":
            return None

        return flavor.integration

    def register_component(self, client: "Client") -> "ComponentResponse":
        """Register a stack component described by these requirements.

        Args:
            client: The ZenML client to be used to provision components.

        Returns:
            The registered stack component.

        Raises:
            ValueError: If the requirements do not specify a flavor.
        """
        from zenml.utils.string_utils import random_str

        if self.flavor is None:
            raise ValueError(
                f"cannot register component of type '{self.type.value}' without "
                "specifying a flavor"
            )

        return client.create_stack_component(
            name=self.name or f"pytest-{random_str(6).lower()}",
            flavor=self.flavor,
            component_type=self.type,
            configuration=self.configuration.model_dump()
            if self.configuration
            else {},
        )


class TestRequirements(BaseTestConfigModel):
    """Test requirements descriptor."""

    name: str = ""
    description: str = ""
    integrations: List[str] = Field(default_factory=list)
    packages: List[str] = Field(default_factory=list)
    system_tools: List[str] = Field(default_factory=list)
    system_os: List[OSType] = Field(default_factory=list)
    stacks: List[StackRequirement] = Field(default_factory=list)
    capabilities: Dict[str, Optional[bool]] = Field(default_factory=dict)
    mandatory: Optional[bool] = None

    def compile(self, harness: "TestHarness") -> None:
        """Validates and compiles the configuration when part of a test harness.

        Args:
            harness: The test harness to validate against.
        """
        for stack in self.stacks:
            stack.compile(harness)

    def check_software_requirements(self) -> Tuple[bool, Optional[str]]:
        """Check if the software requirements are met.

        Returns:
            The true/false result and a message describing which requirements
            are not met.
        """
        from zenml.integrations.registry import integration_registry

        if self.system_os:
            this_os = platform.system().lower().replace("darwin", "macos")
            if this_os not in self.system_os:
                return False, f"unsupported operating system '{this_os}'"

        missing_system_tools = []
        for tool in self.system_tools:
            if not shutil.which(tool):
                missing_system_tools.append(tool)
        if missing_system_tools:
            return (
                False,
                f"missing system tools: {', '.join(set(missing_system_tools))}",
            )

        missing_integrations = []

        integrations = self.integrations.copy()

        for stack in self.stacks:
            integration = stack.get_integration()
            if integration is not None:
                integrations.append(integration)

        for integration in integrations:
            if not integration_registry.is_installed(integration):
                missing_integrations.append(integration)

        if missing_integrations:
            return (
                False,
                f"missing integrations: {', '.join(set(missing_integrations))}",
            )

        try:
            for p in self.packages:
                pkg_resources.get_distribution(p)
        except pkg_resources.DistributionNotFound as e:
            return False, f"missing package: {e}"

        return True, None

    def check_stack_requirements(
        self,
        client: "Client",
        environment: Optional["TestEnvironment"] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Check if the stack component requirements are met.

        Args:
            client: The ZenML client to be used to check ZenML requirements.
            environment: Optional environment against which to check mandatory
                stack requirements.

        Returns:
            The true/false result and a message describing which requirements
            are not met.
        """
        for stack_requirement in self.stacks:
            result, message = stack_requirement.check_requirements(
                client=client,
                environment=environment,
            )
            if not result:
                return result, message

        return True, None

    def check_capabilities(
        self,
        environment: "TestEnvironment",
    ) -> Tuple[bool, Optional[str]]:
        """Check if the capabilities are met.

        Args:
            environment: Environment providing the capabilities against which
                to run the check.

        Returns:
            The true/false result and a message describing which capabilities
            are not met.
        """
        env_capabilities = environment.config.capabilities
        for capability, value in self.capabilities.items():
            value = value or True
            env_value = env_capabilities.get(capability, False)
            if value != env_value:
                if value:
                    return (
                        False,
                        f"environment '{environment.config.name}' is missing "
                        f"capability '{capability}'",
                    )
                else:
                    return (
                        False,
                        f"environment '{environment.config.name}' has unwanted "
                        f"capability '{capability}'",
                    )

        return True, None

    def check_requirements(
        self,
        client: "Client",
        environment: Optional["TestEnvironment"] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Check if all requirements are met.

        Args:
            client: The ZenML client to be used to check ZenML requirements.
            environment: Optional environment against which to check mandatory
                requirements.

        Returns:
            The true/false result and a message describing which requirements
            are not met.
        """
        result, message = self.check_software_requirements()
        if not result:
            return result, message

        if environment:
            result, message = self.check_capabilities(environment=environment)
            if not result:
                return result, message

        return self.check_stack_requirements(
            client=client, environment=environment
        )
