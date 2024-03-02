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
"""Endpoint definitions for authentication (login)."""

from fastapi import APIRouter

import zenml
from zenml.constants import API, INFO, VERSION_1
from zenml.models import ServerModel
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.utils import handle_exceptions, zen_store

router = APIRouter(
    prefix=API + VERSION_1,
    tags=["server"],
    responses={401: error_response},
)


@router.get("/version")
def version() -> str:
    """Get version of the server.

    Returns:
        String representing the version of the server.
    """
    return zenml.__version__


@router.get(
    INFO,
    response_model=ServerModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def server_info() -> ServerModel:
    """Get information about the server.

    Returns:
        Information about the server.
    """
    return zen_store().get_store_info()
