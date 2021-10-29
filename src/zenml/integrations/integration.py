#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
from typing import Any, Dict, Tuple, Type, cast

import pkg_resources

from zenml.exceptions import IntegrationError
from zenml.integrations.registry import integration_registry
from zenml.logger import get_logger

logger = get_logger(__name__)


class IntegrationMeta(type):
    def __new__(
            mcs, name: str, bases: Tuple[Type[Any], ...], dct: Dict[str, Any]
    ) -> "IntegrationMeta":
        cls = cast(Type["Integration"], super().__new__(mcs, name, bases, dct))
        if name != "Integration":
            integration_registry.register_integration(cls.NAME, cls)
        return cls


class Integration(metaclass=IntegrationMeta):
    NAME = "base_integration"

    REQUIREMENTS = []

    @classmethod
    def check_installation(cls):
        try:
            pkg_resources.require(cls.REQUIREMENTS)
        except pkg_resources.DistributionNotFound:
            raise IntegrationError("Required packages not fully installed.")
        except pkg_resources.VersionConflict:
            raise IntegrationError("Version conflicts in required packages.")

    @staticmethod
    def activate():
        """ """
