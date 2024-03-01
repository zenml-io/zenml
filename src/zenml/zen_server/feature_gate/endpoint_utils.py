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
from zenml.zen_server.rbac.models import ResourceType
from zenml.zen_server.utils import feature_gate


def check_entitlement(resource_type: ResourceType) -> bool:
    """Queries the feature gate to see if the operation falls within the tenants entitlements.

    Args:
        resource_type: The type of resource to check for.

    Returns:
        True if the tenant is entitled, False else.
    """
    return feature_gate().check_entitlement(resource=resource_type)


def report_usage(resource_type: ResourceType) -> None:
    """Reports the creation/usage of a feature/resource.

    Args:
        resource_type: The type of resource to report a usage for
    """
    feature_gate().report_event(resource=resource_type)


def report_decrement(resource_type: ResourceType) -> None:
    """Reports the deletion/deactivation of a feature/resource.

    Args:
        resource_type: The type of resource to report a decrement in count for.
    """
    feature_gate().report_event(
        resource=resource_type, is_decrement=True
    )
