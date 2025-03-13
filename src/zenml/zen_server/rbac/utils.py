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
"""RBAC utility functions."""

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
    Type,
    TypeVar,
)
from uuid import UUID

from pydantic import BaseModel

from zenml.exceptions import IllegalOperationError
from zenml.models import (
    BaseIdentifiedResponse,
    Page,
    ProjectScopedRequest,
    ProjectScopedResponse,
    UserResponse,
    UserScopedResponse,
)
from zenml.zen_server.auth import get_auth_context
from zenml.zen_server.rbac.models import Action, Resource, ResourceType
from zenml.zen_server.utils import rbac, server_config

if TYPE_CHECKING:
    from zenml.zen_stores.schemas import BaseSchema

AnyResponse = TypeVar("AnyResponse", bound=BaseIdentifiedResponse)  # type: ignore[type-arg]
AnyModel = TypeVar("AnyModel", bound=BaseModel)


def dehydrate_page(page: Page[AnyResponse]) -> Page[AnyResponse]:
    """Dehydrate all items of a page.

    Args:
        page: The page to dehydrate.

    Returns:
        The page with (potentially) dehydrated items.
    """
    new_items = dehydrate_response_model_batch(page.items)
    return page.model_copy(update={"items": new_items})


def dehydrate_response_model_batch(
    batch: List[AnyResponse],
) -> List[AnyResponse]:
    """Dehydrate all items of a batch.

    Args:
        batch: The batch to dehydrate.

    Returns:
        The batch with (potentially) dehydrated items.
    """
    if not server_config().rbac_enabled:
        return batch

    auth_context = get_auth_context()
    assert auth_context

    resource_list = [get_subresources_for_model(item) for item in batch]
    resources = set.union(*resource_list) if resource_list else set()
    permissions = rbac().check_permissions(
        user=auth_context.user, resources=resources, action=Action.READ
    )

    new_batch = [
        dehydrate_response_model(item, permissions=permissions)
        for item in batch
    ]

    return new_batch


def dehydrate_response_model(
    model: AnyModel, permissions: Optional[Dict[Resource, bool]] = None
) -> AnyModel:
    """Dehydrate a model if necessary.

    Args:
        model: The model to dehydrate.
        permissions: Prefetched permissions that will be used to check whether
            sub-models will be included in the model or not. If a sub-model
            refers to a resource which is not included in this dictionary, the
            permissions will be checked with the RBAC component.

    Returns:
        The (potentially) dehydrated model.
    """
    if not server_config().rbac_enabled:
        return model

    if not permissions:
        auth_context = get_auth_context()
        assert auth_context

        resources = get_subresources_for_model(model)
        permissions = rbac().check_permissions(
            user=auth_context.user, resources=resources, action=Action.READ
        )

    dehydrated_values = {}
    # See `get_subresources_for_model(...)` for a detailed explanation why we
    # need to use `model.__iter__()` here
    for key, value in model.__iter__():
        dehydrated_values[key] = _dehydrate_value(
            value, permissions=permissions
        )

    return type(model).model_validate(dehydrated_values)


def _dehydrate_value(
    value: Any, permissions: Optional[Dict[Resource, bool]] = None
) -> Any:
    """Helper function to recursive dehydrate any object.

    Args:
        value: The value to dehydrate.
        permissions: Prefetched permissions that will be used to check whether
            sub-models will be included in the model or not. If a sub-model
            refers to a resource which is not included in this dictionary, the
            permissions will be checked with the RBAC component.

    Returns:
        The recursively dehydrated value.
    """
    if isinstance(value, BaseIdentifiedResponse):
        permission_model = get_surrogate_permission_model_for_model(
            value, action=Action.READ
        )
        resource = get_resource_for_model(permission_model)
        if not resource:
            return dehydrate_response_model(value, permissions=permissions)

        has_permissions = (permissions or {}).get(resource, False)
        if has_permissions or has_permissions_for_model(
            model=permission_model, action=Action.READ
        ):
            return dehydrate_response_model(value, permissions=permissions)
        else:
            return get_permission_denied_model(value)
    elif isinstance(value, Page):
        return dehydrate_page(page=value)
    elif isinstance(value, BaseModel):
        return dehydrate_response_model(value, permissions=permissions)
    elif isinstance(value, Dict):
        return {
            k: _dehydrate_value(v, permissions=permissions)
            for k, v in value.items()
        }
    elif isinstance(value, (List, Set, tuple)):
        type_ = type(value)
        return type_(
            _dehydrate_value(v, permissions=permissions) for v in value
        )
    else:
        return value


