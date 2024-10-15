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
"""ZenML Pro implementation of the feature gate."""

from typing import Any, Dict
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.config.server_config import ServerConfiguration
from zenml.exceptions import SubscriptionUpgradeRequiredError
from zenml.logger import get_logger
from zenml.zen_server.cloud_utils import cloud_connection
from zenml.zen_server.feature_gate.feature_gate_interface import (
    FeatureGateInterface,
)
from zenml.zen_server.rbac.models import ResourceType

logger = get_logger(__name__)

server_config = ServerConfiguration.get_server_config()

ORGANIZATION_ID = server_config.metadata.get("organization_id", "unknown")

USAGE_EVENT_ENDPOINT = "/usage-event"
ENTITLEMENT_ENDPOINT = f"/organizations/{ORGANIZATION_ID}/entitlement"


class RawUsageEvent(BaseModel):
    """Model for reporting raw usage of a feature.

    In case of consumables the UsageReport allows the Pricing Backend to
    increment the usage per time-frame by 1.
    """

    organization_id: str = Field(
        description="The organization that this usage can be attributed to.",
    )
    feature: ResourceType = Field(
        description="The feature whose usage is being reported.",
    )
    total: int = Field(
        description="The total amount of entities of this type."
    )
    metadata: Dict[str, Any] = Field(
        default={},
        description="Allows attaching additional metadata to events.",
    )


class ZenMLCloudFeatureGateInterface(FeatureGateInterface):
    """ZenML Cloud Feature Gate implementation."""

    def __init__(self) -> None:
        """Initialize the object."""
        self._connection = cloud_connection()

    def check_entitlement(self, resource: ResourceType) -> None:
        """Checks if a user is entitled to create a resource.

        Args:
            resource: The resource the user wants to create

        Raises:
            SubscriptionUpgradeRequiredError: in case a subscription limit is reached
        """
        try:
            response = self._connection.get(
                endpoint=ENTITLEMENT_ENDPOINT + "/" + resource, params=None
            )
        except SubscriptionUpgradeRequiredError:
            raise SubscriptionUpgradeRequiredError(
                f"Your subscription reached its `{resource}` limit. Please "
                f"upgrade your subscription or reach out to us."
            )

        if response.status_code != 200:
            logger.warning(
                "Unexpected response status code from entitlement "
                f"endpoint: {response.status_code}. Message: "
                f"{response.json()}"
            )

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
        data = RawUsageEvent(
            organization_id=ORGANIZATION_ID,
            feature=resource,
            total=1 if not is_decrement else -1,
            metadata={
                "tenant_id": str(server_config.external_server_id),
                "resource_id": str(resource_id),
            },
        ).model_dump()
        response = self._connection.post(
            endpoint=USAGE_EVENT_ENDPOINT, data=data
        )
        if response.status_code != 200:
            logger.error(
                "Usage report not accepted by upstream backend. "
                f"Status Code: {response.status_code}, Message: "
                f"{response.json()}."
            )
