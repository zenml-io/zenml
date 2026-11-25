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
from typing import Any, Dict, Iterator, List, Optional
from unittest.mock import MagicMock, PropertyMock
from uuid import uuid4

import pytest

pytest.importorskip("modal")

from zenml.enums import StackComponentType  # noqa: E402
from zenml.integrations.modal.flavors import (  # noqa: E402
    ModalSandboxConfig,
    ModalSandboxSettings,
)
from zenml.integrations.modal.sandbox_utils import (  # noqa: E402
    normalize_optional_config_value,
)
from zenml.integrations.modal.sandboxes import (  # noqa: E402
    ModalSandbox,
    ModalSandboxProcess,
    ModalSandboxSession,
)
from zenml.integrations.modal.sandboxes.utils import (  # noqa: E402
    line_buffer,
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
    # A freshly created session wraps a running sandbox; _destroy() only
    # terminates when poll() reports it's still alive.
    fake_sandbox.poll.return_value = None
    return ModalSandboxSession(fake_sandbox, parent=parent)


@contextmanager
def _patch_modal() -> Iterator[MagicMock]:
    """Substitute the ``modal`` module with a MagicMock everywhere it's bound.

    Production code imports ``modal`` eagerly at module top (in both
    ``modal_sandbox.py`` and ``sandbox_utils.py``), so swap the
    already-bound names in both modules plus ``sys.modules['modal']``.
    """
    from zenml.integrations.modal import sandbox_utils
    from zenml.integrations.modal.sandboxes import modal_sandbox

    real_mod = sys.modules.get("modal")
    real_su_modal = sandbox_utils.modal
    real_ms_modal = modal_sandbox.modal
    fake = MagicMock(name="modal")
    sys.modules["modal"] = fake
    sandbox_utils.modal = fake
    modal_sandbox.modal = fake
    try:
        yield fake
    finally:
        sandbox_utils.modal = real_su_modal
        modal_sandbox.modal = real_ms_modal
        if real_mod is not None:
            sys.modules["modal"] = real_mod
        else:
            del sys.modules["modal"]


def _make_modal_sandbox(
    *,
    environment: Optional[Dict[str, str]] = None,
    secrets: Optional[List[Any]] = None,
    config: Optional[ModalSandboxConfig] = None,
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
        assert normalize_optional_config_value(None) is None

    def test_empty_string_returns_none(self) -> None:
        assert normalize_optional_config_value("") is None
        assert normalize_optional_config_value("   ") is None

    def test_strips_whitespace(self) -> None:
        assert normalize_optional_config_value("  foo  ") == "foo"


class TestLineBuffer:
    def test_yields_complete_lines(self) -> None:
        chunks = [b"hello\nworld\n"]
        assert list(line_buffer(chunks)) == ["hello\n", "world\n"]

    def test_joins_split_lines_across_chunks(self) -> None:
        chunks = [b"alp", b"ha\nbe", b"ta\n"]
        assert list(line_buffer(chunks)) == ["alpha\n", "beta\n"]

    def test_flushes_trailing_partial_line(self) -> None:
        chunks = [b"final line without newline"]
        assert list(line_buffer(chunks)) == ["final line without newline"]

    def test_handles_str_chunks(self) -> None:
        chunks = ["foo\n", "bar"]
        assert list(line_buffer(chunks)) == ["foo\n", "bar"]

    def test_skips_none_chunks(self) -> None:
        chunks: List[Any] = [None, b"a\n", None]
        assert list(line_buffer(chunks)) == ["a\n"]


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
    def test_stdoutline_buffered(self) -> None:
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
        # Modal's ContainerProcess.returncode raises InvalidError while
        # the command runs; exit_code must use poll() and return None.
        fake = MagicMock()
        type(fake).returncode = PropertyMock(
            side_effect=RuntimeError("not finished")
        )
        fake.poll.return_value = None
        session = _make_session(MagicMock(object_id="sb_xyz"))
        proc = ModalSandboxProcess(fake, session=session, started_at=0.0)
        assert proc.exit_code is None

    def test_exit_code_after_completion(self) -> None:
        fake = MagicMock()
        fake.poll.return_value = 7
        session = _make_session(MagicMock(object_id="sb_xyz"))
        proc = ModalSandboxProcess(fake, session=session, started_at=0.0)
        assert proc.exit_code == 7

    def test_wait_with_timeout_polls_to_completion(self) -> None:
        # Modal's own wait() has no timeout parameter; a bounded wait
        # polls instead and returns the exit code once available.
        fake = MagicMock()
        fake.poll.side_effect = [None, None, 7]
        session = _make_session(MagicMock(object_id="sb_xyz"))
        proc = ModalSandboxProcess(fake, session=session, started_at=0.0)
        assert proc.wait(timeout=5.0) == 7
        fake.wait.assert_not_called()

    def test_wait_with_timeout_raises_on_deadline(self) -> None:
        fake = MagicMock()
        fake.poll.return_value = None
        session = _make_session(MagicMock(object_id="sb_xyz"))
        proc = ModalSandboxProcess(fake, session=session, started_at=0.0)
        with pytest.raises(TimeoutError, match="did not exit"):
            proc.wait(timeout=0.3)

    def test_kill_raises_not_implemented(self) -> None:
        # Modal has no per-command termination, so kill() is unsupported
        # rather than tearing down the whole sandbox (which would also stop
        # sibling commands). The base collect() tolerates this — it wraps
        # kill() in try/except.
        fake_sandbox = MagicMock(object_id="sb_xyz")
        session = _make_session(fake_sandbox)
        proc = ModalSandboxProcess(
            MagicMock(), session=session, started_at=0.0
        )
        with pytest.raises(NotImplementedError, match="per-command"):
            proc.kill()
        # The sandbox is left running and the session stays open.
        fake_sandbox.terminate.assert_not_called()
        assert session.closed is False


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

    def test_exec_passes_env(self) -> None:
        # Per-exec env vars are forwarded directly via Sandbox.exec(env=...).
        # The integration requires modal>=1.4 (exec/create env=, plus the
        # filesystem accessor and get_dashboard_url the sandbox relies on).
        fake_sandbox = MagicMock(object_id="sb_xyz")
        fake_sandbox.exec.return_value = MagicMock()
        _make_session(fake_sandbox).exec(["echo", "hi"], env={"FOO": "bar"})
        fake_sandbox.exec.assert_called_once_with(
            "echo", "hi", env={"FOO": "bar"}
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
        assert snap.sandbox_id == session._parent.id

    def test_destroy_calls_terminate(self) -> None:
        fake_sandbox = MagicMock(object_id="sb_xyz")
        session = _make_session(fake_sandbox)
        session.destroy()
        fake_sandbox.terminate.assert_called_once()
        assert session.closed is True

    def test_destroy_raises_and_keeps_handle_open_on_failure(self) -> None:
        # A failed terminate must surface (the sandbox keeps billing
        # until TTL) and leave the handle open so destroy() can retry.
        fake_sandbox = MagicMock(object_id="sb_xyz")
        fake_sandbox.terminate.side_effect = RuntimeError("api down")
        session = _make_session(fake_sandbox)
        with pytest.raises(RuntimeError, match="Failed to terminate"):
            session.destroy()
        assert session.closed is False
        fake_sandbox.terminate.side_effect = None
        session.destroy()  # retry succeeds
        assert session.closed is True

    def test_destroy_is_noop_when_sandbox_already_terminated(self) -> None:
        # If the sandbox already exited (destroyed elsewhere or TTL
        # expired), destroy() must not call terminate() or surface an
        # error about a resource that is no longer running/billing.
        fake_sandbox = MagicMock(object_id="sb_xyz")
        session = _make_session(fake_sandbox)
        fake_sandbox.poll.return_value = 0  # already terminated
        session.destroy()
        fake_sandbox.terminate.assert_not_called()
        assert session.closed is True

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
            fake_sandbox.poll.return_value = None  # still running
            modal_mock.Sandbox.from_id.return_value = fake_sandbox
            session = _make_modal_sandbox().attach("sb_xyz")
        modal_mock.Sandbox.from_id.assert_called_once_with(
            "sb_xyz", client=None
        )
        assert session.id == "sb_xyz"

    def test_attach_rejects_terminated_sandbox(self) -> None:
        # Modal returns a handle even for a dead sandbox; attach() must
        # fail fast instead of handing out a session whose first exec
        # fails with a confusing Modal error.
        with _patch_modal() as modal_mock:
            fake_sandbox = MagicMock(object_id="sb_dead")
            fake_sandbox.poll.return_value = 0  # already terminated
            modal_mock.Sandbox.from_id.return_value = fake_sandbox
            with pytest.raises(RuntimeError, match="already terminated"):
                _make_modal_sandbox().attach("sb_dead")

    def test_attach_wraps_modal_errors_in_runtime_error(self) -> None:
        with _patch_modal() as modal_mock:
            modal_mock.Sandbox.from_id.side_effect = RuntimeError(
                "sandbox not found"
            )
            with pytest.raises(RuntimeError, match="sb_missing"):
                _make_modal_sandbox().attach("sb_missing")

    def test_app_lookup_per_session_honors_modal_environment(self) -> None:
        # modal_environment is a setting, so each create_session must do
        # its own App lookup with the effective environment instead of
        # reusing a cached App from an earlier lookup.
        with _patch_modal() as modal_mock:
            modal_mock.App.lookup.return_value = MagicMock()
            modal_mock.Image.from_registry.return_value = MagicMock()
            modal_mock.Sandbox.create.return_value = MagicMock(
                object_id="sb_a"
            )
            sandbox = _make_modal_sandbox()
            sandbox.create_session(
                settings=ModalSandboxSettings(modal_environment="staging")
            )
            sandbox.create_session(
                settings=ModalSandboxSettings(modal_environment="prod")
            )
        assert modal_mock.App.lookup.call_count == 2
        environments = [
            call.kwargs["environment_name"]
            for call in modal_mock.App.lookup.call_args_list
        ]
        assert environments == ["staging", "prod"]

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
        modal_mock.Image.from_id.assert_called_once_with("im-old", client=None)
        modal_mock.Sandbox.create.assert_called_once()
        assert session.id == "sb_new"

    def test_restore_uses_configured_modal_client(self) -> None:
        # restore() must load the snapshot Image with the client built from
        # the component's token_id/token_secret, not Modal's ambient auth.
        with _patch_modal() as modal_mock:
            fake_client = MagicMock()
            fake_client.is_closed.return_value = False
            modal_mock.Client.from_credentials.return_value = fake_client
            modal_mock.App.lookup.return_value = MagicMock()
            modal_mock.Image.from_id.return_value = MagicMock()
            modal_mock.Sandbox.create.return_value = MagicMock(
                object_id="sb_new"
            )
            sandbox = _make_modal_sandbox(
                config=ModalSandboxConfig(
                    token_id="ak-test", token_secret="as-test"
                )
            )
            snap = SandboxSnapshot(sandbox_id=sandbox.id, ref="im-old")
            sandbox.restore(snap)
        modal_mock.Image.from_id.assert_called_once_with(
            "im-old", client=fake_client
        )

    def test_restore_reapplies_session_environment(self) -> None:
        # Env vars are runtime config, not filesystem state — the snapshot
        # image doesn't carry them, so restore must re-inject them.
        with _patch_modal() as modal_mock:
            modal_mock.App.lookup.return_value = MagicMock()
            modal_mock.Image.from_id.return_value = MagicMock()
            modal_mock.Sandbox.create.return_value = MagicMock(
                object_id="sb_new"
            )
            sandbox = _make_modal_sandbox(
                config=ModalSandboxConfig(
                    sandbox_environment={"SESSION_VAR": "x"}
                )
            )
            snap = SandboxSnapshot(sandbox_id=sandbox.id, ref="im-old")
            sandbox.restore(snap)
        create_kwargs = modal_mock.Sandbox.create.call_args.kwargs
        assert create_kwargs.get("env") == {"SESSION_VAR": "x"}

    def test_create_session_passes_env_kwarg(self) -> None:
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

    def test_image_setting_passes_through_to_from_registry(self) -> None:
        with _patch_modal() as modal_mock:
            modal_mock.App.lookup.return_value = MagicMock()
            modal_mock.Image.from_registry.return_value = MagicMock()
            modal_mock.Sandbox.create.return_value = MagicMock(
                object_id="sb_new"
            )

            settings = ModalSandboxSettings(image="my-registry/app:v1")
            _make_modal_sandbox().create_session(settings=settings)
        modal_mock.Image.from_registry.assert_called_with("my-registry/app:v1")

    def test_cpu_and_memory_settings_reach_sandbox_create(self) -> None:
        with _patch_modal() as modal_mock:
            modal_mock.App.lookup.return_value = MagicMock()
            modal_mock.Image.from_registry.return_value = MagicMock()
            modal_mock.Sandbox.create.return_value = MagicMock(
                object_id="sb_new"
            )

            settings = ModalSandboxSettings(cpu=2, memory="2GB")
            _make_modal_sandbox().create_session(settings=settings)
        create_kwargs = modal_mock.Sandbox.create.call_args.kwargs
        assert create_kwargs.get("cpu") == 2
        assert create_kwargs.get("memory") == 2000


class TestModalSandboxConfig:
    def test_settings_fields_exist_on_config(self) -> None:
        # The config must inherit the settings so registration-time values
        # like --image aren't silently dropped (extra="ignore").
        config = ModalSandboxConfig(
            image="my-registry/app:v1", sandbox_environment={"FOO": "1"}
        )
        assert config.image == "my-registry/app:v1"
        assert config.sandbox_environment == {"FOO": "1"}

    def test_defaults(self) -> None:
        config = ModalSandboxConfig()
        assert config.image == "python:3.11-slim"
        # Sandbox TTL default is 1 hour, not the step operator's 24 hours.
        assert config.timeout == 3600
        assert ModalSandboxSettings().timeout == 3600


class TestRegistryCredentials:
    """Registry credentials are only handed out for images in the registry."""

    @staticmethod
    def _patch_active_stack_registry(
        monkeypatch: pytest.MonkeyPatch, uri: str
    ) -> MagicMock:
        from zenml.container_registries.base_container_registry import (
            BaseContainerRegistry,
        )

        registry = MagicMock()
        registry.config.uri = uri
        registry.credentials = ("user", "pass")
        registry.is_valid_image_name_for_registry.side_effect = lambda image: (
            BaseContainerRegistry.is_valid_image_name_for_registry(
                registry, image
            )
        )
        client = MagicMock()
        client.active_stack.container_registry = registry
        # modal_sandbox imports Client at module top, so patch the name
        # where it is looked up, not at its source module.
        monkeypatch.setattr(
            "zenml.integrations.modal.sandboxes.modal_sandbox.Client",
            lambda: client,
        )
        return registry

    def test_credentials_passed_for_image_in_stack_registry(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._patch_active_stack_registry(monkeypatch, "my-registry.io/team")
        with _patch_modal() as modal_mock:
            modal_mock.App.lookup.return_value = MagicMock()
            modal_mock.Image.from_registry.return_value = MagicMock()
            modal_mock.Sandbox.create.return_value = MagicMock(
                object_id="sb_new"
            )
            fake_secret = MagicMock()
            modal_mock.Secret.from_dict.return_value = fake_secret

            settings = ModalSandboxSettings(image="my-registry.io/team/app:v1")
            _make_modal_sandbox().create_session(settings=settings)
        modal_mock.Image.from_registry.assert_called_once_with(
            "my-registry.io/team/app:v1", secret=fake_secret
        )

    def test_no_credentials_for_docker_hub_style_image(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._patch_active_stack_registry(monkeypatch, "my-registry.io/team")
        with _patch_modal() as modal_mock:
            modal_mock.App.lookup.return_value = MagicMock()
            modal_mock.Image.from_registry.return_value = MagicMock()
            modal_mock.Sandbox.create.return_value = MagicMock(
                object_id="sb_new"
            )

            settings = ModalSandboxSettings(image="python:3.11-slim")
            _make_modal_sandbox().create_session(settings=settings)
        modal_mock.Image.from_registry.assert_called_once_with(
            "python:3.11-slim"
        )


# ---------------------------------------------------------------------------
# Modal client factory wiring
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

        _make_session(fake_sandbox).upload_file(str(src_path), "/tmp/in.bin")  # nosec B108
        fake_sandbox.filesystem.copy_from_local.assert_called_once_with(
            str(src_path),
            "/tmp/in.bin",  # nosec B108
        )

    def test_download_file_delegates_to_filesystem_api(
        self, tmp_path: Any
    ) -> None:
        dst_path = tmp_path / "out.bin"
        fake_sandbox = MagicMock(object_id="sb_xyz")

        _make_session(fake_sandbox).download_file(
            "/tmp/out.bin",
            str(dst_path),  # nosec B108
        )
        fake_sandbox.filesystem.copy_to_local.assert_called_once_with(
            "/tmp/out.bin",
            str(dst_path),  # nosec B108
        )


# ---------------------------------------------------------------------------
# Log forwarding
# ---------------------------------------------------------------------------


class TestModalLogForwarding:
    """Process stdout/stderr forward to the session log source."""

    def test_process_stdout_emits_lines_at_info(self) -> None:
        fake_process = MagicMock()
        fake_process.stdout = [b"hello\n", b"world\n"]
        session = _make_session(MagicMock(object_id="sb_xyz"))
        session._emit_log = MagicMock()  # type: ignore[method-assign]
        proc = ModalSandboxProcess(
            fake_process, session=session, started_at=0.0
        )
        assert list(proc.stdout()) == ["hello\n", "world\n"]
        session._emit_log.assert_any_call("hello", level=logging.INFO)
        session._emit_log.assert_any_call("world", level=logging.INFO)

    def test_process_stderr_emits_lines_at_error(self) -> None:
        fake_process = MagicMock()
        fake_process.stderr = [b"oops\n"]
        session = _make_session(MagicMock(object_id="sb_xyz"))
        session._emit_log = MagicMock()  # type: ignore[method-assign]
        proc = ModalSandboxProcess(
            fake_process, session=session, started_at=0.0
        )
        assert list(proc.stderr()) == ["oops\n"]
        session._emit_log.assert_called_once_with("oops", level=logging.ERROR)


class TestModalDashboardUrl:
    """The Modal-specific _get_dashboard_url() override."""

    def test_returns_url_when_modal_provides_it(self) -> None:
        fake_sandbox = MagicMock(object_id="sb_xyz")
        fake_sandbox.get_dashboard_url.return_value = (
            "https://modal.com/id/sb-x"
        )
        session = _make_session(fake_sandbox)
        assert session._get_dashboard_url() == "https://modal.com/id/sb-x"
