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
"""Unit tests for the Modal Sandbox flavor.

Modal's API is heavily mocked — these tests exercise the wiring around it
(line buffering, env merging, snapshot/restore round-trip) but do not boot a
real Modal Sandbox.
"""

import sys
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator, List
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

pytest.importorskip("modal")

from zenml.enums import StackComponentType  # noqa: E402
from zenml.integrations.modal.flavors import (  # noqa: E402
    ModalSandboxConfig,
    ModalSandboxSettings,
)
from zenml.integrations.modal.sandboxes import (  # noqa: E402
    ModalSandbox,
    ModalSandboxProcess,
    ModalSandboxSession,
    ModalSandboxSnapshot,
)
from zenml.integrations.modal.sandboxes.modal_sandbox import (  # noqa: E402
    _line_buffer,
)
from zenml.sandboxes import (  # noqa: E402
    STEP_IMAGE,
    BaseSandbox,
    BaseSandboxSnapshot,
    SandboxExecError,
)


def _make_session(
    fake_sandbox: Any, *, forward_logs: bool = False
) -> ModalSandboxSession:
    """Builds a ModalSandboxSession with a fake parent for tests.

    Args:
        fake_sandbox: Mock Modal Sandbox.
        forward_logs: Whether to opt into log forwarding.

    Returns:
        Session under test.
    """
    return ModalSandboxSession(
        fake_sandbox,
        parent=MagicMock(spec=BaseSandbox, flavor="modal"),
        forward_logs=forward_logs,
    )


@contextmanager
def _patch_modal() -> Iterator[MagicMock]:
    """Substitutes the ``modal`` module with a MagicMock for ``import modal``.

    The Modal sandbox impl imports ``modal`` lazily inside each function, so
    we have to swap the real module in ``sys.modules`` for the duration of
    the test.
    """
    real = sys.modules.get("modal")
    fake = MagicMock(name="modal")
    sys.modules["modal"] = fake
    try:
        yield fake
    finally:
        if real is not None:
            sys.modules["modal"] = real
        else:
            del sys.modules["modal"]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_modal_sandbox(
    *,
    environment: dict | None = None,
    secrets: list | None = None,
) -> ModalSandbox:
    """Builds a ModalSandbox without going through Stack/Client."""
    return ModalSandbox(
        name="test-modal",
        id=uuid4(),
        config=ModalSandboxConfig(),
        flavor="modal",
        type=StackComponentType.SANDBOX,
        user=None,
        created=datetime.now(),
        updated=datetime.now(),
        environment=environment or {},
        secrets=secrets or [],
    )


# ---------------------------------------------------------------------------
# _line_buffer
# ---------------------------------------------------------------------------


class TestLineBuffer:
    def test_yields_complete_lines(self) -> None:
        chunks = [b"hello\nworld\n"]
        assert list(_line_buffer(chunks)) == ["hello\n", "world\n"]

    def test_joins_split_lines_across_chunks(self) -> None:
        # Split the word "alpha" across chunk boundaries — "hel" trips
        # the CI typos check.
        chunks = [b"alp", b"ha\nbe", b"ta\n"]
        assert list(_line_buffer(chunks)) == ["alpha\n", "beta\n"]

    def test_flushes_trailing_partial_line(self) -> None:
        chunks = [b"final line without newline"]
        assert list(_line_buffer(chunks)) == ["final line without newline"]

    def test_handles_str_chunks(self) -> None:
        chunks = ["foo\n", "bar"]
        assert list(_line_buffer(chunks)) == ["foo\n", "bar"]

    def test_skips_none_chunks(self) -> None:
        chunks: List[Any] = [None, b"a\n", None]
        assert list(_line_buffer(chunks)) == ["a\n"]


# ---------------------------------------------------------------------------
# Env merging is now BaseSandbox._resolve_session_environment — exercised
# in tests/unit/sandboxes/test_base_sandbox.py. Modal just consumes it.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# ModalSandboxSnapshot
# ---------------------------------------------------------------------------