def has_permissions_for_model(model: AnyModel, action: Action) -> bool:
    """If the active user has permissions to perform the action on the model.

    Args:
        model: The model the user wants to perform the action on.
        action: The action the user wants to perform.

    Returns:
        If the active user has permissions to perform the action on the model.
    """
    if is_owned_by_authenticated_user(model):
        return True

    try:
        verify_permission_for_model(model=model, action=action)
        return True
    except IllegalOperationError:
        return False


def get_permission_denied_model(model: AnyResponse) -> AnyResponse:
    """Get a model to return in case of missing read permissions.

    Args:
        model: The original model.

    Returns:
        The permission denied model.
    """
    return model.model_copy(
        update={
            "body": None,
            "metadata": None,
            "resources": None,
            "permission_denied": True,
        }
    )


def batch_verify_permissions_for_models(
    models: Sequence[AnyModel],
    action: Action,
) -> None:
    """Batch permission verification for models.

    Args:
        models: The models the user wants to perform the action on.
        action: The action the user wants to perform.
    """
    if not server_config().rbac_enabled:
        return

    resources = set()
    for model in models:
        if is_owned_by_authenticated_user(model):
            # The model owner always has permissions
            continue

        permission_model = get_surrogate_permission_model_for_model(
            model, action=action
        )

        if resource := get_resource_for_model(permission_model):
            resources.add(resource)

    batch_verify_permissions(resources=resources, action=action)


def verify_permission_for_model(model: AnyModel, action: Action) -> None:
    """Verifies if a user has permission to perform an action on a model.

    Args:
        model: The model the user wants to perform the action on.
        action: The action the user wants to perform.
    """
    batch_verify_permissions_for_models(models=[model], action=action)


def batch_verify_permissions(
    resources: Set[Resource],
    action: Action,
) -> None:
    """Batch permission verification.

    Args:
        resources: The resources the user wants to perform the action on.
        action: The action the user wants to perform.

    Raises:
        IllegalOperationError: If the user is not allowed to perform the action.
        RuntimeError: If the permission verification failed unexpectedly.
    """
    if not server_config().rbac_enabled:
        return

    auth_context = get_auth_context()
    assert auth_context

    permissions = rbac().check_permissions(
        user=auth_context.user, resources=resources, action=action
    )

    for resource in resources:
        if resource not in permissions:
            # This should never happen if the RBAC implementation is working
            # correctly
            raise RuntimeError(
                f"Failed to verify permissions to {action.upper()} resource "
                f"'{resource}'."
            )

        if not permissions[resource]:
            raise IllegalOperationError(
                message=f"Insufficient permissions to {action.upper()} "
                f"resource '{resource}'.",
            )


def verify_permission(
    resource_type: str,
    action: Action,
    resource_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
) -> None:
    """Verifies if a user has permission to perform an action on a resource.

    Args:
        resource_type: The type of resource that the user wants to perform the
            action on.
        action: The action the user wants to perform.
        resource_id: ID of the resource the user wants to perform the action on.
        project_id: ID of the project the user wants to perform the action
            on. Only used for project scoped resources.
    """
    resource = Resource(
        type=resource_type, id=resource_id, project_id=project_id
    )
    batch_verify_permissions(resources={resource}, action=action)


def get_allowed_resource_ids(
    resource_type: str,
    action: Action = Action.READ,
    project_id: Optional[UUID] = None,
) -> Optional[Set[UUID]]:
    """Get all resource IDs of a resource type that a user can access.

    Args:
        resource_type: The resource type.
        action: The action the user wants to perform on the resource.
        project_id: Optional project ID to filter the resources by.
            Required for project scoped resources.

    Returns:
        A list of resource IDs or `None` if the user has full access to the
        all instances of the resource.
    """
    if not server_config().rbac_enabled:
        return None

    auth_context = get_auth_context()
    assert auth_context

    (
        has_full_resource_access,
        allowed_ids,
    ) = rbac().list_allowed_resource_ids(
        user=auth_context.user,
        resource=Resource(type=resource_type, project_id=project_id),
        action=action,
    )

    if has_full_resource_access:
        return None

    return {UUID(id) for id in allowed_ids}


