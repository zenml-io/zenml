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
"""Unit tests for HuggingFace Jobs step operator utility functions.

These tests stub huggingface_hub in sys.modules so they run in CI
environments where the package is not installed.
"""

import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest

from zenml.integrations.huggingface.flavors.huggingface_jobs_step_operator_flavor import (
    HuggingFaceJobsStepOperatorConfig,
    HuggingFaceJobsStepOperatorSettings,
)


def _stub_huggingface_hub(
    monkeypatch,
    *,
    token: str | None = None,
    has_run_job: bool = True,
    installed_version: str = "0.30.0",
) -> types.ModuleType:
    """Create and install a fake huggingface_hub module in sys.modules.

    Args:
        monkeypatch: pytest monkeypatch fixture.
        token: Token to return from HfFolder.get_token().
        has_run_job: Whether to include the run_job symbol.
        installed_version: Version string for importlib.metadata.

    Returns:
        The fake module.
    """
    fake_hf = types.ModuleType("huggingface_hub")
    fake_hf.__version__ = installed_version

    if has_run_job:
        fake_hf.run_job = lambda **kwargs: None  # type: ignore[attr-defined]

    class FakeHfFolder:
        @staticmethod
        def get_token() -> str | None:
            return token

    fake_hf.HfFolder = FakeHfFolder  # type: ignore[attr-defined]

    # Also stub the private _space_api submodule
    fake_space_api = types.ModuleType("huggingface_hub._space_api")
    fake_hf._space_api = fake_space_api  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "huggingface_hub", fake_hf)
    monkeypatch.setitem(
        sys.modules, "huggingface_hub._space_api", fake_space_api
    )

    # Stub importlib.metadata.version for version checks
    original_version = importlib.metadata.version

    def _patched_version(name: str) -> str:
        if name == "huggingface_hub":
            return installed_version
        return original_version(name)

    monkeypatch.setattr(importlib.metadata, "version", _patched_version)

    return fake_hf


def _reload_step_operator_module() -> types.ModuleType:
    """Reload the step operator module to pick up stubbed sys.modules.

    Returns:
        The reloaded module.
    """
    import zenml.integrations.huggingface.step_operators.huggingface_jobs_step_operator as mod

    return importlib.reload(mod)


class TestSplitEnvironment:
    """Tests for the split_environment utility function."""

    def test_pass_as_secrets_true(self):
        from zenml.integrations.huggingface.step_operators.huggingface_jobs_step_operator import (
            split_environment,
        )

        env = {"KEY1": "val1", "KEY2": "val2", "SECRET": "s3cr3t"}
        plain, secrets = split_environment(env, pass_as_secrets=True)
        assert plain == {}
        assert secrets == env

    def test_pass_as_secrets_false(self):
        from zenml.integrations.huggingface.step_operators.huggingface_jobs_step_operator import (
            split_environment,
        )

        env = {"KEY1": "val1", "KEY2": "val2"}
        plain, secrets = split_environment(env, pass_as_secrets=False)
        assert plain == env
        assert secrets == {}

    def test_empty_environment(self):
        from zenml.integrations.huggingface.step_operators.huggingface_jobs_step_operator import (
            split_environment,
        )

        plain, secrets = split_environment({}, pass_as_secrets=True)
        assert plain == {}
        assert secrets == {}

    def test_returns_copies(self):
        """Verify returned dicts are copies, not references."""
        from zenml.integrations.huggingface.step_operators.huggingface_jobs_step_operator import (
            split_environment,
        )

        env = {"KEY": "val"}
        plain, secrets = split_environment(env, pass_as_secrets=True)
        secrets["NEW"] = "new"
        assert "NEW" not in env

    def test_returns_copies_plain(self):
        from zenml.integrations.huggingface.step_operators.huggingface_jobs_step_operator import (
            split_environment,
        )

        env = {"KEY": "val"}
        plain, secrets = split_environment(env, pass_as_secrets=False)
        plain["NEW"] = "new"
        assert "NEW" not in env

    def test_strips_hf_token_from_plain_env(self):
        """HF token keys must never appear in plain_env."""
        from zenml.integrations.huggingface.step_operators.huggingface_jobs_step_operator import (
            split_environment,
        )

        env = {
            "KEY1": "val1",
            "HF_TOKEN": "secret_token",
            "HUGGING_FACE_HUB_TOKEN": "legacy_token",
        }
        plain, secrets = split_environment(env, pass_as_secrets=False)
        assert "HF_TOKEN" not in plain
        assert "HUGGING_FACE_HUB_TOKEN" not in plain
        assert plain == {"KEY1": "val1"}
        assert secrets == {}

    def test_strips_hf_token_from_secrets(self):
        """HF token keys stripped from secrets too (operator injects separately)."""
        from zenml.integrations.huggingface.step_operators.huggingface_jobs_step_operator import (
            split_environment,
        )

        env = {
            "KEY1": "val1",
            "HF_TOKEN": "secret_token",
            "HUGGING_FACE_HUB_TOKEN": "legacy_token",
        }
        plain, secrets = split_environment(env, pass_as_secrets=True)
        assert "HF_TOKEN" not in secrets
        assert "HUGGING_FACE_HUB_TOKEN" not in secrets
        assert plain == {}
        assert secrets == {"KEY1": "val1"}