class TestModalSnapshot:
    def test_provider_defaults_to_modal(self) -> None:
        snap = ModalSandboxSnapshot(ref="im-123")
        assert snap.provider == "modal"

    def test_provider_is_frozen(self) -> None:
        # The provider field is frozen — callers cannot mint a snapshot
        # that lies about which flavor it belongs to.
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ModalSandboxSnapshot(provider="other-flavor", ref="im-123")

    def test_subclass_of_base_snapshot(self) -> None:
        snap = ModalSandboxSnapshot(ref="im-123")
        assert isinstance(snap, BaseSandboxSnapshot)

    def test_round_trip(self) -> None:
        snap = ModalSandboxSnapshot(ref="im-123", metadata={"size": 42})
        restored = ModalSandboxSnapshot.model_validate_json(
            snap.model_dump_json()
        )
        assert restored == snap


# ---------------------------------------------------------------------------
# Materializer registration via ModalIntegration.activate()
# ---------------------------------------------------------------------------


class TestMaterializerRegistration:
    def test_activate_registers_snapshot_materializer(self) -> None:
        from zenml.integrations.modal import ModalIntegration
        from zenml.integrations.modal.materializers import (
            ModalSandboxSnapshotMaterializer,
        )
        from zenml.materializers.materializer_registry import (
            materializer_registry,
        )

        ModalIntegration.activate()
        # The registry resolves the type via direct lookup, not MRO.
        resolved = materializer_registry.materializer_types.get(
            ModalSandboxSnapshot
        )
        assert resolved is ModalSandboxSnapshotMaterializer


# ---------------------------------------------------------------------------
# Settings merge — component defaults must survive a partial override
# ---------------------------------------------------------------------------


class TestSettingsMerge:
    def test_component_defaults_survive_partial_override(self) -> None:
        # Build a sandbox with component-level Modal config defaults set.
        sandbox = ModalSandbox(
            name="test-modal",
            id=uuid4(),
            config=ModalSandboxConfig(
                gpu="A100",
                cpu=4.0,
                region="us-east",
            ),
            flavor="modal",
            type=StackComponentType.SANDBOX,
            user=None,
            created=datetime.now(),
            updated=datetime.now(),
            environment={},
            secrets=[],
        )
        # Override only timeout_seconds — gpu/cpu/region must persist.
        override = ModalSandboxSettings(timeout_seconds=600)
        eff = sandbox.effective_settings(override)
        assert eff.gpu == "A100"
        assert eff.cpu == 4.0
        assert eff.region == "us-east"
        assert eff.timeout_seconds == 600

    def test_override_wins_on_explicit_field_collision(self) -> None:
        sandbox = ModalSandbox(
            name="test-modal",
            id=uuid4(),
            config=ModalSandboxConfig(gpu="A100"),
            flavor="modal",
            type=StackComponentType.SANDBOX,
            user=None,
            created=datetime.now(),
            updated=datetime.now(),
            environment={},
            secrets=[],
        )
        override = ModalSandboxSettings(gpu="H100")
        assert sandbox.effective_settings(override).gpu == "H100"

    def test_none_override_returns_config_defaults(self) -> None:
        sandbox = ModalSandbox(
            name="test-modal",
            id=uuid4(),
            config=ModalSandboxConfig(gpu="A100", cpu=4.0),
            flavor="modal",
            type=StackComponentType.SANDBOX,
            user=None,
            created=datetime.now(),
            updated=datetime.now(),
            environment={},
            secrets=[],
        )
        eff = sandbox.effective_settings(None)
        assert eff.gpu == "A100"
        assert eff.cpu == 4.0


# ---------------------------------------------------------------------------
# ModalSandboxProcess
# ---------------------------------------------------------------------------


