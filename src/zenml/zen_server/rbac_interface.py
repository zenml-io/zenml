from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from uuid import UUID

from pydantic import BaseModel

from zenml.enums import StrEnum


class Action(StrEnum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"


class ResourceType(StrEnum):
    STACK = "stack"
    COMPONENT = "component"
    PIPELINE = "pipeline"


class Resource(BaseModel):
    type: str
    id: Optional[UUID] = None


class RBACInterface(ABC):
    @abstractmethod
    def has_permission(
        self, user: UUID, resource: Resource, action: str
    ) -> bool:
        """Checks if a user has permission to perform an action on a resource.

        Args:
            user: ID of the user which wants to access a resource.
            resource: The resource the user wants to access.
            action: The action that the user wants to perform on the resource.

        Returns:
            Whether the user has permission to perform an action on a resource.
        """

    @abstractmethod
    def list_allowed_resource_ids(
        self, user: UUID, resource: Resource, action: str
    ) -> Tuple[bool, List[str]]:
        """Lists all resource IDs of a resource type that a user can access.

        Args:
            user: ID of the user which wants to access a resource.
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
