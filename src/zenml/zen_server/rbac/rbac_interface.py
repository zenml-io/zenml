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
"""RBAC interface definition."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, List, Set, Tuple

from zenml.zen_server.rbac.models import Action, Resource

if TYPE_CHECKING:
    from zenml.models import UserResponse


class RBACInterface(ABC):
    """RBAC interface definition."""

    @abstractmethod
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

    @abstractmethod
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
