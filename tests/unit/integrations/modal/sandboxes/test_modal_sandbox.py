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
    _resolve_environment,
)
from zenml.sandboxes import (  # noqa: E402
    STEP_IMAGE,
    BaseSandboxSnapshot,
    SandboxExecError,
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
        chunks = [b"hel", b"lo\nwo", b"rld\n"]
        assert list(_line_buffer(chunks)) == ["hello\n", "world\n"]

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
# _resolve_environment
# ---------------------------------------------------------------------------


class TestResolveEnvironment:
    def test_component_env_alone(self) -> None:
        merged = _resolve_environment(
            component_env={"A": "1"},
            component_secret_ids=[],
            settings_env={},
            copy_local_env=False,
        )
        assert merged == {"A": "1"}

    def test_settings_override_component(self) -> None:
        merged = _resolve_environment(
            component_env={"A": "1", "B": "1"},
            component_secret_ids=[],
            settings_env={"A": "2"},
            copy_local_env=False,
        )
        assert merged == {"A": "2", "B": "1"}

    def test_secrets_layered_between_component_and_settings(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Component env defines A; secret defines B; Settings overrides B.
        fake_secret = MagicMock(secret_values={"B": "from_secret"})
        fake_client = MagicMock()
        fake_client.get_secret.return_value = fake_secret
        with patch(
            "zenml.integrations.modal.sandboxes.modal_sandbox.Client",
            return_value=fake_client,
        ):
            merged = _resolve_environment(
                component_env={"A": "1"},
                component_secret_ids=["secret-uuid"],
                settings_env={"B": "from_settings"},
                copy_local_env=False,
            )
        assert merged == {"A": "1", "B": "from_settings"}

    def test_copy_local_env_layered_last(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("FROM_LOCAL", "local-val")
        merged = _resolve_environment(
            component_env={"A": "1"},
            component_secret_ids=[],
            settings_env={},
            copy_local_env=True,
        )
        assert merged["A"] == "1"
        assert merged["FROM_LOCAL"] == "local-val"


# ---------------------------------------------------------------------------
# ModalSandboxSnapshot
# ---------------------------------------------------------------------------


class TestModalSnapshot:
    def test_provider_defaults_to_modal(self) -> None:
        snap = ModalSandboxSnapshot(ref="im-123")
        assert snap.provider == "modal"

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

    def test_kill_swallows_already_exited(self) -> None:
        fake = MagicMock()
        fake.kill.side_effect = RuntimeError("already terminated")
        ModalSandboxProcess(fake).kill()  # no raise


# ---------------------------------------------------------------------------
# ModalSandboxSession
# ---------------------------------------------------------------------------


class TestModalSandboxSession:
    def test_id_from_sandbox_object_id(self) -> None:
        fake_sandbox = MagicMock(object_id="sb_xyz")
        session = ModalSandboxSession(fake_sandbox)
        assert session.id == "sb_xyz"

    def test_exec_list_command_passes_argv(self) -> None:
        fake_sandbox = MagicMock(object_id="sb_xyz")
        fake_sandbox.exec.return_value = MagicMock()
        ModalSandboxSession(fake_sandbox).exec(["python", "-c", "print(1)"])
        fake_sandbox.exec.assert_called_once_with("python", "-c", "print(1)")

    def test_exec_string_command_shell_split(self) -> None:
        fake_sandbox = MagicMock(object_id="sb_xyz")
        fake_sandbox.exec.return_value = MagicMock()
        ModalSandboxSession(fake_sandbox).exec("python -c 'print(1)'")
        # shlex.split → ["python", "-c", "print(1)"]
        fake_sandbox.exec.assert_called_once_with("python", "-c", "print(1)")

    def test_exec_launch_failure_raises_sandbox_exec_error(self) -> None:
        fake_sandbox = MagicMock(object_id="sb_xyz")
        fake_sandbox.exec.side_effect = RuntimeError("image broken")
        with pytest.raises(SandboxExecError, match="image broken"):
            ModalSandboxSession(fake_sandbox).exec(["nope"])

    def test_snapshot_packages_image_id(self) -> None:
        fake_sandbox = MagicMock(object_id="sb_xyz")
        fake_sandbox.snapshot_filesystem.return_value = MagicMock(
            object_id="im-123"
        )
        snap = ModalSandboxSession(fake_sandbox).snapshot()
        assert snap.provider == "modal"
        assert snap.ref == "im-123"

    def test_destroy_calls_terminate(self) -> None:
        fake_sandbox = MagicMock(object_id="sb_xyz")
        ModalSandboxSession(fake_sandbox).destroy()
        fake_sandbox.terminate.assert_called_once()

    def test_close_is_a_noop(self) -> None:
        # Modal Sandbox has no client-side resources to release; close()
        # must not call terminate() (that's destroy()'s job).
        fake_sandbox = MagicMock(object_id="sb_xyz")
        ModalSandboxSession(fake_sandbox).close()
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
