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
"""Tests for the SSH integration utilities.

The pure-function tests validate GPU normalization, Docker flag construction,
and env-file serialization. The disk-guard and docker-login tests mock the
SSH connection, so no remote host is required.
"""

from contextlib import contextmanager
from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest

from zenml.integrations.ssh.utils import (
    build_compose_gpu_deploy,
    build_docker_gpus_flag,
    build_docker_run_command,
    build_mount_mappings,
    check_remote_disk,
    docker_login,
    get_free_disk_bytes,
    normalize_gpu_indices,
    prepare_remote_workdir,
    run_preflight_checks,
    serialize_env_for_docker_env_file,
    validate_mount_path,
)

_MODULE = "zenml.integrations.ssh.utils"

# --- normalize_gpu_indices ---


class TestNormalizeGpuIndices:
    def test_sorts_indices(self) -> None:
        assert normalize_gpu_indices([2, 0, 1]) == [0, 1, 2]

    def test_removes_duplicates(self) -> None:
        assert normalize_gpu_indices([1, 1, 0, 0]) == [0, 1]

    def test_single_index(self) -> None:
        assert normalize_gpu_indices([3]) == [3]

    def test_empty_list(self) -> None:
        assert normalize_gpu_indices([]) == []

    def test_rejects_negative_index(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            normalize_gpu_indices([-1, 0])

    def test_zero_is_valid(self) -> None:
        assert normalize_gpu_indices([0]) == [0]


# --- build_docker_gpus_flag ---


class TestBuildDockerGpusFlag:
    def test_single_gpu(self) -> None:
        assert build_docker_gpus_flag([0]) == '"device=0"'

    def test_multiple_gpus(self) -> None:
        assert build_docker_gpus_flag([0, 2]) == '"device=0,2"'

    def test_many_gpus(self) -> None:
        assert build_docker_gpus_flag([0, 1, 2, 3]) == '"device=0,1,2,3"'

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one"):
            build_docker_gpus_flag([])


# --- serialize_env_for_docker_env_file ---


class TestSerializeEnvForDockerEnvFile:
    def test_basic_key_value(self) -> None:
        result = serialize_env_for_docker_env_file({"FOO": "bar"})
        assert result == "FOO=bar\n"

    def test_multiple_keys_sorted(self) -> None:
        result = serialize_env_for_docker_env_file(
            {"ZEBRA": "z", "ALPHA": "a"}
        )
        assert result == "ALPHA=a\nZEBRA=z\n"

    def test_empty_value(self) -> None:
        result = serialize_env_for_docker_env_file({"KEY": ""})
        assert result == "KEY=\n"

    def test_empty_dict(self) -> None:
        result = serialize_env_for_docker_env_file({})
        assert result == ""

    def test_value_with_equals(self) -> None:
        """Values can contain '=' (only keys cannot)."""
        result = serialize_env_for_docker_env_file({"K": "a=b=c"})
        assert result == "K=a=b=c\n"

    def test_rejects_key_with_equals(self) -> None:
        with pytest.raises(ValueError, match="forbidden"):
            serialize_env_for_docker_env_file({"A=B": "val"})

    def test_rejects_key_with_nul(self) -> None:
        with pytest.raises(ValueError, match="forbidden"):
            serialize_env_for_docker_env_file({"A\x00B": "val"})

    def test_rejects_value_with_newline(self) -> None:
        with pytest.raises(ValueError, match="newline"):
            serialize_env_for_docker_env_file({"KEY": "line1\nline2"})

    def test_rejects_value_with_nul(self) -> None:
        with pytest.raises(ValueError, match="newline or NUL"):
            serialize_env_for_docker_env_file({"KEY": "val\x00ue"})

    def test_special_chars_in_values(self) -> None:
        """Values with spaces, quotes, JSON should be preserved."""
        result = serialize_env_for_docker_env_file(
            {"JSON": '{"key": "val"}', "SPACES": "hello world"}
        )
        lines = result.strip().split("\n")
        assert 'JSON={"key": "val"}' in lines
        assert "SPACES=hello world" in lines


# --- validate_mount_path / build_mount_mappings ---


class TestMounts:
    def test_validate_accepts_absolute_posix_path(self) -> None:
        assert validate_mount_path("/data/sets") == "/data/sets"

    def test_validate_rejects_relative_path(self) -> None:
        with pytest.raises(RuntimeError, match="Invalid mount path"):
            validate_mount_path("data/sets")

    def test_validate_rejects_path_with_colon(self) -> None:
        with pytest.raises(RuntimeError, match="Invalid mount path"):
            validate_mount_path("/data:/extra")

    def test_build_mappings(self) -> None:
        mappings = build_mount_mappings({"/host/a": "/c/a", "/host/b": "/c/b"})
        assert mappings == ["/host/a:/c/a", "/host/b:/c/b"]

    def test_build_mappings_validates_each_path(self) -> None:
        with pytest.raises(RuntimeError, match="Invalid mount path"):
            build_mount_mappings({"relative": "/container"})

    def test_build_mappings_empty(self) -> None:
        assert build_mount_mappings({}) == []


# --- build_compose_gpu_deploy ---


class TestBuildComposeGpuDeploy:
    def test_reserves_given_devices(self) -> None:
        deploy = build_compose_gpu_deploy([0, 2])
        device = deploy["resources"]["reservations"]["devices"][0]
        assert device["driver"] == "nvidia"
        assert device["device_ids"] == ["0", "2"]
        assert device["capabilities"] == ["gpu"]

    def test_normalizes_indices(self) -> None:
        deploy = build_compose_gpu_deploy([2, 0, 2])
        device = deploy["resources"]["reservations"]["devices"][0]
        assert device["device_ids"] == ["0", "2"]


# --- build_docker_run_command ---


class TestBuildDockerRunCommand:
    def test_minimal(self) -> None:
        cmd = build_docker_run_command(
            docker_binary="docker",
            image="img:latest",
            args=["python", "-m", "step"],
            container_name="c1",
        )
        assert cmd.startswith("docker run -d --name c1")
        assert cmd.endswith("img:latest python -m step")
        assert "--gpus" not in cmd
        assert "-v" not in cmd

    def test_full(self) -> None:
        cmd = build_docker_run_command(
            docker_binary="docker",
            image="img",
            args=["run"],
            container_name="c1",
            env_file="/work/env",
            network="host",
            entrypoint="/bin/entry",
            gpu_indices=[2, 0],
            mounts={"/data": "/models"},
            extra_args=["--shm-size", "1g"],
        )
        assert "--network host" in cmd
        assert "--env-file /work/env" in cmd
        # GPU indices are normalized (sorted, unique)
        assert '--gpus "device=0,2"' in cmd
        assert "-v /data:/models" in cmd
        assert "--shm-size 1g" in cmd
        assert "--entrypoint /bin/entry" in cmd

    def test_validates_mount_paths(self) -> None:
        with pytest.raises(RuntimeError, match="Invalid mount path"):
            build_docker_run_command(
                docker_binary="docker",
                image="img",
                args=[],
                container_name="c1",
                mounts={"relative": "/c"},
            )


def _mock_ssh_with_statvfs(f_bavail: int, f_frsize: int) -> MagicMock:
    """Build a mock SSHClient whose sftp().statvfs reports the given space."""
    ssh = MagicMock()
    stats = MagicMock(f_bavail=f_bavail, f_frsize=f_frsize)

    @contextmanager
    def fake_sftp() -> Iterator[MagicMock]:
        sftp = MagicMock()
        sftp.statvfs.return_value = stats
        yield sftp

    ssh.sftp.side_effect = fake_sftp
    return ssh


# --- run_preflight_checks ---


class TestRunPreflightChecks:
    def test_passes_when_docker_available(self) -> None:
        ssh = MagicMock()
        ssh.exec.return_value = MagicMock(
            exit_code=0, stdout="Docker version 27.0", stderr=""
        )
        run_preflight_checks(ssh, "docker")
        assert "docker --version" in ssh.exec.call_args.args[0]

    def test_raises_when_docker_missing(self) -> None:
        ssh = MagicMock()
        ssh.exec.return_value = MagicMock(
            exit_code=127, stdout="", stderr="command not found"
        )
        with pytest.raises(RuntimeError, match="Docker is not available"):
            run_preflight_checks(ssh, "docker")


# --- get_free_disk_bytes ---


class TestGetFreeDiskBytes:
    def test_multiplies_blocks_by_size(self) -> None:
        ssh = _mock_ssh_with_statvfs(f_bavail=1000, f_frsize=4096)
        assert get_free_disk_bytes(ssh, "/data") == 1000 * 4096

    def test_returns_none_when_statvfs_unsupported(self) -> None:
        ssh = MagicMock()

        @contextmanager
        def fake_sftp() -> Iterator[MagicMock]:
            sftp = MagicMock()
            sftp.statvfs.side_effect = OSError("statvfs not supported")
            yield sftp

        ssh.sftp.side_effect = fake_sftp
        assert get_free_disk_bytes(ssh, "/data") is None


# --- check_remote_disk ---


class TestCheckRemoteDisk:
    def test_raises_when_below_threshold(self) -> None:
        ssh = _mock_ssh_with_statvfs(f_bavail=1, f_frsize=1024**3)  # 1 GB
        with pytest.raises(RuntimeError, match="free"):
            check_remote_disk(ssh, "/data", 5.0)

    def test_passes_when_enough_free(self) -> None:
        ssh = _mock_ssh_with_statvfs(f_bavail=50, f_frsize=1024**3)  # 50 GB
        check_remote_disk(ssh, "/data", 5.0)

    def test_skips_when_statvfs_unsupported(self) -> None:
        ssh = MagicMock()
        with patch(f"{_MODULE}.get_free_disk_bytes", return_value=None):
            check_remote_disk(ssh, "/data", 5.0)

    def test_disabled_when_threshold_is_zero(self) -> None:
        ssh = MagicMock()
        check_remote_disk(ssh, "/data", 0.0)
        # Guard is disabled, so it must not query the remote host.
        ssh.sftp.assert_not_called()


# --- docker_login ---


class TestDockerLogin:
    def _registry(self, credentials: object = ("user", "pass")) -> MagicMock:
        registry = MagicMock()
        registry.credentials = credentials
        registry.config.uri = "registry.example.com"
        return registry

    def test_runs_login_command(self) -> None:
        ssh = MagicMock()
        ssh.exec.return_value = MagicMock(exit_code=0, stdout="", stderr="")
        docker_login(ssh, self._registry(), "docker")
        command = ssh.exec.call_args.args[0]
        assert "docker login" in command
        assert "--password-stdin" in command
        assert "registry.example.com" in command

    def test_raises_without_credentials(self) -> None:
        registry = self._registry(credentials=None)
        with pytest.raises(RuntimeError, match="credentials"):
            docker_login(MagicMock(), registry, "docker")

    def test_raises_when_login_fails(self) -> None:
        ssh = MagicMock()
        ssh.exec.return_value = MagicMock(
            exit_code=1, stdout="", stderr="bad creds"
        )
        with pytest.raises(RuntimeError, match="docker login"):
            docker_login(ssh, self._registry(), "docker")


# --- prepare_remote_workdir ---


class TestPrepareRemoteWorkdir:
    def _ssh_ok(self) -> MagicMock:
        ssh = MagicMock()
        ssh.exec.return_value = MagicMock(exit_code=0, stdout="", stderr="")
        return ssh

    def test_runs_preflight_mkdir_and_cleanup(self) -> None:
        ssh = self._ssh_ok()
        with patch(f"{_MODULE}.get_free_disk_bytes", return_value=None):
            prepare_remote_workdir(
                ssh,
                docker_binary="docker",
                workdir="/work",
                minimum_free_disk_gb=5.0,
                cleanup_command="find /work -delete",
            )
        commands = [call.args[0] for call in ssh.exec.call_args_list]
        assert "docker --version" in commands
        assert "mkdir -p /work" in commands
        assert "find /work -delete" in commands

    def test_raises_when_mkdir_fails(self) -> None:
        ssh = MagicMock()

        def fake_exec(command: str, **kwargs: object) -> MagicMock:
            if command.startswith("mkdir"):
                return MagicMock(exit_code=1, stdout="", stderr="denied")
            return MagicMock(exit_code=0, stdout="", stderr="")

        ssh.exec.side_effect = fake_exec
        with pytest.raises(RuntimeError, match="create remote directory"):
            prepare_remote_workdir(
                ssh,
                docker_binary="docker",
                workdir="/work",
                minimum_free_disk_gb=0.0,
            )

    def test_skips_cleanup_and_login_when_none(self) -> None:
        ssh = self._ssh_ok()
        with patch(f"{_MODULE}.docker_login") as login:
            prepare_remote_workdir(
                ssh,
                docker_binary="docker",
                workdir="/work",
                minimum_free_disk_gb=0.0,
            )
        login.assert_not_called()
        commands = [call.args[0] for call in ssh.exec.call_args_list]
        assert not any(c.startswith("find") for c in commands)

    def test_logs_in_when_registry_given(self) -> None:
        ssh = self._ssh_ok()
        registry = MagicMock()
        with patch(f"{_MODULE}.docker_login") as login:
            prepare_remote_workdir(
                ssh,
                docker_binary="docker",
                workdir="/work",
                minimum_free_disk_gb=0.0,
                container_registry=registry,
            )
        login.assert_called_once_with(
            ssh=ssh, container_registry=registry, docker_binary="docker"
        )
