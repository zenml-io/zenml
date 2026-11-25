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
"""Unit tests for the Backblaze B2 artifact store flavor.

These tests intentionally exercise only the config/flavor surface that the
B2 integration adds on top of the inherited S3 implementation: the flavor
identifier, runtime B2 fallbacks, and the typed ``config`` property on the
artifact store. We mock ``boto3.resource`` so no real S3/B2 client is
constructed during instantiation.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from zenml.enums import StackComponentType
from zenml.integrations.b2.artifact_stores.b2_artifact_store import (
    B2ArtifactStore,
)
from zenml.integrations.b2.flavors.b2_artifact_store_flavor import (
    B2_APPLICATION_KEY_ENV_VAR,
    B2_KEY_ID_ENV_VAR,
    B2_USER_AGENT,
    DEFAULT_B2_ENDPOINT_URL,
    B2ArtifactStoreConfig,
    B2ArtifactStoreFlavor,
)


def test_flavor_name_and_display_name():
    """The flavor identifier and display name are B2-specific."""
    flavor = B2ArtifactStoreFlavor()
    assert flavor.name == "b2"
    assert flavor.display_name == "Backblaze B2"


def test_flavor_config_class_is_b2_config():
    """The flavor's config class is the B2 subclass, not the S3 base."""
    flavor = B2ArtifactStoreFlavor()
    assert flavor.config_class is B2ArtifactStoreConfig


def test_flavor_no_service_connector_requirements():
    """No B2 service connector ships yet, so requirements should be None."""
    flavor = B2ArtifactStoreFlavor()
    assert flavor.service_connector_requirements is None


def test_config_does_not_persist_runtime_defaults(monkeypatch):
    """A bare config does not store runtime B2 fallbacks."""
    monkeypatch.delenv(B2_KEY_ID_ENV_VAR, raising=False)
    monkeypatch.delenv(B2_APPLICATION_KEY_ENV_VAR, raising=False)

    config = B2ArtifactStoreConfig(path="s3://my-b2-bucket")
    assert config.client_kwargs is None
    assert config.config_kwargs is None
    assert config.key is None
    assert config.secret is None


def test_user_provided_endpoint_url_overrides_default(monkeypatch):
    """An explicit endpoint_url in client_kwargs is preserved as-is."""
    monkeypatch.delenv(B2_KEY_ID_ENV_VAR, raising=False)
    monkeypatch.delenv(B2_APPLICATION_KEY_ENV_VAR, raising=False)

    custom_endpoint = "https://s3.eu-central-003.backblazeb2.com"
    config = B2ArtifactStoreConfig(
        path="s3://my-b2-bucket",
        client_kwargs={"endpoint_url": custom_endpoint},
    )
    assert config.client_kwargs is not None
    assert config.client_kwargs["endpoint_url"] == custom_endpoint


def test_missing_endpoint_url_is_not_persisted(monkeypatch):
    """Client kwargs without an endpoint are persisted as provided."""
    monkeypatch.delenv(B2_KEY_ID_ENV_VAR, raising=False)
    monkeypatch.delenv(B2_APPLICATION_KEY_ENV_VAR, raising=False)

    config = B2ArtifactStoreConfig(
        path="s3://my-b2-bucket",
        client_kwargs={"region_name": "us-west-004"},
    )
    assert config.client_kwargs is not None
    assert config.client_kwargs["region_name"] == "us-west-004"
    assert "endpoint_url" not in config.client_kwargs


def test_b2_env_vars_populate_runtime_credentials(monkeypatch):
    """B2_APPLICATION_KEY_ID / B2_APPLICATION_KEY are runtime fallbacks."""
    monkeypatch.setenv(B2_KEY_ID_ENV_VAR, "b2-key-id")
    monkeypatch.setenv(B2_APPLICATION_KEY_ENV_VAR, "b2-app-key")

    store = _build_b2_artifact_store(monkeypatch, clear_env=False)
    assert store.config.key is None
    assert store.config.secret is None

    kwargs = store._build_boto3_kwargs()
    assert kwargs["aws_access_key_id"] == "b2-key-id"
    assert kwargs["aws_secret_access_key"] == "b2-app-key"


def test_explicit_credentials_take_precedence_over_env(monkeypatch):
    """Config-provided key/secret are not clobbered by B2 env vars."""
    monkeypatch.setenv(B2_KEY_ID_ENV_VAR, "env-key-id")
    monkeypatch.setenv(B2_APPLICATION_KEY_ENV_VAR, "env-app-key")

    config = B2ArtifactStoreConfig(
        path="s3://my-b2-bucket",
        key="explicit-key",
        secret="explicit-secret",
    )
    assert config.key == "explicit-key"
    assert config.secret == "explicit-secret"