class TestModalSandboxProcess:
    def test_stdout_line_buffered(self) -> None:
        fake = MagicMock()
        fake.stdout = [b"a\nb\n"]
        proc = ModalSandboxProcess(fake)
        assert list(proc.stdout()) == ["a\n", "b\n"]

    def test_wait_returns_int(self) -> None:
        fake = MagicMock()
        fake.returncode = 0
        proc = ModalSandboxProcess(fake)
        assert proc.wait() == 0
        fake.wait.assert_called_once()

    def test_exit_code_none_while_running(self) -> None:
        fake = MagicMock()
        fake.returncode = None
        proc = ModalSandboxProcess(fake)
        assert proc.exit_code is None

    def test_wait_with_timeout_raises_not_implemented(self) -> None:
        # Modal has no per-exec timeout; we refuse rather than silently drop.
        fake = MagicMock()
        with pytest.raises(NotImplementedError, match="timeout"):
            ModalSandboxProcess(fake).wait(timeout=5.0)

    def test_kill_closes_stdin(self) -> None:
        # Modal has no per-command kill — we close stdin as best-effort.
        fake = MagicMock()
        ModalSandboxProcess(fake).kill()
        fake.stdin.close.assert_called_once()

    def test_kill_tolerates_stdin_close_failure(self) -> None:
        fake = MagicMock()
        fake.stdin.close.side_effect = RuntimeError("already closed")
        ModalSandboxProcess(fake).kill()  # no raise


# ---------------------------------------------------------------------------
# ModalSandboxSession
# ---------------------------------------------------------------------------


class TestModalSandboxSession:
    def test_id_from_sandbox_object_id(self) -> None:
        fake_sandbox = MagicMock(object_id="sb_xyz")
        session = _make_session(fake_sandbox)
        assert session.id == "sb_xyz"

    def test_exec_list_command_passes_argv(self) -> None:
        fake_sandbox = MagicMock(object_id="sb_xyz")
        fake_sandbox.exec.return_value = MagicMock()
        _make_session(fake_sandbox).exec(["python", "-c", "print(1)"])
        fake_sandbox.exec.assert_called_once_with("python", "-c", "print(1)")

    def test_exec_string_command_shell_split(self) -> None:
        fake_sandbox = MagicMock(object_id="sb_xyz")
        fake_sandbox.exec.return_value = MagicMock()
        _make_session(fake_sandbox).exec("python -c 'print(1)'")
        # shlex.split → ["python", "-c", "print(1)"]
        fake_sandbox.exec.assert_called_once_with("python", "-c", "print(1)")

    def test_exec_launch_failure_raises_sandbox_exec_error(self) -> None:
        fake_sandbox = MagicMock(object_id="sb_xyz")
        fake_sandbox.exec.side_effect = RuntimeError("image broken")
        with pytest.raises(SandboxExecError, match="image broken"):
            _make_session(fake_sandbox).exec(["nope"])

    def test_snapshot_packages_image_id(self) -> None:
        fake_sandbox = MagicMock(object_id="sb_xyz")
        fake_sandbox.snapshot_filesystem.return_value = MagicMock(
            object_id="im-123"
        )
        snap = _make_session(fake_sandbox).snapshot()
        assert snap.provider == "modal"
        assert snap.ref == "im-123"

    def test_destroy_calls_terminate(self) -> None:
        fake_sandbox = MagicMock(object_id="sb_xyz")
        _make_session(fake_sandbox).destroy()
        fake_sandbox.terminate.assert_called_once()

    def test_close_is_a_noop(self) -> None:
        # Modal Sandbox has no client-side resources to release; close()
        # must not call terminate() (that's destroy()'s job).
        fake_sandbox = MagicMock(object_id="sb_xyz")
        _make_session(fake_sandbox).close()
        fake_sandbox.terminate.assert_not_called()


# ---------------------------------------------------------------------------
# ModalSandbox (factory)
# ---------------------------------------------------------------------------


