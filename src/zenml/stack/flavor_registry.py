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
"""Implementation of the ZenML flavor registry."""

from collections import defaultdict
from typing import DefaultDict, Dict, List, Type

from zenml.analytics.utils import analytics_disabler
from zenml.enums import StackComponentType
from zenml.integrations.registry import integration_registry
from zenml.logger import get_logger
from zenml.models import (
    FlavorFilter,
    FlavorResponse,
    FlavorUpdate,
)
from zenml.stack import Flavor
from zenml.zen_stores.base_zen_store import BaseZenStore

logger = get_logger(__name__)


class FlavorRegistry:
    """Registry for stack component flavors.

    The flavors defined by ZenML must be registered here.
    """

    def __init__(self) -> None:
        """Initialization of the flavors."""
        self._flavors: DefaultDict[
            StackComponentType, Dict[str, FlavorResponse]
        ] = defaultdict(dict)

    def register_flavors(self, store: BaseZenStore) -> None:
        """Register all flavors to the DB.

        Args:
            store: The instance of a store to use for persistence
        """
        self.register_builtin_flavors(store=store)
        self.register_integration_flavors(store=store)

    @property
    def builtin_flavors(self) -> List[Type[Flavor]]:
        """A list of all default in-built flavors.

        Returns:
            A list of builtin flavors.
        """
        from zenml.artifact_stores import LocalArtifactStoreFlavor
        from zenml.container_registries import (
            AzureContainerRegistryFlavor,
            DefaultContainerRegistryFlavor,
            DockerHubContainerRegistryFlavor,
            GCPContainerRegistryFlavor,
            GitHubContainerRegistryFlavor,
        )
        from zenml.image_builders import LocalImageBuilderFlavor
        from zenml.orchestrators import (
            LocalDockerOrchestratorFlavor,
            LocalOrchestratorFlavor,
        )

        flavors = [
            LocalArtifactStoreFlavor,
            LocalOrchestratorFlavor,
            LocalDockerOrchestratorFlavor,
            DefaultContainerRegistryFlavor,
            AzureContainerRegistryFlavor,
            DockerHubContainerRegistryFlavor,
            GCPContainerRegistryFlavor,
            GitHubContainerRegistryFlavor,
            LocalImageBuilderFlavor,
        ]
        return flavors

    @property
    def integration_flavors(self) -> List[Type[Flavor]]:
        """A list of all default integration flavors.

        Returns:
            A list of integration flavors.
        """
        integrated_flavors = []
        for _, integration in integration_registry.integrations.items():
            for flavor in integration.flavors():
                integrated_flavors.append(flavor)

        return integrated_flavors

    def register_builtin_flavors(self, store: BaseZenStore) -> None:
        """Registers the default built-in flavors.

        Args:
            store: The instance of the zen_store to use
        """
        with analytics_disabler():
            for flavor in self.builtin_flavors:
                flavor_request_model = flavor().to_model(
                    integration="built-in",
                    is_custom=False,
                )
                existing_flavor = store.list_flavors(
                    FlavorFilter(
                        name=flavor_request_model.name,
                        type=flavor_request_model.type,
                    )
                )

                if len(existing_flavor) == 0:
                    store.create_flavor(flavor_request_model)
                else:
                    flavor_update_model = FlavorUpdate.parse_obj(
                        flavor_request_model
                    )
                    store.update_flavor(
                        existing_flavor[0].id, flavor_update_model
                    )

    @staticmethod
    def register_integration_flavors(store: BaseZenStore) -> None:
        """Registers the flavors implemented by integrations.

        Args:
            store: The instance of the zen_store to use
        """
        with analytics_disabler():
            for name, integration in integration_registry.integrations.items():
                try:
                    integrated_flavors = integration.flavors()
                    for flavor in integrated_flavors:
                        flavor_request_model = flavor().to_model(
                            integration=name,
                            is_custom=False,
                        )
                        existing_flavor = store.list_flavors(
                            FlavorFilter(
                                name=flavor_request_model.name,
                                type=flavor_request_model.type,
                            )
                        )
                        if len(existing_flavor) == 0:
                            store.create_flavor(flavor_request_model)
                        else:
                            flavor_update_model = FlavorUpdate.parse_obj(
                                flavor_request_model
                            )
                            store.update_flavor(
                                existing_flavor[0].id, flavor_update_model
                            )
                except Exception as e:
                    logger.warning(
                        f"Integration {name} failed to register flavors. "
                        f"Error: {e}"
                    )