def test_missing_b2_env_vars_leave_credentials_unset(monkeypatch):
    """Without env vars and no explicit creds, key/secret stay None."""
    monkeypatch.delenv(B2_KEY_ID_ENV_VAR, raising=False)
    monkeypatch.delenv(B2_APPLICATION_KEY_ENV_VAR, raising=False)

    config = B2ArtifactStoreConfig(path="s3://my-b2-bucket")
    assert config.key is None
    assert config.secret is None


def test_b2_artifact_store_config_property_returns_b2_config(monkeypatch):
    """The artifact store's typed config property returns a B2 config."""
    monkeypatch.delenv(B2_KEY_ID_ENV_VAR, raising=False)
    monkeypatch.delenv(B2_APPLICATION_KEY_ENV_VAR, raising=False)

    with patch("boto3.resource", MagicMock()):
        artifact_store = B2ArtifactStore(
            name="",
            id=uuid4(),
            config=B2ArtifactStoreConfig(path="s3://my-b2-bucket"),
            flavor="b2",
            type=StackComponentType.ARTIFACT_STORE,
            user=uuid4(),
            created=datetime.now(),
            updated=datetime.now(),
        )

    assert isinstance(artifact_store.config, B2ArtifactStoreConfig)
    assert artifact_store.flavor == "b2"
    assert artifact_store.type == StackComponentType.ARTIFACT_STORE
    assert artifact_store.config.client_kwargs is None


def _build_b2_artifact_store(
    monkeypatch,
    clear_env: bool = True,
    config: B2ArtifactStoreConfig | None = None,
) -> B2ArtifactStore:
    """Construct a B2ArtifactStore with boto3.resource mocked.

    Args:
        monkeypatch: pytest's monkeypatch fixture.
        clear_env: Whether to clear B2 credential environment variables.
        config: Optional config for the artifact store.

    Returns:
        A B2ArtifactStore wired with a default config.
    """
    if clear_env:
        monkeypatch.delenv(B2_KEY_ID_ENV_VAR, raising=False)
        monkeypatch.delenv(B2_APPLICATION_KEY_ENV_VAR, raising=False)

    with patch("boto3.resource", MagicMock()):
        return B2ArtifactStore(
            name="",
            id=uuid4(),
            config=config or B2ArtifactStoreConfig(path="s3://my-b2-bucket"),
            flavor="b2",
            type=StackComponentType.ARTIFACT_STORE,
            user=uuid4(),
            created=datetime.now(),
            updated=datetime.now(),
        )


def test_build_boto3_kwargs_forwards_config_kwargs_into_boto3_config(
    monkeypatch,
):
    """`_build_boto3_kwargs` wraps `config_kwargs` into a botocore Config.

    The boto3.resource path must see a Config carrying the B2 user agent
    suffix even though it is not persisted on the component config.
    """
    from botocore.config import Config

    store = _build_b2_artifact_store(monkeypatch)
    parent_kwargs = {"endpoint_url": DEFAULT_B2_ENDPOINT_URL}

    with patch.object(
        type(store).__mro__[1],
        "_build_boto3_kwargs",
        return_value=dict(parent_kwargs),
    ):
        kwargs = store._build_boto3_kwargs()

    assert "config" in kwargs
    assert isinstance(kwargs["config"], Config)
    assert B2_USER_AGENT in (kwargs["config"].user_agent_extra or "")
    assert kwargs["endpoint_url"] == DEFAULT_B2_ENDPOINT_URL


def test_build_boto3_kwargs_preserves_user_agent_extra(monkeypatch):
    """User-provided user agent extras are preserved."""
    from botocore.config import Config

    store = _build_b2_artifact_store(
        monkeypatch,
        config=B2ArtifactStoreConfig(
            path="s3://my-b2-bucket",
            config_kwargs={"user_agent_extra": "caller-supplied"},
        ),
    )
    parent_kwargs = {"endpoint_url": DEFAULT_B2_ENDPOINT_URL}

    with patch.object(
        type(store).__mro__[1],
        "_build_boto3_kwargs",
        return_value=dict(parent_kwargs),
    ):
        kwargs = store._build_boto3_kwargs()

    assert isinstance(kwargs["config"], Config)
    assert "caller-supplied" in kwargs["config"].user_agent_extra
    assert B2_USER_AGENT in kwargs["config"].user_agent_extra


def test_build_boto3_kwargs_preserves_existing_config(monkeypatch):
    """If the parent already returned a `config`, it is not overwritten."""
    from botocore.config import Config

    store = _build_b2_artifact_store(monkeypatch)
    parent_config = Config(user_agent_extra="caller-supplied")
    parent_kwargs = {
        "endpoint_url": DEFAULT_B2_ENDPOINT_URL,
        "config": parent_config,
    }

    with patch.object(
        type(store).__mro__[1],
        "_build_boto3_kwargs",
        return_value=dict(parent_kwargs),
    ):
        kwargs = store._build_boto3_kwargs()

    assert kwargs["config"] is parent_config
