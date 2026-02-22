#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Tests for Modal sandbox streaming log forwarding."""

import socket
from typing import List

import pytest

from zenml.integrations.modal.sandboxes.modal_sandbox import (
    ModalSandboxProcess,
    ModalSandboxSession,
    _is_command_router_disabled,
    _patch_command_router_fallback,
    _readline_from_stream,
    _run_awaitable,
    _wait_for_process,
    _write_to_stream,
)
from zenml.sandboxes import SandboxSessionMetadata


class _FakeStream:
    """Simple stream that returns predefined lines via readline()."""

    def __init__(self, lines: List[str]) -> None:
        self._lines = list(lines)

    def readline(self) -> str:
        """Returns the next line until the stream is exhausted."""
        return self._lines.pop(0) if self._lines else ""


class _FakeProcess:
    """Minimal process object with stdout/stderr and wait behavior."""

    def __init__(
        self, stdout_lines: List[str], stderr_lines: List[str], returncode: int
    ) -> None:
        self.stdout = _FakeStream(stdout_lines)
        self.stderr = _FakeStream(stderr_lines)
        self.returncode = returncode

    def wait(self) -> int:
        """Returns the process return code."""
        return self.returncode


class _DrainOnlyStream:
    """Simple stream that requires drain() to flush input writes."""

    def __init__(self) -> None:
        self.written: List[bytes] = []
        self.drain_calls = 0

    def write(self, payload: bytes) -> None:
        """Buffers payload writes before a drain call."""
        self.written.append(payload)

    async def drain(self) -> None:
        """Tracks that the buffered payload was flushed."""
        self.drain_calls += 1


class _IterOnlyStream:
    """Simple stream that supports iterator-based line reads only."""

    def __init__(self, lines: List[str]) -> None:
        self._lines = list(lines)

    def __iter__(self) -> "_IterOnlyStream":
        """Returns self as an iterator."""
        return self

    def __next__(self) -> str:
        """Returns the next line until exhaustion."""
        if not self._lines:
            raise StopIteration
        return self._lines.pop(0)


class _PollingProcess:
    """Simple process exposing poll()/wait() behavior for timeout tests."""

    def __init__(self, poll_values: List[object]) -> None:
        self._poll_values = list(poll_values)
        self.wait_calls = 0

    def poll(self):
        """Returns sequential poll values."""
        if not self._poll_values:
            return None
        return self._poll_values.pop(0)

    def wait(self) -> int:
        """Tracks wait calls when fallback polling is not used."""
        self.wait_calls += 1
        return 0


def test_modal_sandbox_process_forwards_logs(mocker) -> None:
    """Ensures streaming stdout/stderr are logged and yielded."""
    info_mock = mocker.patch(
        "zenml.integrations.modal.sandboxes.modal_sandbox.logger.info"
    )
    warning_mock = mocker.patch(
        "zenml.integrations.modal.sandboxes.modal_sandbox.logger.warning"
    )
    process = _FakeProcess(
        stdout_lines=["line out 1\n", "line out 2\n"],
        stderr_lines=["line err 1\n"],
        returncode=7,
    )

    wrapper = ModalSandboxProcess(
        process=process,
        terminate_session=lambda **_: None,
    )

    stdout = list(wrapper.stdout_iter())
    stderr = list(wrapper.stderr_iter())
    exit_code = wrapper.wait()

    assert stdout == ["line out 1\n", "line out 2\n"]
    assert stderr == ["line err 1\n"]
    assert exit_code == 7

    info_mock.assert_any_call("[sandbox:stdout] %s", "line out 1")
    info_mock.assert_any_call("[sandbox:stdout] %s", "line out 2")
    warning_mock.assert_any_call("[sandbox:stderr] %s", "line err 1")


class _FailingRouterSandbox:
    """Fake sandbox that raises when command router init is attempted."""

    def __init__(self) -> None:
        self.calls = 0

    async def _get_command_router_client(self, task_id: str):
        self.calls += 1
        raise socket.gaierror(8, "nodename nor servname provided")


def test_command_router_fallback_on_dns_error(mocker) -> None:
    """Ensures DNS failures degrade to server-side exec path fallback."""
    warning_mock = mocker.patch(
        "zenml.integrations.modal.sandboxes.modal_sandbox.logger.warning"
    )
    sandbox = _FailingRouterSandbox()

    _patch_command_router_fallback(sandbox)

    result = sandbox._get_command_router_client
    assert result is not None

    assert _run_awaitable(sandbox._get_command_router_client("task-1")) is None
    assert _run_awaitable(sandbox._get_command_router_client("task-1")) is None
    assert sandbox.calls == 1
    assert _is_command_router_disabled(sandbox)
    warning_mock.assert_called_once()


