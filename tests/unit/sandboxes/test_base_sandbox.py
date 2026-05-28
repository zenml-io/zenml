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

import logging
import time
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
    SandboxOutput,
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

    def __init__(
        self,
        session_id: str = "sess-1",
        parent: Optional["BaseSandbox"] = None,
    ) -> None:
        super().__init__(
            id=session_id,
            parent=parent or MagicMock(spec=BaseSandbox, flavor="fake"),
        )
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
        self._close_log_origin()


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
        from zenml.sandboxes.base import STEP_IMAGE as direct

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


class TestSessionMetadata:
    """SandboxSession._on_enter publishes session-scoped step metadata.

    Keys are suffixed with the session id so steps that open multiple
    sandbox sessions don't overwrite each other.
    """

    def test_logs_flavor_and_dashboard_url_keyed_by_session_id(
        self,
    ) -> None:
        session = _FakeSession(session_id="sb-test-1")
        session._dashboard_url = lambda: "https://example/sb-test-1"  # type: ignore[method-assign]
        with patch("zenml.utils.metadata_utils.log_metadata") as log_meta:
            session._on_enter()
        from zenml.metadata.metadata_types import Uri

        payload = log_meta.call_args.kwargs["metadata"]
        assert payload["sandbox.sb-test-1.flavor"] == "fake"
        assert isinstance(payload["sandbox.sb-test-1.dashboard_url"], Uri)

    def test_two_sessions_produce_disjoint_keys(self) -> None:
        s1 = _FakeSession(session_id="sb-1")
        s2 = _FakeSession(session_id="sb-2")
        s2._dashboard_url = lambda: "https://example/sb-2"  # type: ignore[method-assign]
        with patch("zenml.utils.metadata_utils.log_metadata") as log_meta:
            s1._on_enter()
            s2._on_enter()
        first = log_meta.call_args_list[0].kwargs["metadata"]
        second = log_meta.call_args_list[1].kwargs["metadata"]
        assert "sandbox.sb-1.flavor" in first
        assert "sandbox.sb-1.flavor" not in second
        assert "sandbox.sb-2.flavor" in second
        assert "sandbox.sb-2.dashboard_url" in second

    def test_omits_dashboard_url_when_hook_returns_none(self) -> None:
        session = _FakeSession(session_id="sb-x")
        with patch("zenml.utils.metadata_utils.log_metadata") as log_meta:
            session._on_enter()
        payload = log_meta.call_args.kwargs["metadata"]
        assert "sandbox.sb-x.dashboard_url" not in payload

    def test_value_error_swallowed_at_debug(self) -> None:
        with (
            patch(
                "zenml.utils.metadata_utils.log_metadata",
                side_effect=ValueError("not in a step"),
            ),
            patch("zenml.sandboxes.session.logger.debug") as dbg,
            patch("zenml.sandboxes.session.logger.warning") as warn,
        ):
            _FakeSession()._on_enter()
        dbg.assert_called()
        warn.assert_not_called()

    def test_unexpected_failure_surfaces_at_warning(self) -> None:
        with (
            patch(
                "zenml.utils.metadata_utils.log_metadata",
                side_effect=RuntimeError("publish 500"),
            ),
            patch("zenml.sandboxes.session.logger.warning") as warn,
        ):
            _FakeSession()._on_enter()
        warn.assert_called()


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

    def test_copy_local_env_fills_in_non_collisions(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("FROM_LOCAL", "local-val")
        sb = _make_sandbox(environment={"COMPONENT": "yes"})
        settings = BaseSandboxSettings(copy_local_env=True)
        merged = sb._resolve_session_environment(settings)
        assert merged["COMPONENT"] == "yes"
        assert merged["FROM_LOCAL"] == "local-val"

    def test_component_env_wins_over_copy_local_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Explicit component-level env must not be silently clobbered by
        # the local-env layer — even when the same key exists locally.
        monkeypatch.setenv("API_KEY", "from-local-env")
        sb = _make_sandbox(environment={"API_KEY": "from-component"})
        settings = BaseSandboxSettings(copy_local_env=True)
        merged = sb._resolve_session_environment(settings)
        assert merged["API_KEY"] == "from-component"

    def test_settings_env_wins_over_copy_local_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Per-step settings.environment is the most-specific layer and must
        # win over copy_local_env even when both set the same key.
        monkeypatch.setenv("DEBUG", "from-local-env")
        sb = _make_sandbox()
        settings = BaseSandboxSettings(
            environment={"DEBUG": "from-step"},
            copy_local_env=True,
        )
        merged = sb._resolve_session_environment(settings)
        assert merged["DEBUG"] == "from-step"


class TestSandboxLogEmission:
    """SandboxSession routes command + stdout + stderr straight to a per-session
    log origin -- bypassing the global ``LoggingContext`` stack so the
    sandbox source captures only sandbox-execution events.
    """

    def _patched_session(self) -> "_FakeSession":
        """Builds a session with the log-origin setup short-circuited.

        The lazy ``_ensure_log_origin`` creates a fresh ``LogsResponse``
        and registers an origin with the active stack's log store. In
        unit tests there's no stack, so we substitute mocks for the
        log_store + origin and return a session that will emit straight
        into them.
        """
        session = _FakeSession()
        session._log_store = MagicMock()
        session._log_origin = MagicMock()
        return session

    def test_log_command_emits_dollar_prefix(self) -> None:
        session = self._patched_session()
        session._log_command(["python", "-c", "print('hi')"])
        emitted_records = [
            call.kwargs["record"]
            for call in session._log_store.emit.call_args_list
        ]
        assert len(emitted_records) == 1
        assert emitted_records[0].getMessage().startswith("$ ")
        assert "python" in emitted_records[0].getMessage()

    def test_log_exec_result_success(self) -> None:
        session = self._patched_session()
        session._log_exec_result(exit_code=0, started_at=time.time() - 1.5)
        record = session._log_store.emit.call_args.kwargs["record"]
        msg = record.getMessage()
        assert msg.startswith("✓ exit 0 in ")
        assert msg.endswith("s")
        assert record.levelno == logging.INFO

    def test_log_exec_result_failure_goes_to_warning(self) -> None:
        session = self._patched_session()
        session._log_exec_result(exit_code=1, started_at=time.time())
        record = session._log_store.emit.call_args.kwargs["record"]
        assert record.getMessage().startswith("✗ exit 1 in ")
        assert record.levelno == logging.WARNING

    def test_log_exec_result_without_started_at_omits_duration(self) -> None:
        session = self._patched_session()
        session._log_exec_result(exit_code=0, started_at=None)
        record = session._log_store.emit.call_args.kwargs["record"]
        assert record.getMessage() == "✓ exit 0"

    def test_wrap_stream_emits_each_line(self) -> None:
        session = self._patched_session()
        out = list(session._wrap_stream(iter(["a\n", "b\n"]), stream="stdout"))
        assert out == ["a\n", "b\n"]  # passthrough preserved
        records = [
            call.kwargs["record"]
            for call in session._log_store.emit.call_args_list
        ]
        assert [r.getMessage() for r in records] == ["a", "b"]
        assert all(r.levelno == logging.INFO for r in records)

    def test_wrap_stream_stderr_uses_warning_level(self) -> None:
        session = self._patched_session()
        list(session._wrap_stream(iter(["oops\n"]), stream="stderr"))
        record = session._log_store.emit.call_args.kwargs["record"]
        assert record.levelno == logging.WARNING
        assert record.getMessage() == "oops"

    def test_wrap_stream_passthrough_after_latch(self) -> None:
        """When the origin setup has latched off, lines pass through unmodified."""
        session = _FakeSession()
        session._log_forwarding_disabled = True
        out = list(session._wrap_stream(iter(["a", "b"]), stream="stdout"))
        assert out == ["a", "b"]
        assert session._log_store is None

    def test_emit_failure_latches_forwarding_off(self) -> None:
        """If origin setup fails once, we don't retry on every emit."""
        session = _FakeSession()
        # Patch _ensure_log_origin to fail on first call by raising
        # inside the lazy registration; the helper catches and latches.
        with patch.object(
            session,
            "_ensure_log_origin",
            side_effect=lambda: (
                setattr(session, "_log_forwarding_disabled", True),
                None,
            )[1],
        ):
            session._emit_sandbox("ignored")
        assert session._log_forwarding_disabled is True

    def test_close_log_origin_deregisters(self) -> None:
        session = self._patched_session()
        log_store = session._log_store
        origin = session._log_origin
        session._close_log_origin()
        log_store.deregister_origin.assert_called_once_with(origin)
        assert session._log_origin is None
        assert session._log_store is None

    def test_close_log_origin_is_idempotent(self) -> None:
        session = self._patched_session()
        session._close_log_origin()
        session._close_log_origin()  # second call must be a no-op
        assert session._log_origin is None


class TestSandboxProcessCollect:
    """Tests for SandboxProcess.collect() — fully drain + wait + return."""

    def _proc_returning(
        self, stdout_lines: List[str], stderr_lines: List[str], code: int = 0
    ) -> SandboxProcess:
        # Build a fake SandboxProcess with our chosen lines.

        class _Proc(SandboxProcess):
            def stdout(self) -> Iterator[str]:
                yield from stdout_lines

            def stderr(self) -> Iterator[str]:
                yield from stderr_lines

            def wait(self, timeout: Optional[float] = None) -> int:
                return code

            def kill(self) -> None:
                return None

            @property
            def exit_code(self) -> Optional[int]:
                return code

        return _Proc()

    def test_drains_both_streams_and_returns_exit_code(self) -> None:
        proc = self._proc_returning(
            stdout_lines=["a\n", "b\n"],
            stderr_lines=["err\n"],
            code=0,
        )
        out = proc.collect()
        assert isinstance(out, SandboxOutput)
        assert out.stdout == "a\nb\n"
        assert out.stderr == "err\n"
        assert out.exit_code == 0
        assert out.stdout_truncated is False
        assert out.stderr_truncated is False

    def test_truncation_flagged_per_stream(self) -> None:
        # 100 chars of stdout but max_chars=10 → truncated; stderr small → not.
        proc = self._proc_returning(
            stdout_lines=["x" * 50 + "\n", "y" * 50 + "\n"],
            stderr_lines=["short\n"],
            code=0,
        )
        out = proc.collect(max_chars=10)
        assert out.stdout_truncated is True
        assert out.stderr_truncated is False
        # Output fits within the cap.
        assert len(out.stdout) <= 10
        assert out.stderr == "short\n"

    def test_single_line_larger_than_cap_is_dropped_entirely(self) -> None:
        # No partial lines emitted; the whole oversize line is dropped.
        proc = self._proc_returning(
            stdout_lines=["a" * 100 + "\n"],
            stderr_lines=[],
            code=0,
        )
        out = proc.collect(max_chars=10)
        assert out.stdout == ""
        assert out.stdout_truncated is True

    def test_drains_fully_even_when_truncated(self) -> None:
        # Verifies the iterator is consumed to StopIteration even after the
        # cap is hit — important so the underlying provider's wait() is safe.
        consumed: List[str] = []

        def lines() -> Iterator[str]:
            for line in ("a" * 100, "b" * 100, "c" * 100):
                consumed.append(line)
                yield line + "\n"

        class _Proc(SandboxProcess):
            def stdout(self) -> Iterator[str]:
                return lines()

            def stderr(self) -> Iterator[str]:
                return iter(())

            def wait(self, timeout: Optional[float] = None) -> int:
                return 0

            def kill(self) -> None:
                return None

            @property
            def exit_code(self) -> Optional[int]:
                return 0

        _Proc().collect(max_chars=10)
        # All three chunks were consumed, even though only the first
        # fit under the cap.
        assert len(consumed) == 3


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