def get_resource_for_model(model: AnyModel) -> Optional[Resource]:
    """Get the resource associated with a model object.

    Args:
        model: The model for which to get the resource.

    Returns:
        The resource associated with the model, or `None` if the model
        is not associated with any resource type.
    """
    resource_type = get_resource_type_for_model(model)
    if not resource_type:
        # This model is not tied to any RBAC resource type
        return None

    project_id: Optional[UUID] = None
    if isinstance(model, ProjectScopedResponse):
        # A project scoped response is always scoped to a specific project
        project_id = model.project.id
    elif isinstance(model, ProjectScopedRequest):
        # A project scoped request is always scoped to a specific project
        project_id = model.project

    resource_id: Optional[UUID] = None
    if isinstance(model, BaseIdentifiedResponse):
        resource_id = model.id

    return Resource(type=resource_type, id=resource_id, project_id=project_id)


def get_surrogate_permission_model_for_model(
    model: BaseModel, action: str
) -> BaseModel:
    """Get a surrogate permission model for a model.

    In some cases a different model instead of the original model is used to
    verify permissions. For example, a parent container model might be used
    to verify permissions for all its children.

    Args:
        model: The original model.
        action: The action that the user wants to perform on the model.

    Returns:
        A surrogate model or the original.
    """
    from zenml.models import ArtifactVersionResponse, ModelVersionResponse

    # Permissions to read entities that represent versions of another entity
    # are checked on the parent entity
    if action == Action.READ:
        if isinstance(model, ModelVersionResponse):
            return model.model
        elif isinstance(model, ArtifactVersionResponse):
            return model.artifact

    return model


def get_resource_type_for_model(
    model: AnyModel,
) -> Optional[ResourceType]:
    """Get the resource type associated with a model object.

    Args:
        model: The model for which to get the resource type.

    Returns:
        The resource type associated with the model, or `None` if the model
        is not associated with any resource type.
    """
    from zenml.models import (
        ActionRequest,
        ActionResponse,
        ArtifactRequest,
        ArtifactResponse,
        ArtifactVersionRequest,
        ArtifactVersionResponse,
        CodeRepositoryRequest,
        CodeRepositoryResponse,
        ComponentRequest,
        ComponentResponse,
        EventSourceRequest,
        EventSourceResponse,
        FlavorRequest,
        FlavorResponse,
        ModelRequest,
        ModelResponse,
        ModelVersionRequest,
        ModelVersionResponse,
        PipelineBuildRequest,
        PipelineBuildResponse,
        PipelineDeploymentRequest,
        PipelineDeploymentResponse,
        PipelineRequest,
        PipelineResponse,
        PipelineRunRequest,
        PipelineRunResponse,
        ProjectRequest,
        ProjectResponse,
        RunMetadataRequest,
        RunTemplateRequest,
        RunTemplateResponse,
        SecretRequest,
        SecretResponse,
        ServiceAccountRequest,
        ServiceAccountResponse,
        ServiceConnectorRequest,
        ServiceConnectorResponse,
        ServiceRequest,
        ServiceResponse,
        StackRequest,
        StackResponse,
        TagRequest,
        TagResponse,
        TriggerExecutionRequest,
        TriggerExecutionResponse,
        TriggerRequest,
        TriggerResponse,
    )

    mapping: Dict[
        Any,
        ResourceType,
    ] = {
        ActionRequest: ResourceType.ACTION,
        ActionResponse: ResourceType.ACTION,
        ArtifactRequest: ResourceType.ARTIFACT,
        ArtifactResponse: ResourceType.ARTIFACT,
        ArtifactVersionRequest: ResourceType.ARTIFACT_VERSION,
        ArtifactVersionResponse: ResourceType.ARTIFACT_VERSION,
        CodeRepositoryRequest: ResourceType.CODE_REPOSITORY,
        CodeRepositoryResponse: ResourceType.CODE_REPOSITORY,
        ComponentRequest: ResourceType.STACK_COMPONENT,
        ComponentResponse: ResourceType.STACK_COMPONENT,
        EventSourceRequest: ResourceType.EVENT_SOURCE,
        EventSourceResponse: ResourceType.EVENT_SOURCE,
        FlavorRequest: ResourceType.FLAVOR,
        FlavorResponse: ResourceType.FLAVOR,
        ModelRequest: ResourceType.MODEL,
        ModelResponse: ResourceType.MODEL,
        ModelVersionRequest: ResourceType.MODEL_VERSION,
        ModelVersionResponse: ResourceType.MODEL_VERSION,
        PipelineBuildRequest: ResourceType.PIPELINE_BUILD,
        PipelineBuildResponse: ResourceType.PIPELINE_BUILD,
        PipelineDeploymentRequest: ResourceType.PIPELINE_DEPLOYMENT,
        PipelineDeploymentResponse: ResourceType.PIPELINE_DEPLOYMENT,
        PipelineRequest: ResourceType.PIPELINE,
        PipelineResponse: ResourceType.PIPELINE,
        PipelineRunRequest: ResourceType.PIPELINE_RUN,
        PipelineRunResponse: ResourceType.PIPELINE_RUN,
        RunMetadataRequest: ResourceType.RUN_METADATA,
        RunTemplateRequest: ResourceType.RUN_TEMPLATE,
        RunTemplateResponse: ResourceType.RUN_TEMPLATE,
        SecretRequest: ResourceType.SECRET,
        SecretResponse: ResourceType.SECRET,
        ServiceAccountRequest: ResourceType.SERVICE_ACCOUNT,
        ServiceAccountResponse: ResourceType.SERVICE_ACCOUNT,
        ServiceConnectorRequest: ResourceType.SERVICE_CONNECTOR,
        ServiceConnectorResponse: ResourceType.SERVICE_CONNECTOR,
        ServiceRequest: ResourceType.SERVICE,
        ServiceResponse: ResourceType.SERVICE,
        StackRequest: ResourceType.STACK,
        StackResponse: ResourceType.STACK,
        TagRequest: ResourceType.TAG,
        TagResponse: ResourceType.TAG,
        TriggerRequest: ResourceType.TRIGGER,
        TriggerResponse: ResourceType.TRIGGER,
        TriggerExecutionRequest: ResourceType.TRIGGER_EXECUTION,
        TriggerExecutionResponse: ResourceType.TRIGGER_EXECUTION,
        ProjectResponse: ResourceType.PROJECT,
        ProjectRequest: ResourceType.PROJECT,
        # UserResponse: ResourceType.USER,
    }

    return mapping.get(type(model))


