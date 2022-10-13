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
"""Endpoint definitions for steps (and artifacts) of pipeline runs."""

from typing import List, Optional

from fastapi import APIRouter, Depends

from zenml.constants import API, ARTIFACTS, VERSION_1
from zenml.models.pipeline_models import ArtifactModel
from zenml.zen_server.auth import authorize
from zenml.zen_server.utils import error_response, handle_exceptions, zen_store

router = APIRouter(
    prefix=API + VERSION_1 + ARTIFACTS,
    tags=["artifacts"],
    dependencies=[Depends(authorize)],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=List[ArtifactModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def list_runs(
    artifact_uri: Optional[str] = None,
) -> List[ArtifactModel]:
    """Get artifacts according to query filters.

    Args:
        artifact_uri: The URI of the artifact by which to filter.

    Returns:
        The artifacts according to query filters.
    """
    return zen_store().list_artifacts(artifact_uri=artifact_uri)
