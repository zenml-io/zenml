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
"""High-level helper functions to write endpoints with RBAC."""

from typing import Any, Callable, List, Optional, Tuple, TypeVar, Union
from uuid import UUID

from zenml.models import (
    BaseFilter,
    BaseIdentifiedResponse,
    BaseRequest,
    BaseUpdate,
    Page,
    ProjectScopedFilter,
    UserScopedRequest,
)
from zenml.zen_server.auth import get_auth_context
from zenml.zen_server.feature_gate.endpoint_utils import (
    check_entitlement,
    report_usage,
)
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.rbac.utils import (
    batch_verify_permissions_for_models,
    dehydrate_page,
    dehydrate_response_model,
    dehydrate_response_model_batch,
    delete_model_resource,
    get_allowed_resource_ids,
    get_resource_type_for_model,
    verify_permission,
    verify_permission_for_model,
)
from zenml.zen_server.utils import server_config, set_filter_project_scope

AnyRequest = TypeVar("AnyRequest", bound=BaseRequest)
AnyResponse = TypeVar("AnyResponse", bound=BaseIdentifiedResponse)  # type: ignore[type-arg]
AnyOtherResponse = TypeVar("AnyOtherResponse", bound=BaseIdentifiedResponse)  # type: ignore[type-arg]
AnyFilter = TypeVar("AnyFilter", bound=BaseFilter)
AnyUpdate = TypeVar("AnyUpdate", bound=BaseUpdate)
UUIDOrStr = TypeVar("UUIDOrStr", UUID, Union[UUID, str])


def verify_permissions_and_create_entity(
    request_model: AnyRequest,
    create_method: Callable[[AnyRequest], AnyResponse],
    surrogate_models: Optional[List[AnyOtherResponse]] = None,
    skip_entitlements: bool = False,
) -> AnyResponse:
    """Verify permissions and create the entity if authorized.

    Args:
        request_model: The entity request model.
        create_method: The method to create the entity.
        surrogate_models: Optional list of surrogate models to verify
            UPDATE permissions for instead of verifying CREATE permissions for
            the request model.
        skip_entitlements: Whether to skip the entitlement check and usage
            increment.

    Returns:
        A model of the created entity.
    """
    if isinstance(request_model, UserScopedRequest):
        auth_context = get_auth_context()
        assert auth_context

        # Ignore the user field set in the request model, if any, and set it to
        # the current user's ID instead. This is just a precaution, given that
        # the SQLZenStore also does this same validation on all request models.
        request_model.user = auth_context.user.id

    if surrogate_models:
        batch_verify_permissions_for_models(
            models=surrogate_models, action=Action.UPDATE
        )
    else:
        verify_permission_for_model(model=request_model, action=Action.CREATE)

    resource_type = get_resource_type_for_model(request_model)

    if resource_type:
        needs_usage_increment = (
            not skip_entitlements
            and resource_type in server_config().reportable_resources
        )
        if needs_usage_increment:
            check_entitlement(resource_type)

    created = create_method(request_model)

    if resource_type and needs_usage_increment:
        report_usage(resource_type, resource_id=created.id)

    return dehydrate_response_model(created)


def verify_permissions_and_batch_create_entity(
    batch: List[AnyRequest],
    create_method: Callable[[List[AnyRequest]], List[AnyResponse]],
) -> List[AnyResponse]:
    """Verify permissions and create a batch of entities if authorized.

    Args:
        batch: The batch to create.
        create_method: The method to create the entities.

    Raises:
        RuntimeError: If the resource type is usage-tracked.

    Returns:
        The created entities.
    """
    auth_context = get_auth_context()
    assert auth_context

    resource_types = set()
    for request_model in batch:
        resource_type = get_resource_type_for_model(request_model)
        if resource_type:
            resource_types.add(resource_type)

        if isinstance(request_model, UserScopedRequest):
            # Ignore the user field set in the request model, if any, and set it
            # to the current user's ID instead. This is just a precaution, given
            # that the SQLZenStore also does this same validation on all request
            # models.
            request_model.user = auth_context.user.id

    batch_verify_permissions_for_models(models=batch, action=Action.CREATE)

    if resource_types & set(server_config().reportable_resources):
        raise RuntimeError(
            "Batch requests are currently not possible with usage-tracked "
            "features."
        )

    created = create_method(batch)
    return dehydrate_response_model_batch(created)


