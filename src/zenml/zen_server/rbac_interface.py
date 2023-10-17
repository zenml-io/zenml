from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Type
from uuid import UUID

from pydantic import BaseModel

from zenml.enums import StrEnum
from zenml.models.base_models import BaseResponseModel

if TYPE_CHECKING:
    from zenml.models import UserResponseModel


class Action(StrEnum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"


class ResourceType(StrEnum):
    STACK = "stack"
    FLAVOR = "flavor"
    STACK_COMPONENT = "stack_component"
    PIPELINE = "pipeline"
    CODE_REPOSITORY = "code-repository"
    MODEL = "model"
    SERVICE_CONNECTOR = "service_connector"
    ARTIFACT = "artifact"
    SECRET = "secret"


def get_resource_type_for_model(
    model: "BaseResponseModel",
) -> Optional[ResourceType]:
    from zenml.models import (
        ArtifactResponseModel,
        CodeRepositoryResponseModel,
        ComponentResponseModel,
        FlavorResponseModel,
        ModelResponseModel,
        PipelineResponseModel,
        SecretResponseModel,
        ServiceConnectorResponseModel,
        StackResponseModel,
    )

    mapping: Dict[Type[BaseResponseModel], ResourceType] = {
        FlavorResponseModel: ResourceType.FLAVOR,
        ServiceConnectorResponseModel: ResourceType.SERVICE_CONNECTOR,
        ComponentResponseModel: ResourceType.STACK_COMPONENT,
        StackResponseModel: ResourceType.STACK,
        PipelineResponseModel: ResourceType.PIPELINE,
        CodeRepositoryResponseModel: ResourceType.CODE_REPOSITORY,
        SecretResponseModel: ResourceType.SECRET,
        ModelResponseModel: ResourceType.MODEL,
        ArtifactResponseModel: ResourceType.ARTIFACT,
    }

    return mapping.get(type(model))


class Resource(BaseModel):
    type: str
    id: Optional[UUID] = None


class RBACInterface(ABC):
    @abstractmethod
    def has_permission(
        self, user: "UserResponseModel", resource: Resource, action: str
    ) -> bool:
        """Checks if a user has permission to perform an action on a resource.

        Args:
            user: User which wants to access a resource.
            resource: The resource the user wants to access.
            action: The action that the user wants to perform on the resource.

        Returns:
            Whether the user has permission to perform an action on a resource.
        """

    @abstractmethod
    def list_allowed_resource_ids(
        self, user: "UserResponseModel", resource: Resource, action: str
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
