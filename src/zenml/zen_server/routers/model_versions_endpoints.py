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
"""Endpoint definitions for models."""

from typing import Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import (
    API,
    ARTIFACTS,
    MODEL_VERSION_ARTIFACTS,
    MODEL_VERSION_PIPELINE_RUNS,
    MODEL_VERSIONS,
    MODELS,
    RUNS,
    VERSION_1,
)
from zenml.models import (
    ModelVersionArtifactFilter,
    ModelVersionArtifactRequest,
    ModelVersionArtifactResponse,
    ModelVersionFilter,
    ModelVersionPipelineRunFilter,
    ModelVersionPipelineRunRequest,
    ModelVersionPipelineRunResponse,
    ModelVersionRequest,
    ModelVersionResponse,
    ModelVersionUpdate,
)
from zenml.models.v2.base.page import Page
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_create_entity,
    verify_permissions_and_delete_entity,
)
from zenml.zen_server.rbac.models import Action
from zenml.zen_server.rbac.utils import (
    dehydrate_page,
    dehydrate_response_model,
    verify_permission_for_model,
)
from zenml.zen_server.routers.models_endpoints import (
    router as model_router,
)
from zenml.zen_server.routers.projects_endpoints import workspace_router
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    set_filter_project_scope,
    zen_store,
)

#################
# Model Versions
#################


router = APIRouter(
    prefix=API + VERSION_1 + MODEL_VERSIONS,
    tags=["model_versions"],
    responses={401: error_response, 403: error_response},
)


@router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
# TODO: the workspace scoped endpoint is only kept for dashboard compatibility
# and can be removed after the migration
@workspace_router.post(
    "/{project_name_or_id}" + MODELS + "/{model_id}" + MODEL_VERSIONS,
    responses={401: error_response, 409: error_response, 422: error_response},
    deprecated=True,
    tags=["model_versions"],
)
@handle_exceptions
def create_model_version(
    model_version: ModelVersionRequest,
    model_id: Optional[UUID] = None,
    project_name_or_id: Optional[Union[str, UUID]] = None,
    _: AuthContext = Security(authorize),
) -> ModelVersionResponse:
    """Creates a model version.

    Args:
        model_version: Model version to create.
        model_id: Optional ID of the model.
        project_name_or_id: Optional name or ID of the project.

    Returns:
        The created model version.
    """
    if project_name_or_id:
        project = zen_store().get_project(project_name_or_id)
        model_version.project = project.id

    if model_id:
        model_version.model = model_id

    return verify_permissions_and_create_entity(
        request_model=model_version,
        create_method=zen_store().create_model_version,
    )


