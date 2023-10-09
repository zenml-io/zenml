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

from typing import Union
from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import (
    API,
    ARTIFACTS,
    LATEST_MODEL_VERSION_PLACEHOLDER,
    MODEL_VERSIONS,
    MODELS,
    RUNS,
    VERSION_1,
)
from zenml.enums import ModelStages, PermissionType
from zenml.models import (
    ModelFilterModel,
    ModelResponseModel,
    ModelUpdateModel,
    ModelVersionArtifactFilterModel,
    ModelVersionArtifactResponseModel,
    ModelVersionFilterModel,
    ModelVersionPipelineRunFilterModel,
    ModelVersionPipelineRunResponseModel,
    ModelVersionResponseModel,
    ModelVersionUpdateModel,
)
from zenml.models.page_model import Page
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    zen_store,
)

#########
# Models
#########

router = APIRouter(
    prefix=API + VERSION_1 + MODELS,
    tags=["models"],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=Page[ModelResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_models(
    model_filter_model: ModelFilterModel = Depends(
        make_dependable(ModelFilterModel)
    ),
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> Page[ModelResponseModel]:
    """Get models according to query filters.

    Args:
        model_filter_model: Filter model used for pagination, sorting,
            filtering


    Returns:
        The models according to query filters.
    """
    return zen_store().list_models(
        model_filter_model=model_filter_model,
    )


@router.get(
    "/{model_name_or_id}",
    response_model=ModelResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_model(
    model_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> ModelResponseModel:
    """Get a model by name or ID.

    Args:
        model_name_or_id: The name or ID of the model to get.

    Returns:
        The model with the given name or ID.
    """
    return zen_store().get_model(model_name_or_id)


@router.put(
    "/{model_id}",
    response_model=ModelResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_model(
    model_id: UUID,
    model_update: ModelUpdateModel,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> ModelResponseModel:
    """Updates a model.

    Args:
        model_id: Name of the stack.
        model_update: Stack to use for the update.

    Returns:
        The updated model.
    """
    return zen_store().update_model(
        model_id=model_id,
        model_update=model_update,
    )


@router.delete(
    "/{model_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_model(
    model_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> None:
    """Delete a model by name or ID.

    Args:
        model_name_or_id: The name or ID of the model to delete.
    """
    zen_store().delete_model(model_name_or_id)


#################
# Model Versions
#################


@router.get(
    "/{model_name_or_id}" + MODEL_VERSIONS,
    response_model=Page[ModelVersionResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_model_versions(
    model_version_filter_model: ModelVersionFilterModel = Depends(
        make_dependable(ModelVersionFilterModel)
    ),
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> Page[ModelVersionResponseModel]:
    """Get model versions according to query filters.

    Args:
        model_version_filter_model: Filter model used for pagination, sorting,
            filtering

    Returns:
        The model versions according to query filters.
    """
    return zen_store().list_model_versions(
        model_version_filter_model=model_version_filter_model,
    )


@router.get(
    "/{model_name_or_id}"
    + MODEL_VERSIONS
    + "/{model_version_name_or_number_or_id}",
    response_model=ModelVersionResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_model_version(
    model_name_or_id: Union[str, UUID],
    model_version_name_or_number_or_id: Union[
        str, int, UUID, ModelStages
    ] = LATEST_MODEL_VERSION_PLACEHOLDER,
    is_number: bool = False,
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> ModelVersionResponseModel:
    """Get a model version by name or ID.

    Args:
        model_name_or_id: The name or ID of the model containing version.
        model_version_name_or_number_or_id: name, id, stage or number of the model version to be retrieved.
                If skipped latest version will be retrieved.
        is_number: If the model_version_name_or_number_or_id is a version number

    Returns:
        The model version with the given name or ID.
    """
    return zen_store().get_model_version(
        model_name_or_id,
        model_version_name_or_number_or_id
        if not is_number
        else int(model_version_name_or_number_or_id),
    )


@router.put(
    "/{model_id}" + MODEL_VERSIONS + "/{model_version_id}",
    response_model=ModelVersionResponseModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def update_model_version(
    model_version_id: UUID,
    model_version_update_model: ModelVersionUpdateModel,
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> ModelVersionResponseModel:
    """Get all model versions by filter.

    Args:
        model_version_id: The ID of model version to be updated.
        model_version_update_model: The model version to be updated.

    Returns:
        An updated model version.
    """
    return zen_store().update_model_version(
        model_version_id=model_version_id,
        model_version_update_model=model_version_update_model,
    )


@router.delete(
    "/{model_name_or_id}" + MODEL_VERSIONS + "/{model_version_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_model_version(
    model_name_or_id: Union[str, UUID],
    model_version_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> None:
    """Delete a model by name or ID.

    Args:
        model_name_or_id: The name or ID of the model containing version.
        model_version_name_or_id: The name or ID of the model version to delete.
    """
    zen_store().delete_model_version(
        model_name_or_id, model_version_name_or_id
    )


##########################
# Model Version Artifacts
##########################


@router.get(
    "/{model_name_or_id}"
    + MODEL_VERSIONS
    + "/{model_version_name_or_id}"
    + ARTIFACTS,
    response_model=Page[ModelVersionArtifactResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_model_version_artifact_links(
    model_version_artifact_link_filter_model: ModelVersionArtifactFilterModel = Depends(
        make_dependable(ModelVersionArtifactFilterModel)
    ),
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> Page[ModelVersionArtifactResponseModel]:
    """Get model version to artifact links according to query filters.

    Args:
        model_version_artifact_link_filter_model: Filter model used for pagination, sorting,
            filtering

    Returns:
        The model version to artifact links according to query filters.
    """
    return zen_store().list_model_version_artifact_links(
        model_version_artifact_link_filter_model=model_version_artifact_link_filter_model,
    )


@router.delete(
    "/{model_name_or_id}"
    + MODEL_VERSIONS
    + "/{model_version_name_or_id}"
    + ARTIFACTS
    + "/{model_version_artifact_link_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_model_version_artifact_link(
    model_name_or_id: Union[str, UUID],
    model_version_name_or_id: Union[str, UUID],
    model_version_artifact_link_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> None:
    """Deletes a model version link.

    Args:
        model_name_or_id: name or ID of the model containing the model version.
        model_version_name_or_id: name or ID of the model version containing the link.
        model_version_artifact_link_name_or_id: name or ID of the model version to artifact link to be deleted.
    """
    zen_store().delete_model_version_artifact_link(
        model_name_or_id,
        model_version_name_or_id,
        model_version_artifact_link_name_or_id,
    )


##############################
# Model Version Pipeline Runs
##############################


@router.get(
    "/{model_name_or_id}"
    + MODEL_VERSIONS
    + "/{model_version_name_or_id}"
    + RUNS,
    response_model=Page[ModelVersionPipelineRunResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_model_version_pipeline_run_links(
    model_version_pipeline_run_link_filter_model: ModelVersionPipelineRunFilterModel = Depends(
        make_dependable(ModelVersionPipelineRunFilterModel)
    ),
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> Page[ModelVersionPipelineRunResponseModel]:
    """Get model version to pipeline run links according to query filters.

    Args:
        model_version_pipeline_run_link_filter_model: Filter model used for pagination, sorting,
            and filtering

    Returns:
        The model version to pipeline run links according to query filters.
    """
    return zen_store().list_model_version_pipeline_run_links(
        model_version_pipeline_run_link_filter_model=model_version_pipeline_run_link_filter_model,
    )


@router.delete(
    "/{model_name_or_id}"
    + MODEL_VERSIONS
    + "/{model_version_name_or_id}"
    + RUNS
    + "/{model_version_pipeline_run_link_name_or_id}",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def delete_model_version_pipeline_run_link(
    model_name_or_id: Union[str, UUID],
    model_version_name_or_id: Union[str, UUID],
    model_version_pipeline_run_link_name_or_id: Union[str, UUID],
    _: AuthContext = Security(authorize, scopes=[PermissionType.WRITE]),
) -> None:
    """Deletes a model version link.

    Args:
        model_name_or_id: name or ID of the model containing the model version.
        model_version_name_or_id: name or ID of the model version containing the link.
        model_version_pipeline_run_link_name_or_id: name or ID of the model version link to be deleted.
    """
    zen_store().delete_model_version_pipeline_run_link(
        model_name_or_id,
        model_version_name_or_id,
        model_version_pipeline_run_link_name_or_id,
    )
