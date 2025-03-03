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
"""Endpoint definitions for the link between tags and resources."""

from typing import Any, List, Tuple
from uuid import UUID

from fastapi import APIRouter, Security

from zenml.constants import (
    API,
    BATCH,
    TAG_RESOURCES,
    VERSION_1,
)
from zenml.enums import TaggableResourceTypes
from zenml.models import TagResourceRequest
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.models import Action
from zenml.zen_server.rbac.utils import (
    batch_verify_permissions_for_models,
)
from zenml.zen_server.utils import (
    handle_exceptions,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + TAG_RESOURCES,
    tags=["tag_resources"],
    responses={401: error_response, 403: error_response},
)


def _get_resource_model(
    resource_id: UUID, resource_type: TaggableResourceTypes
) -> Any:
    """Get the model for a given resource type.

    Args:
        resource_id: The ID of the resource.
        resource_type: The type of the resource.

    Returns:
        The model for the given resource type.

    Raises:
        ValueError: If the resource type is invalid.
    """
    if resource_type == TaggableResourceTypes.ARTIFACT:
        return zen_store().get_artifact(resource_id)
    elif resource_type == TaggableResourceTypes.ARTIFACT_VERSION:
        return zen_store().get_artifact_version(resource_id)
    elif resource_type == TaggableResourceTypes.MODEL:
        return zen_store().get_model(resource_id)
    elif resource_type == TaggableResourceTypes.MODEL_VERSION:
        return zen_store().get_model_version(resource_id)
    elif resource_type == TaggableResourceTypes.PIPELINE:
        return zen_store().get_pipeline(resource_id)
    elif resource_type == TaggableResourceTypes.PIPELINE_RUN:
        return zen_store().get_run(resource_id)
    elif resource_type == TaggableResourceTypes.RUN_TEMPLATE:
        return zen_store().get_run_template(resource_id)
    else:
        raise ValueError(f"Invalid resource type: {resource_type}")


@router.post(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def create_tag_resource(
    tag_resource: TagResourceRequest,
    _: AuthContext = Security(authorize),
) -> None:
    """Attach different tags to different resources.

    Args:
        tag_resource: A tag resource request.
    """
    verify_models = []
    verify_models.append(zen_store().get_tag(tag_resource.tag_id))
    verify_models.append(
        _get_resource_model(
            tag_resource.resource_id, tag_resource.resource_type
        )
    )

    batch_verify_permissions_for_models(
        models=verify_models,
        action=Action.UPDATE,
    )

    zen_store().create_tag_resource(tag_resource=tag_resource)


@router.post(
    BATCH,
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def batch_create_tag_resource(
    tag_resources: List[TagResourceRequest],
    _: AuthContext = Security(authorize),
) -> None:
    """Attach different tags to different resources.

    Args:
        tag_resources: A list of tag resource requests.
    """
    verify_models = []

    for tag_resource in tag_resources:
        # TODO: Optimize this to not append repeated models
        verify_models.append(zen_store().get_tag(tag_resource.tag_id))
        verify_models.append(
            _get_resource_model(
                tag_resource.resource_id, tag_resource.resource_type
            )
        )

    batch_verify_permissions_for_models(
        models=verify_models,
        action=Action.UPDATE,
    )

    for tag_resource in tag_resources:
        zen_store().create_tag_resource(tag_resource=tag_resource)


@router.delete(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_tag_resource(
    tag_id: UUID,
    resource_id: UUID,
    resource_type: TaggableResourceTypes,
    _: AuthContext = Security(authorize),
) -> None:
    """Detach a tag from a resource.

    Args:
        tag_id: The ID of the tag to delete.
        resource_id: The ID of the resource to delete.
        resource_type: The type of the resource to delete.
    """
    verify_models = []
    verify_models.append(zen_store().get_tag(tag_id))
    verify_models.append(_get_resource_model(resource_id, resource_type))

    batch_verify_permissions_for_models(
        models=verify_models,
        action=Action.UPDATE,
    )
    zen_store().delete_tag_resource(
        tag_id=tag_id, resource_id=resource_id, resource_type=resource_type
    )


@router.delete(
    BATCH,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def batch_delete_tag_resource(
    tag_resources: List[Tuple[UUID, UUID, TaggableResourceTypes]],
    _: AuthContext = Security(authorize),
) -> None:
    """Detach different tags from different resources.

    Args:
        tag_resources: A list of tag resource requests.
    """
    verify_models = []
    for tag_id, resource_id, resource_type in tag_resources:
        verify_models.append(zen_store().get_tag(tag_id))
        verify_models.append(_get_resource_model(resource_id, resource_type))

    batch_verify_permissions_for_models(
        models=verify_models,
        action=Action.UPDATE,
    )

    for tag_id, resource_id, resource_type in tag_resources:
        zen_store().delete_tag_resource(
            tag_id=tag_id, resource_id=resource_id, resource_type=resource_type
        )
