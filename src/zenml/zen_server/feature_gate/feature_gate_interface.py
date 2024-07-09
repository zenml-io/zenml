#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Definition of the feature gate interface."""

from abc import ABC, abstractmethod
from uuid import UUID

from zenml.zen_server.rbac.models import ResourceType


class FeatureGateInterface(ABC):
    """RBAC interface definition."""

    @abstractmethod
    def check_entitlement(self, resource: ResourceType) -> None:
        """Checks if a user is entitled to create a resource.

        Args:
            resource: The resource the user wants to create

        Raises:
            UpgradeRequiredError in case a subscription limit is reached
        """

    @abstractmethod
    def report_event(
        self,
        resource: ResourceType,
        resource_id: UUID,
        is_decrement: bool = False,
    ) -> None:
        """Reports the usage of a feature to the aggregator backend.

        Args:
            resource: The resource the user created
            resource_id: ID of the resource that was created/deleted.
            is_decrement: In case this event reports an actual decrement of usage
        """
