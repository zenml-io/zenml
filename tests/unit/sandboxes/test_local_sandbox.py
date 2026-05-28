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
"""Unit tests for the LocalSandbox flavor."""

import os
import sys
from datetime import datetime
from typing import Optional
from uuid import uuid4

import pytest

from zenml.enums import StackComponentType
from zenml.sandboxes import (
    BaseSandboxSettings,
    LocalSandbox,
    LocalSandboxConfig,
    LocalSandboxFlavor,
    LocalSandboxSettings,
    SandboxExecError,
)


def _make_local_sandbox(
    *,
    environment: Optional[dict] = None,
) -> LocalSandbox:
    """Builds a LocalSandbox without going through Stack/Client."""
    return LocalSandbox(
        name="test-local",
        id=uuid4(),
        config=LocalSandboxConfig(),
        flavor="local",
        type=StackComponentType.SANDBOX,
        user=None,
        created=datetime.now(),
        updated=datetime.now(),
        environment=environment or {},
        secrets=[],
    )


class TestFlavor:
    def test_flavor_name_is_local(self) -> None:
        assert LocalSandboxFlavor().name == "local"

    def test_implementation_class(self) -> None:
        assert LocalSandboxFlavor().implementation_class is LocalSandbox

    def test_is_remote_false(self) -> None:
        assert LocalSandboxConfig().is_remote is False


class TestSettings:
    def test_inherits_base_fields(self) -> None:
        s = LocalSandboxSettings(timeout_seconds=60)
        assert s.timeout_seconds == 60
        assert s.base_image is None