class TestResolveToken:
    """Tests for the _resolve_token utility function."""

    def test_token_from_config(self):
        from zenml.integrations.huggingface.step_operators.huggingface_jobs_step_operator import (
            _resolve_token,
        )

        config = MagicMock(spec=HuggingFaceJobsStepOperatorConfig)
        config.token = "hf_config_token"
        assert _resolve_token(config) == "hf_config_token"

    def test_token_from_hf_token_env(self, monkeypatch):
        from zenml.integrations.huggingface.step_operators.huggingface_jobs_step_operator import (
            _resolve_token,
        )

        config = MagicMock(spec=HuggingFaceJobsStepOperatorConfig)
        config.token = None
        monkeypatch.setenv("HF_TOKEN", "hf_env_token")
        monkeypatch.delenv("HUGGING_FACE_HUB_TOKEN", raising=False)
        assert _resolve_token(config) == "hf_env_token"

    def test_token_from_legacy_env(self, monkeypatch):
        from zenml.integrations.huggingface.step_operators.huggingface_jobs_step_operator import (
            _resolve_token,
        )

        config = MagicMock(spec=HuggingFaceJobsStepOperatorConfig)
        config.token = None
        monkeypatch.delenv("HF_TOKEN", raising=False)
        monkeypatch.setenv("HUGGING_FACE_HUB_TOKEN", "hf_legacy_token")
        assert _resolve_token(config) == "hf_legacy_token"

    def test_token_from_cached_login(self, monkeypatch):
        """Uses stubbed huggingface_hub for cached token lookup."""
        _stub_huggingface_hub(monkeypatch, token="hf_cached_token")
        mod = _reload_step_operator_module()

        config = MagicMock(spec=HuggingFaceJobsStepOperatorConfig)
        config.token = None
        monkeypatch.delenv("HF_TOKEN", raising=False)
        monkeypatch.delenv("HUGGING_FACE_HUB_TOKEN", raising=False)

        assert mod._resolve_token(config) == "hf_cached_token"

    def test_no_token_raises(self, monkeypatch):
        """Raises when no token source is available."""
        _stub_huggingface_hub(monkeypatch, token=None)
        mod = _reload_step_operator_module()

        config = MagicMock(spec=HuggingFaceJobsStepOperatorConfig)
        config.token = None
        monkeypatch.delenv("HF_TOKEN", raising=False)
        monkeypatch.delenv("HUGGING_FACE_HUB_TOKEN", raising=False)

        with pytest.raises(RuntimeError, match="No Hugging Face token"):
            mod._resolve_token(config)

    def test_config_token_takes_precedence(self, monkeypatch):
        """Config token wins even when env vars are set."""
        from zenml.integrations.huggingface.step_operators.huggingface_jobs_step_operator import (
            _resolve_token,
        )

        config = MagicMock(spec=HuggingFaceJobsStepOperatorConfig)
        config.token = "hf_config_token"
        monkeypatch.setenv("HF_TOKEN", "hf_env_token")
        assert _resolve_token(config) == "hf_config_token"