def is_owned_by_authenticated_user(model: AnyModel) -> bool:
    """Returns whether the currently authenticated user owns the model.

    Args:
        model: The model for which to check the ownership.

    Returns:
        Whether the currently authenticated user owns the model.
    """
    auth_context = get_auth_context()
    assert auth_context

    if isinstance(model, UserScopedResponse):
        if model.user:
            return model.user.id == auth_context.user.id
        else:
            # The model is server-owned and for RBAC purposes we consider
            # every user to be the owner of it
            return True

    return False


def get_subresources_for_model(
    model: AnyModel,
) -> Set[Resource]:
    """Get all sub-resources of a model which need permission verification.

    Args:
        model: The model for which to get all the resources.

    Returns:
        All resources of a model which need permission verification.
    """
    resources = set()

    # We don't want to use `model.model_dump()` here as that recursively
    # converts models to dicts, but we want to preserve those classes for
    # the recursive `_get_subresources_for_value` calls.
    # We previously used `dict(model)` here, but that lead to issues with
    # models overwriting `__getattr__`, this `model.__iter__()` has the same
    # results though.
    if isinstance(model, Page):
        for item in model:
            resources.update(_get_subresources_for_value(item))
    else:
        for _, value in model.__iter__():
            resources.update(_get_subresources_for_value(value))

    return resources


def _get_subresources_for_value(value: Any) -> Set[Resource]:
    """Helper function to recursive retrieve resources of any object.

    Args:
        value: The value for which to get all the resources.

    Returns:
        All resources of the value which need permission verification.
    """
    if isinstance(value, BaseIdentifiedResponse):
        resources = set()
        if not is_owned_by_authenticated_user(value):
            value = get_surrogate_permission_model_for_model(
                value, action=Action.READ
            )
            if resource := get_resource_for_model(value):
                resources.add(resource)

        return resources.union(get_subresources_for_model(value))
    elif isinstance(value, BaseModel):
        return get_subresources_for_model(value)
    elif isinstance(value, Dict):
        resources_list = [
            _get_subresources_for_value(v) for v in value.values()
        ]
        return set.union(*resources_list) if resources_list else set()
    elif isinstance(value, (List, Set, tuple)):
        resources_list = [_get_subresources_for_value(v) for v in value]
        return set.union(*resources_list) if resources_list else set()
    else:
        return set()


