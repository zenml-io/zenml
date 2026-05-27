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
"""Unit tests for the Sandbox base abstraction."""

from datetime import datetime
from typing import Dict, Iterator, List, Optional, Type, Union
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from zenml.enums import StackComponentType
from zenml.sandboxes import (
    STEP_IMAGE,
    BaseSandbox,
    BaseSandboxConfig,
    BaseSandboxFlavor,
    BaseSandboxSettings,
    BaseSandboxSnapshot,
    SandboxExecError,
    SandboxProcess,
    SandboxSession,
)


class _FakeProcess(SandboxProcess):
    """Minimal SandboxProcess for testing."""

    def __init__(self, code: int = 0) -> None:
        self._code = code

    def stdout(self) -> Iterator[str]:
        yield "line1"
        yield "line2"

    def stderr(self) -> Iterator[str]:
        return iter(())

    def wait(self, timeout: Optional[float] = None) -> int:
        return self._code

    def kill(self) -> None:
        return None

    @property
    def exit_code(self) -> Optional[int]:
        return self._code


class _FakeSession(SandboxSession):
    """Minimal SandboxSession for testing. Only implements `exec` + `close`."""

    def __init__(self, session_id: str = "sess-1") -> None:
        self.id = session_id
        self.closed = False

    def exec(
        self,
        command: Union[str, List[str]],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> SandboxProcess:
        return _FakeProcess()

    def close(self) -> None:
        self.closed = True


class _FakeSandbox(BaseSandbox):
    """Minimal BaseSandbox for testing. `create_session` returns a fake."""

    def create_session(
        self, settings: Optional[BaseSandboxSettings] = None
    ) -> SandboxSession:
        return _FakeSession()


class _FakeSandboxFlavor(BaseSandboxFlavor):
    """Minimal flavor pointing at _FakeSandbox."""

    @property
    def name(self) -> str:
        return "fake"

    @property
    def implementation_class(self) -> Type[BaseSandbox]:
        return _FakeSandbox


def _make_sandbox(
    flavor: str = "fake",
    *,
    environment: Optional[Dict[str, str]] = None,
    secrets: Optional[List] = None,
) -> _FakeSandbox:
    """Build a _FakeSandbox without going through Stack/Client."""
    return _FakeSandbox(
        name="test-sandbox",
        id=uuid4(),
        config=BaseSandboxConfig(),
        flavor=flavor,
        type=StackComponentType.SANDBOX,
        user=None,
        created=datetime.now(),
        updated=datetime.now(),
        environment=environment or {},
        secrets=secrets or [],
    )


class TestStepImageSentinel:
    def test_sentinel_is_a_string(self) -> None:
        assert isinstance(STEP_IMAGE, str)

    def test_sentinel_value_matches_module_export(self) -> None:
        from zenml.sandboxes.base_sandbox import STEP_IMAGE as direct

        assert STEP_IMAGE == direct


class TestFlavor:
    def test_flavor_type_is_sandbox(self) -> None:
        assert _FakeSandboxFlavor().type == StackComponentType.SANDBOX

    def test_default_config_class_is_base(self) -> None:
        assert _FakeSandboxFlavor().config_class is BaseSandboxConfig


class TestConfig:
    def test_is_remote_defaults_false(self) -> None:
        # Sandboxes are called from inside step code; server doesn't need
        # to reach them — unlike orchestrators / step operators.
        assert BaseSandboxConfig().is_remote is False
        assert BaseSandboxConfig().is_local is True


class TestSettings:
    def test_defaults(self) -> None:
        s = BaseSandboxSettings()
        assert s.base_image is None
        assert s.environment == {}
        assert s.copy_local_env is False
        assert s.timeout_seconds is None
        assert s.forward_logs_to_step is None

    def test_step_image_sentinel_accepted(self) -> None:
        s = BaseSandboxSettings(base_image=STEP_IMAGE)
        assert s.base_image == STEP_IMAGE


class TestSnapshotModel:
    def test_round_trip(self) -> None:
        snap = BaseSandboxSnapshot(
            provider="fake",
            ref="snap-123",
            metadata={"size_mb": 42},
        )
        restored = BaseSandboxSnapshot.model_validate_json(
            snap.model_dump_json()
        )
        assert restored == snap

    def test_metadata_defaults_empty(self) -> None:
        snap = BaseSandboxSnapshot(provider="fake", ref="r")
        assert snap.metadata == {}


class TestSessionContextManager:
    def test_with_block_calls_close(self) -> None:
        session = _FakeSession()
        with session as s:
            assert s is session
            assert session.closed is False
        assert session.closed is True


class TestSessionOptionalMethods:
    """Optional methods on SandboxSession raise NotImplementedError by default."""

    def test_aexec_default_raises(self) -> None:
        import asyncio

        session = _FakeSession()
        with pytest.raises(NotImplementedError):
            asyncio.run(session.aexec("echo hi"))

    def test_snapshot_default_raises(self) -> None:
        with pytest.raises(NotImplementedError):
            _FakeSession().snapshot()

    def test_upload_file_default_raises(self) -> None:
        with pytest.raises(NotImplementedError):
            _FakeSession().upload_file("/local", "/remote")

    def test_download_file_default_raises(self) -> None:
        with pytest.raises(NotImplementedError):
            _FakeSession().download_file("/remote", "/local")

    def test_destroy_default_raises(self) -> None:
        with pytest.raises(NotImplementedError):
            _FakeSession().destroy()


class TestSandboxOptionalMethods:
    def test_attach_default_raises(self) -> None:
        with pytest.raises(NotImplementedError):
            _make_sandbox().attach("sess-1")


class TestRestoreProviderGuard:
    def test_validate_snapshot_provider_rejects_cross_provider(self) -> None:
        sandbox = _make_sandbox(flavor="fake")
        wrong_snap = BaseSandboxSnapshot(provider="other", ref="r")
        with pytest.raises(ValueError, match="provider 'other'"):
            sandbox._validate_snapshot_provider(wrong_snap)

    def test_validate_snapshot_provider_passes_on_match(self) -> None:
        sandbox = _make_sandbox(flavor="fake")
        matching_snap = BaseSandboxSnapshot(provider="fake", ref="r")
        # Returns None; no exception.
        assert sandbox._validate_snapshot_provider(matching_snap) is None

    def test_restore_default_raises_not_implemented(self) -> None:
        # Base restore() is opt-in. Flavors override; default raises.
        sandbox = _make_sandbox(flavor="fake")
        snap = BaseSandboxSnapshot(provider="fake", ref="r")
        with pytest.raises(NotImplementedError):
            sandbox.restore(snap)


class TestResolveSessionEnvironment:
    def test_component_env_alone(self) -> None:
        sb = _make_sandbox(environment={"A": "1"})
        merged = sb._resolve_session_environment(None)
        assert merged == {"A": "1"}

    def test_settings_env_overrides_component(self) -> None:
        sb = _make_sandbox(environment={"A": "1", "B": "1"})
        settings = BaseSandboxSettings(environment={"A": "2"})
        merged = sb._resolve_session_environment(settings)
        assert merged == {"A": "2", "B": "1"}

    def test_secrets_exploded_between_component_and_settings(self) -> None:
        # Component secret defines API_KEY; Settings overrides.
        fake_secret = MagicMock(secret_values={"API_KEY": "from_secret"})
        fake_client = MagicMock()
        fake_client.get_secret.return_value = fake_secret
        sb = _make_sandbox(secrets=["secret-uuid"])
        settings = BaseSandboxSettings(environment={"API_KEY": "from_step"})
        with patch("zenml.client.Client", return_value=fake_client):
            merged = sb._resolve_session_environment(settings)
        assert merged["API_KEY"] == "from_step"  # settings wins

    def test_settings_env_resolves_secret_references(self) -> None:
        fake_secret = MagicMock(secret_values={"api_key": "sk-xxx"})
        fake_client = MagicMock()
        fake_client.get_secret_by_name_and_private_status.return_value = (
            fake_secret
        )
        sb = _make_sandbox()
        settings = BaseSandboxSettings(
            environment={"OPENAI_API_KEY": "{{openai_creds.api_key}}"}
        )
        with patch("zenml.client.Client", return_value=fake_client):
            merged = sb._resolve_session_environment(settings)
        assert merged["OPENAI_API_KEY"] == "sk-xxx"

    def test_settings_env_unresolvable_ref_is_skipped(self) -> None:
        # Bad refs log a warning and drop the key — not raise.
        fake_client = MagicMock()
        fake_client.get_secret_by_name_and_private_status.side_effect = (
            RuntimeError("not found")
        )
        sb = _make_sandbox()
        settings = BaseSandboxSettings(
            environment={
                "OK": "plain",
                "BAD": "{{missing_secret.key}}",
            }
        )
        with patch("zenml.client.Client", return_value=fake_client):
            merged = sb._resolve_session_environment(settings)
        assert merged == {"OK": "plain"}

    def test_copy_local_env_layered_last(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("FROM_LOCAL", "local-val")
        sb = _make_sandbox(environment={"COMPONENT": "yes"})
        settings = BaseSandboxSettings(copy_local_env=True)
        merged = sb._resolve_session_environment(settings)
        assert merged["COMPONENT"] == "yes"
        assert merged["FROM_LOCAL"] == "local-val"


class TestResolveForwardLogs:
    def test_explicit_true(self) -> None:
        sb = _make_sandbox()
        s = BaseSandboxSettings(forward_logs_to_step=True)
        assert sb.resolve_forward_logs_to_step(s) is True

    def test_explicit_false(self) -> None:
        sb = _make_sandbox()
        s = BaseSandboxSettings(forward_logs_to_step=False)
        assert sb.resolve_forward_logs_to_step(s) is False

    def test_none_defaults_true_for_step_image(self) -> None:
        sb = _make_sandbox()
        s = BaseSandboxSettings(base_image=STEP_IMAGE)
        assert sb.resolve_forward_logs_to_step(s) is True

    def test_none_defaults_false_for_other_images(self) -> None:
        sb = _make_sandbox()
        assert sb.resolve_forward_logs_to_step(BaseSandboxSettings()) is False
        assert (
            sb.resolve_forward_logs_to_step(
                BaseSandboxSettings(base_image="python:3.11-slim")
            )
            is False
        )


class TestForwardLines:
    def test_yields_lines_unchanged(self) -> None:
        with patch("zenml.sandboxes.base_sandbox.logger") as log:
            out = list(
                BaseSandbox.forward_lines(
                    iter(["a\n", "b\n"]), stream="stdout"
                )
            )
            assert out == ["a\n", "b\n"]
            log.info.assert_any_call("a")
            log.info.assert_any_call("b")

    def test_stderr_goes_to_warning(self) -> None:
        with patch("zenml.sandboxes.base_sandbox.logger") as log:
            list(BaseSandbox.forward_lines(iter(["oops\n"]), stream="stderr"))
            log.warning.assert_called_with("oops")


class TestForwardSessionLogs:
    def test_falls_back_gracefully_when_setup_raises(self) -> None:
        sb = _make_sandbox()
        # No active stack/log store in this test process — setup_logging_context
        # raises. The context manager should yield anyway, not error.
        with patch(
            "zenml.utils.logging_utils.setup_logging_context",
            side_effect=RuntimeError("no log store"),
        ):
            with sb.forward_session_logs("sess-1"):
                pass  # must not raise


class TestSandboxExecError:
    def test_is_runtime_error_subclass(self) -> None:
        assert issubclass(SandboxExecError, RuntimeError)

    def test_message_passes_through(self) -> None:
        err = SandboxExecError("command not found: foo")
        assert "command not found" in str(err)


class TestCreateSessionIsRequired:
    def test_create_session_returns_session(self) -> None:
        # Sanity: the only abstract method on BaseSandbox is create_session;
        # our fake implements it and returns a working session.
        session = _make_sandbox().create_session()
        assert isinstance(session, SandboxSession)
        assert session.id == "sess-1"
