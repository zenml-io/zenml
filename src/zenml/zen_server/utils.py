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
"""Util functions for the ZenML Server."""

import os
from functools import wraps
from typing import Any, Callable, List, Optional, TypeVar, cast

from fastapi import HTTPException
from pydantic import BaseModel

from zenml.config.global_config import GlobalConfiguration
from zenml.constants import ENV_ZENML_SERVER_ROOT_URL_PATH
from zenml.enums import StoreType
from zenml.exceptions import (
    EntityExistsError,
    IllegalOperationError,
    NotAuthorizedError,
    StackComponentExistsError,
    StackExistsError,
)
from zenml.logger import get_logger
from zenml.zen_stores.base_zen_store import BaseZenStore

logger = get_logger(__name__)


ROOT_URL_PATH = os.getenv(ENV_ZENML_SERVER_ROOT_URL_PATH, "")


_zen_store: Optional[BaseZenStore] = None


def zen_store() -> BaseZenStore:
    """Initialize the ZenML Store.

    Returns:
        The ZenML Store.

    Raises:
        RuntimeError: If the ZenML Store has not been initialized.
    """
    global _zen_store
    if _zen_store is None:
        raise RuntimeError("ZenML Store not initialized")
    return _zen_store


def initialize_zen_store() -> None:
    """Initialize the ZenML Store.

    Raises:
        ValueError: If the ZenML Store is using a REST back-end.
    """
    global _zen_store

    logger.debug("Initializing ZenML Store for FastAPI...")
    _zen_store = GlobalConfiguration().zen_store

    # We override track_analytics=False because we do not
    # want to track anything server side.
    _zen_store.track_analytics = False

    if _zen_store.type == StoreType.REST:
        raise ValueError(
            "Server cannot be started with a REST store type. Make sure you "
            "configure ZenML to use a non-networked store backend "
            "when trying to start the ZenML Server."
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


def not_authorized(error: Exception) -> HTTPException:
    """Convert an Exception to a HTTP 401 response.

    Args:
        error: Exception to convert.

    Returns:
        HTTPException with status code 401.
    """
    return HTTPException(status_code=401, detail=error_detail(error))


def forbidden(error: Exception) -> HTTPException:
    """Convert an Exception to a HTTP 403 response.

    Args:
        error: Exception to convert.

    Returns:
        HTTPException with status code 403.
    """
    return HTTPException(status_code=403, detail=error_detail(error))


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


def unprocessable(error: Exception) -> HTTPException:
    """Convert an Exception to a HTTP 409 response.

    Args:
        error: Exception to convert.

    Returns:
        HTTPException with status code 422.
    """
    return HTTPException(status_code=422, detail=error_detail(error))


F = TypeVar("F", bound=Callable[..., Any])


def handle_exceptions(func: F) -> F:
    """Decorator to handle exceptions in the API.

    Args:
        func: Function to decorate.

    Returns:
        Decorated function.
    """

    @wraps(func)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except NotAuthorizedError as error:
            logger.exception("Authorization error")
            raise not_authorized(error) from error
        except KeyError as error:
            logger.exception("Entity not found")
            raise not_found(error) from error
        except (
            StackExistsError,
            StackComponentExistsError,
            EntityExistsError,
        ) as error:
            logger.exception("Entity already exists")
            raise conflict(error) from error
        except IllegalOperationError as error:
            logger.exception("Illegal operation")
            raise forbidden(error) from error
        except ValueError as error:
            logger.exception("Validation error")
            raise unprocessable(error) from error

    return cast(F, decorated)