class TestModalSandbox:
    def test_attach_calls_from_id(self) -> None:
        with _patch_modal() as modal_mock:
            fake_sandbox = MagicMock(object_id="sb_xyz")
            modal_mock.Sandbox.from_id.return_value = fake_sandbox
            session = _make_modal_sandbox().attach("sb_xyz")
        modal_mock.Sandbox.from_id.assert_called_once_with("sb_xyz")
        assert session.id == "sb_xyz"

    def test_attach_wraps_modal_errors_in_runtime_error(self) -> None:
        with _patch_modal() as modal_mock:
            modal_mock.Sandbox.from_id.side_effect = RuntimeError(
                "sandbox not found"
            )
            with pytest.raises(RuntimeError, match="sb_missing"):
                _make_modal_sandbox().attach("sb_missing")

    def test_app_lookup_cached_across_create_sessions(self) -> None:
        # _get_app should only call modal.App.lookup once per ModalSandbox
        # instance; the cached App is reused on the second create_session.
        with _patch_modal() as modal_mock:
            modal_mock.App.lookup.return_value = MagicMock()
            modal_mock.Image.from_registry.return_value = MagicMock()
            modal_mock.Sandbox.create.return_value = MagicMock(
                object_id="sb_a"
            )
            sandbox = _make_modal_sandbox()
            sandbox.create_session()
            sandbox.create_session()
        assert modal_mock.App.lookup.call_count == 1


class TestModalSandboxFileIO:
    def test_upload_file_delegates_to_filesystem_api(
        self, tmp_path: Any
    ) -> None:
        src_path = tmp_path / "in.bin"
        src_path.write_bytes(b"payload")
        fake_sandbox = MagicMock(object_id="sb_xyz")

        _make_session(fake_sandbox).upload_file(str(src_path), "/tmp/in.bin")
        fake_sandbox.filesystem.copy_from_local.assert_called_once_with(
            str(src_path), "/tmp/in.bin"
        )

    def test_download_file_delegates_to_filesystem_api(
        self, tmp_path: Any
    ) -> None:
        dst_path = tmp_path / "out.bin"
        fake_sandbox = MagicMock(object_id="sb_xyz")

        _make_session(fake_sandbox).download_file(
            "/tmp/out.bin", str(dst_path)
        )
        fake_sandbox.filesystem.copy_to_local.assert_called_once_with(
            "/tmp/out.bin", str(dst_path)
        )


