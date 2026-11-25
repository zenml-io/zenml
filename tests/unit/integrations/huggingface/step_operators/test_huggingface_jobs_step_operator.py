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
"""Unit tests for the HuggingFace Jobs step operator.

Uses real ``huggingface_hub.JobInfo`` objects when ``huggingface_hub`` is
installed, and mirrors the exact runtime shape (plain ``str`` for
``JobStatus.stage``, ``JobOwner.name``, ``get_token``) when running in
minimal CI environments without ``huggingface_hub``.
"""

import enum
import logging
import sys
import types
from typing import Any, Optional
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from zenml.config.resource_settings import ResourceSettings
from zenml.constants import (
    METADATA_ORCHESTRATOR_LOGS_URL,
    METADATA_ORCHESTRATOR_RUN_ID,
    METADATA_ORCHESTRATOR_URL,
)
from zenml.enums import ExecutionStatus, StackComponentType
from zenml.exceptions import (
    RunInterruptedException,
    RunStoppedException,
    StackValidationError,
)
from zenml.integrations.huggingface.flavors.huggingface_jobs_step_operator_flavor import (
    HuggingFaceJobsStepOperatorConfig,
    HuggingFaceJobsStepOperatorSettings,
)
from zenml.integrations.huggingface.step_operators import (
    huggingface_jobs_step_operator as mod,
)
from zenml.metadata.metadata_types import Uri
from zenml.step_operators import BaseStepOperator


class _FallbackJobStage(str, enum.Enum):
    """Mirrors real huggingface_hub.JobStage values when hub is uninstalled."""

    COMPLETED = "COMPLETED"
    CANCELED = "CANCELED"
    ERROR = "ERROR"
    DELETED = "DELETED"
    SCHEDULING = "SCHEDULING"
    RUNNING = "RUNNING"


def _make_job_info(
    stage: str,
    *,
    job_id: str = "job-123",
    owner_name: str = "alice",
    message: Optional[str] = None,
) -> Any:
    """Build a JobInfo whose ``status.stage`` is a plain string, like the SDK.

    Uses the real ``huggingface_hub.JobInfo`` constructor when available.

    Args:
        stage: Raw stage string (e.g. ``"RUNNING"``, ``"COMPLETED"``).
        job_id: Job identifier.
        owner_name: Job owner/namespace name.
        message: Optional status message.

    Returns:
        A real ``JobInfo`` or a shape-identical ``SimpleNamespace``.
    """
    payload = {
        "id": job_id,
        "owner": {"id": "owner-1", "name": owner_name, "type": "user"},
        "status": {"stage": stage, "message": message},
    }
    real_hf = sys.modules.get("huggingface_hub")
    job_info_cls = getattr(real_hf, "JobInfo", None) if real_hf else None
    if job_info_cls is not None:
        return job_info_cls(**payload)

    return types.SimpleNamespace(
        id=job_id,
        owner=types.SimpleNamespace(
            id="owner-1", name=owner_name, type="user"
        ),
        status=types.SimpleNamespace(stage=stage, message=message),
        url=f"https://huggingface.co/jobs/{owner_name}/{job_id}",
    )


