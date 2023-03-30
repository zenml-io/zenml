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
"""REST API exception handling."""

from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Type

import requests
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from zenml.exceptions import (
    AuthorizationException,
    DoesNotExistException,
    DuplicateRunNameError,
    EntityExistsError,
    IllegalOperationError,
    SecretExistsError,
    StackComponentExistsError,
    StackExistsError,
    ValidationError,
    ZenKeyError,
)

if TYPE_CHECKING:
    from fastapi import HTTPException


class ErrorModel(BaseModel):
    """Base class for error responses."""

    detail: Any


error_response = dict(model=ErrorModel)

# Map exceptions to HTTP status codes. This is used in two ways:
# 1. When an exception is raised in the server, the exception is converted to a
#   error response with the appropriate status code and with the exception class
#   name and arguments as the response body.
# 2. When HTTP error response is received by the client, the error response is
#  converted back to an exception based on the status code and the exception
#  class name and arguments are extracted from the response body.
#
# NOTE: The order of the exceptions is important. The first matching
# exception will be used, so the more specific exceptions should be
# listed first. For error responses that cannot be unpacked into an
# exception, the last (the more generic) exception in the list corresponding
# to the status code will be used.
REST_API_EXCEPTIONS: List[Tuple[Type[Exception], int]] = [
    # 409 Conflict
    (StackExistsError, 409),
    (StackComponentExistsError, 409),
    (SecretExistsError, 409),
    (DuplicateRunNameError, 409),
    (EntityExistsError, 409),
    # 403 Forbidden
    (IllegalOperationError, 403),
    # 401 Unauthorized
    (AuthorizationException, 401),
    # 404 Not Found
    (DoesNotExistException, 404),
    (ZenKeyError, 404),
    (KeyError, 404),
    # 400 Bad Request
    (PydanticValidationError, 400),
    (ValidationError, 400),
    (ValueError, 400),
    # 422 Unprocessable Entity
    (NotImplementedError, 422),
    (PydanticValidationError, 422),
    (ValueError, 400),
    # 500 Internal Server Error
    (RuntimeError, 500),
    # 501 Not Implemented,
    (NotImplementedError, 501),
]


def error_detail(error: Exception) -> List[str]:
    """Convert an Exception to API representation.

    Args:
        error: Exception to convert.

    Returns:
        List of strings representing the error.
    """
    return [type(error).__name__, str(error)]


def http_exception_from_error(error: Exception) -> "HTTPException":
    """Convert an Exception to a HTTPException.

    Args:
        error: Exception to convert.

    Returns:
        HTTPException with the appropriate status code and error detail.
    """
    from fastapi import HTTPException

    for exception, status_code in REST_API_EXCEPTIONS:
        if isinstance(error, exception):
            return HTTPException(
                status_code=status_code, detail=error_detail(error)
            )
    else:
        return HTTPException(status_code=500, detail=error_detail(error))


def exception_from_response(
    response: requests.Response,
) -> Optional[Exception]:
    """Convert an error HTTP response to an exception.

    Args:
        response: HTTP error response to convert.

    Returns:
        Exception with the appropriate type and arguments, or None if the
        response does not contain an error or the response cannot be unpacked
        into an exception.
    """

    def unpack_exc() -> Tuple[Optional[str], str]:
        """Unpack the response body into an exception name and message.

        Returns:
            Tuple of exception name and message.
        """
        try:
            detail = response.json().get("detail", response.text)
        except requests.exceptions.JSONDecodeError:
            return None, response.text

        # The detail should be a list of strings encoding the exception
        # class name and the exception message
        if not isinstance(detail, list):
            return None, response.text

        # First detail item is the exception class name
        if len(detail) < 1 or not isinstance(detail[0], str):
            return None, response.text

        # Remaining detail items are the exception arguments
        message = ": ".join([str(arg) for arg in detail[1:]])
        return detail[0], message

    exc_name, exc_msg = unpack_exc()
    default_exc: Optional[Type[Exception]] = None

    for exception, status_code in REST_API_EXCEPTIONS:
        if response.status_code != status_code:
            continue
        default_exc = exception
        if exc_name == exception.__name__:
            break
    else:
        if default_exc is None:
            return None

        exception = default_exc

    return exception(exc_msg)
