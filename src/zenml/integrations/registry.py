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

from typing import TYPE_CHECKING, Any, ClassVar, Dict, Type

from zenml.exceptions import IntegrationError
from zenml.logger import get_logger
from zenml.utils.source_utils import LazyLoader

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.integrations.integration import Integration


class IntegrationRegistry(object):
    """Registry to keep track of ZenML Integrations"""

    _integrations: ClassVar[Dict[Type[Any], Type["Integration"]]] = {}

    @property
    def integrations(self):
        """Method to get integrations dictionary"""
        self.activate()
        return self._integrations

    @classmethod
    def register_integration(
        cls, key: Type[Any], type_: Type["Integration"]
    ) -> None:
        """Method to register an integration with a given name"""
        cls._integrations[key] = type_

    @classmethod
    def activate(cls):
        """Method to activate the integrations with are registered in the
        registry"""
        for name in list(cls._integrations.keys()):
            try:
                integration = cls._integrations.get(name)
                if issubclass(type(integration), LazyLoader):
                    integration.load()
                    integration = cls._integrations.get(name)
                integration.activate()
                logger.info(f"Integration `{name}` is activated.")
            except (ModuleNotFoundError, IntegrationError) as e:
                cls._integrations.pop(name)
                logger.warning(
                    f"Integration `{name}` could not be activated. {e}"
                )


integration_registry = IntegrationRegistry()
