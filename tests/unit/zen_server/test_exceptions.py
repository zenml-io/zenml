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

import json
from typing import Type

import pytest
import requests
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from zenml.exceptions import (
    AuthorizationException,
    DoesNotExistException,
    DuplicateRunNameError,
    EntityExistsError,
    IllegalOperationError,
    ValidationError,
    ZenKeyError,
)
from zenml.zen_server.exceptions import (
    exception_from_response,
    http_exception_from_error,
)


class DummyExceptionModel(BaseModel):
    """Test exception model."""

    test_attr: str


def get_exception(exception_type: Type[Exception]) -> Exception:
    """Get a dummy exception instance."""
    if exception_type == PydanticValidationError:
        try:
            DummyExceptionModel()
        except PydanticValidationError as e:
            return e
    else:
        return exception_type("test message")


@pytest.mark.parametrize(
    "exception_type",
    [
        EntityExistsError,
        EntityExistsError,
        EntityExistsError,
        DuplicateRunNameError,
        EntityExistsError,
        IllegalOperationError,
        AuthorizationException,
        DoesNotExistException,
        ZenKeyError,
        KeyError,
        PydanticValidationError,
        ValidationError,
        ValueError,
        RuntimeError,
        NotImplementedError,
    ],
)
def test_http_exception_reconstruction(exception_type: Type[Exception]):
    """Test the HTTP exception reconstruction."""

    exception = get_exception(exception_type)
    http_exception = http_exception_from_error(exception)

    response = requests.Response()
    response.status_code = http_exception.status_code
    response._content = json.dumps(dict(detail=http_exception.detail)).encode()
    reconstructed_exception = exception_from_response(response)

    assert reconstructed_exception is not None
    if exception_type is PydanticValidationError:
        # PydanticValidationError is a subclass of ValueError and we don't
        # encode PydanticValidationError explicitly in the response
        assert reconstructed_exception.__class__ is ValueError
        assert reconstructed_exception.args == (str(exception),)
    elif exception_type is KeyError:
        # KeyError is a bit of an oddball because it adds quotes around the
        # message
        assert reconstructed_exception.__class__ is exception_type
        assert reconstructed_exception.args == (f"'{exception.args[0]}'",)
    else:
        assert reconstructed_exception.__class__ is exception_type
        assert reconstructed_exception.args == exception.args


@pytest.mark.parametrize(
    "exception_type",
    [
        EntityExistsError,
        EntityExistsError,
        EntityExistsError,
        DuplicateRunNameError,
        EntityExistsError,
        IllegalOperationError,
        AuthorizationException,
        DoesNotExistException,
        ZenKeyError,
        KeyError,
        ValidationError,
        ValueError,
        RuntimeError,
        NotImplementedError,
    ],
)
def test_http_exception_inheritance(exception_type: Type[Exception]):
    """Test the HTTP exception inheritance with arbitrary exception types."""

    class SampleException(exception_type):
        """Sample exception."""

    exception = get_exception(SampleException)
    http_exception = http_exception_from_error(exception)

    response = requests.Response()
    response.status_code = http_exception.status_code
    response._content = json.dumps(dict(detail=http_exception.detail)).encode()
    reconstructed_exception = exception_from_response(response)

    assert reconstructed_exception is not None
    if exception_type is KeyError:
        # KeyError is a bit of an oddball because it adds quotes around the
        # message
        assert reconstructed_exception.__class__ is exception_type
        assert reconstructed_exception.args == (f"'{exception.args[0]}'",)
    else:
        assert reconstructed_exception.__class__ is exception_type
        assert reconstructed_exception.args == exception.args


def test_reconstruct_unknown_exception_as_runtime_error():
    """Test that unknown exceptions are reconstructed as RuntimeError."""

    class SampleException(Exception):
        """Sample exception."""

    exception = get_exception(SampleException)
    http_exception = http_exception_from_error(exception)

    response = requests.Response()
    response.status_code = http_exception.status_code
    response._content = json.dumps(dict(detail=http_exception.detail)).encode()
    reconstructed_exception = exception_from_response(response)

    assert reconstructed_exception is not None
    assert reconstructed_exception.__class__ is RuntimeError
    assert reconstructed_exception.args == exception.args


@pytest.mark.parametrize(
    ["error_code", "exception_type"],
    [
        (409, EntityExistsError),
        (403, IllegalOperationError),
        (401, AuthorizationException),
        (404, KeyError),
        (400, ValueError),
        (422, ValueError),
        (500, RuntimeError),
        (501, NotImplementedError),
    ],
)
def test_unpack_unknown_error(error_code, exception_type):
    """Test that arbitrary errors are properly reconstructed."""

    response = requests.Response()
    response.status_code = error_code
    response._content = "error message".encode()
    reconstructed_exception = exception_from_response(response)

    assert reconstructed_exception is not None
    assert reconstructed_exception.__class__ is exception_type
    assert reconstructed_exception.args == ("error message",)

    response = requests.Response()
    response.status_code = error_code
    response._content = json.dumps(dict(err="error message")).encode()
    reconstructed_exception = exception_from_response(response)

    assert reconstructed_exception is not None
    assert reconstructed_exception.__class__ is exception_type
    assert reconstructed_exception.args == ('{"err": "error message"}',)

    response = requests.Response()
    response.status_code = error_code
    response._content = json.dumps(dict(detail="error message")).encode()
    reconstructed_exception = exception_from_response(response)

    assert reconstructed_exception is not None
    assert reconstructed_exception.__class__ is exception_type
    assert reconstructed_exception.args == ("error message",)

    response = requests.Response()
    response.status_code = error_code
    response._content = json.dumps(
        dict(detail=["FakeError", "error message"])
    ).encode()
    reconstructed_exception = exception_from_response(response)

    assert reconstructed_exception is not None
    assert reconstructed_exception.__class__ is exception_type
    assert reconstructed_exception.args == ("error message",)

    response = requests.Response()
    response.status_code = error_code
    response._content = json.dumps(
        [exception_type.__name__, "error message"]
    ).encode()
    reconstructed_exception = exception_from_response(response)

    assert reconstructed_exception is not None
    assert reconstructed_exception.__class__ is exception_type
    assert reconstructed_exception.args == ("error message",)
