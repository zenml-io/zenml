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
"""Pure helpers for building Docker commands and env-files."""

from typing import List, Mapping, Sequence


def normalize_gpu_indices(indices: Sequence[int]) -> List[int]:
    """Normalize GPU indices into a sorted, unique, validated list.

    Args:
        indices: GPU device indices (may be unsorted or contain duplicates).

    Returns:
        Sorted unique list of non-negative GPU indices.

    Raises:
        ValueError: If any index is negative.
    """
    for idx in indices:
        if idx < 0:
            raise ValueError(
                f"GPU index must be non-negative, got {idx}. "
                "Use the device indices reported by nvidia-smi on the "
                "remote host."
            )
    return sorted(set(indices))


def build_docker_gpus_flag(gpu_indices: Sequence[int]) -> str:
    """Build the value for the Docker --gpus flag.

    Args:
        gpu_indices: Normalized (sorted, unique) GPU device indices.

    Returns:
        String suitable for ``docker run --gpus '<value>'``, e.g.
        ``'"device=0,2"'`` (outer single-quotes added by the caller).

    Raises:
        ValueError: If no GPU indices are provided.
    """
    if not gpu_indices:
        raise ValueError("gpu_indices must contain at least one index.")
    device_list = ",".join(str(i) for i in gpu_indices)
    return f'"device={device_list}"'


def serialize_env_for_docker_env_file(env: Mapping[str, str]) -> str:
    """Serialize environment variables into Docker --env-file format.

    Args:
        env: Mapping of environment variable names to values.

    Returns:
        String content suitable for writing to a Docker env-file.

    Raises:
        ValueError: If any key or value contains forbidden characters.
    """
    lines: List[str] = []
    for key, value in sorted(env.items()):
        if "\x00" in key or "=" in key:
            raise ValueError(
                f"Environment variable name {key!r} contains forbidden "
                "characters (NUL or '='). This would corrupt the env-file."
            )
        if "\x00" in value or "\n" in value:
            raise ValueError(
                f"Environment variable {key!r} has a value containing "
                "a newline or NUL character. Docker env-file format is "
                "line-based and cannot represent multi-line values safely. "
                "Consider base64-encoding the value."
            )
        lines.append(f"{key}={value}")
    return "\n".join(lines) + "\n" if lines else ""
