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
"""Tests for SSH step operator remote Docker helpers.

These are pure-function tests that validate GPU normalization, Docker flag
construction, and env-file serialization without needing SSH, Docker, or GPUs.
"""

import pytest

from zenml.integrations.ssh.remote_docker import (
    build_docker_gpus_flag,
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
