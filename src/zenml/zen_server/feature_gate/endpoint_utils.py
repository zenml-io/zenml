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
"""All endpoint utils for the feature gate implementations."""

from uuid import UUID

from zenml.zen_server.rbac.models import ResourceType
from zenml.zen_server.utils import feature_gate, server_config


def check_entitlement(resource_type: ResourceType) -> None:
    """Queries the feature gate to see if the operation falls within the tenants entitlements.

    Raises an exception if the user is not entitled to create an instance of the
    resource. Otherwise, simply returns.

    Args:
        resource_type: The type of resource to check for.
    """
    if not server_config().feature_gate_enabled:
        return
    return feature_gate().check_entitlement(resource=resource_type)


def report_usage(resource_type: ResourceType, resource_id: UUID) -> None:
    """Reports the creation/usage of a feature/resource.

    Args:
        resource_type: The type of resource to report a usage for
        resource_id: ID of the resource that was created.
    """
    if not server_config().feature_gate_enabled:
        return
    feature_gate().report_event(
        resource=resource_type, resource_id=resource_id
    )


def report_decrement(resource_type: ResourceType, resource_id: UUID) -> None:
    """Reports the deletion/deactivation of a feature/resource.

    Args:
        resource_type: The type of resource to report a decrement in count for.
        resource_id: ID of the resource that was deleted.
    """
    if not server_config().feature_gate_enabled:
        return
    feature_gate().report_event(
        resource=resource_type, resource_id=resource_id, is_decrement=True
    )