class _FailingUnderlyingRouterSandbox:
    """Fake underlying sandbox with failing router initialization."""

    async def _get_command_router_client(self, task_id: str):
        raise socket.gaierror(8, "nodename nor servname provided")

    async def exec(self) -> str:
        await self._get_command_router_client("task-1")
        return "ok"


class _SyncWrapperSandbox:
    """Fake synchronized wrapper around an underlying sandbox object."""

    def __init__(self, underlying: _FailingUnderlyingRouterSandbox) -> None:
        self.__dict__["_sync_original_fake"] = underlying

    async def _get_command_router_client(self, task_id: str):
        raise RuntimeError("Wrapper-level method should not be used by exec.")

    async def exec(self) -> str:
        return await self.__dict__["_sync_original_fake"].exec()


def test_command_router_fallback_patches_sync_original_wrapper(mocker) -> None:
    """Ensures fallback patch reaches synchronized underlying sandbox objects."""
    warning_mock = mocker.patch(
        "zenml.integrations.modal.sandboxes.modal_sandbox.logger.warning"
    )
    wrapper = _SyncWrapperSandbox(_FailingUnderlyingRouterSandbox())

    _patch_command_router_fallback(wrapper)

    assert _run_awaitable(wrapper.exec()) == "ok"
    assert _is_command_router_disabled(wrapper)
    warning_mock.assert_called_once()


class _FlakyExecSandbox:
    """Fake sandbox whose first exec call fails with DNS resolution error."""

    def __init__(self) -> None:
        self.exec_calls = 0

    def exec(self, *args, **kwargs) -> str:
        self.exec_calls += 1
        if self.exec_calls == 1:
            raise socket.gaierror(8, "nodename nor servname provided")
        return "process"


def test_exec_process_retries_after_dns_error() -> None:
    """Ensures Modal sandbox exec is retried once after DNS router errors."""
    sandbox = _FlakyExecSandbox()
    session = ModalSandboxSession(
        sandbox=sandbox,
        app_run_context=None,
        app_run_context_is_async=False,
        raise_on_failure=False,
        metadata=SandboxSessionMetadata(
            session_id="session-1", provider="modal"
        ),
        cpu=1.0,
        memory_mb=1024,
        gpu=None,
        cpu_cost_per_core_second_usd=None,
        memory_cost_per_gib_second_usd=None,
    )

    process = session._exec_process(["python", "-c", "print('hello')"])

    assert process == "process"
    assert sandbox.exec_calls == 2


def test_write_to_stream_flushes_with_drain() -> None:
    """Ensures stream writes use drain() for Modal stream writers."""
    stream = _DrainOnlyStream()

    _write_to_stream(stream, "hello")

    assert stream.written == ["hello"]
    assert stream.drain_calls == 1


def test_readline_from_stream_uses_iterator_fallback() -> None:
    """Ensures line reads work for iterator-only stream implementations."""
    stream = _IterOnlyStream(["line 1\n", "line 2\n"])

    assert _readline_from_stream(stream) == "line 1\n"
    assert _readline_from_stream(stream) == "line 2\n"
    assert _readline_from_stream(stream) == ""


def test_wait_for_process_uses_poll_for_timeouts() -> None:
    """Ensures timeout-enabled waits rely on poll() instead of wait kwargs."""
    process = _PollingProcess([None, None, 3])

    exit_code = _wait_for_process(process, timeout_seconds=1)

    assert exit_code == 3
    assert process.wait_calls == 0


def test_wait_for_process_returns_timeout_code() -> None:
    """Ensures timeout-enabled waits return -1 when poll never completes."""
    process = _PollingProcess([None, None, None])

    exit_code = _wait_for_process(process, timeout_seconds=0)

    assert exit_code == -1
    assert process.wait_calls == 0


def test_code_interpreter_requires_command_router() -> None:
    """Ensures interpreter startup fails fast when router fallback is active."""
    sandbox = _FlakyExecSandbox()
    sandbox._zenml_command_router_disabled = True
    session = ModalSandboxSession(
        sandbox=sandbox,
        app_run_context=None,
        app_run_context_is_async=False,
        raise_on_failure=False,
        metadata=SandboxSessionMetadata(
            session_id="session-1", provider="modal"
        ),
        cpu=1.0,
        memory_mb=1024,
        gpu=None,
        cpu_cost_per_core_second_usd=None,
        memory_cost_per_gib_second_usd=None,
    )

    with pytest.raises(RuntimeError, match="requires a direct command router"):
        session.code_interpreter()