def _install_hf_module(
    monkeypatch: pytest.MonkeyPatch,
    *,
    token: Optional[str] = "hf_cached_token",
    has_jobs_api: bool = True,
    hf_debug: bool = False,
) -> types.ModuleType:
    """Install a controllable huggingface_hub module in sys.modules.

    When the real ``huggingface_hub`` package is installed, preserves its
    real ``JobInfo`` and ``JobStage`` classes while patching only the network
    functions and ``get_token``.

    Args:
        monkeypatch: pytest monkeypatch fixture.
        token: Token returned by ``get_token()``.
        has_jobs_api: Whether Jobs API functions exist on the module.
        hf_debug: Value of ``constants.HF_DEBUG``.

    Returns:
        The patched module object.
    """
    real_job_info = None
    real_job_stage = None
    try:
        import huggingface_hub as real_hf

        real_job_info = getattr(real_hf, "JobInfo", None)
        real_job_stage = getattr(real_hf, "JobStage", None)
    except ImportError:
        pass

    fake_hf = types.ModuleType("huggingface_hub")
    fake_hf.constants = types.SimpleNamespace(HF_DEBUG=hf_debug)  # type: ignore[attr-defined]
    fake_hf.get_token = MagicMock(return_value=token)  # type: ignore[attr-defined]

    if real_job_info is not None:
        fake_hf.JobInfo = real_job_info  # type: ignore[attr-defined]

    if has_jobs_api:
        fake_hf.JobStage = real_job_stage or _FallbackJobStage  # type: ignore[attr-defined]
        fake_hf.run_job = MagicMock(  # type: ignore[attr-defined]
            return_value=_make_job_info("SCHEDULING")
        )
        fake_hf.inspect_job = MagicMock(  # type: ignore[attr-defined]
            return_value=_make_job_info("RUNNING")
        )
        fake_hf.cancel_job = MagicMock()  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "huggingface_hub", fake_hf)
    return fake_hf


def _make_operator(
    config: Optional[HuggingFaceJobsStepOperatorConfig] = None,
) -> mod.HuggingFaceJobsStepOperator:
    """Create a HuggingFaceJobsStepOperator instance without store wiring.

    Args:
        config: Optional operator configuration.

    Returns:
        A configured operator instance.
    """
    operator = mod.HuggingFaceJobsStepOperator.__new__(
        mod.HuggingFaceJobsStepOperator
    )
    operator.id = uuid4()
    operator.name = "hf_jobs"
    operator._config = config or HuggingFaceJobsStepOperatorConfig(
        token="hf_operator_token"
    )
    return operator


def _make_step_run_info(
    *,
    settings: Optional[HuggingFaceJobsStepOperatorSettings] = None,
    resource_settings: Optional[ResourceSettings] = None,
) -> MagicMock:
    """Create a mock StepRunInfo suitable for submit() tests.

    Args:
        settings: Optional step operator settings.
        resource_settings: Optional step resource settings.

    Returns:
        A mock StepRunInfo.
    """
    info = MagicMock()
    info.step_run_id = uuid4()
    info.run_name = "test-run"
    info.pipeline_step_name = "train_step"
    info.get_image.return_value = "docker.io/user/zenml:latest"
    info.config.resource_settings = resource_settings or ResourceSettings()
    info.step_run.run_metadata = {}
    info._settings = settings or HuggingFaceJobsStepOperatorSettings()
    return info


class TestSplitEnvironment:
    """Tests for split_environment."""

    def test_pass_as_secrets_true_keeps_all_vars_in_secrets(self) -> None:
        env = {
            "KEY1": "val1",
            "HF_TOKEN": "step_token",
            "HUGGING_FACE_HUB_TOKEN": "legacy_step_token",
        }
        plain, secrets = mod.split_environment(env, pass_as_secrets=True)
        assert plain == {}
        assert secrets == env

    def test_pass_as_secrets_false_routes_hf_tokens_to_secrets(self) -> None:
        env = {
            "KEY1": "val1",
            "HF_TOKEN": "step_token",
            "HUGGING_FACE_HUB_TOKEN": "legacy_step_token",
        }
        plain, secrets = mod.split_environment(env, pass_as_secrets=False)
        assert plain == {"KEY1": "val1"}
        assert secrets == {
            "HF_TOKEN": "step_token",
            "HUGGING_FACE_HUB_TOKEN": "legacy_step_token",
        }

    def test_pass_as_secrets_false_without_hf_tokens(self) -> None:
        env = {"KEY1": "val1", "KEY2": "val2"}
        plain, secrets = mod.split_environment(env, pass_as_secrets=False)
        assert plain == env
        assert secrets == {}

    def test_returns_copies(self) -> None:
        env = {"KEY": "val"}
        plain, secrets = mod.split_environment(env, pass_as_secrets=True)
        secrets["NEW"] = "new"
        assert "NEW" not in env
        assert plain == {}

        plain2, _ = mod.split_environment(env, pass_as_secrets=False)
        plain2["NEW"] = "new"
        assert "NEW" not in env


