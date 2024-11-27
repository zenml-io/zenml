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

from typing import Any, Callable, List, TypeVar, Union
from uuid import UUID

from pydantic import BaseModel

from zenml.constants import (
    REPORTABLE_RESOURCES,
    REQUIRES_CUSTOM_RESOURCE_REPORTING,
)
from zenml.exceptions import IllegalOperationError
from zenml.models import (
    BaseFilter,
    BaseIdentifiedResponse,
    BaseRequest,
    Page,
    UserScopedRequest,
)
from zenml.zen_server.auth import get_auth_context
from zenml.zen_server.feature_gate.endpoint_utils import (
    check_entitlement,
    report_usage,
)
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.rbac.utils import (
    dehydrate_page,
    dehydrate_response_model,
    get_allowed_resource_ids,
    verify_permission,
    verify_permission_for_model,
)

AnyRequest = TypeVar("AnyRequest", bound=BaseRequest)
AnyResponse = TypeVar("AnyResponse", bound=BaseIdentifiedResponse)  # type: ignore[type-arg]
AnyFilter = TypeVar("AnyFilter", bound=BaseFilter)
AnyUpdate = TypeVar("AnyUpdate", bound=BaseModel)
UUIDOrStr = TypeVar("UUIDOrStr", UUID, Union[UUID, str])


def verify_permissions_and_create_entity(
    request_model: AnyRequest,
    resource_type: ResourceType,
    create_method: Callable[[AnyRequest], AnyResponse],
) -> AnyResponse:
    """Verify permissions and create the entity if authorized.

    Args:
        request_model: The entity request model.
        resource_type: The resource type of the entity to create.
        create_method: The method to create the entity.

    Raises:
        IllegalOperationError: If the request model has a different owner then
            the currently authenticated user.

    Returns:
        A model of the created entity.
    """
    if isinstance(request_model, UserScopedRequest):
        auth_context = get_auth_context()
        assert auth_context

        if request_model.user != auth_context.user.id:
            raise IllegalOperationError(
                f"Not allowed to create resource '{resource_type}' for a "
                "different user."
            )
    verify_permission(resource_type=resource_type, action=Action.CREATE)

    needs_usage_increment = (
        resource_type in REPORTABLE_RESOURCES
        and resource_type not in REQUIRES_CUSTOM_RESOURCE_REPORTING
    )
    if needs_usage_increment:
        check_entitlement(resource_type)

    created = create_method(request_model)

    if needs_usage_increment:
        report_usage(resource_type, resource_id=created.id)

    return created


def verify_permissions_and_batch_create_entity(
    batch: List[AnyRequest],
    resource_type: ResourceType,
    create_method: Callable[[List[AnyRequest]], List[AnyResponse]],
) -> List[AnyResponse]:
    """Verify permissions and create a batch of entities if authorized.

    Args:
        batch: The batch to create.
        resource_type: The resource type of the entities to create.
        create_method: The method to create the entities.

    Raises:
        IllegalOperationError: If the request model has a different owner then
            the currently authenticated user.
        RuntimeError: If the resource type is usage-tracked.

    Returns:
        The created entities.
    """
    auth_context = get_auth_context()
    assert auth_context

    for request_model in batch:
        if isinstance(request_model, UserScopedRequest):
            if request_model.user != auth_context.user.id:
                raise IllegalOperationError(
                    f"Not allowed to create resource '{resource_type}' for a "
                    "different user."
                )

    verify_permission(resource_type=resource_type, action=Action.CREATE)

    if resource_type in REPORTABLE_RESOURCES:
        raise RuntimeError(
            "Batch requests are currently not possible with usage-tracked features."
        )

    created = create_method(batch)
    return created


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
    """
    auth_context = get_auth_context()
    assert auth_context

    allowed_ids = get_allowed_resource_ids(resource_type=resource_type)
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
) -> AnyResponse:
    """Verify permissions and update an entity.

    Args:
        id: The ID of the entity to update.
        update_model: The entity update model.
        get_method: The method to fetch the entity.
        update_method: The method to update the entity.

    Returns:
        A model of the updated entity.
    """
    # We don't need the hydrated version here
    model = get_method(id, False)
    verify_permission_for_model(model, action=Action.UPDATE)
    updated_model = update_method(model.id, update_model)
    return dehydrate_response_model(updated_model)


def verify_permissions_and_delete_entity(
    id: UUIDOrStr,
    get_method: Callable[[UUIDOrStr, bool], AnyResponse],
    delete_method: Callable[[UUIDOrStr], None],
) -> AnyResponse:
    """Verify permissions and delete an entity.

    Args:
        id: The ID of the entity to delete.
        get_method: The method to fetch the entity.
        delete_method: The method to delete the entity.

    Returns:
        The deleted entity.
    """
    # We don't need the hydrated version here
    model = get_method(id, False)
    verify_permission_for_model(model, action=Action.DELETE)
    delete_method(model.id)

    return model


def verify_permissions_and_prune_entities(
    resource_type: ResourceType,
    prune_method: Callable[..., None],
    **kwargs: Any,
) -> None:
    """Verify permissions and prune entities of certain type.

    Args:
        resource_type: The resource type of the entities to prune.
        prune_method: The method to prune the entities.
        kwargs: Keyword arguments to pass to the prune method.
    """
    verify_permission(resource_type=resource_type, action=Action.PRUNE)
    prune_method(**kwargs)