class TestCreateSession:
    def test_warns_on_no_isolation(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        import logging

        with caplog.at_level(logging.WARNING, logger="zenml"):
            session = _make_local_sandbox().create_session()
            try:
                assert any(
                    "NO isolation" in record.message
                    for record in caplog.records
                ), f"Expected NO isolation warning, got: {caplog.records}"
            finally:
                session.close()

    def test_session_id_is_local_prefixed(self) -> None:
        session = _make_local_sandbox().create_session()
        try:
            assert session.id.startswith("local-")
        finally:
            session.close()


class TestExec:
    def test_basic_exec_returns_stdout(self) -> None:
        session = _make_local_sandbox().create_session()
        try:
            process = session.exec(
                [sys.executable, "-c", "print('hello from local sandbox')"]
            )
            stdout = list(process.stdout())
            stderr = list(process.stderr())
            exit_code = process.wait()
            assert exit_code == 0
            assert "hello from local sandbox\n" in stdout
            assert stderr == []
        finally:
            session.close()

    def test_non_zero_exit_is_surfaced(self) -> None:
        session = _make_local_sandbox().create_session()
        try:
            process = session.exec(
                [sys.executable, "-c", "import sys; sys.exit(3)"]
            )
            assert process.wait() == 3
            assert process.exit_code == 3
        finally:
            session.close()

    def test_stderr_separately_streamed(self) -> None:
        session = _make_local_sandbox().create_session()
        try:
            process = session.exec(
                [
                    sys.executable,
                    "-c",
                    "import sys; print('out'); print('err', file=sys.stderr)",
                ]
            )
            stdout = list(process.stdout())
            stderr = list(process.stderr())
            process.wait()
            assert stdout == ["out\n"]
            assert stderr == ["err\n"]
        finally:
            session.close()

    def test_command_not_found_raises_exec_error(self) -> None:
        session = _make_local_sandbox().create_session()
        try:
            with pytest.raises(SandboxExecError):
                session.exec(["this-binary-does-not-exist-xyz"])
        finally:
            session.close()

    def test_string_command_is_shell_split(self) -> None:
        session = _make_local_sandbox().create_session()
        try:
            process = session.exec(f"{sys.executable} -c 'print(2 + 2)'")
            stdout = list(process.stdout())
            process.wait()
            assert stdout == ["4\n"]
        finally:
            session.close()

    def test_exec_after_close_raises(self) -> None:
        session = _make_local_sandbox().create_session()
        session.close()
        with pytest.raises(SandboxExecError):
            session.exec([sys.executable, "-c", "pass"])


class TestEnvAndCwd:
    def test_component_env_propagates_to_subprocess(self) -> None:
        sandbox = _make_local_sandbox(environment={"FROM_COMPONENT": "yes"})
        session = sandbox.create_session()
        try:
            process = session.exec(
                [
                    sys.executable,
                    "-c",
                    "import os; print(os.environ.get('FROM_COMPONENT', ''))",
                ]
            )
            stdout = list(process.stdout())
            process.wait()
            assert stdout == ["yes\n"]
        finally:
            session.close()

    def test_settings_env_overrides_component_env(self) -> None:
        sandbox = _make_local_sandbox(environment={"K": "from-component"})
        settings = LocalSandboxSettings(environment={"K": "from-settings"})
        session = sandbox.create_session(settings=settings)
        try:
            process = session.exec(
                [sys.executable, "-c", "import os; print(os.environ['K'])"]
            )
            stdout = list(process.stdout())
            process.wait()
            assert stdout == ["from-settings\n"]
        finally:
            session.close()

    def test_per_exec_env_overrides_session_env(self) -> None:
        sandbox = _make_local_sandbox(environment={"K": "from-session"})
        session = sandbox.create_session()
        try:
            process = session.exec(
                [sys.executable, "-c", "import os; print(os.environ['K'])"],
                env={"K": "from-exec"},
            )
            stdout = list(process.stdout())
            process.wait()
            assert stdout == ["from-exec\n"]
        finally:
            session.close()

    def test_workdir_is_session_tmpdir(self) -> None:
        session = _make_local_sandbox().create_session()
        try:
            process = session.exec(
                [sys.executable, "-c", "import os; print(os.getcwd())"]
            )
            stdout = list(process.stdout())
            process.wait()
            assert "zenml-local-sandbox-" in stdout[0]
        finally:
            session.close()


class TestCloseAndDestroy:
    def test_close_removes_workdir(self) -> None:
        sandbox = _make_local_sandbox()
        session = sandbox.create_session()
        workdir = session._workdir  # type: ignore[attr-defined]
        assert os.path.isdir(workdir)
        session.close()
        assert not os.path.isdir(workdir)

    def test_close_is_idempotent(self) -> None:
        session = _make_local_sandbox().create_session()
        session.close()
        session.close()  # must not raise

    def test_destroy_delegates_to_close(self) -> None:
        sandbox = _make_local_sandbox()
        session = sandbox.create_session()
        workdir = session._workdir  # type: ignore[attr-defined]
        session.destroy()
        assert not os.path.isdir(workdir)


class TestOptionalMethods:
    def test_snapshot_default_raises(self) -> None:
        session = _make_local_sandbox().create_session()
        try:
            with pytest.raises(NotImplementedError):
                session.snapshot()
        finally:
            session.close()

    def test_attach_default_raises(self) -> None:
        with pytest.raises(NotImplementedError):
            _make_local_sandbox().attach("local-xyz")

    def test_upload_file_default_raises(self) -> None:
        session = _make_local_sandbox().create_session()
        try:
            with pytest.raises(NotImplementedError):
                session.upload_file("/local", "/remote")
        finally:
            session.close()


class TestSettingsCoercion:
    def test_base_settings_coerced_to_local(self) -> None:
        sandbox = _make_local_sandbox()
        base = BaseSandboxSettings(environment={"K": "v"})
        eff = sandbox.resolve_settings(base)
        assert isinstance(eff, LocalSandboxSettings)
        assert eff.environment == {"K": "v"}

    def test_none_returns_defaults(self) -> None:
        eff = _make_local_sandbox().resolve_settings(None)
        assert eff.base_image is None
        assert eff.environment == {}


class TestBuiltinFlavorRegistration:
    def test_local_sandbox_is_in_builtin_flavors(self) -> None:
        # Without this registration the flavor isn't auto-available;
        # users would have to register a custom flavor instead of just
        # `zenml sandbox register foo --flavor=local`.
        from zenml.stack.flavor_registry import FlavorRegistry

        flavors = FlavorRegistry().builtin_flavors
        assert LocalSandboxFlavor in flavors
