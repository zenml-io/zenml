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

from types import SimpleNamespace
from uuid import uuid4

import pytest

from zenml.exceptions import CredentialsNotValid
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


class _ZenStore:
    def __init__(self, api_key: _ApiKey):
        self.api_key = api_key
        self.updated_api_key_ids = []

    def get_internal_api_key(self, api_key_id):
        assert api_key_id == self.api_key.id
        return self.api_key

    def update_internal_api_key(self, api_key_id, _):
        self.updated_api_key_ids.append(api_key_id)


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
