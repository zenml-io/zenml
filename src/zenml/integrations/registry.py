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

from typing import TYPE_CHECKING, Dict, Type, Union

from zenml.exceptions import IntegrationError
from zenml.logger import get_logger
from zenml.utils.source_utils import LazyLoader

if TYPE_CHECKING:
    from zenml.integrations.integration import Integration

logger = get_logger(__name__)


class IntegrationRegistry(object):
    """Registry to keep track of ZenML Integrations"""

    def __init__(self) -> None:
        self._integrations: Dict[
            str, Union[Type["Integration"], LazyLoader]
        ] = {}

    @property
    def integrations(self) -> Dict[str, Union[Type["Integration"], LazyLoader]]:
        """Method to get integrations dictionary.

        Returns:
            A dict of integration key to type of `Integration`.
        """
        self.activate()
        return self._integrations

    def register_integration(
        self, key: str, type_: Union[Type["Integration"], LazyLoader]
    ) -> None:
        """Method to register an integration with a given name"""
        self._integrations[key] = type_

    def activate(self) -> None:
        """Method to activate the integrations with are registered in the
        registry"""
        for name in list(self._integrations.keys()):
            try:
                integration = self._integrations.get(name)
                if isinstance(integration, LazyLoader):
                    integration.load()
                    integration = self._integrations.get(name)

                # TODO [ENG-185]: Figure out a better method to load integration
                #  from LazyLoader. Maybe we can use the LazyLoader not to
                #  load the module but the class itself. But we're not sure
                #  what kind of a follow up affect this might have on the
                #  actual thing.
                if integration is not None:
                    integration.activate()
                else:
                    raise ValueError(
                        f"Integration {name} is not present in "
                        f"self._integrations. Available integrations: "
                        f"{list(self._integrations.keys())}."
                    )

                logger.debug(f"Integration `{name}` is activated.")
            except (ModuleNotFoundError, IntegrationError) as e:
                self._integrations.pop(name)
                logger.debug(
                    f"Integration `{name}` could not be activated. {e}"
                )


integration_registry = IntegrationRegistry()
