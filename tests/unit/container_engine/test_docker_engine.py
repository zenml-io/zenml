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
"""Tests for :mod:`zenml.container_engines.docker_engine`."""

from typing import Any, Dict, Optional

import docker.auth as docker_auth
import docker.credentials as docker_credentials
import pytest
from docker.client import DockerClient

from zenml.container_engines.docker_engine import (
    DockerContainerEngine,
    _AuthsCredentialStore,
)

ZENML_AUTH_STORE = "zenml-auths"
SYSTEM_AUTH_STORE = "system-auths"


class _StaticCredentialStore:
    """Credential store with fixed credentials for docker-py auth tests."""

    def __init__(self, username: str, password: str) -> None:
        """Initialize the store.

        Args:
            username: Username returned for every registry.
            password: Password returned for every registry.
        """
        self._username = username
        self._password = password

    def get(self, server: str) -> Dict[str, str]:
        """Get credentials for a registry.

        Args:
            server: Registry server.

        Returns:
            Credentials in Docker credential helper format.
        """
        return {"Username": self._username, "Secret": self._password}

    def list(self) -> Dict[str, str]:
        """List stored registry credentials.

        Returns:
            Registry-to-username mapping in Docker credential helper format.
        """
        return {"registry.example.com": self._username}


def _auth_config_with_store() -> docker_auth.AuthConfig:
    """Create a docker-py auth config with the in-memory auth store installed."""
    auth_config = docker_auth.AuthConfig({"auths": {}, "credHelpers": {}})
    auth_config._stores[ZENML_AUTH_STORE] = _AuthsCredentialStore(
        auth_config.auths
    )
    return auth_config


def _docker_client_with_auth_config() -> DockerClient:
    """Create a real docker-py client with an isolated auth config."""
    client = DockerClient(base_url="http://127.0.0.1:2375", version="1.41")
    client.api._auth_configs = _auth_config_with_store()
    return client


def _mock_successful_login(client: DockerClient) -> list[Optional[str]]:
    """Make a docker-py client record login auths without network access."""
    logged_in_registries: list[Optional[str]] = []

    def login(
        username: str,
        password: str,
        registry: Optional[str],
        reauth: bool,
    ) -> Dict[str, Any]:
        """Store credentials like docker-py does after a successful login."""
        logged_in_registries.append(registry)
        auth_config = {
            "username": username,
            "password": password,
            "serveraddress": registry,
        }
        client.api._auth_configs.add_auth(
            registry or docker_auth.INDEX_NAME, auth_config
        )
        return auth_config

    client.login = login
    return logged_in_registries


def test_auths_credential_store_get_returns_username_and_secret() -> None:
    """Credential store adapts in-memory auths to helper credentials."""
    auths = {
        "registry.example.com": {
            "username": "zenml",
            "password": "password",
            "serveraddress": "registry.example.com",
        }
    }

    credentials = _AuthsCredentialStore(auths).get("registry.example.com")

    assert credentials == {
        "Username": "zenml",
        "Secret": "password",
    }


def test_auths_credential_store_get_raises_for_missing_registry() -> None:
    """Credential store raises when no in-memory auth exists."""
    store = _AuthsCredentialStore({})

    with pytest.raises(docker_credentials.CredentialsNotFound):
        store.get("registry.example.com")


def test_auths_credential_store_list_returns_auth_entries() -> None:
    """Credential store lists populated in-memory auth entries."""
    store = _AuthsCredentialStore(
        {
            "registry.example.com": {
                "username": "zenml",
                "password": "password",
                "serveraddress": "registry.example.com",
            },
            "empty.example.com": {},
        }
    )

    assert store.list() == {"registry.example.com": "zenml"}


def test_auths_credential_store_resolves_dockerhub_index_url() -> None:
    """Credential store maps Docker Hub index URL to docker.io auth."""
    auth_config = {
        "username": "zenml",
        "password": "password",
        "serveraddress": None,
    }

    credentials = _AuthsCredentialStore(
        {docker_auth.INDEX_NAME: auth_config}
    ).get(docker_auth.INDEX_URL)

    assert credentials == {
        "Username": "zenml",
        "Secret": "password",
    }


def test_client_property_installs_auths_credential_store(mocker) -> None:
    """Client creation installs the in-memory auth credential store."""
    client = DockerClient(base_url="http://127.0.0.1:2375", version="1.41")
    auth_config = docker_auth.AuthConfig({"auths": {}})
    client.api._auth_configs = auth_config
    mocker.patch(
        "zenml.container_engines.docker_engine.DockerClient.from_env",
        return_value=client,
    )

    engine = DockerContainerEngine()

    assert isinstance(
        engine.client.api._auth_configs._stores[ZENML_AUTH_STORE],
        _AuthsCredentialStore,
    )


