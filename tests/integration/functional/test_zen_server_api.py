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
from typing import Tuple

import pytest
import requests

from zenml.client import Client
from zenml.constants import API, STACKS, USERS, VERSION_1

SERVER_START_STOP_TIMEOUT = 30


@pytest.fixture
def rest_api_auth_token() -> Tuple[str, str]:
    """Get an authentication token from the server.

    Yield:
        The server's REST API base URL and an authentication token.
    """
    from zenml.zen_stores.rest_zen_store import RestZenStore

    zen_store = Client().zen_store
    assert isinstance(zen_store, RestZenStore)

    yield zen_store.url, zen_store.get_or_generate_api_token()


def test_list_stacks_endpoint(rest_api_auth_token):
    """Test that the list stack endpoint works."""
    endpoint, token = rest_api_auth_token
    api_endpoint = endpoint + API + VERSION_1

    stacks_response = requests.get(
        api_endpoint + STACKS,
        headers={"Authorization": f"Bearer {token}"},
        timeout=31,
    )
    assert stacks_response.status_code == 200
    assert isinstance(stacks_response.json(), dict)
    assert len(stacks_response.json()["items"]) >= 1


def test_list_users_endpoint(rest_api_auth_token):
    """Test that the list users endpoint works."""
    endpoint, token = rest_api_auth_token
    api_endpoint = endpoint + API + VERSION_1

    users_response = requests.get(
        api_endpoint + USERS,
        headers={"Authorization": f"Bearer {token}"},
        timeout=31,
    )
    assert users_response.status_code == 200
    assert isinstance(users_response.json(), dict)
    assert len(users_response.json()["items"]) >= 1


def test_server_requires_auth(rest_api_auth_token):
    """Test that most service methods require authorization."""
    endpoint, _ = rest_api_auth_token
    api_endpoint = endpoint + API + VERSION_1

    stacks_response = requests.get(api_endpoint + STACKS, timeout=31)
    assert stacks_response.status_code == 401

    users_response = requests.get(api_endpoint + USERS, timeout=31)
    assert users_response.status_code == 401

    # health doesn't require auth
    health_response = requests.get(endpoint + "/health", timeout=31)
    assert health_response.status_code == 200
