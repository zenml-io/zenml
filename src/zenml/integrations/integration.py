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

import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, cast

import pkg_resources
from pkg_resources import Requirement

from zenml.integrations.registry import integration_registry
from zenml.logger import get_logger
from zenml.stack.flavor import Flavor
from zenml.utils.integration_utils import parse_requirement

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
    REQUIRED_ZENML_INTEGRATIONS: List[str] = []

    APT_PACKAGES: List[str] = []
    REQUIREMENTS_IGNORED_ON_UNINSTALL: List[str] = []

    @classmethod
    def check_installation(cls) -> bool:
        """Method to check whether the required packages are installed.

        Returns:
            True if all required packages are installed, False otherwise.
        """
        for r in cls.get_requirements():
            try:
                # First check if the base package is installed
                dist = pkg_resources.get_distribution(r)

                # Next, check if the dependencies (including extras) are
                # installed
                deps: List[Requirement] = []

                _, extras = parse_requirement(r)
                if extras:
                    extra_list = extras[1:-1].split(",")
                    for extra in extra_list:
                        try:
                            requirements = dist.requires(extras=[extra])  # type: ignore[arg-type]
                        except pkg_resources.UnknownExtra as e:
                            logger.debug(f"Unknown extra: {str(e)}")
                            return False
                        deps.extend(requirements)
                else:
                    deps = dist.requires()

                for ri in deps:
                    try:
                        # Remove the "extra == ..." part from the requirement string
                        cleaned_req = re.sub(
                            r"; extra == \"\w+\"", "", str(ri)
                        )
                        pkg_resources.get_distribution(cleaned_req)
                    except pkg_resources.DistributionNotFound as e:
                        logger.debug(
                            f"Unable to find required dependency "
                            f"'{e.req}' for requirement '{r}' "
                            f"necessary for integration '{cls.NAME}'."
                        )
                        return False
                    except pkg_resources.VersionConflict as e:
                        logger.debug(
                            f"Package version '{e.dist}' does not match "
                            f"version '{e.req}' required by '{r}' "
                            f"necessary for integration '{cls.NAME}'."
                        )
                        return False

            except pkg_resources.DistributionNotFound as e:
                logger.debug(
                    f"Unable to find required package '{e.req}' for "
                    f"integration {cls.NAME}."
                )
                return False
            except pkg_resources.VersionConflict as e:
                logger.debug(
                    f"Package version '{e.dist}' does not match version "
                    f"'{e.req}' necessary for integration {cls.NAME}."
                )
                return False

        logger.debug(
            f"Integration {cls.NAME} is installed correctly with "
            f"requirements {cls.get_requirements()}."
        )
        return True

    @classmethod
    def get_requirements(cls, target_os: Optional[str] = None) -> List[str]:
        """Method to get the requirements for the integration.

        Args:
            target_os: The target operating system to get the requirements for.

        Returns:
            A list of requirements.
        """
        from zenml.integrations.registry import integration_registry

        reqs: List[str] = []

        for required_integration_name in cls.REQUIRED_ZENML_INTEGRATIONS:
            reqs.extend(
                integration_registry.select_integration_requirements(
                    integration_name=required_integration_name,
                    target_os=target_os,
                )
            )

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