def test_login_client_registers_auths_credential_helper() -> None:
    """Login registers the in-memory auth helper for the target registry."""
    client = _docker_client_with_auth_config()
    _mock_successful_login(client)
    engine = DockerContainerEngine()
    engine._client = client

    engine.login_client(
        username="zenml",
        password="password",
        registry="registry.example.com",
    )

    auth_config = client.api._auth_configs
    helper_name = auth_config.cred_helpers["registry.example.com"]
    assert auth_config._stores[helper_name].get("registry.example.com") == {
        "Username": "zenml",
        "Secret": "password",
    }


def test_login_client_helper_takes_precedence_for_resolve_authconfig() -> None:
    """Registered helper makes registry auth resolve to login credentials."""
    client = _docker_client_with_auth_config()
    _mock_successful_login(client)
    engine = DockerContainerEngine()
    engine._client = client

    engine.login_client(
        username="zenml",
        password="password",
        registry="registry.example.com",
    )

    assert client.api._auth_configs.resolve_authconfig(
        "registry.example.com"
    ) == {
        "ServerAddress": "registry.example.com",
        "Username": "zenml",
        "Password": "password",
    }


def test_auths_helper_overrides_system_store_for_resolve_authconfig() -> None:
    """Docker-py's registry auth resolution prefers our helper."""
    auth_config = docker_auth.AuthConfig(
        {
            "auths": {
                "registry.example.com": {
                    "username": "zenml",
                    "password": "password",
                    "serveraddress": "registry.example.com",
                }
            },
            "credsStore": SYSTEM_AUTH_STORE,
            "credHelpers": {"registry.example.com": ZENML_AUTH_STORE},
        }
    )
    auth_config._stores[ZENML_AUTH_STORE] = _AuthsCredentialStore(
        auth_config.auths
    )
    auth_config._stores[SYSTEM_AUTH_STORE] = _StaticCredentialStore(
        username="system",
        password="system-password",
    )

    assert auth_config.resolve_authconfig("registry.example.com") == {
        "ServerAddress": "registry.example.com",
        "Username": "zenml",
        "Password": "password",
    }


def test_login_client_helper_takes_precedence_for_build_credentials() -> None:
    """Registered helper exposes login credentials to Docker build auth."""
    client = _docker_client_with_auth_config()
    _mock_successful_login(client)
    engine = DockerContainerEngine()
    engine._client = client

    engine.login_client(
        username="zenml",
        password="password",
        registry="registry.example.com",
    )

    credentials = client.api._auth_configs.get_all_credentials()

    assert credentials["registry.example.com"] == {
        "ServerAddress": "registry.example.com",
        "Username": "zenml",
        "Password": "password",
    }


def test_auths_helper_overrides_system_store_for_build_credentials() -> None:
    """Docker-py's build auth collection applies our helper last."""
    auth_config = docker_auth.AuthConfig(
        {
            "auths": {
                "registry.example.com": {
                    "username": "zenml",
                    "password": "password",
                    "serveraddress": "registry.example.com",
                }
            },
            "credsStore": SYSTEM_AUTH_STORE,
            "credHelpers": {"registry.example.com": ZENML_AUTH_STORE},
        }
    )
    auth_config._stores[ZENML_AUTH_STORE] = _AuthsCredentialStore(
        auth_config.auths
    )
    auth_config._stores[SYSTEM_AUTH_STORE] = _StaticCredentialStore(
        username="system",
        password="system-password",
    )

    credentials = auth_config.get_all_credentials()

    assert credentials["registry.example.com"] == {
        "ServerAddress": "registry.example.com",
        "Username": "zenml",
        "Password": "password",
    }


def test_dockerhub_login_uses_index_url_for_auth_and_helper() -> None:
    """Docker Hub login aligns auths and helper keys on docker-py's index URL."""
    client = _docker_client_with_auth_config()
    logged_in_registries = _mock_successful_login(client)
    engine = DockerContainerEngine()
    engine._client = client

    engine.login_client(
        username="zenml",
        password="password",
        registry="docker.io",
    )

    auth_config = client.api._auth_configs
    assert logged_in_registries == [docker_auth.INDEX_URL]
    assert docker_auth.INDEX_URL in auth_config.auths
    assert auth_config.cred_helpers[docker_auth.INDEX_URL] == ZENML_AUTH_STORE
    assert auth_config.resolve_authconfig("docker.io") == {
        "ServerAddress": docker_auth.INDEX_URL,
        "Username": "zenml",
        "Password": "password",
    }
