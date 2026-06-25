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
"""Tests for the SSH step operator async interface (submit/get_status/cancel).

All SSH connections are mocked — no actual remote host is required.
"""

from typing import Any, Dict
from unittest.mock import MagicMock, patch

from zenml.enums import ExecutionStatus
from zenml.integrations.ssh.ssh_client import RemoteCommandResult
from zenml.integrations.ssh.step_operators.ssh_step_operator import (
    SSH_CONTAINER_NAME_METADATA_KEY,
    SSHStepOperator,
)


def _make_step_run(metadata: Dict[str, Any]) -> MagicMock:
    """Build a fake StepRunResponse with the given run_metadata."""
    step_run = MagicMock()
    step_run.run_metadata = dict(metadata)
    return step_run


def _make_mock_ssh(
    exec_results: Dict[str, RemoteCommandResult] | None = None,
) -> MagicMock:
    """Build a mock SSHClient that maps command substrings to results.

    Args:
        exec_results: Mapping of command substring -> result.
    """
    ssh_instance = MagicMock()

    def fake_exec(command: str, **kwargs: Any) -> RemoteCommandResult:
        if exec_results:
            for pattern, result in exec_results.items():
                if pattern in command:
                    return result
        return RemoteCommandResult(exit_code=0, stdout="", stderr="")

    ssh_instance.exec = MagicMock(side_effect=fake_exec)
    ssh_instance.put_text = MagicMock()
    return ssh_instance


def _make_operator() -> SSHStepOperator:
    """Build an SSHStepOperator with minimal mocked config."""
    operator = SSHStepOperator.__new__(SSHStepOperator)
    config = MagicMock()
    config.hostname = "test-host"
    config.port = 22
    config.username = "testuser"
    config.ssh_key_path = "/fake/key"
    config.ssh_private_key = None
    config.ssh_key_passphrase = None
    config.verify_host_key = False
    config.known_hosts_path = None
    config.connection_timeout = 10.0
    config.keepalive_interval = 30
    config.docker_binary = "docker"
    operator._config = config
    operator.connector = None
    return operator


# --- get_status ---


class TestGetStatus:
    """get_status() reads container state via docker inspect."""

    def _run(
        self,
        operator: SSHStepOperator,
        step_run: MagicMock,
        exec_results: Dict[str, RemoteCommandResult],
    ) -> ExecutionStatus:
        mock_ssh = _make_mock_ssh(exec_results=exec_results)
        with patch(
            "zenml.integrations.ssh.step_operators.ssh_step_operator.SSHClient"
        ) as mock_cls:
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_ssh)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            return operator.get_status(step_run)

    def test_running(self) -> None:
        operator = _make_operator()
        step_run = _make_step_run(
            {SSH_CONTAINER_NAME_METADATA_KEY: "zenml-step-abc"}
        )
        result = self._run(
            operator,
            step_run,
            {"inspect": RemoteCommandResult(exit_code=0, stdout="running 0")},
        )
        assert result == ExecutionStatus.RUNNING

    def test_exited_success(self) -> None:
        operator = _make_operator()
        step_run = _make_step_run(
            {SSH_CONTAINER_NAME_METADATA_KEY: "zenml-step-abc"}
        )
        result = self._run(
            operator,
            step_run,
            {"inspect": RemoteCommandResult(exit_code=0, stdout="exited 0")},
        )
        assert result == ExecutionStatus.COMPLETED

    def test_exited_failure(self) -> None:
        operator = _make_operator()
        step_run = _make_step_run(
            {SSH_CONTAINER_NAME_METADATA_KEY: "zenml-step-abc"}
        )
        result = self._run(
            operator,
            step_run,
            {"inspect": RemoteCommandResult(exit_code=0, stdout="exited 137")},
        )
        assert result == ExecutionStatus.FAILED

    def test_missing_container_returns_failed(self) -> None:
        operator = _make_operator()
        step_run = _make_step_run(
            {SSH_CONTAINER_NAME_METADATA_KEY: "zenml-step-abc"}
        )
        result = self._run(
            operator,
            step_run,
            {
                "inspect": RemoteCommandResult(
                    exit_code=1, stdout="", stderr="No such container"
                )
            },
        )
        assert result == ExecutionStatus.FAILED

    def test_no_metadata_returns_failed(self) -> None:
        """With no recorded container, get_status short-circuits to FAILED."""
        operator = _make_operator()
        step_run = _make_step_run({})
        assert operator.get_status(step_run) == ExecutionStatus.FAILED


# --- cancel ---


class TestCancel:
    def test_cancel_stops_container(self) -> None:
        operator = _make_operator()
        step_run = _make_step_run(
            {SSH_CONTAINER_NAME_METADATA_KEY: "zenml-step-cancel"}
        )
        mock_ssh = _make_mock_ssh()
        with patch(
            "zenml.integrations.ssh.step_operators.ssh_step_operator.SSHClient"
        ) as mock_cls:
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_ssh)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            operator.cancel(step_run)

        exec_calls = [str(c) for c in mock_ssh.exec.call_args_list]
        assert any(
            "stop" in c and "zenml-step-cancel" in c for c in exec_calls
        )

    def test_cancel_no_metadata_is_noop(self) -> None:
        """Cancel with no recorded container must not open an SSH connection."""
        operator = _make_operator()
        step_run = _make_step_run({})
        with patch(
            "zenml.integrations.ssh.step_operators.ssh_step_operator.SSHClient"
        ) as mock_cls:
            operator.cancel(step_run)
            mock_cls.assert_not_called()

    def test_cancel_suppresses_errors(self) -> None:
        """Cancel is best-effort — exceptions must not propagate."""
        operator = _make_operator()
        step_run = _make_step_run(
            {SSH_CONTAINER_NAME_METADATA_KEY: "zenml-step-err"}
        )
        with patch(
            "zenml.integrations.ssh.step_operators.ssh_step_operator.SSHClient"
        ) as mock_cls:
            mock_cls.return_value.__enter__ = MagicMock(
                side_effect=ConnectionError("SSH failed")
            )
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            operator.cancel(step_run)
