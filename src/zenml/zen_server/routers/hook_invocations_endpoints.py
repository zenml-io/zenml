#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Endpoint definitions for hook invocations of pipeline runs."""

from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import (
    API,
    HOOK_INVOCATIONS,
    VERSION_1,
)
from zenml.models import (
    HookInvocationFilter,
    HookInvocationRequest,
    HookInvocationResponse,
    Page,
)
from zenml.zen_server.auth import (
    AuthContext,
    authorize,
)
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_create_entity,
)
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.rbac.utils import (
    batch_verify_permissions_for_models,
    dehydrate_page,
    dehydrate_response_model,
    get_allowed_resource_ids,
    verify_permission_for_model,
)
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    make_dependable,
    set_filter_project_scope,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + HOOK_INVOCATIONS,
    tags=["hook_invocations"],
    responses={401: error_response, 403: error_response},
)


@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def list_hook_invocations(
    hook_invocation_filter_model: HookInvocationFilter = Depends(
        make_dependable(HookInvocationFilter)
    ),
    hydrate: bool = False,
    auth_context: AuthContext = Security(authorize),
) -> Page[HookInvocationResponse]:
    """Get hook invocations according to query filters.

    Args:
        hook_invocation_filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.
        auth_context: Authentication context.

    Returns:
        The hook invocations according to query filters.
    """
    set_filter_project_scope(hook_invocation_filter_model)
    assert isinstance(hook_invocation_filter_model.project, UUID)

    allowed_pipeline_run_ids = get_allowed_resource_ids(
        resource_type=ResourceType.PIPELINE_RUN,
        project_id=hook_invocation_filter_model.project,
    )
    hook_invocation_filter_model.configure_rbac(
        authenticated_user_id=auth_context.user.id,
        pipeline_run_id=allowed_pipeline_run_ids,
    )

    page = zen_store().list_hook_invocations(
        hook_invocation_filter_model=hook_invocation_filter_model,
        hydrate=hydrate,
    )
    return dehydrate_page(page)


@router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def create_hook_invocation(
    hook_invocation: HookInvocationRequest,
    _: AuthContext = Security(authorize),
) -> HookInvocationResponse:
    """Create a hook invocation.

    Args:
        hook_invocation: The hook invocation to create.

    Returns:
        The created hook invocation.
    """
    pipeline_run = zen_store().get_run(
        hook_invocation.pipeline_run_id, hydrate=False
    )

    # The caller can only link output artifact versions they are allowed to
    # read, otherwise they could associate versions they cannot access.
    artifact_version_ids = {
        artifact_version_id
        for output in hook_invocation.outputs.values()
        for artifact_version_id in output
    }
    if artifact_version_ids:
        batch_verify_permissions_for_models(
            models=[
                zen_store().get_artifact_version(artifact_version_id)
                for artifact_version_id in artifact_version_ids
            ],
            action=Action.READ,
        )

    return verify_permissions_and_create_entity(
        request_model=hook_invocation,
        create_method=zen_store().create_hook_invocation,
        surrogate_models=[pipeline_run],
    )


@router.get(
    "/{hook_invocation_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper(deduplicate=True)
def get_hook_invocation(
    hook_invocation_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> HookInvocationResponse:
    """Get one specific hook invocation.

    Args:
        hook_invocation_id: ID of the hook invocation to get.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The hook invocation.
    """
    hook_invocation = zen_store().get_hook_invocation(
        hook_invocation_id, hydrate=hydrate
    )
    pipeline_run = zen_store().get_run(
        hook_invocation.pipeline_run_id, hydrate=False
    )
    verify_permission_for_model(pipeline_run, action=Action.READ)

    return dehydrate_response_model(hook_invocation)


@router.delete(
    "/{hook_invocation_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def delete_hook_invocation(
    hook_invocation_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Delete a hook invocation.

    Args:
        hook_invocation_id: ID of the hook invocation to delete.
    """
    hook_invocation = zen_store().get_hook_invocation(
        hook_invocation_id, hydrate=False
    )
    pipeline_run = zen_store().get_run(
        hook_invocation.pipeline_run_id, hydrate=False
    )
    verify_permission_for_model(pipeline_run, action=Action.UPDATE)

    zen_store().delete_hook_invocation(hook_invocation_id)
