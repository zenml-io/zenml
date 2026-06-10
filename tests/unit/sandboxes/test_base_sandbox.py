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
from pydantic import ValidationError

from zenml.enums import StackComponentType
from zenml.sandboxes import (
    BaseSandbox,
    BaseSandboxConfig,
    BaseSandboxFlavor,
    BaseSandboxSettings,
    SandboxExecError,
    SandboxOutput,
    SandboxProcess,
    SandboxSession,
    SandboxSessionClosedError,
    SandboxSnapshot,
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
    """Minimal SandboxSession for testing. Only implements `exec` + `_close`."""

    def __init__(
        self,
        session_id: str = "sess-1",
        parent: Optional["BaseSandbox"] = None,
    ) -> None:
        super().__init__(
            id=session_id,
            parent=parent or MagicMock(spec=BaseSandbox, flavor="fake"),
        )
        self.was_closed = False
        self.close_count = 0

    def _exec(
        self,
        command: Union[str, List[str]],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> SandboxProcess:
        return _FakeProcess()

    def _close(self) -> None:
        self.was_closed = True
        self.close_count += 1


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
        assert s.sandbox_environment == {}


class TestSnapshotModel:
    def test_round_trip(self) -> None:
        snap = SandboxSnapshot(
            sandbox_id=uuid4(),
            ref="snap-123",
            metadata={"size_mb": 42},
        )
        restored = SandboxSnapshot.model_validate_json(snap.model_dump_json())
        assert restored == snap

    def test_metadata_defaults_empty(self) -> None:
        snap = SandboxSnapshot(sandbox_id=uuid4(), ref="r")
        assert snap.metadata == {}

    def test_sandbox_id_is_required(self) -> None:
        with pytest.raises(ValidationError):
            SandboxSnapshot(ref="r")


class TestSessionContextManager:
    def test_with_block_calls_close(self) -> None:
        session = _FakeSession()
        with session as s:
            assert s is session
            assert session.was_closed is False
        assert session.was_closed is True
        assert session.closed is True

    def test_use_after_close_raises(self) -> None:
        # close() is terminal: every session-using operation on a closed
        # handle must fail loudly instead of half-working unlogged.
        session = _FakeSession()
        session.close()
        with pytest.raises(SandboxSessionClosedError):
            session.exec("true")
        with pytest.raises(SandboxSessionClosedError):
            session.create_snapshot()
        with pytest.raises(SandboxSessionClosedError):
            session.upload_file("a", "b")
        with pytest.raises(SandboxSessionClosedError):
            session.download_file("a", "b")

    def test_close_is_idempotent(self) -> None:
        session = _FakeSession()
        session.close()
        session.close()
        assert session.close_count == 1

    def test_direct_close_flushes_log_ctx(self) -> None:
        # Users may call close() without the context manager; the logging
        # context must not leak in that path either.
        session = _FakeSession()
        with patch.object(session, "_close_logging_context") as fake_close_log:
            session.close()
        assert session.was_closed is True
        fake_close_log.assert_called_once()

    def test_exit_flushes_log_ctx_when_close_raises(self) -> None:
        # The base close() must call _close_logging_context() even when
        # the flavor _close() hook raises: log cleanup is base-owned, not
        # delegated to subclasses that may forget or error out before
        # reaching the call.
        class _RaisingSession(SandboxSession):
            def __init__(self) -> None:
                super().__init__(
                    id="raise-test",
                    parent=MagicMock(spec=BaseSandbox, flavor="fake"),
                )

            def _exec(
                self,
                command: Union[str, List[str]],
                *,
                cwd: Optional[str] = None,
                env: Optional[Dict[str, str]] = None,
            ) -> SandboxProcess:
                return _FakeProcess()

            def _close(self) -> None:
                raise RuntimeError("close failed")

        session = _RaisingSession()
        with patch.object(session, "_close_logging_context") as fake_close_log:
            with pytest.raises(RuntimeError, match="close failed"):
                with session:
                    pass
        fake_close_log.assert_called_once()


class TestSessionMetadata:
    """SandboxSession publishes session-scoped step metadata on creation.

    Keys are suffixed with the session id so steps that open multiple
    sandbox sessions don't overwrite each other.
    """

    def test_publishes_on_construction(self) -> None:
        with patch("zenml.utils.metadata_utils.log_metadata") as log_meta:
            _FakeSession(session_id="sb-new")
        published = [
            c.kwargs.get("metadata", {}) for c in log_meta.call_args_list
        ]
        assert any("sandbox.sb-new.flavor" in m for m in published)

    def test_logs_flavor_and_dashboard_url_keyed_by_session_id(
        self,
    ) -> None:
        session = _FakeSession(session_id="sb-test-1")
        session._get_dashboard_url = lambda: "https://example/sb-test-1"  # type: ignore[method-assign]
        with patch("zenml.utils.metadata_utils.log_metadata") as log_meta:
            session._publish_sandbox_metadata()
        from zenml.metadata.metadata_types import Uri

        payload = log_meta.call_args.kwargs["metadata"]
        assert payload["sandbox.sb-test-1.flavor"] == "fake"
        assert isinstance(payload["sandbox.sb-test-1.dashboard_url"], Uri)

    def test_two_sessions_produce_disjoint_keys(self) -> None:
        s1 = _FakeSession(session_id="sb-1")
        s2 = _FakeSession(session_id="sb-2")
        s2._get_dashboard_url = lambda: "https://example/sb-2"  # type: ignore[method-assign]
        with patch("zenml.utils.metadata_utils.log_metadata") as log_meta:
            s1._publish_sandbox_metadata()
            s2._publish_sandbox_metadata()
        first = log_meta.call_args_list[0].kwargs["metadata"]
        second = log_meta.call_args_list[1].kwargs["metadata"]
        assert "sandbox.sb-1.flavor" in first
        assert "sandbox.sb-1.flavor" not in second
        assert "sandbox.sb-2.flavor" in second
        assert "sandbox.sb-2.dashboard_url" in second

    def test_omits_dashboard_url_when_hook_returns_none(self) -> None:
        session = _FakeSession(session_id="sb-x")
        with patch("zenml.utils.metadata_utils.log_metadata") as log_meta:
            session._publish_sandbox_metadata()
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
            _FakeSession()._publish_sandbox_metadata()
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
            _FakeSession()._publish_sandbox_metadata()
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
            _FakeSession().create_snapshot()

    def test_upload_file_default_raises(self) -> None:
        with pytest.raises(NotImplementedError):
            _FakeSession().upload_file("/local", "/remote")

    def test_download_file_default_raises(self) -> None:
        with pytest.raises(NotImplementedError):
            _FakeSession().download_file("/remote", "/local")

    def test_destroy_default_raises(self) -> None:
        # The default _destroy hook raises before any state change, so an
        # unsupported destroy leaves the handle open and usable.
        session = _FakeSession()
        with pytest.raises(NotImplementedError):
            session.destroy()
        assert session.closed is False

    def test_destroy_closes_handle_and_flushes_logging(self) -> None:
        class _DestroyableSession(_FakeSession):
            def __init__(self) -> None:
                super().__init__()
                self.destroyed = False

            def _destroy(self) -> None:
                self.destroyed = True

        session = _DestroyableSession()
        with patch.object(session, "_close_logging_context") as fake_close_log:
            session.destroy()
        assert session.destroyed is True
        assert session.closed is True
        assert session.was_closed is True
        fake_close_log.assert_called_once()

    def test_destroy_failure_leaves_handle_open(self) -> None:
        # _destroy runs before close(), so a flavor failure propagates
        # and leaves the handle open for retry.
        class _FailingDestroySession(_FakeSession):
            def _destroy(self) -> None:
                raise RuntimeError("provider unavailable")

        session = _FailingDestroySession()
        with pytest.raises(RuntimeError, match="provider unavailable"):
            session.destroy()
        assert session.closed is False
        session.exec("true")  # still usable


class TestSandboxOptionalMethods:
    def test_attach_default_raises(self) -> None:
        with pytest.raises(NotImplementedError):
            _make_sandbox().attach("sess-1")


class TestRestoreSnapshotGuard:
    def test_validate_rejects_snapshot_from_other_sandbox(self) -> None:
        sandbox = _make_sandbox(flavor="fake")
        wrong_snap = SandboxSnapshot(sandbox_id=uuid4(), ref="r")
        with pytest.raises(ValueError, match="different sandbox"):
            sandbox._validate_snapshot(wrong_snap)

    def test_validate_passes_on_matching_sandbox_id(self) -> None:
        sandbox = _make_sandbox(flavor="fake")
        matching_snap = SandboxSnapshot(sandbox_id=sandbox.id, ref="r")
        # Returns None; no exception.
        assert sandbox._validate_snapshot(matching_snap) is None

    def test_restore_default_raises_not_implemented(self) -> None:
        # Base restore() is opt-in. Flavors override; default raises.
        sandbox = _make_sandbox(flavor="fake")
        snap = SandboxSnapshot(sandbox_id=sandbox.id, ref="r")
        with pytest.raises(NotImplementedError):
            sandbox.restore(snap)


class TestResolveSessionEnvironment:
    def test_empty_settings_returns_empty(self) -> None:
        merged = _make_sandbox()._resolve_session_environment(
            BaseSandboxSettings()
        )
        assert merged == {}

    def test_returns_settings_environment(self) -> None:
        settings = BaseSandboxSettings(sandbox_environment={"A": "1"})
        merged = _make_sandbox()._resolve_session_environment(settings)
        assert merged == {"A": "1"}

    def test_component_env_and_secrets_not_injected(self) -> None:
        # Only settings.sandbox_environment flows into the session env;
        # component env vars and secrets do not.
        sb = _make_sandbox(environment={"A": "1"}, secrets=["secret-uuid"])
        settings = BaseSandboxSettings(sandbox_environment={"B": "2"})
        assert sb._resolve_session_environment(settings) == {"B": "2"}


class TestSandboxLogEmission:
    """SandboxSession routes command + stdout + stderr straight to a per-session
    log origin -- bypassing the global ``LoggingContext`` stack so the
    sandbox source captures only sandbox-execution events.
    """

    def _patched_session(self) -> "_FakeSession":
        """Builds a session with a mock LoggingContext short-circuiting setup.

        The real `_get_logging_context` calls `setup_logging_context` +
        `ctx.begin()` which require an active stack. We bypass both by
        injecting a mock context that supports `emit` and `end`.
        """
        session = _FakeSession()
        session._logging_context = MagicMock()
        return session

    def test_log_command_emits_dollar_prefix(self) -> None:
        session = self._patched_session()
        session._log_command(["python", "-c", "print('hi')"])
        records = [
            call.args[0]
            for call in session._logging_context.emit.call_args_list
        ]
        assert len(records) == 1
        assert records[0].getMessage().startswith("$ ")
        assert "python" in records[0].getMessage()

    def test_log_exec_result_success(self) -> None:
        session = self._patched_session()
        session._log_exec_result(exit_code=0, started_at=time.time() - 1.5)
        record = session._logging_context.emit.call_args.args[0]
        msg = record.getMessage()
        assert msg.startswith("OK exit code 0 in ")
        assert msg.endswith("s")
        assert record.levelno == logging.INFO

    def test_log_exec_result_failure_goes_to_error(self) -> None:
        session = self._patched_session()
        session._log_exec_result(exit_code=1, started_at=time.time())
        record = session._logging_context.emit.call_args.args[0]
        assert record.getMessage().startswith("FAIL exit code 1 in ")
        assert record.levelno == logging.ERROR

    def test_wrap_stream_emits_each_line(self) -> None:
        session = self._patched_session()
        out = list(session._wrap_stream(iter(["a\n", "b\n"])))
        assert out == ["a\n", "b\n"]  # passthrough preserved
        records = [
            call.args[0]
            for call in session._logging_context.emit.call_args_list
        ]
        assert [r.getMessage() for r in records] == ["a", "b"]
        assert all(r.levelno == logging.INFO for r in records)

    def test_wrap_stream_emits_at_given_log_level(self) -> None:
        # Stream lines are emitted at the level the caller passes; the
        # local flavor wraps stderr at ERROR.
        session = self._patched_session()
        list(session._wrap_stream(iter(["oops\n"]), log_level=logging.ERROR))
        record = session._logging_context.emit.call_args.args[0]
        assert record.levelno == logging.ERROR
        assert record.getMessage() == "oops"

    def test_wrap_stream_passthrough_after_latch(self) -> None:
        """When the origin setup has latched off, lines pass through unmodified."""
        session = _FakeSession()
        session._logging_disabled = True
        out = list(session._wrap_stream(iter(["a", "b"])))
        assert out == ["a", "b"]
        assert session._logging_context is None

    def test_close_is_terminal_for_logging(self) -> None:
        # The context is created lazily on first emit; after close, an
        # emit (e.g. draining a leftover stream) must not resurrect a
        # fresh context that nothing would ever close.
        session = _FakeSession()
        ctx = MagicMock()
        session._logging_context = ctx
        session.close()
        ctx.end.assert_called_once()
        assert session._logging_context is None
        assert session._logging_disabled is True
        session._emit_log("after close")
        assert session._logging_context is None

    def test_emit_failure_latches_forwarding_off(self) -> None:
        """If LoggingContext setup fails once, we don't retry on every emit."""
        session = _FakeSession()
        with patch(
            "zenml.utils.logging_utils.setup_logging_context",
            side_effect=RuntimeError("no log store"),
        ):
            session._emit_log("ignored")
        assert session._logging_disabled is True
        assert session._logging_context is None

    def test_no_step_context_disables_forwarding(self) -> None:
        # With no active step there is nothing to attach logs to, so
        # forwarding latches off instead of creating an orphan logs record.
        session = _FakeSession()
        with patch(
            "zenml.steps.step_context.StepContext.get", return_value=None
        ):
            assert session._get_logging_context() is None
        assert session._logging_disabled is True
        assert session._logging_context is None

    def test_close_log_ctx_calls_end(self) -> None:
        session = self._patched_session()
        ctx = session._logging_context
        session._close_logging_context()
        ctx.end.assert_called_once()
        assert session._logging_context is None

    def test_close_log_ctx_is_idempotent(self) -> None:
        session = self._patched_session()
        session._close_logging_context()
        session._close_logging_context()  # second call must be a no-op
        assert session._logging_context is None


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

        return _Proc(
            session=MagicMock(spec=SandboxSession), started_at=time.time()
        )

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

        _Proc(
            session=MagicMock(spec=SandboxSession), started_at=time.time()
        ).collect(max_chars=10)
        # All three chunks were consumed, even though only the first
        # fit under the cap.
        assert len(consumed) == 3

    def test_collect_called_twice_raises(self) -> None:
        # Streams are drained by the first collect(), so a second call
        # would fabricate an empty SandboxOutput. It must fail loudly
        # instead, and the OK/FAIL marker must only be emitted once.
        proc = self._proc_returning(
            stdout_lines=["x\n"], stderr_lines=[], code=0
        )
        fake_session = MagicMock(spec=SandboxSession)
        proc._session = fake_session
        out = proc.collect()
        assert out.stdout == "x\n"
        with pytest.raises(RuntimeError, match="already collected"):
            proc.collect()
        assert fake_session._log_exec_result.call_count == 1

    def test_drain_exception_kills_process_and_reraises(self) -> None:
        # If a stream iterator raises mid-iteration, collect() must
        # NOT silently swallow it (would return empty output and a
        # potentially-deadlocked wait() on an undrained pipe). Instead
        # the drain thread captures the exception, collect() kills the
        # process, then re-raises so the caller sees the failure.
        kill_called = [False]

        class _RaisingProc(SandboxProcess):
            def stdout(self) -> Iterator[str]:
                yield "ok\n"
                raise RuntimeError("stream blew up")

            def stderr(self) -> Iterator[str]:
                return iter(())

            def wait(self, timeout: Optional[float] = None) -> int:
                return 0

            def kill(self) -> None:
                kill_called[0] = True

            @property
            def exit_code(self) -> Optional[int]:
                return 0

        with pytest.raises(RuntimeError, match="stream blew up"):
            _RaisingProc(
                session=MagicMock(spec=SandboxSession),
                started_at=time.time(),
            ).collect()
        assert kill_called[0] is True

    def test_concurrent_drain_on_both_streams_at_volume(self) -> None:
        # The original B2 bug was reported as concurrent drain on both
        # streams: the new threaded drain should handle this without
        # deadlock or interleaving issues. We don't have a real pipe
        # here (that's covered in test_local_sandbox.py), but verify
        # the iterator-level behavior: 1000 lines on each stream are
        # all captured.
        out_lines = [f"out-{i}\n" for i in range(1000)]
        err_lines = [f"err-{i}\n" for i in range(1000)]
        proc = self._proc_returning(
            stdout_lines=out_lines, stderr_lines=err_lines, code=0
        )
        out = proc.collect()
        assert out.stdout.count("\n") == 1000
        assert out.stderr.count("\n") == 1000
        assert out.stdout.endswith("out-999\n")
        assert out.stderr.endswith("err-999\n")


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
