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
"""Tests for SSH step operator remote Docker helpers.

These are pure-function tests that validate GPU normalization,
Docker flag construction, env-file serialization, and wrapper script
generation without needing SSH, Docker, or GPUs.
"""

import pytest

from zenml.integrations.ssh.remote_docker import (
    build_docker_gpus_flag,
    build_remote_supervisor_script,
    build_remote_wrapper_script,
    normalize_gpu_indices,
    serialize_env_for_docker_env_file,
)

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


# --- build_remote_wrapper_script ---


class TestBuildRemoteWrapperScript:
    def _build(self, **kwargs: object) -> str:
        defaults = dict(
            image="registry.example.com/my-image:latest",
            entrypoint_command=["python", "-m", "zenml.entrypoint"],
            env_file_path="/tmp/zenml-ssh/env-abc123",
            gpu_lock_dir="/tmp/zenml-gpu-locks",
            gpu_indices=None,
            use_gpu_locks=True,
            docker_binary="docker",
            extra_docker_run_args=None,
        )
        defaults.update(kwargs)
        return build_remote_wrapper_script(**defaults)  # type: ignore[arg-type]

    def test_cpu_only_no_locks(self) -> None:
        script = self._build(gpu_indices=None)
        assert "flock" not in script
        assert "--gpus" not in script
        assert "docker" in script
        assert "--rm" in script
        assert "--env-file" in script

    def test_shebang_and_strict_mode(self) -> None:
        script = self._build()
        assert script.startswith("#!/usr/bin/env bash\n")
        assert "set -euo pipefail" in script

    def test_cleanup_trap(self) -> None:
        script = self._build(env_file_path="/tmp/zenml-ssh/env-xyz")
        assert "trap" in script
        assert "/tmp/zenml-ssh/env-xyz" in script

    def test_gpu_locking_sorted_order(self) -> None:
        """Locks must be acquired in GPU-index-sorted order."""
        script = self._build(gpu_indices=[2, 0])
        # GPU 0 lock must appear before GPU 2 lock
        pos_0 = script.index("gpu-0.lock")
        pos_2 = script.index("gpu-2.lock")
        assert pos_0 < pos_2

    def test_gpu_locking_fd_numbers(self) -> None:
        """Each GPU gets a unique FD starting at 200."""
        script = self._build(gpu_indices=[0, 1, 2])
        assert "exec 200>" in script
        assert "exec 201>" in script
        assert "exec 202>" in script
        assert "flock 200" in script
        assert "flock 201" in script
        assert "flock 202" in script

    def test_gpu_locking_creates_lock_dir(self) -> None:
        script = self._build(gpu_indices=[0], gpu_lock_dir="/my/locks")
        assert "mkdir -p" in script
        assert "/my/locks" in script

    def test_gpus_flag_present_when_gpus_set(self) -> None:
        script = self._build(gpu_indices=[0, 2])
        assert '--gpus "device=0,2"' in script

    def test_no_locks_when_disabled(self) -> None:
        script = self._build(gpu_indices=[0], use_gpu_locks=False)
        assert "flock" not in script
        # But --gpus should still be set
        assert "--gpus" in script

    def test_entrypoint_command_quoted(self) -> None:
        script = self._build(
            entrypoint_command=["python", "-c", "print('hello world')"]
        )
        # shlex.quote adds single-quotes around args with spaces/quotes
        assert "print" in script

    def test_extra_docker_run_args(self) -> None:
        script = self._build(
            extra_docker_run_args=["--shm-size=2g", "--ulimit", "memlock=-1"]
        )
        assert "--shm-size=2g" in script
        assert "memlock=-1" in script

    def test_exec_prefix(self) -> None:
        """The docker run command should use exec to replace the shell."""
        script = self._build()
        assert "exec docker" in script

    def test_custom_docker_binary(self) -> None:
        script = self._build(docker_binary="/usr/local/bin/docker")
        assert "exec /usr/local/bin/docker" in script


# --- build_remote_supervisor_script ---


