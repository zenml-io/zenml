#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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

import os

import pytest

# Skip this entire module if the optional dependency isn't available, because
# the module under test imports `modal` at import time.
pytest.importorskip("modal")

from zenml.integrations.modal.utils import (
    MODAL_CONFIG_PATH,
    MODAL_ENVIRONMENT_ENV,
    MODAL_TOKEN_ID_ENV,
    MODAL_TOKEN_SECRET_ENV,
    MODAL_WORKSPACE_ENV,
    _set_env_if_present,
    _validate_token_prefix,
    build_modal_image,
    setup_modal_client,
)


class StackStubNoRegistry:
    """Stack stub with no container registry to trigger early validation."""

    container_registry = None


class ContainerRegistryStubNoCreds:
    """Container registry stub with missing credentials."""

    def __init__(self):
        self.credentials = None


class StackStubWithRegistryNoCreds:
    """Stack stub with a container registry but no credentials."""

    def __init__(self):
        self.container_registry = ContainerRegistryStubNoCreds()


def test_build_modal_image_raises_when_no_registry() -> None:
    with pytest.raises(RuntimeError) as e:
        build_modal_image(
            "repo/image:tag", StackStubNoRegistry(), environment=None
        )
    assert "No Container registry found in the stack" in str(e.value)


def test_build_modal_image_raises_when_no_credentials() -> None:
    with pytest.raises(RuntimeError) as e:
        build_modal_image(
            "repo/image:tag", StackStubWithRegistryNoCreds(), environment=None
        )
    assert "No Docker credentials found for the container registry" in str(
        e.value
    )


def test_set_env_if_present_sets_and_returns_true(monkeypatch) -> None:
    monkeypatch.delenv("FOO_TEST", raising=False)
    assert _set_env_if_present("FOO_TEST", "bar") is True
    assert os.environ["FOO_TEST"] == "bar"


def test_set_env_if_present_ignores_none_and_empty(monkeypatch) -> None:
    monkeypatch.delenv("FOO_TEST", raising=False)

    assert _set_env_if_present("FOO_TEST", None) is False
    assert "FOO_TEST" not in os.environ

    assert _set_env_if_present("FOO_TEST", "") is False
    assert "FOO_TEST" not in os.environ


def test_validate_token_prefix_warns_on_invalid_prefix(caplog) -> None:
    with caplog.at_level("WARNING"):
        _validate_token_prefix("invalid-token", "ak-", "Token ID")
    assert "Expected prefix: ak-" in caplog.text


def test_setup_modal_client_sets_env_from_args(monkeypatch) -> None:
    # Ensure a clean environment
    monkeypatch.delenv(MODAL_TOKEN_ID_ENV, raising=False)
    monkeypatch.delenv(MODAL_TOKEN_SECRET_ENV, raising=False)
    monkeypatch.delenv(MODAL_WORKSPACE_ENV, raising=False)
    monkeypatch.delenv(MODAL_ENVIRONMENT_ENV, raising=False)

    setup_modal_client(
        token_id="ak-abc123",
        token_secret="as-def456",
        workspace="my-ws",
        environment="main",
    )

    assert os.environ[MODAL_TOKEN_ID_ENV] == "ak-abc123"
    assert os.environ[MODAL_TOKEN_SECRET_ENV] == "as-def456"
    assert os.environ[MODAL_WORKSPACE_ENV] == "my-ws"
    assert os.environ[MODAL_ENVIRONMENT_ENV] == "main"


def test_setup_modal_client_warns_when_only_one_token_provided(
    monkeypatch, caplog
) -> None:
    monkeypatch.delenv(MODAL_TOKEN_ID_ENV, raising=False)
    monkeypatch.delenv(MODAL_TOKEN_SECRET_ENV, raising=False)

    with caplog.at_level("WARNING"):
        setup_modal_client(token_id="ak-abc123", token_secret=None)

    assert "Only token ID provided" in caplog.text
    assert os.environ[MODAL_TOKEN_ID_ENV] == "ak-abc123"
    assert MODAL_TOKEN_SECRET_ENV not in os.environ


def test_setup_modal_client_prefers_args_over_env(monkeypatch) -> None:
    monkeypatch.setenv(MODAL_TOKEN_ID_ENV, "ak-old")
    monkeypatch.setenv(MODAL_TOKEN_SECRET_ENV, "as-old")

    setup_modal_client(token_id="ak-new", token_secret="as-new")

    assert os.environ[MODAL_TOKEN_ID_ENV] == "ak-new"
    assert os.environ[MODAL_TOKEN_SECRET_ENV] == "as-new"


def test_setup_modal_client_logs_missing_config_when_no_tokens_and_no_config(
    monkeypatch, caplog
) -> None:
    # Clear tokens from environment
    monkeypatch.delenv(MODAL_TOKEN_ID_ENV, raising=False)
    monkeypatch.delenv(MODAL_TOKEN_SECRET_ENV, raising=False)

    # Pretend modal config is missing
    monkeypatch.setenv(
        "HOME", "/nonexistent-home-for-test"
    )  # defensive isolation
    monkeypatch.setattr("os.path.exists", lambda path: False)

    with caplog.at_level("WARNING"):
        setup_modal_client()

    # Should warn that the default config file is missing
    assert "No platform config found at" in caplog.text
    assert str(MODAL_CONFIG_PATH) in caplog.text


def test_setup_modal_client_warns_on_bad_token_prefixes(
    monkeypatch, caplog
) -> None:
    monkeypatch.delenv(MODAL_TOKEN_ID_ENV, raising=False)
    monkeypatch.delenv(MODAL_TOKEN_SECRET_ENV, raising=False)

    with caplog.at_level("WARNING"):
        setup_modal_client(token_id="bad-id", token_secret="bad-secret")

    # Both ID and secret should trigger prefix warnings
    assert "Expected prefix: ak-" in caplog.text
    assert "Expected prefix: as-" in caplog.text