class TestResolveToken:
    """Tests for _resolve_token."""

    def test_config_token_takes_precedence(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_hf = _install_hf_module(monkeypatch, token="hf_from_get_token")
        config = HuggingFaceJobsStepOperatorConfig(token="hf_config_token")
        assert mod._resolve_token(config) == "hf_config_token"
        fake_hf.get_token.assert_not_called()

    def test_uses_huggingface_hub_get_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_hf = _install_hf_module(monkeypatch, token="hf_from_get_token")
        monkeypatch.delenv("HUGGING_FACE_HUB_TOKEN", raising=False)
        config = HuggingFaceJobsStepOperatorConfig(token=None)
        assert mod._resolve_token(config) == "hf_from_get_token"
        fake_hf.get_token.assert_called_once()

    def test_falls_back_to_legacy_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_hf_module(monkeypatch, token=None)
        monkeypatch.setenv("HUGGING_FACE_HUB_TOKEN", "hf_legacy_token")
        config = HuggingFaceJobsStepOperatorConfig(token=None)
        assert mod._resolve_token(config) == "hf_legacy_token"

    def test_no_token_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _install_hf_module(monkeypatch, token=None)
        monkeypatch.delenv("HUGGING_FACE_HUB_TOKEN", raising=False)
        config = HuggingFaceJobsStepOperatorConfig(token=None)
        with pytest.raises(RuntimeError, match="hf auth login"):
            mod._resolve_token(config)


class TestCheckHfJobsAvailability:
    """Tests for _check_hf_jobs_availability."""

    def test_available(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _install_hf_module(monkeypatch, has_jobs_api=True)
        mod._check_hf_jobs_availability()

    def test_unavailable_missing_jobs_api(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_hf_module(monkeypatch, has_jobs_api=False)
        with pytest.raises(RuntimeError, match="0.34.0"):
            mod._check_hf_jobs_availability()

    def test_unavailable_not_installed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(sys.modules, "huggingface_hub", None)
        with pytest.raises(RuntimeError, match="0.34.0"):
            mod._check_hf_jobs_availability()


class TestSettingsAndConfig:
    """Tests for settings and config defaults."""

    def test_default_settings(self) -> None:
        settings = HuggingFaceJobsStepOperatorSettings()
        assert settings.hardware_flavor is None
        assert settings.timeout is None
        assert settings.namespace is None

    def test_default_config(self) -> None:
        config = HuggingFaceJobsStepOperatorConfig()
        assert config.token is None
        assert config.pass_env_as_secrets is True
        assert config.is_remote is True
        assert not hasattr(config, "stream_logs")
        assert not hasattr(config, "poll_interval_seconds")


class TestValidator:
    """Tests for stack validation."""

    def _make_stack(
        self,
        *,
        local_artifact_store: bool = False,
        local_registry: bool = False,
        include_image_builder: bool = True,
    ) -> MagicMock:
        stack = MagicMock()
        stack.name = "hf-test-stack"
        stack.artifact_store.name = "artifact_store"
        stack.artifact_store.type = StackComponentType.ARTIFACT_STORE
        stack.artifact_store.config.is_local = local_artifact_store
        stack.container_registry.name = "container_registry"
        stack.container_registry.type = StackComponentType.CONTAINER_REGISTRY
        stack.container_registry.config.is_local = local_registry

        components = [stack.artifact_store, stack.container_registry]
        if include_image_builder:
            image_builder = MagicMock()
            image_builder.type = StackComponentType.IMAGE_BUILDER
            components.append(image_builder)
        stack.all_components = components
        return stack

    def test_rejects_local_artifact_store(self) -> None:
        operator = _make_operator()
        validator = operator.validator
        assert validator is not None

        with pytest.raises(StackValidationError, match="artifact store"):
            validator.validate(self._make_stack(local_artifact_store=True))

    def test_rejects_local_container_registry(self) -> None:
        operator = _make_operator()
        validator = operator.validator
        assert validator is not None

        with pytest.raises(StackValidationError, match="container registry"):
            validator.validate(self._make_stack(local_registry=True))

    def test_rejects_missing_image_builder(self) -> None:
        operator = _make_operator()
        validator = operator.validator
        assert validator is not None

        with pytest.raises(StackValidationError, match="IMAGE_BUILDER"):
            validator.validate(self._make_stack(include_image_builder=False))

    def test_accepts_remote_stack(self) -> None:
        operator = _make_operator()
        validator = operator.validator
        assert validator is not None

        validator.validate(self._make_stack())


class TestSubmit:
    """Tests for submit()."""

    def test_submit_passes_hardware_string_persists_owner_and_does_not_inject_operator_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_hf = _install_hf_module(monkeypatch)
        fake_hf.run_job.return_value = _make_job_info(
            "SCHEDULING", job_id="job-999", owner_name="strickvl"
        )
        publish_mock = MagicMock()
        monkeypatch.setattr(mod, "publish_step_run_metadata", publish_mock)

        operator = _make_operator(
            HuggingFaceJobsStepOperatorConfig(
                token="hf_operator_admin_token",
                hardware_flavor="h200",
                timeout="2h",
            )
        )
        settings = HuggingFaceJobsStepOperatorSettings(
            hardware_flavor="h200",
            timeout="2h",
            namespace=None,
        )
        monkeypatch.setattr(operator, "get_settings", lambda _info: settings)

        info = _make_step_run_info(settings=settings)
        operator.submit(
            info=info,
            entrypoint_command=["python", "-m", "zenml.step"],
            environment={"ZENML_STORE_URL": "https://example.com"},
        )

        fake_hf.run_job.assert_called_once_with(
            image="docker.io/user/zenml:latest",
            command=["python", "-m", "zenml.step"],
            env=None,
            secrets={"ZENML_STORE_URL": "https://example.com"},
            flavor="h200",
            timeout="2h",
            namespace=None,
            token="hf_operator_admin_token",
        )
        published = publish_mock.call_args.kwargs["step_run_metadata"][
            operator.id
        ]
        assert published[mod.STEP_JOB_ID_METADATA_KEY] == "job-999"
        assert published[METADATA_ORCHESTRATOR_RUN_ID] == "job-999"
        assert published[mod._HF_JOB_NAMESPACE_METADATA_KEY] == "strickvl"
        assert published[METADATA_ORCHESTRATOR_URL] == Uri(
            "https://huggingface.co/jobs/strickvl/job-999"
        )
        assert published[METADATA_ORCHESTRATOR_LOGS_URL] == Uri(
            "https://huggingface.co/jobs/strickvl/job-999"
        )
        assert info.step_run.run_metadata[mod.STEP_JOB_ID_METADATA_KEY] == (
            "job-999"
        )
        assert (
            info.step_run.run_metadata[mod._HF_JOB_NAMESPACE_METADATA_KEY]
            == "strickvl"
        )

    def test_submit_preserves_step_supplied_hf_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_hf = _install_hf_module(monkeypatch)
        fake_hf.run_job.return_value = _make_job_info("SCHEDULING")
        monkeypatch.setattr(mod, "publish_step_run_metadata", MagicMock())

        operator = _make_operator(
            HuggingFaceJobsStepOperatorConfig(
                token="hf_operator_admin_token",
                pass_env_as_secrets=False,
            )
        )
        monkeypatch.setattr(
            operator,
            "get_settings",
            lambda _info: HuggingFaceJobsStepOperatorSettings(),
        )
        info = _make_step_run_info()

        operator.submit(
            info=info,
            entrypoint_command=["python", "run.py"],
            environment={
                "PLAIN_VAR": "1",
                "HF_TOKEN": "hf_scoped_step_token",
            },
        )

        call_kwargs = fake_hf.run_job.call_args.kwargs
        assert call_kwargs["env"] == {"PLAIN_VAR": "1"}
        assert call_kwargs["secrets"] == {"HF_TOKEN": "hf_scoped_step_token"}
        assert call_kwargs["token"] == "hf_operator_admin_token"

    def test_submit_cancels_job_and_reraises_when_metadata_publish_fails(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_hf = _install_hf_module(monkeypatch)
        fake_hf.run_job.return_value = _make_job_info(
            "SCHEDULING", job_id="job-orphan", owner_name="my-org"
        )
        monkeypatch.setattr(
            mod,
            "publish_step_run_metadata",
            MagicMock(side_effect=RuntimeError("server unreachable")),
        )

        operator = _make_operator()
        monkeypatch.setattr(
            operator,
            "get_settings",
            lambda _info: HuggingFaceJobsStepOperatorSettings(),
        )
        info = _make_step_run_info()

        with pytest.raises(RuntimeError, match="server unreachable"):
            operator.submit(
                info=info,
                entrypoint_command=["python", "run.py"],
                environment={},
            )

        fake_hf.cancel_job.assert_called_once_with(
            job_id="job-orphan",
            namespace="my-org",
            token="hf_operator_token",
        )

    def test_submit_warns_on_resource_settings_and_hf_debug(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        fake_hf = _install_hf_module(monkeypatch, hf_debug=True)
        fake_hf.run_job.return_value = _make_job_info("SCHEDULING")
        monkeypatch.setattr(mod, "publish_step_run_metadata", MagicMock())

        operator = _make_operator()
        monkeypatch.setattr(
            operator,
            "get_settings",
            lambda _info: HuggingFaceJobsStepOperatorSettings(),
        )
        info = _make_step_run_info(
            resource_settings=ResourceSettings(gpu_count=1)
        )

        with caplog.at_level(logging.WARNING):
            operator.submit(
                info=info,
                entrypoint_command=["python", "run.py"],
                environment={"SECRET_KEY": "value"},
            )

        assert "ResourceSettings" in caplog.text
        assert "hardware_flavor" in caplog.text
        assert "HF_DEBUG" in caplog.text


class TestGetStatus:
    """Tests for get_status() using plain-string stages."""

    @pytest.mark.parametrize(
        ("stage", "expected"),
        [
            ("COMPLETED", ExecutionStatus.COMPLETED),
            ("ERROR", ExecutionStatus.FAILED),
            ("CANCELED", ExecutionStatus.FAILED),
            ("DELETED", ExecutionStatus.FAILED),
            ("RUNNING", ExecutionStatus.RUNNING),
            ("SCHEDULING", ExecutionStatus.RUNNING),
        ],
    )
    def test_maps_plain_string_stages(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stage: str,
        expected: ExecutionStatus,
    ) -> None:
        fake_hf = _install_hf_module(monkeypatch)
        fake_hf.inspect_job.return_value = _make_job_info(
            stage, message="boom" if stage == "ERROR" else None
        )

        operator = _make_operator()
        step_run = MagicMock()
        step_run.run_metadata = {
            mod.STEP_JOB_ID_METADATA_KEY: "job-123",
            mod._HF_JOB_NAMESPACE_METADATA_KEY: "my-org",
        }

        assert operator.get_status(step_run) == expected
        fake_hf.inspect_job.assert_called_once_with(
            job_id="job-123",
            namespace="my-org",
            token="hf_operator_token",
        )


class TestWait:
    """Tests for wait() lifecycle and cancellation."""

    def test_wait_polls_running_then_completed_with_plain_string_stage(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_hf = _install_hf_module(monkeypatch)
        fake_hf.inspect_job.side_effect = [
            _make_job_info("SCHEDULING"),
            _make_job_info("RUNNING"),
            _make_job_info("COMPLETED"),
        ]
        monkeypatch.setattr(
            "zenml.step_operators.base_step_operator.time.sleep",
            lambda _s: None,
        )

        operator = _make_operator()
        step_run = MagicMock()
        step_run.id = uuid4()
        step_run.run_metadata = {
            mod.STEP_JOB_ID_METADATA_KEY: "job-123",
            mod._HF_JOB_NAMESPACE_METADATA_KEY: "alice",
        }

        assert operator.wait(step_run) == ExecutionStatus.COMPLETED
        assert fake_hf.inspect_job.call_count == 3
        fake_hf.cancel_job.assert_not_called()

    @pytest.mark.parametrize(
        "exc_cls",
        [KeyboardInterrupt, RunStoppedException, RunInterruptedException],
    )
    def test_wait_cancels_job_on_stop_or_interrupt(
        self,
        monkeypatch: pytest.MonkeyPatch,
        exc_cls: type[BaseException],
    ) -> None:
        fake_hf = _install_hf_module(monkeypatch)
        fake_hf.inspect_job.return_value = _make_job_info("RUNNING")

        def _raise_on_sleep(_seconds: float) -> None:
            raise exc_cls("stopped")

        monkeypatch.setattr(
            "zenml.step_operators.base_step_operator.time.sleep",
            _raise_on_sleep,
        )

        operator = _make_operator()
        step_run = MagicMock()
        step_run.id = uuid4()
        step_run.run_metadata = {
            mod.STEP_JOB_ID_METADATA_KEY: "job-stop",
            mod._HF_JOB_NAMESPACE_METADATA_KEY: "alice",
        }

        with pytest.raises(exc_cls):
            operator.wait(step_run)

        fake_hf.cancel_job.assert_called_once_with(
            job_id="job-stop",
            namespace="alice",
            token="hf_operator_token",
        )

    def test_wait_cancels_job_when_base_wait_returns_stopped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_hf = _install_hf_module(monkeypatch)
        monkeypatch.setattr(
            BaseStepOperator,
            "wait",
            lambda _self, _step_run: ExecutionStatus.STOPPED,
        )

        operator = _make_operator()
        step_run = MagicMock()
        step_run.run_metadata = {
            mod.STEP_JOB_ID_METADATA_KEY: "job-stopped",
            mod._HF_JOB_NAMESPACE_METADATA_KEY: "alice",
        }

        assert operator.wait(step_run) == ExecutionStatus.STOPPED
        fake_hf.cancel_job.assert_called_once_with(
            job_id="job-stopped",
            namespace="alice",
            token="hf_operator_token",
        )


class TestCancelAndJobIdentity:
    """Tests for cancel() and _get_job_identity()."""

    def test_cancel_calls_cancel_job(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_hf = _install_hf_module(monkeypatch)
        operator = _make_operator()
        step_run = MagicMock()
        step_run.run_metadata = {
            mod.STEP_JOB_ID_METADATA_KEY: "job-456",
            mod._HF_JOB_NAMESPACE_METADATA_KEY: "zenml-org",
        }

        operator.cancel(step_run)

        fake_hf.cancel_job.assert_called_once_with(
            job_id="job-456",
            namespace="zenml-org",
            token="hf_operator_token",
        )

    def test_cancel_suppresses_errors(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_hf = _install_hf_module(monkeypatch)
        fake_hf.cancel_job.side_effect = RuntimeError("API down")

        operator = _make_operator()
        step_run = MagicMock()
        step_run.run_metadata = {mod.STEP_JOB_ID_METADATA_KEY: "job-789"}

        operator.cancel(step_run)

    def test_fallback_to_orchestrator_run_id(self) -> None:
        operator = _make_operator()
        step_run = MagicMock()
        step_run.run_metadata = {METADATA_ORCHESTRATOR_RUN_ID: "job-fallback"}

        job_id, namespace = operator._get_job_identity(step_run)
        assert job_id == "job-fallback"
        assert namespace is None

    def test_missing_metadata_raises(self) -> None:
        operator = _make_operator()
        step_run = MagicMock()
        step_run.run_metadata = {}

        with pytest.raises(RuntimeError, match="Cannot find HuggingFace Job"):
            operator._get_job_identity(step_run)