class TestCheckHfJobsAvailability:
    """Tests for the _check_hf_jobs_availability function."""

    def test_available(self, monkeypatch):
        """Should not raise when run_job is importable and version is OK."""
        _stub_huggingface_hub(
            monkeypatch, has_run_job=True, installed_version="0.30.0"
        )
        mod = _reload_step_operator_module()
        mod._check_hf_jobs_availability()

    def test_unavailable_no_run_job(self, monkeypatch):
        """Should raise when run_job is not importable."""
        _stub_huggingface_hub(
            monkeypatch, has_run_job=False, installed_version="0.30.0"
        )
        mod = _reload_step_operator_module()

        with pytest.raises(RuntimeError, match="Jobs API"):
            mod._check_hf_jobs_availability()

    def test_unavailable_old_version(self, monkeypatch):
        """Should raise when version is too old."""
        _stub_huggingface_hub(
            monkeypatch, has_run_job=False, installed_version="0.25.0"
        )
        mod = _reload_step_operator_module()

        with pytest.raises(RuntimeError, match="0.25.0"):
            mod._check_hf_jobs_availability()

    def test_unavailable_not_installed(self, monkeypatch):
        """Should raise when huggingface_hub is not installed at all."""
        # Remove from sys.modules and make importlib.metadata.version fail
        monkeypatch.delitem(sys.modules, "huggingface_hub", raising=False)
        monkeypatch.delitem(
            sys.modules, "huggingface_hub._space_api", raising=False
        )

        original_version = importlib.metadata.version

        def _patched_version(name: str) -> str:
            if name == "huggingface_hub":
                raise importlib.metadata.PackageNotFoundError(name)
            return original_version(name)

        monkeypatch.setattr(importlib.metadata, "version", _patched_version)
        mod = _reload_step_operator_module()

        with pytest.raises(RuntimeError, match="not installed"):
            mod._check_hf_jobs_availability()


class TestSettings:
    """Tests for HuggingFaceJobsStepOperatorSettings defaults."""

    def test_default_settings(self):
        settings = HuggingFaceJobsStepOperatorSettings()
        assert settings.hardware_flavor is None
        assert settings.timeout is None
        assert settings.namespace is None

    def test_override_settings(self):
        settings = HuggingFaceJobsStepOperatorSettings(
            hardware_flavor="a10g-small",
            timeout="2h",
            namespace="my-org",
        )
        assert settings.hardware_flavor == "a10g-small"
        assert settings.timeout == "2h"
        assert settings.namespace == "my-org"


class TestConfig:
    """Tests for HuggingFaceJobsStepOperatorConfig defaults."""

    def test_default_config(self):
        config = HuggingFaceJobsStepOperatorConfig()
        assert config.token is None
        assert config.pass_env_as_secrets is True
        assert config.stream_logs is False
        assert config.poll_interval_seconds == 10.0
        assert config.is_remote is True

    def test_custom_config(self):
        config = HuggingFaceJobsStepOperatorConfig(
            token="hf_test",
            hardware_flavor="a100-large",
            timeout="1h",
            namespace="zenml-org",
            pass_env_as_secrets=False,
            stream_logs=True,
            poll_interval_seconds=30.0,
        )
        assert config.token == "hf_test"
        assert config.hardware_flavor == "a100-large"
        assert config.timeout == "1h"
        assert config.namespace == "zenml-org"
        assert config.pass_env_as_secrets is False
        assert config.stream_logs is True
        assert config.poll_interval_seconds == 30.0
