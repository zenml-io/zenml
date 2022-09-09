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
"""Util functions for the ZenServer."""

from typing import Any, List

from fastapi import Depends, HTTPException
from pydantic import BaseModel
from zenml.enums import StoreType

from zenml.config.global_config import GlobalConfiguration
from zenml.zen_stores.base_zen_store import BaseZenStore


# TODO(Stefan): figure out how not to populate the ZenStore with default
# user/stack and make this a method instead of a global variable
zen_store: BaseZenStore = GlobalConfiguration().zen_store
# We override track_analytics=False because we do not
# want to track anything server side.
zen_store.track_analytics = False

if zen_store.type == StoreType.REST:
    raise ValueError(
        "Server cannot be started with a REST store type. Make sure you "
        "configure ZenML to use a non-networked store backend "
        "when trying to start the ZenServer."
    )


class ErrorModel(BaseModel):
    """Base class for error responses."""

    detail: Any


error_response = dict(model=ErrorModel)


def error_detail(error: Exception) -> List[str]:
    """Convert an Exception to API representation.

    Args:
        error: Exception to convert.

    Returns:
        List of strings representing the error.
    """
    return [type(error).__name__] + [str(a) for a in error.args]


def not_found(error: Exception) -> HTTPException:
    """Convert an Exception to a HTTP 404 response.

    Args:
        error: Exception to convert.

    Returns:
        HTTPException with status code 404.
    """
    return HTTPException(status_code=404, detail=error_detail(error))


def conflict(error: Exception) -> HTTPException:
    """Convert an Exception to a HTTP 409 response.

    Args:
        error: Exception to convert.

    Returns:
        HTTPException with status code 409.
    """
    return HTTPException(status_code=409, detail=error_detail(error))
