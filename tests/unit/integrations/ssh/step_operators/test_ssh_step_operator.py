#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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

import json
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from zenml.enums import ExecutionStatus
from zenml.integrations.ssh.ssh_utils import RemoteCommandResult
from zenml.integrations.ssh.step_operators.ssh_step_operator import (
    SSH_CANCEL_FILE_METADATA_KEY,
    SSH_CONTAINER_NAME_METADATA_KEY,
    SSH_STATUS_FILE_METADATA_KEY,
    SSHStepOperator,
)


def _make_step_run(metadata: Dict[str, Any]) -> MagicMock:
    """Build a fake StepRunResponse with the given run_metadata."""
    step_run = MagicMock()
    step_run.run_metadata = dict(metadata)
    return step_run


def _make_mock_ssh(
    exec_results: Dict[str, RemoteCommandResult] | None = None,
    read_text_result: str | None = None,
    read_text_error: Exception | None = None,
) -> MagicMock:
    """Build a mock SSHClient context manager.

    Args:
        exec_results: Mapping of command substring -> result.
        read_text_result: Return value for read_text().
        read_text_error: Exception to raise from read_text().
    """
    ssh_instance = MagicMock()

    def fake_exec(command: str, **kwargs: Any) -> RemoteCommandResult:
        if exec_results:
            for pattern, result in exec_results.items():
                if pattern in command:
                    return result
        return RemoteCommandResult(exit_code=0, stdout="", stderr="")

    ssh_instance.exec = MagicMock(side_effect=fake_exec)

    if read_text_error:
        ssh_instance.read_text = MagicMock(side_effect=read_text_error)
    elif read_text_result is not None:
        ssh_instance.read_text = MagicMock(return_value=read_text_result)
    else:
        ssh_instance.read_text = MagicMock(return_value="")

    ssh_instance.put_text = MagicMock()
    ssh_instance.file_exists = MagicMock(return_value=True)

    return ssh_instance


# --- _map_state_to_status ---


class TestMapStateToStatus:
    def test_running(self) -> None:
        assert (
            SSHStepOperator._map_state_to_status("running")
            == ExecutionStatus.RUNNING
        )

    def test_completed(self) -> None:
        assert (
            SSHStepOperator._map_state_to_status("completed")
            == ExecutionStatus.COMPLETED
        )

    def test_failed(self) -> None:
        assert (
            SSHStepOperator._map_state_to_status("failed")
            == ExecutionStatus.FAILED
        )

    def test_stopped(self) -> None:
        assert (
            SSHStepOperator._map_state_to_status("stopped")
            == ExecutionStatus.FAILED
        )

    def test_unknown_defaults_to_running(self) -> None:
        assert (
            SSHStepOperator._map_state_to_status("unknown")
            == ExecutionStatus.RUNNING
        )


# --- get_status ---


