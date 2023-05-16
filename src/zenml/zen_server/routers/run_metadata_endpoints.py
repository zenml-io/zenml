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


from fastapi import APIRouter, Depends, Security

from zenml.constants import API, RUN_METADATA, VERSION_1
from zenml.enums import PermissionType
from zenml.models import RunMetadataResponseModel
from zenml.models.page_model import Page
from zenml.models.run_metadata_models import RunMetadataFilterModel
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.utils import (
    handle_exceptions,
    make_dependable,
    zen_store,
)

router = APIRouter(
    prefix=API + VERSION_1 + RUN_METADATA,
    tags=["run_metadata"],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=Page[RunMetadataResponseModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_run_metadata(
    run_metadata_filter_model: RunMetadataFilterModel = Depends(
        make_dependable(RunMetadataFilterModel)
    ),
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ]),
) -> Page[RunMetadataResponseModel]:
    """Get run metadata according to query filters.

    Args:
        run_metadata_filter_model: Filter model used for pagination, sorting,
            filtering.

    Returns:
        The pipeline runs according to query filters.
    """
    return zen_store().list_run_metadata(run_metadata_filter_model)
