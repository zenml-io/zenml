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
"""Unit tests for ZenML server authentication helpers."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from zenml.exceptions import CredentialsNotValid
from zenml.models import APIKeyInternalResponse, UserResponse
from zenml.models.v2.core.api_key import APIKeyResponseMetadata
from zenml.models.v2.core.user import UserResponseMetadata
from zenml.zen_server import auth


class _ApiKey:
    def __init__(self):
        self.id = uuid4()
        self.name = "test-key"
        self.active = True
        self.service_account = SimpleNamespace(
            active=True, external_user_id=None, name="test-service-account"
        )
        self.verified_keys = []

    def verify_key(self, key: str) -> bool:
        self.verified_keys.append(key)
        return key == "valid"

    def is_token_generation_valid(self, token_generation):
        return True


class _ZenStore:
    def __init__(self, api_key: _ApiKey):
        self.api_key = api_key
        self.updated_api_key_ids = []

    def get_internal_api_key(self, api_key_id):
        assert api_key_id == self.api_key.id
        return self.api_key

    def update_internal_api_key(self, api_key_id, _):
        self.updated_api_key_ids.append(api_key_id)


def _api_key_model(
    *,
    key_generation: int,
    last_rotated: datetime,
    retain_period_minutes: int,
) -> APIKeyInternalResponse:
    return APIKeyInternalResponse.model_construct(
        id=uuid4(),
        name="test-key",
        key_generation=key_generation,
        body=SimpleNamespace(active=True),
        metadata=APIKeyResponseMetadata(
            description="",
            retain_period_minutes=retain_period_minutes,
            last_login=None,
            last_rotated=last_rotated,
        ),
    )


def _user_model(
    *,
    password_changed_at=None,
    is_service_account: bool = False,
) -> UserResponse:
    return UserResponse.model_construct(
        id=uuid4(),
        name="test-user",
        body=SimpleNamespace(is_service_account=is_service_account),
        metadata=UserResponseMetadata(
            password_changed_at=password_changed_at,
            email=None,
            external_user_id=None,
            user_metadata={},
        ),
    )


def test_fetch_and_verify_api_key_rejects_empty_key(monkeypatch):
    """Ensure empty client-supplied API key secrets are still verified."""
    api_key = _ApiKey()
    monkeypatch.setattr(auth, "zen_store", lambda: _ZenStore(api_key))

    with pytest.raises(CredentialsNotValid):
        auth._fetch_and_verify_api_key(api_key_id=api_key.id, key_to_verify="")

    assert api_key.verified_keys == [""]


def test_fetch_and_verify_api_key_allows_internal_skip(monkeypatch):
    """Ensure the internal JWT re-auth path can still skip key verification."""
    api_key = _ApiKey()
    store = _ZenStore(api_key)
    monkeypatch.setattr(auth, "zen_store", lambda: store)

    auth._fetch_and_verify_api_key(api_key_id=api_key.id, key_to_verify=None)

    assert api_key.verified_keys == []
    assert store.updated_api_key_ids == [api_key.id]


def test_api_key_token_generation_allows_legacy_tokens():
    """Ensure JWTs without a generation claim remain valid."""
    api_key = _api_key_model(
        key_generation=2,
        last_rotated=datetime.utcnow(),
        retain_period_minutes=5,
    )

    assert api_key.is_token_generation_valid(token_generation=None)


def test_api_key_token_generation_allows_current_generation():
    """Ensure JWTs issued for the current API key generation are valid."""
    api_key = _api_key_model(
        key_generation=2,
        last_rotated=datetime.utcnow(),
        retain_period_minutes=5,
    )

    assert api_key.is_token_generation_valid(token_generation=2)


def test_api_key_token_generation_allows_retained_previous_generation():
    """Ensure the previous API key generation follows the retain period."""
    api_key = _api_key_model(
        key_generation=2,
        last_rotated=datetime.utcnow(),
        retain_period_minutes=5,
    )

    assert api_key.is_token_generation_valid(token_generation=1)


def test_api_key_token_generation_rejects_expired_previous_generation():
    """Ensure previous-generation JWTs expire with the retain period."""
    api_key = _api_key_model(
        key_generation=2,
        last_rotated=datetime.utcnow() - timedelta(minutes=6),
        retain_period_minutes=5,
    )

    assert not api_key.is_token_generation_valid(token_generation=1)


def test_api_key_token_generation_rejects_older_generation():
    """Ensure only the immediately previous API key generation is retained."""
    api_key = _api_key_model(
        key_generation=3,
        last_rotated=datetime.utcnow(),
        retain_period_minutes=5,
    )

    assert not api_key.is_token_generation_valid(token_generation=1)


def test_password_change_check_allows_legacy_tokens():
    """Ensure JWTs without an issued-at claim remain valid."""
    user = _user_model(password_changed_at=datetime.utcnow())

    assert user.is_token_issued_after_password_change(issued_at=None)


def test_password_change_check_rejects_stale_user_tokens():
    """Ensure user JWTs issued before a password change are rejected."""
    password_changed_at = datetime.utcnow()
    user = _user_model(password_changed_at=password_changed_at)

    assert not user.is_token_issued_after_password_change(
        issued_at=password_changed_at - timedelta(seconds=1)
    )


def test_password_change_check_allows_fresh_user_tokens():
    """Ensure user JWTs issued after a password change are valid."""
    password_changed_at = datetime.utcnow()
    user = _user_model(password_changed_at=password_changed_at)

    assert user.is_token_issued_after_password_change(
        issued_at=password_changed_at + timedelta(seconds=1)
    )


def test_password_change_check_skips_service_accounts():
    """Ensure service accounts are governed by API key generation checks."""
    password_changed_at = datetime.utcnow()
    user = _user_model(
        password_changed_at=password_changed_at, is_service_account=True
    )

    assert user.is_token_issued_after_password_change(
        issued_at=password_changed_at - timedelta(seconds=1)
    )