class TestGetStatus:
    """Test get_status() with mocked SSH connections."""

    def _make_operator(self) -> SSHStepOperator:
        """Build an SSHStepOperator with minimal config."""
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
        return operator

    def test_reads_completed_from_status_file(self) -> None:
        operator = self._make_operator()
        step_run = _make_step_run(
            {
                SSH_STATUS_FILE_METADATA_KEY: "/tmp/status.json",
                SSH_CONTAINER_NAME_METADATA_KEY: "zenml-step-abc",
            }
        )
        status_json = json.dumps({"state": "completed", "exit_code": 0})
        mock_ssh = _make_mock_ssh(read_text_result=status_json)

        with patch(
            "zenml.integrations.ssh.step_operators.ssh_step_operator.SSHClient"
        ) as mock_cls:
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_ssh)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = operator.get_status(step_run)

        assert result == ExecutionStatus.COMPLETED

    def test_reads_failed_from_status_file(self) -> None:
        operator = self._make_operator()
        step_run = _make_step_run(
            {
                SSH_STATUS_FILE_METADATA_KEY: "/tmp/status.json",
                SSH_CONTAINER_NAME_METADATA_KEY: "zenml-step-abc",
            }
        )
        status_json = json.dumps({"state": "failed", "exit_code": 1})
        mock_ssh = _make_mock_ssh(read_text_result=status_json)

        with patch(
            "zenml.integrations.ssh.step_operators.ssh_step_operator.SSHClient"
        ) as mock_cls:
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_ssh)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = operator.get_status(step_run)

        assert result == ExecutionStatus.FAILED

    def test_reads_running_from_status_file(self) -> None:
        operator = self._make_operator()
        step_run = _make_step_run(
            {
                SSH_STATUS_FILE_METADATA_KEY: "/tmp/status.json",
                SSH_CONTAINER_NAME_METADATA_KEY: "zenml-step-abc",
            }
        )
        status_json = json.dumps({"state": "running"})
        mock_ssh = _make_mock_ssh(read_text_result=status_json)

        with patch(
            "zenml.integrations.ssh.step_operators.ssh_step_operator.SSHClient"
        ) as mock_cls:
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_ssh)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = operator.get_status(step_run)

        assert result == ExecutionStatus.RUNNING

    def test_stopped_maps_to_failed(self) -> None:
        operator = self._make_operator()
        step_run = _make_step_run(
            {
                SSH_STATUS_FILE_METADATA_KEY: "/tmp/status.json",
                SSH_CONTAINER_NAME_METADATA_KEY: "zenml-step-abc",
            }
        )
        status_json = json.dumps({"state": "stopped"})
        mock_ssh = _make_mock_ssh(read_text_result=status_json)

        with patch(
            "zenml.integrations.ssh.step_operators.ssh_step_operator.SSHClient"
        ) as mock_cls:
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_ssh)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = operator.get_status(step_run)

        assert result == ExecutionStatus.FAILED

    def test_fallback_to_docker_inspect_running(self) -> None:
        """When status file is missing, fall back to docker inspect."""
        operator = self._make_operator()
        step_run = _make_step_run(
            {
                SSH_STATUS_FILE_METADATA_KEY: "/tmp/status.json",
                SSH_CONTAINER_NAME_METADATA_KEY: "zenml-step-abc",
            }
        )
        mock_ssh = _make_mock_ssh(
            read_text_error=FileNotFoundError("no file"),
            exec_results={
                "inspect": RemoteCommandResult(exit_code=0, stdout="running"),
            },
        )

        with patch(
            "zenml.integrations.ssh.step_operators.ssh_step_operator.SSHClient"
        ) as mock_cls:
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_ssh)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = operator.get_status(step_run)

        assert result == ExecutionStatus.RUNNING

    def test_fallback_to_docker_inspect_exited_success(self) -> None:
        operator = self._make_operator()
        step_run = _make_step_run(
            {
                SSH_STATUS_FILE_METADATA_KEY: "/tmp/status.json",
                SSH_CONTAINER_NAME_METADATA_KEY: "zenml-step-abc",
            }
        )

        call_count = [0]

        def fake_exec(command: str, **kwargs: Any) -> RemoteCommandResult:
            call_count[0] += 1
            if "State.Status" in command:
                return RemoteCommandResult(exit_code=0, stdout="exited")
            if "State.ExitCode" in command:
                return RemoteCommandResult(exit_code=0, stdout="0")
            return RemoteCommandResult(exit_code=0)

        mock_ssh = _make_mock_ssh(read_text_error=FileNotFoundError("no file"))
        mock_ssh.exec = MagicMock(side_effect=fake_exec)

        with patch(
            "zenml.integrations.ssh.step_operators.ssh_step_operator.SSHClient"
        ) as mock_cls:
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_ssh)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = operator.get_status(step_run)

        assert result == ExecutionStatus.COMPLETED

    def test_both_fail_returns_failed(self) -> None:
        """When both status file and docker inspect fail, return FAILED."""
        operator = self._make_operator()
        step_run = _make_step_run(
            {
                SSH_STATUS_FILE_METADATA_KEY: "/tmp/status.json",
                SSH_CONTAINER_NAME_METADATA_KEY: "zenml-step-abc",
            }
        )
        mock_ssh = _make_mock_ssh(
            read_text_error=FileNotFoundError("no file"),
            exec_results={
                "inspect": RemoteCommandResult(
                    exit_code=1, stdout="", stderr="No such container"
                ),
            },
        )

        with patch(
            "zenml.integrations.ssh.step_operators.ssh_step_operator.SSHClient"
        ) as mock_cls:
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_ssh)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = operator.get_status(step_run)

        assert result == ExecutionStatus.FAILED


# --- cancel ---


class TestCancel:
    def _make_operator(self) -> SSHStepOperator:
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
        return operator

    def test_cancel_writes_marker_and_stops(self) -> None:
        operator = self._make_operator()
        step_run = _make_step_run(
            {
                SSH_CONTAINER_NAME_METADATA_KEY: "zenml-step-cancel",
                SSH_CANCEL_FILE_METADATA_KEY: "/tmp/cancel-abc",
            }
        )
        mock_ssh = _make_mock_ssh()

        with patch(
            "zenml.integrations.ssh.step_operators.ssh_step_operator.SSHClient"
        ) as mock_cls:
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_ssh)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            operator.cancel(step_run)

        # Verify touch and docker stop were called.
        exec_calls = [str(c) for c in mock_ssh.exec.call_args_list]
        assert any("touch" in c and "cancel-abc" in c for c in exec_calls)
        assert any(
            "docker stop" in c and "zenml-step-cancel" in c for c in exec_calls
        )

    def test_cancel_suppresses_errors(self) -> None:
        """Cancel is best-effort — exceptions should not propagate."""
        operator = self._make_operator()
        step_run = _make_step_run(
            {
                SSH_CONTAINER_NAME_METADATA_KEY: "zenml-step-err",
                SSH_CANCEL_FILE_METADATA_KEY: "/tmp/cancel-err",
            }
        )

        with patch(
            "zenml.integrations.ssh.step_operators.ssh_step_operator.SSHClient"
        ) as mock_cls:
            mock_cls.return_value.__enter__ = MagicMock(
                side_effect=ConnectionError("SSH failed")
            )
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            # Should not raise.
            operator.cancel(step_run)
