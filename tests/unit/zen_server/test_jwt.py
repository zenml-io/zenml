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
from zenml.enums import DownloadType
from zenml.exceptions import (
    AuthorizationException,
)
from zenml.zen_server.auth import (
    generate_download_token,
    verify_download_token,
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
        claims=claims,
    )

    encoded_token = token.encode()
    decoded_token = JWTToken.decode_token(encoded_token)

    assert decoded_token.user_id == user_id
    assert decoded_token.device_id == device_id
    assert decoded_token.api_key_id == api_key_id
    assert decoded_token.schedule_id == schedule_id
    assert decoded_token.pipeline_run_id == pipeline_run_id
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
        "fake_key_that_is_long_enough_for_hs256",
        algorithm=config.jwt_token_algorithm,
    )

    with pytest.raises(AuthorizationException):
        JWTToken.decode_token(fake_token)


def test_token_wrong_signature_can_skip_signature_verification():
    """Test that signature verification can be disabled explicitly."""
    config = server_config()
    user_id = uuid.uuid4()
    token = JWTToken(
        user_id=user_id,
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
        "fake_key_that_is_long_enough_for_hs256",
        algorithm=config.jwt_token_algorithm,
    )

    decoded_token = JWTToken.decode_token(fake_token, verify=False)

    assert decoded_token.user_id == user_id


def test_disabling_verification_skips_all_claim_checks():
    """Test that ``verify=False`` is all-or-nothing.

    Disabling verification skips not only the signature but every other claim
    check (audience, issuer, expiry). This matches PyJWT's behavior, where
    ``verify_signature=False`` turns off the remaining checks too. Validating
    claims on a token whose signature is unverified would be meaningless, since
    an unsigned token can be forged with any claims.
    """
    config = server_config()
    user_id = uuid.uuid4()
    token = JWTToken(
        user_id=user_id,
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
    claims_data["aud"] = "fake_audience"
    fake_token = jwt.encode(
        claims_data,
        "fake_key_that_is_long_enough_for_hs256",
        algorithm=config.jwt_token_algorithm,
    )

    decoded_token = JWTToken.decode_token(fake_token, verify=False)

    assert decoded_token.user_id == user_id


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


def test_download_token_verification():
    """Test that download tokens verify with matching expected claims."""
    resource_id = uuid.uuid4()
    extra_claims = {"artifact_path": "models/model.pkl"}
    token = generate_download_token(
        download_type=DownloadType.ARTIFACT_VERSION,
        resource_id=resource_id,
        extra_claims=extra_claims,
    )

    with does_not_raise():
        verify_download_token(
            token=token,
            download_type=DownloadType.ARTIFACT_VERSION,
            resource_id=resource_id,
            extra_claims=extra_claims,
        )


def test_download_token_rejects_mismatched_claims():
    """Test that download tokens reject mismatched expected claims."""
    resource_id = uuid.uuid4()
    token = generate_download_token(
        download_type=DownloadType.SNAPSHOT_CODE,
        resource_id=resource_id,
        extra_claims={"snapshot_path": "snapshots/current.tar.gz"},
    )

    with pytest.raises(AuthorizationException):
        verify_download_token(
            token=token,
            download_type=DownloadType.SNAPSHOT_CODE,
            resource_id=resource_id,
            extra_claims={"snapshot_path": "snapshots/other.tar.gz"},
        )
