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
"""Tests for sandbox execution error behavior."""

import pytest

from zenml.integrations.modal.sandboxes.modal_sandbox import (
    ModalSandboxSession,
)
from zenml.sandboxes import (
    SandboxExecError,
    SandboxExecResult,
    SandboxSessionMetadata,
)


class _FakeReadableStream:
    """Minimal readable stream that always returns the configured payload."""

    def __init__(self, payload: str) -> None:
        self._payload = payload

    def read(self) -> str:
        """Reads the configured payload."""
        return self._payload


class _FakeProcess:
    """Minimal process object used by ModalSandboxSession.exec_run tests."""

    def __init__(
        self, *, exit_code: int, stdout: str = "", stderr: str = ""
    ) -> None:
        self.returncode = exit_code
        self.stdout = _FakeReadableStream(stdout)
        self.stderr = _FakeReadableStream(stderr)

    def wait(self) -> int:
        """Waits for process completion and returns the process exit code."""
        return self.returncode


def _create_modal_session(*, raise_on_failure: bool) -> ModalSandboxSession:
    """Creates a Modal session object without requiring the Modal SDK."""
    return ModalSandboxSession(
        sandbox=object(),
        app_run_context=None,
        app_run_context_is_async=False,
        raise_on_failure=raise_on_failure,
        metadata=SandboxSessionMetadata(
            session_id="session-1", provider="modal"
        ),
        cpu=1.0,
        memory_mb=1024,
        gpu=None,
        cpu_cost_per_core_second_usd=None,
        memory_cost_per_gib_second_usd=None,
    )


def test_sandbox_exec_error_preserves_result_and_formats_stderr_tail() -> None:
    """Tests that SandboxExecError keeps the result and truncates stderr."""
    stderr = "\n".join([f"line-{index}" for index in range(1, 13)])
    result = SandboxExecResult(exit_code=7, stderr=stderr)

    error = SandboxExecError(result)

    assert error.result is result
    error_message = str(error)
    assert "exit code 7" in error_message

    expected_tail = "\n".join([f"line-{index}" for index in range(3, 13)])
    assert error_message.endswith(expected_tail)
    assert "line-1\n" not in error_message
    assert "line-2\n" not in error_message


def test_sandbox_exec_error_without_stderr_has_compact_message() -> None:
    """Tests that SandboxExecError message stays compact for empty stderr."""
    error = SandboxExecError(SandboxExecResult(exit_code=5, stderr=""))

    assert str(error) == "Sandbox command failed with exit code 5"


def test_modal_exec_run_check_false_suppresses_error(monkeypatch) -> None:
    """Tests that `check=False` suppresses SandboxExecError for non-zero exits."""
    session = _create_modal_session(raise_on_failure=True)

    def _failing_process(*args, **kwargs):  # type: ignore[no-untyped-def]
        return _FakeProcess(exit_code=13, stderr="failure")

    monkeypatch.setattr(session, "_exec_process", _failing_process)

    result = session.exec_run(["python", "-c", "print('hello')"], check=False)

    assert result.exit_code == 13
    assert result.stderr == "failure"

    with pytest.raises(SandboxExecError):
        session.exec_run(["python", "-c", "print('hello')"])