def get_schema_for_resource_type(
    resource_type: ResourceType,
) -> Type["BaseSchema"]:
    """Get the database schema for a resource type.

    Args:
        resource_type: The resource type for which to get the database schema.

    Returns:
        The database schema.
    """
    from zenml.zen_stores.schemas import (
        ActionSchema,
        ArtifactSchema,
        ArtifactVersionSchema,
        CodeRepositorySchema,
        EventSourceSchema,
        FlavorSchema,
        ModelSchema,
        ModelVersionSchema,
        PipelineBuildSchema,
        PipelineDeploymentSchema,
        PipelineRunSchema,
        PipelineSchema,
        RunMetadataSchema,
        RunTemplateSchema,
        SecretSchema,
        ServiceConnectorSchema,
        ServiceSchema,
        StackComponentSchema,
        StackSchema,
        TagSchema,
        TriggerExecutionSchema,
        TriggerSchema,
        UserSchema,
    )

    mapping: Dict[ResourceType, Type["BaseSchema"]] = {
        ResourceType.STACK: StackSchema,
        ResourceType.FLAVOR: FlavorSchema,
        ResourceType.STACK_COMPONENT: StackComponentSchema,
        ResourceType.PIPELINE: PipelineSchema,
        ResourceType.CODE_REPOSITORY: CodeRepositorySchema,
        ResourceType.MODEL: ModelSchema,
        ResourceType.MODEL_VERSION: ModelVersionSchema,
        ResourceType.SERVICE_CONNECTOR: ServiceConnectorSchema,
        ResourceType.ARTIFACT: ArtifactSchema,
        ResourceType.ARTIFACT_VERSION: ArtifactVersionSchema,
        ResourceType.SECRET: SecretSchema,
        ResourceType.SERVICE: ServiceSchema,
        ResourceType.TAG: TagSchema,
        ResourceType.SERVICE_ACCOUNT: UserSchema,
        # ResourceType.PROJECT: ProjectSchema,
        ResourceType.PIPELINE_RUN: PipelineRunSchema,
        ResourceType.PIPELINE_DEPLOYMENT: PipelineDeploymentSchema,
        ResourceType.PIPELINE_BUILD: PipelineBuildSchema,
        ResourceType.RUN_TEMPLATE: RunTemplateSchema,
        ResourceType.RUN_METADATA: RunMetadataSchema,
        # ResourceType.USER: UserSchema,
        ResourceType.ACTION: ActionSchema,
        ResourceType.EVENT_SOURCE: EventSourceSchema,
        ResourceType.TRIGGER: TriggerSchema,
        ResourceType.TRIGGER_EXECUTION: TriggerExecutionSchema,
    }

    return mapping[resource_type]


def update_resource_membership(
    user: UserResponse, resource: Resource, actions: List[Action]
) -> None:
    """Update the resource membership of a user.

    Args:
        user: User for which the resource membership should be updated.
        resource: The resource.
        actions: The actions that the user should be able to perform on the
            resource.
    """
    if not server_config().rbac_enabled:
        return

    rbac().update_resource_membership(
        user=user, resource=resource, actions=actions
    )


def delete_model_resource(model: AnyModel) -> None:
    """Delete resource membership information for a model.

    Args:
        model: The model for which to delete the resource membership information.
    """
    delete_model_resources(models=[model])


def delete_model_resources(models: List[AnyModel]) -> None:
    """Delete resource membership information for a list of models.

    Args:
        models: The models for which to delete the resource membership information.
    """
    if not server_config().rbac_enabled:
        return

    resources = set()
    for model in models:
        if resource := get_resource_for_model(model):
            resources.add(resource)

    delete_resources(resources=list(resources))


def delete_resources(resources: List[Resource]) -> None:
    """Delete resource membership information for a list of resources.

    Args:
        resources: The resources for which to delete the resource membership
            information.
    """
    if not server_config().rbac_enabled:
        return

    rbac().delete_resources(resources=resources)
