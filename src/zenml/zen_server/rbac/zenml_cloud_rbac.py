#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Cloud RBAC implementation."""

from typing import TYPE_CHECKING, Dict, List, Set, Tuple

from zenml.zen_server.cloud_utils import cloud_connection
from zenml.zen_server.rbac.models import Action, Resource
from zenml.zen_server.rbac.rbac_interface import RBACInterface
from zenml.zen_server.utils import server_config

if TYPE_CHECKING:
    from zenml.models import UserResponse


PERMISSIONS_ENDPOINT = "/rbac/check_permissions"
ALLOWED_RESOURCE_IDS_ENDPOINT = "/rbac/allowed_resource_ids"
RESOURCE_MEMBERSHIP_ENDPOINT = "/rbac/resource_members"

SERVER_SCOPE_IDENTIFIER = "server"

SERVER_ID = server_config().external_server_id


def _convert_to_cloud_resource(resource: Resource) -> str:
    """Convert a resource to a ZenML Pro Management Plane resource.

    Args:
        resource: The resource to convert.

    Returns:
        The converted resource.
    """
    resource_string = f"{SERVER_ID}@{SERVER_SCOPE_IDENTIFIER}:{resource.type}"

    if resource.id:
        resource_string += f"/{resource.id}"

    return resource_string


def _convert_from_cloud_resource(cloud_resource: str) -> Resource:
    """Convert a cloud resource to a ZenML server resource.

    Args:
        cloud_resource: The cloud resource to convert.

    Raises:
        ValueError: If the cloud resource is invalid for this server.

    Returns:
        The converted resource.
    """
    scope, resource_type_and_id = cloud_resource.rsplit(":", maxsplit=1)

    if scope != f"{SERVER_ID}@{SERVER_SCOPE_IDENTIFIER}":
        raise ValueError("Invalid scope for server resource.")

    if "/" in resource_type_and_id:
        resource_type, resource_id = resource_type_and_id.split("/")
        return Resource(type=resource_type, id=resource_id)
    else:
        return Resource(type=resource_type_and_id)


class ZenMLCloudRBAC(RBACInterface):
    """RBAC implementation that uses the ZenML Pro Management Plane as a backend."""

    def __init__(self) -> None:
        """Initialize the object."""
        self._connection = cloud_connection()

    def check_permissions(
        self, user: "UserResponse", resources: Set[Resource], action: Action
    ) -> Dict[Resource, bool]:
        """Checks if a user has permissions to perform an action on resources.

        Args:
            user: User which wants to access a resource.
            resources: The resources the user wants to access.
            action: The action that the user wants to perform on the resources.

        Returns:
            A dictionary mapping resources to a boolean which indicates whether
            the user has permissions to perform the action on that resource.
        """
        if not resources:
            # No need to send a request if there are no resources
            return {}

        if user.is_service_account:
            # Service accounts have full permissions for now
            return {resource: True for resource in resources}

        # At this point it's a regular user, which in a ZenML Pro with RBAC
        # enabled is always authenticated using external authentication
        assert user.external_user_id

        params = {
            "user_id": str(user.external_user_id),
            "resources": [
                _convert_to_cloud_resource(resource) for resource in resources
            ],
            "action": str(action),
        }
        response = self._connection.get(
            endpoint=PERMISSIONS_ENDPOINT, params=params
        )
        value = response.json()

        assert isinstance(value, dict)
        return {_convert_from_cloud_resource(k): v for k, v in value.items()}

    def list_allowed_resource_ids(
        self, user: "UserResponse", resource: Resource, action: Action
    ) -> Tuple[bool, List[str]]:
        """Lists all resource IDs of a resource type that a user can access.

        Args:
            user: User which wants to access a resource.
            resource: The resource the user wants to access.
            action: The action that the user wants to perform on the resource.

        Returns:
            A tuple (full_resource_access, resource_ids).
            `full_resource_access` will be `True` if the user can perform the
            given action on any instance of the given resource type, `False`
            otherwise. If `full_resource_access` is `False`, `resource_ids`
            will contain the list of instance IDs that the user can perform
            the action on.
        """
        assert not resource.id
        if user.is_service_account:
            # Service accounts have full permissions for now
            return True, []

        # At this point it's a regular user, which in the ZenML Pro with RBAC
        # enabled is always authenticated using external authentication
        assert user.external_user_id
        params = {
            "user_id": str(user.external_user_id),
            "resource": _convert_to_cloud_resource(resource),
            "action": str(action),
        }
        response = self._connection.get(
            endpoint=ALLOWED_RESOURCE_IDS_ENDPOINT, params=params
        )
        response_json = response.json()

        full_resource_access: bool = response_json["full_access"]
        allowed_ids: List[str] = response_json["ids"]

        return full_resource_access, allowed_ids

    def update_resource_membership(
        self, user: "UserResponse", resource: Resource, actions: List[Action]
    ) -> None:
        """Update the resource membership of a user.

        Args:
            user: User for which the resource membership should be updated.
            resource: The resource.
            actions: The actions that the user should be able to perform on the
                resource.
        """
        if user.is_service_account:
            # Service accounts have full permissions for now
            return

        data = {
            "user_id": str(user.external_user_id),
            "resource": _convert_to_cloud_resource(resource),
            "actions": [str(action) for action in actions],
        }
        self._connection.post(endpoint=RESOURCE_MEMBERSHIP_ENDPOINT, data=data)
