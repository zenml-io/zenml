#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Tests for privacy-safe analytics error classification."""

from zenml.analytics.error_classification import (
    CATEGORY_AUTH,
    CATEGORY_CONFIG,
    CATEGORY_CONNECTIVITY,
    CATEGORY_RESOURCE,
    CATEGORY_USER_CODE,
    classify_error,
)
from zenml.exceptions import AuthorizationException, StackValidationError


def _classify(exc: BaseException) -> dict:
    """Raise and classify an exception so it has a real traceback."""
    try:
        raise exc
    except BaseException as e:  # noqa: B902
        return classify_error(type(e), e, e.__traceback__)


def test_no_exception_returns_empty() -> None:
    """Classification of a non-failure is an empty dict (no labels added)."""
    assert classify_error(None, None, None) == {}


def test_returns_closed_vocabulary_keys() -> None:
    """Every classified error yields exactly the three safe labels."""
    result = _classify(ValueError("boom"))
    assert set(result) == {
        "error_category",
        "error_origin",
        "error_fingerprint",
    }


def test_zenml_exceptions_are_config() -> None:
    """ZenML's own exceptions are treated as config/usage problems."""
    assert _classify(StackValidationError("x"))["error_category"] == (
        CATEGORY_CONFIG
    )


def test_authorization_exception_is_auth() -> None:
    """Authorization errors are categorised as auth."""
    assert _classify(AuthorizationException("x"))["error_category"] == (
        CATEGORY_AUTH
    )


def test_connectivity_errors() -> None:
    """Builtin connection/timeout errors map to connectivity."""
    assert _classify(ConnectionError())["error_category"] == (
        CATEGORY_CONNECTIVITY
    )
    assert _classify(TimeoutError())["error_category"] == (
        CATEGORY_CONNECTIVITY
    )


def test_memory_error_is_resource() -> None:
    """Out-of-memory maps to the resource category."""
    assert _classify(MemoryError())["error_category"] == CATEGORY_RESOURCE


def test_plain_user_exception_is_user_code() -> None:
    """An exception raised here (the 'user' frame) is user_code origin."""
    result = _classify(ValueError("boom"))
    assert result["error_origin"] == CATEGORY_USER_CODE


def test_fingerprint_is_stable_and_opaque() -> None:
    """Same error type+path yields the same 16-char hex fingerprint."""
    a = _classify(ValueError("secret value one"))
    b = _classify(ValueError("totally different secret"))
    # Fingerprint depends on type + code path, NOT the (differing) messages.
    assert a["error_fingerprint"] == b["error_fingerprint"]
    assert len(a["error_fingerprint"]) == 16
    int(a["error_fingerprint"], 16)  # is valid hex


def test_fingerprint_excludes_message_content() -> None:
    """The message text must never appear in any output value."""
    secret = "ssn-123-45-6789"
    result = _classify(ValueError(secret))
    assert secret not in "".join(result.values())


def test_classification_never_raises_on_bad_input() -> None:
    """Robustness: malformed input returns a dict, never raises."""
    assert isinstance(classify_error(ValueError, None, None), dict)
