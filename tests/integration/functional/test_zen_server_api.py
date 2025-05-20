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
    """Pytest fixture to get the ZenML server's REST API base URL and an authentication token.

    This fixture assumes that the ZenML client is configured to use a
    RESTZenStore, from which it retrieves the API URL and a valid
    authentication token.

    Yields:
        Tuple[str, str]: A tuple containing the server's REST API base URL
            (e.g., "http://localhost:8080") and an API authentication token.
    """
    from zenml.zen_stores.rest_zen_store import RestZenStore

    zen_store = Client().zen_store
    assert isinstance(zen_store, RestZenStore)

    yield zen_store.url, zen_store.get_or_generate_api_token()


def test_list_stacks_endpoint(rest_api_auth_token: Tuple[str, str]) -> None:
    """Tests the functionality of the `/api/v1/stacks` endpoint.

    This test verifies that the endpoint returns a successful (200) response,
    that the response is a JSON dictionary, and that it contains at least one
    stack item, indicating the endpoint is serving stack data correctly.

    Args:
        rest_api_auth_token: A tuple containing the server's REST API base URL
            and an authentication token, provided by the `rest_api_auth_token`
            fixture.
    """
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


def test_list_users_endpoint(rest_api_auth_token: Tuple[str, str]) -> None:
    """Tests the functionality of the `/api/v1/users` endpoint.

    This test verifies that the endpoint returns a successful (200) response,
    that the response is a JSON dictionary, and that it contains at least one
    user item, indicating the endpoint is serving user data correctly.

    Args:
        rest_api_auth_token: A tuple containing the server's REST API base URL
            and an authentication token, provided by the `rest_api_auth_token`
            fixture.
    """
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


def test_server_requires_auth(rest_api_auth_token: Tuple[str, str]) -> None:
    """Tests that server API endpoints require authentication.

    This test verifies that requests to protected endpoints like `/api/v1/stacks`
    and `/api/v1/users` return a 401 Unauthorized status code when no
    authentication token is provided. It also checks that public endpoints
    like `/health` can be accessed without authentication.

    Args:
        rest_api_auth_token: A tuple containing the server's REST API base URL
            and an authentication token, provided by the `rest_api_auth_token`
            fixture. The token is not used in this test to verify
            unauthenticated access.
    """
    endpoint, _ = rest_api_auth_token
    api_endpoint = endpoint + API + VERSION_1

    stacks_response = requests.get(api_endpoint + STACKS, timeout=31)
    assert stacks_response.status_code == 401

    users_response = requests.get(api_endpoint + USERS, timeout=31)
    assert users_response.status_code == 401

    # health doesn't require auth
    health_response = requests.get(endpoint + "/health", timeout=31)
    assert health_response.status_code == 200

[end of tests/integration/functional/test_zen_server_api.py]
