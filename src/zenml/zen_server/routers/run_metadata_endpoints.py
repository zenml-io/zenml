#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Endpoint definitions for run metadata."""


from uuid import UUID

from fastapi import APIRouter, Depends, Security

from zenml.constants import API, RUN_METADATA, VERSION_1
from zenml.models import Page, RunMetadataFilter, RunMetadataResponse
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_list_entities,
)
from zenml.zen_server.rbac.models import ResourceType
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + RUN_METADATA,
    tags=["run_metadata"],
    responses={401: error_response, 403: error_response},
)


@router.get(
    "",
    response_model=Page[RunMetadataResponse],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_run_metadata(
    run_metadata_filter_model: RunMetadataFilter = Depends(
        make_dependable(RunMetadataFilter)
    ),
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> Page[RunMetadataResponse]:
    """Get run metadata according to query filters.

    Args:
        run_metadata_filter_model: Filter model used for pagination, sorting,
            filtering.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The pipeline runs according to query filters.
    """
    return verify_permissions_and_list_entities(
        filter_model=run_metadata_filter_model,
        resource_type=ResourceType.RUN_METADATA,
        list_method=zen_store().list_run_metadata,
        hydrate=hydrate,
    )


@router.get(
    "/{run_metadata_id}",
    response_model=RunMetadataResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_run_metadata(
    run_metadata_id: UUID,
    hydrate: bool = False,
    _: AuthContext = Security(authorize),
) -> RunMetadataResponse:
    """Get run metadata by ID.

    Args:
        run_metadata_id: The ID of run metadata.
        hydrate: Flag deciding whether to hydrate the output model(s)
            by including metadata fields in the response.

    Returns:
        The run metadata response.
    """
    return zen_store().get_run_metadata(
        run_metadata_id=run_metadata_id, hydrate=hydrate
    )
