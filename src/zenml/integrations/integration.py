#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Base and meta classes for ZenML integrations."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, cast

from packaging.requirements import Requirement

from zenml.integrations.registry import integration_registry
from zenml.logger import get_logger
from zenml.stack.flavor import Flavor
from zenml.utils.package_utils import get_dependencies, requirement_installed

if TYPE_CHECKING:
    from zenml.plugins.base_plugin_flavor import BasePluginFlavor


logger = get_logger(__name__)


class IntegrationMeta(type):
    """Metaclass responsible for registering different Integration subclasses."""

    def __new__(
        mcs, name: str, bases: Tuple[Type[Any], ...], dct: Dict[str, Any]
    ) -> "IntegrationMeta":
        """Hook into creation of an Integration class.

        Args:
            name: The name of the class being created.
            bases: The base classes of the class being created.
            dct: The dictionary of attributes of the class being created.

        Returns:
            The newly created class.
        """
        cls = cast(Type["Integration"], super().__new__(mcs, name, bases, dct))
        if name != "Integration":
            integration_registry.register_integration(cls.NAME, cls)
        return cls


class Integration(metaclass=IntegrationMeta):
    """Base class for integration in ZenML."""

    NAME = "base_integration"

    REQUIREMENTS: List[str] = []
    APT_PACKAGES: List[str] = []
    REQUIREMENTS_IGNORED_ON_UNINSTALL: List[str] = []

    @classmethod
    def check_installation(cls) -> bool:
        """Method to check whether the required packages are installed.

        Returns:
            True if all required packages are installed, False otherwise.
        """
        for requirement in cls.get_requirements():
            parsed_requirement = Requirement(requirement)

            if not requirement_installed(parsed_requirement):
                logger.debug(
                    "Requirement '%s' for integration '%s' is not installed "
                    "or installed with the wrong version.",
                    requirement,
                    cls.NAME,
                )
                return False

            dependencies = get_dependencies(parsed_requirement)

            for dependency in dependencies:
                if not requirement_installed(dependency):
                    logger.debug(
                        "Requirement '%s' for integration '%s' is not "
                        "installed or installed with the wrong version.",
                        dependency,
                        cls.NAME,
                    )
                    return False

        logger.debug(
            f"Integration '{cls.NAME}' is installed correctly with "
            f"requirements {cls.get_requirements()}."
        )
        return True

    @classmethod
    def get_requirements(
        cls,
        target_os: Optional[str] = None,
        python_version: Optional[str] = None,
    ) -> List[str]:
        """Method to get the requirements for the integration.

        Args:
            target_os: The target operating system to get the requirements for.
            python_version: The Python version to use for the requirements.

        Returns:
            A list of requirements.
        """
        return cls.REQUIREMENTS

    @classmethod
    def get_uninstall_requirements(
        cls, target_os: Optional[str] = None
    ) -> List[str]:
        """Method to get the uninstall requirements for the integration.

        Args:
            target_os: The target operating system to get the requirements for.

        Returns:
            A list of requirements.
        """
        ret = []
        for each in cls.get_requirements(target_os=target_os):
            is_ignored = False
            for ignored in cls.REQUIREMENTS_IGNORED_ON_UNINSTALL:
                if each.startswith(ignored):
                    is_ignored = True
                    break
            if not is_ignored:
                ret.append(each)
        return ret

    @classmethod
    def activate(cls) -> None:
        """Abstract method to activate the integration."""

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Abstract method to declare new stack component flavors.

        Returns:
            A list of new stack component flavors.
        """
        return []

    @classmethod
    def plugin_flavors(cls) -> List[Type["BasePluginFlavor"]]:
        """Abstract method to declare new plugin flavors.

        Returns:
            A list of new plugin flavors.
        """
        return []