@model_router.get(
    "/{model_name_or_id}" + MODEL_VERSIONS,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_model_versions(
    model_version_filter_model: ModelVersionFilter = Depends(
        make_dependable(ModelVersionFilter)
    ),
    model_name_or_id: Optional[Union[str, UUID]] = None,
    hydrate: bool = False,
    auth_context: AuthContext = Security(authorize),
) -> Page[ModelVersionResponse]:
    """Get model versions according to query filters.

    Args:
        model_version_filter_model: Filter model used for pagination, sorting,
            filtering.
        model_name_or_id: Optional name or ID of the model.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.
        auth_context: The authentication context.

    Returns:
        The model versions according to query filters.

    Raises:
        ValueError: If the model is missing from the filter.
    """
    if model_name_or_id:
        model_version_filter_model.model = model_name_or_id

    if not model_version_filter_model.model:
        raise ValueError("Model missing from the filter")

    # A project scoped request must always be scoped to a specific
    # project. This is required for the RBAC check to work.
    set_filter_project_scope(model_version_filter_model)
    assert isinstance(model_version_filter_model.project, UUID)

    model = zen_store().get_model_by_name_or_id(
        model_version_filter_model.model,
        project=model_version_filter_model.project,
    )

    # Check read permissions on the model
    verify_permission_for_model(model, action=Action.READ)

    model_version_filter_model.configure_rbac(
        authenticated_user_id=auth_context.user.id
    )

    model_versions = zen_store().list_model_versions(
        model_version_filter_model=model_version_filter_model,
        hydrate=hydrate,
    )
    return dehydrate_page(model_versions)


@router.get(
    "/{model_version_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_model_version(
    model_version_id: UUID,
    hydrate: bool = True,
    _: AuthContext = Security(authorize),
) -> ModelVersionResponse:
    """Get a model version by ID.

    Args:
        model_version_id: id of the model version to be retrieved.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The model version with the given name or ID.
    """
    model_version = zen_store().get_model_version(
        model_version_id=model_version_id,
        hydrate=hydrate,
    )
    verify_permission_for_model(model_version.model, action=Action.READ)
    return dehydrate_response_model(model_version)


@router.put(
    "/{model_version_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_model_version(
    model_version_id: UUID,
    model_version_update_model: ModelVersionUpdate,
    _: AuthContext = Security(authorize),
) -> ModelVersionResponse:
    """Get all model versions by filter.

    Args:
        model_version_id: The ID of model version to be updated.
        model_version_update_model: The model version to be updated.

    Returns:
        An updated model version.
    """
    model_version = zen_store().get_model_version(model_version_id)

    if model_version_update_model.stage:
        # Make sure the user has permissions to promote the model
        verify_permission_for_model(model_version.model, action=Action.PROMOTE)

    verify_permission_for_model(model_version, action=Action.UPDATE)
    updated_model_version = zen_store().update_model_version(
        model_version_id=model_version_id,
        model_version_update_model=model_version_update_model,
    )

    return dehydrate_response_model(updated_model_version)


@router.delete(
    "/{model_version_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_model_version(
    model_version_id: UUID,
    _: AuthContext = Security(authorize),
) -> None:
    """Delete a model by name or ID.

    Args:
        model_version_id: The name or ID of the model version to delete.
    """
    verify_permissions_and_delete_entity(
        id=model_version_id,
        get_method=zen_store().get_model_version,
        delete_method=zen_store().delete_model_version,
    )


##########################
# Model Version Artifacts
##########################

model_version_artifacts_router = APIRouter(
    prefix=API + VERSION_1 + MODEL_VERSION_ARTIFACTS,
    tags=["model_version_artifacts"],
    responses={401: error_response},
)


@model_version_artifacts_router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_model_version_artifact_link(
    model_version_artifact_link: ModelVersionArtifactRequest,
    _: AuthContext = Security(authorize),
) -> ModelVersionArtifactResponse:
    """Create a new model version to artifact link.

    Args:
        model_version_artifact_link: The model version to artifact link to create.

    Returns:
        The created model version to artifact link.
    """
    model_version = zen_store().get_model_version(
        model_version_artifact_link.model_version
    )

    return verify_permissions_and_create_entity(
        request_model=model_version_artifact_link,
        create_method=zen_store().create_model_version_artifact_link,
        # Check for UPDATE permissions on the model version instead of the
        # model version artifact link
        surrogate_models=[model_version],
    )


@model_version_artifacts_router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_model_version_artifact_links(
    model_version_artifact_link_filter_model: ModelVersionArtifactFilter = Depends(
        make_dependable(ModelVersionArtifactFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[ModelVersionArtifactResponse]:
    """Get model version to artifact links according to query filters.

    Args:
        model_version_artifact_link_filter_model: Filter model used for
            pagination, sorting, filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The model version to artifact links according to query filters.
    """
    return zen_store().list_model_version_artifact_links(
        model_version_artifact_link_filter_model=model_version_artifact_link_filter_model,
        hydrate=hydrate,
    )


@router.delete(
    "/{model_version_id}"
    + ARTIFACTS
    + "/{model_version_artifact_link_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_model_version_artifact_link(
    model_version_id: UUID,
    model_version_artifact_link_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize),
) -> None:
    """Deletes a model version to artifact link.

    Args:
        model_version_id: ID of the model version containing the link.
        model_version_artifact_link_name_or_id: name or ID of the model
            version to artifact link to be deleted.
    """
    model_version = zen_store().get_model_version(model_version_id)
    verify_permission_for_model(model_version, action=Action.UPDATE)

    zen_store().delete_model_version_artifact_link(
        model_version_id,
        model_version_artifact_link_name_or_id,
    )


@router.delete(
    "/{model_version_id}" + ARTIFACTS,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_all_model_version_artifact_links(
    model_version_id: UUID,
    only_links: bool = True,
    _: AuthContext = Security(authorize),
) -> None:
    """Deletes all model version to artifact links.

    Args:
        model_version_id: ID of the model version containing links.
        only_links: Whether to only delete the link to the artifact.
    """
    model_version = zen_store().get_model_version(model_version_id)
    verify_permission_for_model(model_version, action=Action.UPDATE)

    zen_store().delete_all_model_version_artifact_links(
        model_version_id, only_links
    )


##############################
# Model Version Pipeline Runs
##############################

model_version_pipeline_runs_router = APIRouter(
    prefix=API + VERSION_1 + MODEL_VERSION_PIPELINE_RUNS,
    tags=["model_version_pipeline_runs"],
    responses={401: error_response},
)


@model_version_pipeline_runs_router.post(
    "",
    responses={401: error_response, 409: error_response, 422: error_response},
)
@handle_exceptions
def create_model_version_pipeline_run_link(
    model_version_pipeline_run_link: ModelVersionPipelineRunRequest,
    _: AuthContext = Security(authorize),
) -> ModelVersionPipelineRunResponse:
    """Create a new model version to pipeline run link.

    Args:
        model_version_pipeline_run_link: The model version to pipeline run link to create.

    Returns:
        - If Model Version to Pipeline Run Link already exists - returns the existing link.
        - Otherwise, returns the newly created model version to pipeline run link.
    """
    model_version = zen_store().get_model_version(
        model_version_pipeline_run_link.model_version, hydrate=False
    )

    return verify_permissions_and_create_entity(
        request_model=model_version_pipeline_run_link,
        create_method=zen_store().create_model_version_pipeline_run_link,
        # Check for UPDATE permissions on the model version instead of the
        # model version pipeline run link
        surrogate_models=[model_version],
    )


@model_version_pipeline_runs_router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_model_version_pipeline_run_links(
    model_version_pipeline_run_link_filter_model: ModelVersionPipelineRunFilter = Depends(
        make_dependable(ModelVersionPipelineRunFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[ModelVersionPipelineRunResponse]:
    """Get model version to pipeline run links according to query filters.

    Args:
        model_version_pipeline_run_link_filter_model: Filter model used for
            pagination, sorting, and filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The model version to pipeline run links according to query filters.
    """
    return zen_store().list_model_version_pipeline_run_links(
        model_version_pipeline_run_link_filter_model=model_version_pipeline_run_link_filter_model,
        hydrate=hydrate,
    )


@router.delete(
    "/{model_version_id}"
    + RUNS
    + "/{model_version_pipeline_run_link_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_model_version_pipeline_run_link(
    model_version_id: UUID,
    model_version_pipeline_run_link_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize),
) -> None:
    """Deletes a model version link.

    Args:
        model_version_id: name or ID of the model version containing the link.
        model_version_pipeline_run_link_name_or_id: name or ID of the model
            version link to be deleted.
    """
    model_version = zen_store().get_model_version(model_version_id)
    verify_permission_for_model(model_version, action=Action.UPDATE)

    zen_store().delete_model_version_pipeline_run_link(
        model_version_id=model_version_id,
        model_version_pipeline_run_link_name_or_id=model_version_pipeline_run_link_name_or_id,
    )
