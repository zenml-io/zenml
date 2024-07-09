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

from zenml.exceptions import (
    AuthorizationException,
    DoesNotExistException,
    DuplicateRunNameError,
    EntityExistsError,
    IllegalOperationError,
    MethodNotAllowedError,
    SecretExistsError,
    StackComponentExistsError,
    StackExistsError,
    SubscriptionUpgradeRequiredError,
    ValidationError,
    ZenKeyError,
)

if TYPE_CHECKING:
    from fastapi import HTTPException


class ErrorModel(BaseModel):
    """Base class for error responses."""

    detail: Optional[Any] = None


error_response = dict(model=ErrorModel)

# Associates exceptions to HTTP status codes. This is used in two ways and the
# order of the exceptions is important in both cases:
#
# 1. In `http_exception_from_error`, when an exception is raised in the server,
# the exception is converted to a error response with the appropriate status
# code and with the exception class name and arguments as the response body. The
# list of entries is traversed and the first entry that is the same as the
# raised exception is used. If no entry is found, the most specific exception
# that is a subclass of the raised exception is used. You should therefore
# order the exceptions from the most specific to the most generic.
#
# 2. In `exception_from_response`, when an HTTP error response is received by
# the client, the error response is converted back to an exception based on the
# status code and the exception class name and arguments extracted from the
# response body. If the exception name in the body is not found in the list of
# exceptions associated with the status code, the last (the more generic)
# exception in the list corresponding to the status code will be used. The list
# of exceptions associated with a status code should have a default exception
# as the last entry, to be used as a fallback.
#
# An exception may be associated with multiple status codes if the same
# exception can be reconstructed from two or more HTTP error responses with
# different status codes (e.g. `ValueError` and the 400 and 422 status codes).
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
    # 402 Payment required
    (SubscriptionUpgradeRequiredError, 402),
    # 404 Not Found
    (DoesNotExistException, 404),
    (ZenKeyError, 404),
    (KeyError, 404),
    # 400 Bad Request
    (ValidationError, 400),
    (ValueError, 400),
    # 422 Unprocessable Entity
    (ValueError, 422),
    # 500 Internal Server Error
    (RuntimeError, 500),
    # 501 Not Implemented,
    (NotImplementedError, 501),
    # 405 Method Not Allowed
    (MethodNotAllowedError, 405),
]


def error_detail(
    error: Exception, exception_type: Optional[Type[Exception]] = None
) -> List[str]:
    """Convert an Exception to API representation.

    Args:
        error: Exception to convert.
        exception_type: Exception type to use in the error response instead of
            the type of the supplied exception. This is useful when the raised
            exception is a subclass of an exception type that is properly
            handled by the REST API.

    Returns:
        List of strings representing the error.
    """
    class_name = (
        exception_type.__name__ if exception_type else type(error).__name__
    )
    return [class_name, str(error)]


def http_exception_from_error(error: Exception) -> "HTTPException":
    """Convert an Exception to a HTTP error response.

    Uses the REST_API_EXCEPTIONS list to determine the appropriate status code
    associated with the exception type. The exception class name and arguments
    are embedded in the HTTP error response body.

    The lookup uses the first occurrence of the exception type in the list. If
    the exception type is not found in the list, the lookup uses `isinstance`
    to determine the most specific exception type corresponding to the supplied
    exception. This allows users to call this method with exception types that
    are not directly listed in the REST_API_EXCEPTIONS list.

    Args:
        error: Exception to convert.

    Returns:
        HTTPException with the appropriate status code and error detail.
    """
    from fastapi import HTTPException

    status_code = 0
    matching_exception_type: Optional[Type[Exception]] = None

    for exception_type, exc_status_code in REST_API_EXCEPTIONS:
        if error.__class__ is exception_type:
            # Found an exact match
            matching_exception_type = exception_type
            status_code = exc_status_code
            break
        if isinstance(error, exception_type):
            # Found a matching exception
            if not matching_exception_type:
                # This is the first matching exception, so keep it
                matching_exception_type = exception_type
                status_code = exc_status_code
                continue

            # This is not the first matching exception, so check if it is more
            # specific than the previous matching exception
            if issubclass(
                exception_type,
                matching_exception_type,
            ):
                matching_exception_type = exception_type
                status_code = exc_status_code

    # When the matching exception is not found in the list, a 500 Internal
    # Server Error is returned
    status_code = status_code or 500
    matching_exception_type = matching_exception_type or RuntimeError

    return HTTPException(
        status_code=status_code,
        detail=error_detail(error, matching_exception_type),
    )


def exception_from_response(
    response: requests.Response,
) -> Optional[Exception]:
    """Convert an error HTTP response to an exception.

    Uses the REST_API_EXCEPTIONS list to determine the appropriate exception
    class to use based on the response status code and the exception class name
    embedded in the response body.

    The last entry in the list of exceptions associated with a status code is
    used as a fallback if the exception class name in the response body is not
    found in the list.

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
            response_json = response.json()
        except requests.exceptions.JSONDecodeError:
            return None, response.text

        if isinstance(response_json, dict):
            detail = response_json.get("detail", response.text)
        else:
            detail = response_json

        # The detail can also be a single string
        if isinstance(detail, str):
            return None, detail

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
            # An entry was found that is an exact match for both the status
            # code and the exception class name.
            break
    else:
        # The exception class name extracted from the response body was not
        # found in the list of exceptions associated with the status code, so
        # use the last entry as a fallback.
        if default_exc is None:
            return None

        exception = default_exc

    return exception(exc_msg)