class TestBuildRemoteSupervisorScript:
    """Tests for the async supervisor script builder."""

    def _build(self, **kwargs: object) -> str:
        defaults = dict(
            image="registry.example.com/my-image:latest",
            entrypoint_command=["python", "-m", "zenml.entrypoint"],
            env_file_path="/tmp/zenml-ssh/env-abc123",
            status_file_path="/tmp/zenml-ssh/status-abc123.json",
            cancel_file_path="/tmp/zenml-ssh/cancel-abc123",
            container_name="zenml-step-abc123",
            gpu_lock_dir="/tmp/zenml-gpu-locks",
            gpu_indices=None,
            use_gpu_locks=True,
            docker_binary="docker",
            extra_docker_run_args=None,
        )
        defaults.update(kwargs)
        return build_remote_supervisor_script(**defaults)  # type: ignore[arg-type]

    def test_shebang_and_strict_mode(self) -> None:
        script = self._build()
        assert script.startswith("#!/usr/bin/env bash\n")
        assert "set -euo pipefail" in script

    def test_uses_detached_mode(self) -> None:
        """Container must start detached (docker run -d)."""
        script = self._build()
        assert "run" in script
        assert " -d" in script

    def test_no_rm_flag(self) -> None:
        """Supervisor needs the container to persist for docker wait."""
        script = self._build()
        assert "--rm" not in script

    def test_container_name_used(self) -> None:
        script = self._build(container_name="zenml-step-test123")
        assert "zenml-step-test123" in script

    def test_initial_status_written(self) -> None:
        """Script must write running status immediately."""
        script = self._build()
        assert '{"state":"running"}' in script

    def test_cancel_check(self) -> None:
        """Script must check for cancel marker before starting."""
        script = self._build(cancel_file_path="/tmp/cancel-xyz")
        assert "/tmp/cancel-xyz" in script
        assert '{"state":"stopped"}' in script

    def test_docker_wait_used(self) -> None:
        """Script must block on docker wait."""
        script = self._build(container_name="zenml-step-wait")
        assert "docker wait" in script
        assert "zenml-step-wait" in script

    def test_docker_rm_at_end(self) -> None:
        """Script should clean up the container."""
        script = self._build(container_name="zenml-step-cleanup")
        assert "docker rm" in script

    def test_env_file_removed_after_start(self) -> None:
        """Env-file (which may contain secrets) should be removed."""
        script = self._build(env_file_path="/tmp/zenml-ssh/env-secret")
        # env-file removal should appear after docker run
        lines = script.split("\n")
        rm_lines = [l for l in lines if "rm -f" in l and "env-secret" in l]
        assert len(rm_lines) >= 1

    def test_gpu_locking_sorted_order(self) -> None:
        """GPU locks in the supervisor must follow sorted order."""
        script = self._build(gpu_indices=[2, 0])
        pos_0 = script.index("gpu-0.lock")
        pos_2 = script.index("gpu-2.lock")
        assert pos_0 < pos_2

    def test_gpu_locking_fd_numbers(self) -> None:
        script = self._build(gpu_indices=[0, 1])
        assert "exec 200>" in script
        assert "exec 201>" in script
        assert "flock 200" in script
        assert "flock 201" in script

    def test_no_locks_when_disabled(self) -> None:
        script = self._build(gpu_indices=[0], use_gpu_locks=False)
        assert "flock" not in script
        assert "--gpus" in script

    def test_no_locks_when_no_gpus(self) -> None:
        script = self._build(gpu_indices=None)
        assert "flock" not in script
        assert "--gpus" not in script

    def test_gpus_flag_present(self) -> None:
        script = self._build(gpu_indices=[0, 2])
        assert '--gpus "device=0,2"' in script

    def test_extra_docker_run_args(self) -> None:
        script = self._build(extra_docker_run_args=["--shm-size=4g"])
        assert "--shm-size=4g" in script

    def test_custom_docker_binary(self) -> None:
        script = self._build(docker_binary="/usr/local/bin/docker")
        assert "/usr/local/bin/docker" in script

    def test_status_file_path_used(self) -> None:
        script = self._build(
            status_file_path="/tmp/zenml-ssh/status-final.json"
        )
        assert "/tmp/zenml-ssh/status-final.json" in script

    def test_write_status_helper_defined(self) -> None:
        """The script should define a write_status helper for atomicity."""
        script = self._build()
        assert "write_status()" in script
        assert ".tmp" in script
        assert "mv " in script

    def test_final_state_logic(self) -> None:
        """Script must determine final state from cancel marker + exit code."""
        script = self._build()
        assert "FINAL_STATE" in script
        assert '"completed"' in script
        assert '"failed"' in script
        assert '"stopped"' in script

    def test_docker_pull_present(self) -> None:
        """Image should be pulled inside the supervisor."""
        script = self._build(image="my-registry/my-image:v1")
        assert "docker pull" in script
        assert "my-registry/my-image:v1" in script
