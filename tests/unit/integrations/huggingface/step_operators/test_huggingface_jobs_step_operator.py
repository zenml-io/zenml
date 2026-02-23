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
"""Unit tests for HuggingFace Jobs step operator utility functions."""

from unittest.mock import MagicMock, patch

import pytest

from zenml.integrations.huggingface.flavors.huggingface_jobs_step_operator_flavor import (
    HuggingFaceJobsStepOperatorConfig,
    HuggingFaceJobsStepOperatorSettings,
)
from zenml.integrations.huggingface.step_operators.huggingface_jobs_step_operator import (
    _check_hf_jobs_availability,
    _resolve_token,
    split_environment,
)


class TestSplitEnvironment:
    """Tests for the split_environment utility function."""

    def test_pass_as_secrets_true(self):
        env = {"KEY1": "val1", "KEY2": "val2", "SECRET": "s3cr3t"}
        plain, secrets = split_environment(env, pass_as_secrets=True)
        assert plain == {}
        assert secrets == env

    def test_pass_as_secrets_false(self):
        env = {"KEY1": "val1", "KEY2": "val2"}
        plain, secrets = split_environment(env, pass_as_secrets=False)
        assert plain == env
        assert secrets == {}

    def test_empty_environment(self):
        plain, secrets = split_environment({}, pass_as_secrets=True)
        assert plain == {}
        assert secrets == {}

    def test_returns_copies(self):
        """Verify returned dicts are copies, not references."""
        env = {"KEY": "val"}
        plain, secrets = split_environment(env, pass_as_secrets=True)
        secrets["NEW"] = "new"
        assert "NEW" not in env

    def test_returns_copies_plain(self):
        env = {"KEY": "val"}
        plain, secrets = split_environment(env, pass_as_secrets=False)
        plain["NEW"] = "new"
        assert "NEW" not in env


class TestResolveToken:
    """Tests for the _resolve_token utility function."""

    def test_token_from_config(self):
        config = MagicMock(spec=HuggingFaceJobsStepOperatorConfig)
        config.token = "hf_config_token"
        assert _resolve_token(config) == "hf_config_token"

    def test_token_from_hf_token_env(self, monkeypatch):
        config = MagicMock(spec=HuggingFaceJobsStepOperatorConfig)
        config.token = None
        monkeypatch.setenv("HF_TOKEN", "hf_env_token")
        monkeypatch.delenv("HUGGING_FACE_HUB_TOKEN", raising=False)
        assert _resolve_token(config) == "hf_env_token"

    def test_token_from_legacy_env(self, monkeypatch):
        config = MagicMock(spec=HuggingFaceJobsStepOperatorConfig)
        config.token = None
        monkeypatch.delenv("HF_TOKEN", raising=False)
        monkeypatch.setenv("HUGGING_FACE_HUB_TOKEN", "hf_legacy_token")
        assert _resolve_token(config) == "hf_legacy_token"

    def test_token_from_cached_login(self, monkeypatch):
        config = MagicMock(spec=HuggingFaceJobsStepOperatorConfig)
        config.token = None
        monkeypatch.delenv("HF_TOKEN", raising=False)
        monkeypatch.delenv("HUGGING_FACE_HUB_TOKEN", raising=False)

        with patch("huggingface_hub.HfFolder") as mock_hf_folder:
            mock_hf_folder.get_token.return_value = "hf_cached_token"
            assert _resolve_token(config) == "hf_cached_token"

    def test_no_token_raises(self, monkeypatch):
        config = MagicMock(spec=HuggingFaceJobsStepOperatorConfig)
        config.token = None
        monkeypatch.delenv("HF_TOKEN", raising=False)
        monkeypatch.delenv("HUGGING_FACE_HUB_TOKEN", raising=False)

        with patch("huggingface_hub.HfFolder") as mock_hf_folder:
            mock_hf_folder.get_token.return_value = None
            with pytest.raises(RuntimeError, match="No Hugging Face token"):
                _resolve_token(config)

    def test_config_token_takes_precedence(self, monkeypatch):
        """Config token wins even when env vars are set."""
        config = MagicMock(spec=HuggingFaceJobsStepOperatorConfig)
        config.token = "hf_config_token"
        monkeypatch.setenv("HF_TOKEN", "hf_env_token")
        assert _resolve_token(config) == "hf_config_token"


class TestCheckHfJobsAvailability:
    """Tests for the _check_hf_jobs_availability function."""

    def test_available(self):
        """Should not raise when run_job is importable."""
        _check_hf_jobs_availability()

    def test_unavailable(self):
        """Should raise RuntimeError when run_job is not importable."""
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "huggingface_hub" and "run_job" in str(args):
                raise ImportError("mocked")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(RuntimeError, match="Jobs API"):
                _check_hf_jobs_availability()


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
        assert config.stream_logs is True
        assert config.poll_interval_seconds == 10.0
        assert config.is_remote is True

    def test_custom_config(self):
        config = HuggingFaceJobsStepOperatorConfig(
            token="hf_test",
            hardware_flavor="a100-large",
            timeout="1h",
            namespace="zenml-org",
            pass_env_as_secrets=False,
            stream_logs=False,
            poll_interval_seconds=30.0,
        )
        assert config.token == "hf_test"
        assert config.hardware_flavor == "a100-large"
        assert config.timeout == "1h"
        assert config.namespace == "zenml-org"
        assert config.pass_env_as_secrets is False
        assert config.stream_logs is False
        assert config.poll_interval_seconds == 30.0
