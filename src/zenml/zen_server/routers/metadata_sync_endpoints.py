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
"""Endpoint definitions for metadata config."""

from asyncio.log import logger

from fastapi import APIRouter, Security

from zenml.constants import API, METADATA_SYNC, VERSION_1
from zenml.enums import PermissionType
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.utils import error_response, handle_exceptions, zen_store

router = APIRouter(
    prefix=API + VERSION_1 + METADATA_SYNC,
    tags=["metadata_sync"],
    responses={401: error_response},
)


@router.get(
    "",
    response_model=None,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def sync_runs(
    _: AuthContext = Security(authorize, scopes=[PermissionType.READ])
) -> None:
    """Sync pipeline runs."""
    try:
        zen_store()._sync_runs()
    except Exception:
        logger.exception("Failed to sync pipeline runs.")
