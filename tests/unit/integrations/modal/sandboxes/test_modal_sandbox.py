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
(line buffering, env injection, snapshot/restore round-trip) but do not boot
a real Modal Sandbox.
"""

import logging
import sys
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator, List
from unittest.mock import MagicMock, patch, sentinel
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
)
from zenml.integrations.modal.sandboxes.modal_sandbox import (  # noqa: E402
    MODAL_STEP_IMAGE_SENTINEL,
    _line_buffer,
    _normalize_optional_config_value,
)
from zenml.sandboxes import (  # noqa: E402
    BaseSandbox,
    SandboxExecError,
    SandboxSnapshot,
)


def _make_session(fake_sandbox: Any) -> ModalSandboxSession:
    """Build a ModalSandboxSession with a fake parent for tests.

    Args:
        fake_sandbox: Mock Modal Sandbox.

    Returns:
        Session under test.
    """
    parent = MagicMock(spec=BaseSandbox)
    parent.flavor = "modal"
    parent.id = uuid4()
    return ModalSandboxSession(fake_sandbox, parent=parent)


@contextmanager
def _patch_modal() -> Iterator[MagicMock]:
    """Substitute the ``modal`` module with a MagicMock for ``import modal``."""
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


def _make_modal_sandbox(
    *,
    environment: dict | None = None,
    secrets: list | None = None,
    config: ModalSandboxConfig | None = None,
) -> ModalSandbox:
    """Build a ModalSandbox without going through Stack/Client."""
    return ModalSandbox(
        name="test-modal",
        id=uuid4(),
        config=config or ModalSandboxConfig(),
        flavor="modal",
        type=StackComponentType.SANDBOX,
        user=None,
        created=datetime.now(),
        updated=datetime.now(),
        environment=environment or {},
        secrets=secrets or [],
    )


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


class TestNormalizeOptionalConfigValue:
    def test_none_returns_none(self) -> None:
        assert _normalize_optional_config_value(None) is None

    def test_empty_string_returns_none(self) -> None:
        assert _normalize_optional_config_value("") is None
        assert _normalize_optional_config_value("   ") is None

    def test_strips_whitespace(self) -> None:
        assert _normalize_optional_config_value("  foo  ") == "foo"


class TestLineBuffer:
    def test_yields_complete_lines(self) -> None:
        chunks = [b"hello\nworld\n"]
        assert list(_line_buffer(chunks)) == ["hello\n", "world\n"]

    def test_joins_split_lines_across_chunks(self) -> None:
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
# Settings merge
# ---------------------------------------------------------------------------


class TestSettingsMerge:
    def test_component_defaults_survive_partial_override(self) -> None:
        sandbox = _make_modal_sandbox(
            config=ModalSandboxConfig(gpu="A100", region="us-east"),
        )
        override = ModalSandboxSettings(timeout=600)
        eff = sandbox.resolve_settings(override)
        assert eff.gpu == "A100"
        assert eff.region == "us-east"
        assert eff.timeout == 600

    def test_override_wins_on_explicit_field_collision(self) -> None:
        sandbox = _make_modal_sandbox(config=ModalSandboxConfig(gpu="A100"))
        override = ModalSandboxSettings(gpu="H100")
        assert sandbox.resolve_settings(override).gpu == "H100"

    def test_none_override_returns_config_defaults(self) -> None:
        sandbox = _make_modal_sandbox(config=ModalSandboxConfig(gpu="A100"))
        eff = sandbox.resolve_settings(None)
        assert eff.gpu == "A100"


# ---------------------------------------------------------------------------
# ModalSandboxProcess
# ---------------------------------------------------------------------------


class TestModalSandboxProcess:
    def test_stdout_line_buffered(self) -> None:
        fake = MagicMock()
        fake.stdout = [b"a\nb\n"]
        session = _make_session(MagicMock(object_id="sb_xyz"))
        proc = ModalSandboxProcess(fake, session=session, started_at=0.0)
        assert list(proc.stdout()) == ["a\n", "b\n"]

    def test_wait_returns_int(self) -> None:
        fake = MagicMock()
        fake.returncode = 0
        session = _make_session(MagicMock(object_id="sb_xyz"))
        proc = ModalSandboxProcess(fake, session=session, started_at=0.0)
        assert proc.wait() == 0
        fake.wait.assert_called_once()

    def test_exit_code_none_while_running(self) -> None:
        fake = MagicMock()
        fake.returncode = None
        session = _make_session(MagicMock(object_id="sb_xyz"))
        proc = ModalSandboxProcess(fake, session=session, started_at=0.0)
        assert proc.exit_code is None

    def test_wait_with_timeout_raises_not_implemented(self) -> None:
        # Modal has no per-exec timeout; we refuse rather than silently drop.
        fake = MagicMock()
        session = _make_session(MagicMock(object_id="sb_xyz"))
        with pytest.raises(NotImplementedError, match="timeout"):
            ModalSandboxProcess(fake, session=session, started_at=0.0).wait(
                timeout=5.0
            )

    def test_kill_closes_stdin(self) -> None:
        fake = MagicMock()
        session = _make_session(MagicMock(object_id="sb_xyz"))
        ModalSandboxProcess(fake, session=session, started_at=0.0).kill()
        fake.stdin.close.assert_called_once()

    def test_kill_tolerates_stdin_close_failure(self) -> None:
        fake = MagicMock()
        fake.stdin.close.side_effect = RuntimeError("already closed")
        session = _make_session(MagicMock(object_id="sb_xyz"))
        ModalSandboxProcess(
            fake, session=session, started_at=0.0
        ).kill()  # no raise


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
        fake_sandbox.exec.assert_called_once_with("python", "-c", "print(1)")

    def test_exec_wraps_env_in_modal_secret(self) -> None:
        # Per-exec env still rides on secrets=[modal.Secret.from_dict(...)]
        # until Sandbox.exec(env=) is verified against Modal 1.x runtime.
        fake_sandbox = MagicMock(object_id="sb_xyz")
        fake_sandbox.exec.return_value = MagicMock()
        with patch("modal.Secret.from_dict") as fake_from_dict:
            fake_from_dict.return_value = sentinel.secret
            _make_session(fake_sandbox).exec(
                ["echo", "hi"], env={"FOO": "bar"}
            )
        fake_from_dict.assert_called_once_with({"FOO": "bar"})
        fake_sandbox.exec.assert_called_once_with(
            "echo", "hi", secrets=[sentinel.secret]
        )

    def test_exec_launch_failure_raises_sandbox_exec_error(self) -> None:
        fake_sandbox = MagicMock(object_id="sb_xyz")
        fake_sandbox.exec.side_effect = RuntimeError("image broken")
        with pytest.raises(SandboxExecError, match="image broken"):
            _make_session(fake_sandbox).exec(["nope"])

    def test_create_snapshot_packages_image_id(self) -> None:
        fake_sandbox = MagicMock(object_id="sb_xyz")
        fake_sandbox.snapshot_filesystem.return_value = MagicMock(
            object_id="im-123"
        )
        session = _make_session(fake_sandbox)
        snap = session.create_snapshot()
        assert isinstance(snap, SandboxSnapshot)
        assert snap.ref == "im-123"
        assert snap.sandbox_id == session._parent_modal.id

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
        # _get_app should call modal.App.lookup only once per ModalSandbox
        # instance.
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


# ---------------------------------------------------------------------------
# _get_modal_client
# ---------------------------------------------------------------------------


class TestGetModalClient:
    def test_returns_none_when_no_credentials_configured(self) -> None:
        sandbox = _make_modal_sandbox()
        # Default config has no token_id / token_secret.
        assert sandbox._get_modal_client() is None

    def test_returns_client_when_credentials_configured(self) -> None:
        sandbox = _make_modal_sandbox(
            config=ModalSandboxConfig(
                token_id="ak-test", token_secret="as-test"
            )
        )
        with _patch_modal() as modal_mock:
            fake_client = MagicMock()
            fake_client.is_closed.return_value = False
            modal_mock.Client.from_credentials.return_value = fake_client
            client = sandbox._get_modal_client()
            assert client is fake_client
            modal_mock.Client.from_credentials.assert_called_once_with(
                "ak-test", "as-test"
            )
            # Second call returns the cached client.
            client2 = sandbox._get_modal_client()
            assert client2 is fake_client
            assert modal_mock.Client.from_credentials.call_count == 1


# ---------------------------------------------------------------------------
# File IO
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Log forwarding & sentinel resolution
# ---------------------------------------------------------------------------


class TestModalLogForwarding:
    """Process stdout/stderr route through session._wrap_stream."""

    def test_process_stdout_routes_through_session_wrap_stream(self) -> None:
        fake_process = MagicMock()
        fake_process.stdout = [b"hello\n", b"world\n"]
        session = _make_session(MagicMock(object_id="sb_xyz"))
        session._wrap_stream = MagicMock(  # type: ignore[method-assign]
            side_effect=lambda lines, log_level: iter(["wrapped"])
        )
        out = list(
            ModalSandboxProcess(
                fake_process, session=session, started_at=0.0
            ).stdout()
        )
        session._wrap_stream.assert_called_once()
        assert (
            session._wrap_stream.call_args.kwargs["log_level"] == logging.INFO
        )
        assert out == ["wrapped"]

    def test_process_stderr_routes_through_session_wrap_stream(self) -> None:
        fake_process = MagicMock()
        fake_process.stderr = [b"oops\n"]
        session = _make_session(MagicMock(object_id="sb_xyz"))
        session._wrap_stream = MagicMock(  # type: ignore[method-assign]
            side_effect=lambda lines, log_level: iter(["wrapped"])
        )
        list(
            ModalSandboxProcess(
                fake_process, session=session, started_at=0.0
            ).stderr()
        )
        assert (
            session._wrap_stream.call_args.kwargs["log_level"] == logging.ERROR
        )

    def test_restore_rejects_cross_provider(self) -> None:
        sandbox = _make_modal_sandbox()
        # sandbox_id pointing at a different component must be rejected.
        wrong = SandboxSnapshot(sandbox_id=uuid4(), ref="ref")
        with pytest.raises(ValueError):
            sandbox.restore(wrong)

    def test_restore_creates_new_sandbox_from_image_id(self) -> None:
        with _patch_modal() as modal_mock:
            modal_mock.App.lookup.return_value = MagicMock()
            modal_mock.Image.from_id.return_value = MagicMock()
            modal_mock.Sandbox.create.return_value = MagicMock(
                object_id="sb_new"
            )
            sandbox = _make_modal_sandbox()
            snap = SandboxSnapshot(sandbox_id=sandbox.id, ref="im-old")
            session = sandbox.restore(snap)
        modal_mock.Image.from_id.assert_called_once_with("im-old")
        modal_mock.Sandbox.create.assert_called_once()
        assert session.id == "sb_new"

    def test_create_session_passes_env_kwarg(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        with _patch_modal() as modal_mock:
            modal_mock.App.lookup.return_value = MagicMock()
            modal_mock.Image.from_registry.return_value = MagicMock()
            modal_mock.Sandbox.create.return_value = MagicMock(
                object_id="sb_new"
            )

            sandbox = _make_modal_sandbox()
            settings = ModalSandboxSettings(
                sandbox_environment={"STEP_VAR": "y"}
            )
            sandbox.create_session(settings=settings)

        create_kwargs = modal_mock.Sandbox.create.call_args.kwargs
        assert create_kwargs.get("env") == {"STEP_VAR": "y"}
        # Env must no longer be smuggled in via secrets=.
        assert "secrets" not in create_kwargs

    def test_step_image_sentinel_resolves_via_snapshot_lookup(self) -> None:
        with (
            _patch_modal() as modal_mock,
            patch(
                "zenml.integrations.modal.sandboxes.modal_sandbox._resolve_step_image",
                return_value="my-registry/step-image:v1",
            ),
        ):
            modal_mock.App.lookup.return_value = MagicMock()
            modal_mock.Image.from_registry.return_value = MagicMock()
            modal_mock.Sandbox.create.return_value = MagicMock(
                object_id="sb_new"
            )

            settings = ModalSandboxSettings(
                base_image=MODAL_STEP_IMAGE_SENTINEL
            )
            _make_modal_sandbox().create_session(settings=settings)
        modal_mock.Image.from_registry.assert_called_with(
            "my-registry/step-image:v1"
        )

    def test_step_image_sentinel_falls_back_when_unresolvable(self) -> None:
        with (
            _patch_modal() as modal_mock,
            patch(
                "zenml.integrations.modal.sandboxes.modal_sandbox._resolve_step_image",
                return_value=None,
            ),
        ):
            modal_mock.App.lookup.return_value = MagicMock()
            modal_mock.Image.from_registry.return_value = MagicMock()
            modal_mock.Sandbox.create.return_value = MagicMock(
                object_id="sb_new"
            )

            settings = ModalSandboxSettings(
                base_image=MODAL_STEP_IMAGE_SENTINEL
            )
            _make_modal_sandbox().create_session(settings=settings)
        modal_mock.Image.from_registry.assert_called_with(
            ModalSandboxConfig().default_image
        )


class TestModalDashboardUrl:
    """The Modal-specific _get_dashboard_url() override."""

    def test_returns_url_when_modal_provides_it(self) -> None:
        fake_sandbox = MagicMock(object_id="sb_xyz")
        fake_sandbox.get_dashboard_url.return_value = (
            "https://modal.com/id/sb-x"
        )
        session = _make_session(fake_sandbox)
        assert session._get_dashboard_url() == "https://modal.com/id/sb-x"

    def test_returns_none_when_get_dashboard_url_fails(self) -> None:
        fake_sandbox = MagicMock(object_id="sb_xyz")
        fake_sandbox.get_dashboard_url.side_effect = AttributeError("old SDK")
        session = _make_session(fake_sandbox)
        assert session._get_dashboard_url() is None
