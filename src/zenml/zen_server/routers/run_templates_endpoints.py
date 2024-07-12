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
"""Endpoint definitions for run templates."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Security

from zenml.config.pipeline_run_configuration import PipelineRunConfiguration
from zenml.constants import API, RUN_TEMPLATES, VERSION_1
from zenml.models import (
    Page,
    PipelineRunResponse,
    RunTemplateFilter,
    RunTemplateResponse,
    RunTemplateUpdate,
)
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_delete_entity,
    verify_permissions_and_get_entity,
    verify_permissions_and_list_entities,
    verify_permissions_and_update_entity,
)
from zenml.zen_server.rbac.models import Action, ResourceType
from zenml.zen_server.rbac.utils import verify_permission
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    server_config,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + RUN_TEMPLATES,
    tags=["run_templates"],
    responses={401: error_response, 403: error_response},
)


@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_run_templates(
    filter_model: RunTemplateFilter = Depends(
        make_dependable(RunTemplateFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[RunTemplateResponse]:
    """Get a page of run templates.

    Args:
        filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        Page of run templates.
    """
    return verify_permissions_and_list_entities(
        filter_model=filter_model,
        resource_type=ResourceType.RUN_TEMPLATE,
        list_method=zen_store().list_run_templates,
        hydrate=hydrate,
    )


@router.get(
    "/{template_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_run_template(
    template_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> RunTemplateResponse:
    """Get a run template.

    Args:
        template_id: ID of the run template to get.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The run template.
    """
    return verify_permissions_and_get_entity(
        id=template_id,
        get_method=zen_store().get_run_template,
        hydrate=hydrate,
    )


@router.put(
    "/{template_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_run_template(
    template_id: UUID,
    update: RunTemplateUpdate,
    _: AuthContext = Security(authorize),
) -> RunTemplateResponse:
    """Update a run template.

    Args:
        template_id: ID of the run template to get.
        update: The updates to apply.

    Returns:
        The updated run template.
    """
    return verify_permissions_and_update_entity(
        id=template_id,
        update_model=update,
        get_method=zen_store().get_run_template,
        update_method=zen_store().update_run_template,
    )


@router.delete(
    "/{template_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_run_template(
    template_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Delete a run template.

    Args:
        template_id: ID of the run template to delete.
    """
    verify_permissions_and_delete_entity(
        id=template_id,
        get_method=zen_store().get_run_template,
        delete_method=zen_store().delete_run_template,
    )


if server_config().workload_manager_enabled:

    @router.post(
        "/{template_id}/runs",
        responses={
            401: error_response,
            404: error_response,
            422: error_response,
        },
    )
    @handle_exceptions
    def create_deployment_run(
        template_id: UUID,
        background_tasks: BackgroundTasks,
        config: Optional[PipelineRunConfiguration] = None,
        auth_context: AuthContext = Security(authorize),
    ) -> PipelineRunResponse:
        """Run a pipeline from a template.

        Args:
            template_id: The ID of the template.
            background_tasks: Background tasks.
            config: Configuration for the pipeline run.
            auth_context: Authentication context.

        Returns:
            The created pipeline run.
        """
        from zenml.zen_server.pipeline_deployment.utils import run_template

        template = verify_permissions_and_get_entity(
            id=template_id,
            get_method=zen_store().get_run_template,
            hydrate=True,
        )

        verify_permission(
            resource_type=ResourceType.PIPELINE_DEPLOYMENT,
            action=Action.CREATE,
        )
        verify_permission(
            resource_type=ResourceType.PIPELINE_RUN, action=Action.CREATE
        )

        return run_template(
            template=template,
            auth_context=auth_context,
            background_tasks=background_tasks,
            run_config=config,
        )
