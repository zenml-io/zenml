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

import contextlib
import uuid
from contextlib import ExitStack as does_not_raise
from datetime import datetime
from time import sleep
from typing import Any, Dict, Generator

import jwt
import pytest

from zenml.constants import DEFAULT_ZENML_JWT_TOKEN_LEEWAY
from zenml.exceptions import (
    AuthorizationException,
)
from zenml.zen_server.jwt import JWTToken
from zenml.zen_server.utils import server_config


def test_encode_decode_works():
    """Test that encoding and decoding JWT tokens generally works."""
    user_id = uuid.uuid4()
    device_id = uuid.uuid4()
    api_key_id = uuid.uuid4()
    schedule_id = uuid.uuid4()
    pipeline_run_id = uuid.uuid4()
    step_run_id = uuid.uuid4()
    claims = {
        "foo": "bar",
        "baz": "qux",
    }

    token = JWTToken(
        user_id=user_id,
        device_id=device_id,
        api_key_id=api_key_id,
        schedule_id=schedule_id,
        pipeline_run_id=pipeline_run_id,
        step_run_id=step_run_id,
        claims=claims,
    )

    encoded_token = token.encode()
    decoded_token = JWTToken.decode_token(encoded_token)

    assert decoded_token.user_id == user_id
    assert decoded_token.device_id == device_id
    assert decoded_token.api_key_id == api_key_id
    assert decoded_token.schedule_id == schedule_id
    assert decoded_token.pipeline_run_id == pipeline_run_id
    assert decoded_token.step_run_id == step_run_id
    # Check that the configured custom claims are included in the decoded claims
    assert decoded_token.claims["foo"] == "bar"
    assert decoded_token.claims["baz"] == "qux"


def test_token_expiration():
    """Test that tokens expire after the specified time."""
    token = JWTToken(
        user_id=uuid.uuid4(),
    )

    expires = datetime.utcnow()
    encoded_token = token.encode(expires=expires)
    with does_not_raise():
        JWTToken.decode_token(encoded_token)

    # Wait for the token to expire, including the leeway
    sleep(DEFAULT_ZENML_JWT_TOKEN_LEEWAY + 1)

    with pytest.raises(AuthorizationException):
        JWTToken.decode_token(encoded_token)


def test_token_wrong_signature():
    """Test that tokens with the wrong signature are rejected."""
    config = server_config()

    token = JWTToken(
        user_id=uuid.uuid4(),
    )
    encoded_token = token.encode()

    # Re-encode the token with a different secret key
    claims_data = jwt.decode(
        encoded_token,
        algorithms=[config.jwt_token_algorithm],
        options={
            "verify_signature": False,
            "verify_exp": False,
            "verify_aud": False,
            "verify_iss": False,
        },
    )
    fake_token = jwt.encode(
        claims_data,
        "fake_key",
        algorithm=config.jwt_token_algorithm,
    )

    with pytest.raises(AuthorizationException):
        JWTToken.decode_token(fake_token)


@contextlib.contextmanager
def _hack_token() -> Generator[Dict[str, Any], None, None]:
    """Hack the token to have different values.

    Yields:
        The claims data of the hacked token.
    """
    # Re-encode the token with a different algorithm

    config = server_config()

    token = JWTToken(
        user_id=uuid.uuid4(),
    )
    encoded_token = token.encode()

    claims_data = jwt.decode(
        encoded_token,
        algorithms=[config.jwt_token_algorithm],
        options={
            "verify_signature": False,
            "verify_exp": False,
            "verify_aud": False,
            "verify_iss": False,
        },
    )

    yield claims_data

    fake_token = jwt.encode(
        claims_data,
        config.jwt_secret_key,
        algorithm=config.jwt_token_algorithm,
    )

    with pytest.raises(AuthorizationException):
        JWTToken.decode_token(fake_token)


def test_token_wrong_audience():
    """Test that tokens with the wrong audience are rejected."""
    with _hack_token() as claims_data:
        claims_data["aud"] = "fake_audience"


def test_token_no_audience():
    """Test that tokens without an audience are rejected."""
    with _hack_token() as claims_data:
        claims_data.pop("aud")


def test_token_wrong_issuer():
    """Test that tokens with the wrong issuer are rejected."""
    with _hack_token() as claims_data:
        claims_data["iss"] = "fake_issuer"


def test_token_no_issuer():
    """Test that tokens without an issuer are rejected."""
    with _hack_token() as claims_data:
        claims_data.pop("iss")