def verify_permissions_and_get_or_create_entity(
    request_model: AnyRequest,
    get_or_create_method: Callable[
        [AnyRequest, Optional[Callable[[], None]]], Tuple[AnyResponse, bool]
    ],
) -> Tuple[AnyResponse, bool]:
    """Verify permissions and create the entity if authorized.

    Args:
        request_model: The entity request model.
        get_or_create_method: The method to get or create the entity.

    Returns:
        The entity and a boolean indicating whether the entity was created.
    """
    if isinstance(request_model, UserScopedRequest):
        auth_context = get_auth_context()
        assert auth_context

        # Ignore the user field set in the request model, if any, and set it to
        # the current user's ID instead. This is just a precaution, given that
        # the SQLZenStore also does this same validation on all request models.
        request_model.user = auth_context.user.id

    resource_type = get_resource_type_for_model(request_model)
    needs_usage_increment = (
        resource_type and resource_type in server_config().reportable_resources
    )

    def _pre_creation_hook() -> None:
        verify_permission_for_model(model=request_model, action=Action.CREATE)
        if resource_type and needs_usage_increment:
            check_entitlement(resource_type=resource_type)

    model, created = get_or_create_method(request_model, _pre_creation_hook)

    if not created:
        verify_permission_for_model(model=model, action=Action.READ)
    elif resource_type and needs_usage_increment:
        report_usage(resource_type, resource_id=model.id)

    return dehydrate_response_model(model), created


def verify_permissions_and_get_entity(
    id: UUIDOrStr,
    get_method: Callable[[UUIDOrStr], AnyResponse],
    **get_method_kwargs: Any,
) -> AnyResponse:
    """Verify permissions and fetch an entity.

    Args:
        id: The ID of the entity to fetch.
        get_method: The method to fetch the entity.
        get_method_kwargs: Keyword arguments to pass to the get method.

    Returns:
        A model of the fetched entity.
    """
    model = get_method(id, **get_method_kwargs)
    verify_permission_for_model(model, action=Action.READ)
    return dehydrate_response_model(model)


def verify_permissions_and_list_entities(
    filter_model: AnyFilter,
    resource_type: ResourceType,
    list_method: Callable[[AnyFilter], Page[AnyResponse]],
    **list_method_kwargs: Any,
) -> Page[AnyResponse]:
    """Verify permissions and list entities.

    Args:
        filter_model: The entity filter model.
        resource_type: The resource type of the entities to list.
        list_method: The method to list the entities.
        list_method_kwargs: Keyword arguments to pass to the list method.

    Returns:
        A page of entity models.

    Raises:
        ValueError: If the filter's project scope is not set or is not a UUID.
    """
    auth_context = get_auth_context()
    assert auth_context

    project_id: Optional[UUID] = None
    if isinstance(filter_model, ProjectScopedFilter):
        # A project scoped filter must always be scoped to a specific
        # project. This is required for the RBAC check to work.
        set_filter_project_scope(filter_model)
        if not filter_model.project or not isinstance(
            filter_model.project, UUID
        ):
            raise ValueError(
                "Project scope must be a UUID, got "
                f"{type(filter_model.project)}."
            )
        project_id = filter_model.project

    allowed_ids = get_allowed_resource_ids(
        resource_type=resource_type, project_id=project_id
    )
    filter_model.configure_rbac(
        authenticated_user_id=auth_context.user.id, id=allowed_ids
    )
    page = list_method(filter_model, **list_method_kwargs)
    return dehydrate_page(page)


def verify_permissions_and_update_entity(
    id: UUIDOrStr,
    update_model: AnyUpdate,
    get_method: Callable[[UUIDOrStr, bool], AnyResponse],
    update_method: Callable[[UUIDOrStr, AnyUpdate], AnyResponse],
    **update_method_kwargs: Any,
) -> AnyResponse:
    """Verify permissions and update an entity.

    Args:
        id: The ID of the entity to update.
        update_model: The entity update model.
        get_method: The method to fetch the entity.
        update_method: The method to update the entity.
        update_method_kwargs: Keyword arguments to pass to the update method.

    Returns:
        A model of the updated entity.
    """
    # We don't need the hydrated version here
    model = get_method(id, False)
    verify_permission_for_model(model, action=Action.UPDATE)
    updated_model = update_method(
        model.id, update_model, **update_method_kwargs
    )
    return dehydrate_response_model(updated_model)


def verify_permissions_and_delete_entity(
    id: UUIDOrStr,
    get_method: Callable[[UUIDOrStr, bool], AnyResponse],
    delete_method: Callable[[UUIDOrStr], None],
    **delete_method_kwargs: Any,
) -> AnyResponse:
    """Verify permissions and delete an entity.

    Args:
        id: The ID of the entity to delete.
        get_method: The method to fetch the entity.
        delete_method: The method to delete the entity.
        delete_method_kwargs: Keyword arguments to pass to the delete method.

    Returns:
        The deleted entity.
    """
    model = get_method(id, True)
    verify_permission_for_model(model, action=Action.DELETE)
    delete_method(model.id, **delete_method_kwargs)
    delete_model_resource(model)

    return model


def verify_permissions_and_prune_entities(
    resource_type: ResourceType,
    prune_method: Callable[..., None],
    project_id: Optional[UUID] = None,
    **kwargs: Any,
) -> None:
    """Verify permissions and prune entities of certain type.

    Args:
        resource_type: The resource type of the entities to prune.
        prune_method: The method to prune the entities.
        project_id: The project ID to prune the entities for.
        kwargs: Keyword arguments to pass to the prune method.
    """
    verify_permission(
        resource_type=resource_type,
        action=Action.PRUNE,
        project_id=project_id,
    )
    prune_method(**kwargs)
