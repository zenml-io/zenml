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
import shutil
from typing import Any, Dict, List, Tuple, Type, cast

import pkg_resources

from zenml.integrations.registry import integration_registry
from zenml.logger import get_logger
from zenml.zen_stores.models import FlavorWrapper

logger = get_logger(__name__)


class IntegrationMeta(type):
    """Metaclass responsible for registering different Integration
    subclasses"""

    def __new__(
        mcs, name: str, bases: Tuple[Type[Any], ...], dct: Dict[str, Any]
    ) -> "IntegrationMeta":
        """Hook into creation of an Integration class."""
        cls = cast(Type["Integration"], super().__new__(mcs, name, bases, dct))
        if name != "Integration":
            integration_registry.register_integration(cls.NAME, cls)
        return cls


class Integration(metaclass=IntegrationMeta):
    """Base class for integration in ZenML"""

    NAME = "base_integration"

    REQUIREMENTS: List[str] = []

    SYSTEM_REQUIREMENTS: Dict[str, str] = {}

    @classmethod
    def check_installation(cls) -> bool:
        """Method to check whether the required packages are installed"""
        try:
            for requirement, command in cls.SYSTEM_REQUIREMENTS.items():
                result = shutil.which(command)

                if result is None:
                    logger.debug(
                        "Unable to find the required packages for %s on your "
                        "system. Please install the packages on your system "
                        "and try again.",
                        requirement,
                    )
                    return False

            for r in cls.REQUIREMENTS:
                pkg_resources.get_distribution(r)
            logger.debug(
                f"Integration {cls.NAME} is installed correctly with "
                f"requirements {cls.REQUIREMENTS}."
            )
            return True
        except pkg_resources.DistributionNotFound as e:
            logger.debug(
                f"Unable to find required package '{e.req}' for "
                f"integration {cls.NAME}."
            )
            return False
        except pkg_resources.VersionConflict as e:
            logger.debug(
                f"VersionConflict error when loading installation {cls.NAME}: "
                f"{str(e)}"
            )
            return False

    @classmethod
    def activate(cls) -> None:
        """Abstract method to activate the integration."""

    @classmethod
    def flavors(cls) -> List[FlavorWrapper]:
        """Abstract method to declare new stack component flavors."""