class TestModalLogForwarding:
    """The Session enters BaseSandbox.forward_session_logs on __enter__."""

    def test_forward_logs_true_opens_context_on_enter(self) -> None:
        parent = MagicMock()
        log_ctx = MagicMock()
        parent.forward_session_logs.return_value = log_ctx
        fake_sandbox = MagicMock(object_id="sb_xyz")

        session = ModalSandboxSession(
            fake_sandbox, parent=parent, forward_logs=True
        )
        with session:
            parent.forward_session_logs.assert_called_once_with("sb_xyz")
            log_ctx.__enter__.assert_called_once()
        log_ctx.__exit__.assert_called_once()

    def test_forward_logs_false_skips_context(self) -> None:
        parent = MagicMock()
        fake_sandbox = MagicMock(object_id="sb_xyz")
        session = ModalSandboxSession(
            fake_sandbox, parent=parent, forward_logs=False
        )
        with session:
            parent.forward_session_logs.assert_not_called()

    def test_close_outside_with_still_closes_log_ctx(self) -> None:
        # If a caller manually __enter__'s the session and then calls
        # close() instead of __exit__, the LoggingContext should still
        # be torn down (no leak).
        parent = MagicMock()
        log_ctx = MagicMock()
        parent.forward_session_logs.return_value = log_ctx
        fake_sandbox = MagicMock(object_id="sb_xyz")
        session = ModalSandboxSession(
            fake_sandbox, parent=parent, forward_logs=True
        )
        session.__enter__()
        session.close()
        log_ctx.__exit__.assert_called_once()
        # Calling close() again is idempotent — no double-exit.
        session.close()
        log_ctx.__exit__.assert_called_once()

    def test_double_enter_does_not_leak_log_ctx(self) -> None:
        parent = MagicMock()
        log_ctx = MagicMock()
        parent.forward_session_logs.return_value = log_ctx
        fake_sandbox = MagicMock(object_id="sb_xyz")
        session = ModalSandboxSession(
            fake_sandbox, parent=parent, forward_logs=True
        )
        session.__enter__()
        session.__enter__()
        # forward_session_logs called exactly once even on double-enter.
        assert parent.forward_session_logs.call_count == 1
        assert log_ctx.__enter__.call_count == 1
        session.close()

    def test_process_stdout_forwards_lines_when_enabled(self) -> None:
        fake_process = MagicMock()
        fake_process.stdout = [b"hello\n", b"world\n"]
        with patch(
            "zenml.integrations.modal.sandboxes.modal_sandbox.BaseSandbox.forward_lines"
        ) as forward:
            forward.side_effect = lambda lines, **_: lines  # passthrough
            out = list(
                ModalSandboxProcess(fake_process, forward_logs=True).stdout()
            )
        # forward_lines was invoked with stream="stdout"; lines pass through.
        forward.assert_called_once()
        assert forward.call_args.kwargs["stream"] == "stdout"
        assert out == ["hello\n", "world\n"]

    def test_restore_rejects_cross_provider(self) -> None:
        wrong = BaseSandboxSnapshot(provider="agent_sandbox", ref="ref")
        with pytest.raises(ValueError, match="provider 'agent_sandbox'"):
            _make_modal_sandbox().restore(wrong)

    def test_restore_creates_new_sandbox_from_image_id(self) -> None:
        with _patch_modal() as modal_mock:
            modal_mock.App.lookup.return_value = MagicMock()
            modal_mock.Image.from_id.return_value = MagicMock()
            modal_mock.Sandbox.create.return_value = MagicMock(
                object_id="sb_new"
            )
            snap = ModalSandboxSnapshot(ref="im-old")
            session = _make_modal_sandbox().restore(snap)
        modal_mock.Image.from_id.assert_called_once_with("im-old")
        modal_mock.Sandbox.create.assert_called_once()
        assert session.id == "sb_new"

    def test_create_session_passes_merged_env_as_modal_secret(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        with _patch_modal() as modal_mock:
            modal_mock.App.lookup.return_value = MagicMock()
            modal_mock.Image.from_registry.return_value = MagicMock()
            modal_mock.Sandbox.create.return_value = MagicMock(
                object_id="sb_new"
            )
            modal_mock.Secret.from_dict = MagicMock(
                side_effect=lambda d: ("SECRET", d)
            )

            sandbox = _make_modal_sandbox(environment={"COMPONENT_VAR": "x"})
            settings = ModalSandboxSettings(
                environment={"STEP_VAR": "y", "COMPONENT_VAR": "override"}
            )
            sandbox.create_session(settings=settings)

        # Inspect the secrets kwarg passed to Sandbox.create
        create_kwargs = modal_mock.Sandbox.create.call_args.kwargs
        assert "secrets" in create_kwargs
        secret_payload = create_kwargs["secrets"][0]
        # Our mocked from_dict returns the dict itself; unwrap.
        env_dict = secret_payload[1]
        assert env_dict["COMPONENT_VAR"] == "override"  # settings wins
        assert env_dict["STEP_VAR"] == "y"

    def test_step_image_sentinel_resolves_to_env_var(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(
            "ZENML_ACTIVE_STEP_IMAGE", "my-registry/step-image:v1"
        )
        with _patch_modal() as modal_mock:
            modal_mock.App.lookup.return_value = MagicMock()
            modal_mock.Image.from_registry.return_value = MagicMock()
            modal_mock.Sandbox.create.return_value = MagicMock(
                object_id="sb_new"
            )

            settings = ModalSandboxSettings(base_image=STEP_IMAGE)
            _make_modal_sandbox().create_session(settings=settings)
        modal_mock.Image.from_registry.assert_called_with(
            "my-registry/step-image:v1"
        )

    def test_step_image_sentinel_falls_back_when_env_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("ZENML_ACTIVE_STEP_IMAGE", raising=False)
        with _patch_modal() as modal_mock:
            modal_mock.App.lookup.return_value = MagicMock()
            modal_mock.Image.from_registry.return_value = MagicMock()
            modal_mock.Sandbox.create.return_value = MagicMock(
                object_id="sb_new"
            )

            settings = ModalSandboxSettings(base_image=STEP_IMAGE)
            _make_modal_sandbox().create_session(settings=settings)
        # Falls back to the flavor's default_image.
        modal_mock.Image.from_registry.assert_called_with(
            ModalSandboxConfig().default_image
        )


class TestExportModalTokens:
    """ModalSandbox._export_modal_tokens copies SecretField values to env."""

    def _build_sandbox_with_tokens(
        self, *, token_id: str = "tk-1", token_secret: str = "ts-1"
    ) -> ModalSandbox:
        return ModalSandbox(
            name="test-modal",
            id=uuid4(),
            config=ModalSandboxConfig(
                token_id=token_id, token_secret=token_secret
            ),
            flavor="modal",
            type=StackComponentType.SANDBOX,
            user=None,
            created=datetime.now(),
            updated=datetime.now(),
            environment={},
            secrets=[],
        )

    def test_exports_both_when_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("MODAL_TOKEN_ID", raising=False)
        monkeypatch.delenv("MODAL_TOKEN_SECRET", raising=False)
        self._build_sandbox_with_tokens()._export_modal_tokens()
        import os

        assert os.environ["MODAL_TOKEN_ID"] == "tk-1"
        assert os.environ["MODAL_TOKEN_SECRET"] == "ts-1"

    def test_does_not_clobber_already_set_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # setdefault semantics: a developer's existing local
        # ~/.modal.toml-derived token wins over a config-carried one.
        monkeypatch.setenv("MODAL_TOKEN_ID", "preexisting")
        monkeypatch.delenv("MODAL_TOKEN_SECRET", raising=False)
        self._build_sandbox_with_tokens()._export_modal_tokens()
        import os

        assert os.environ["MODAL_TOKEN_ID"] == "preexisting"
        assert os.environ["MODAL_TOKEN_SECRET"] == "ts-1"

    def test_noop_when_both_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("MODAL_TOKEN_ID", raising=False)
        monkeypatch.delenv("MODAL_TOKEN_SECRET", raising=False)
        ModalSandbox(
            name="t",
            id=uuid4(),
            config=ModalSandboxConfig(),
            flavor="modal",
            type=StackComponentType.SANDBOX,
            user=None,
            created=datetime.now(),
            updated=datetime.now(),
            environment={},
            secrets=[],
        )._export_modal_tokens()
        import os

        assert "MODAL_TOKEN_ID" not in os.environ
        assert "MODAL_TOKEN_SECRET" not in os.environ

    def test_attach_exports_tokens(self) -> None:
        # Remote orchestrators reattach via .attach(); without the
        # token export the modal.Sandbox.from_id call would fail.
        with _patch_modal() as modal_mock:
            modal_mock.Sandbox.from_id.return_value = MagicMock(
                object_id="sb_xyz"
            )
            sandbox = self._build_sandbox_with_tokens(token_id="attach-tk")
            import os

            os.environ.pop("MODAL_TOKEN_ID", None)
            sandbox.attach("sb_xyz")
            assert os.environ["MODAL_TOKEN_ID"] == "attach-tk"


class TestModalDashboardUrl:
    """The Modal-specific _dashboard_url() override.

    Generic step-metadata logging behaviour now lives on the base in
    SandboxSession._on_enter (covered by tests/unit/sandboxes/). These
    tests only verify the Modal flavor's URL-resolution hook.
    """

    def test_returns_url_when_modal_provides_it(self) -> None:
        fake_sandbox = MagicMock(object_id="sb_xyz")
        fake_sandbox.get_dashboard_url.return_value = (
            "https://modal.com/id/sb-x"
        )
        session = _make_session(fake_sandbox)
        assert session._dashboard_url() == "https://modal.com/id/sb-x"

    def test_returns_none_when_get_dashboard_url_fails(self) -> None:
        fake_sandbox = MagicMock(object_id="sb_xyz")
        fake_sandbox.get_dashboard_url.side_effect = AttributeError("old SDK")
        session = _make_session(fake_sandbox)
        assert session._dashboard_url() is None
