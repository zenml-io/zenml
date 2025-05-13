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

from zenml.zen_server.utils import feature_gate, server_config


def check_entitlement(feature: str) -> None:
    """Queries the feature gate to see if the operation falls within the Pro workspaces entitlements.

    Raises an exception if the user is not entitled to create an instance of the
    resource. Otherwise, simply returns.

    Args:
        feature: The feature to check for.
    """
    if not server_config().feature_gate_enabled:
        return
    return feature_gate().check_entitlement(feature=feature)


def report_usage(feature: str, resource_id: UUID) -> None:
    """Reports the creation/usage of a feature/resource.

    Args:
        feature: The feature to report a usage for.
        resource_id: ID of the resource that was created.
    """
    if not server_config().feature_gate_enabled:
        return
    feature_gate().report_event(feature=feature, resource_id=resource_id)


def report_decrement(feature: str, resource_id: UUID) -> None:
    """Reports the deletion/deactivation of a feature/resource.

    Args:
        feature: The feature to report a decrement in count for.
        resource_id: ID of the resource that was deleted.
    """
    if not server_config().feature_gate_enabled:
        return
    feature_gate().report_event(
        feature=feature, resource_id=resource_id, is_decrement=True
    )
