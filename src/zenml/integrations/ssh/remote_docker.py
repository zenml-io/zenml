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
"""Pure helpers for building Docker commands and GPU-locked wrapper scripts.

All functions in this module are side-effect-free: they take inputs and
return strings.  The actual execution happens over SSH in the step operator.
"""

import shlex
from typing import List, Mapping, Optional, Sequence


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

    Each line is ``KEY=VALUE``.  Values containing newlines or NUL bytes
    are rejected because the env-file format is line-based and ambiguous
    for multi-line values.

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


def build_remote_wrapper_script(
    *,
    image: str,
    entrypoint_command: Sequence[str],
    env_file_path: str,
    gpu_lock_dir: str,
    gpu_indices: Optional[Sequence[int]],
    use_gpu_locks: bool,
    docker_binary: str,
    extra_docker_run_args: Optional[Sequence[str]] = None,
) -> str:
    """Generate a bash script that acquires GPU locks then runs a container.

    The script uses file-descriptor-based flock to acquire one lock per
    GPU index in sorted order (deadlock avoidance via resource ordering).
    Locks are held for the lifetime of the docker run process and released
    automatically when the script exits.

    Args:
        image: Fully-qualified Docker image name (with registry and tag).
        entrypoint_command: The ZenML step entrypoint command as a list
            of arguments.
        env_file_path: Absolute path on the remote host to the env-file.
        gpu_lock_dir: Directory where per-GPU lock files are created.
        gpu_indices: Normalized GPU indices, or None for CPU-only.
        use_gpu_locks: Whether to acquire flock locks for the GPUs.
        docker_binary: Path to the docker binary on the remote host.
        extra_docker_run_args: Optional extra arguments for docker run.

    Returns:
        Complete bash script as a string.
    """
    parts: List[str] = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
    ]

    # Cleanup trap: remove the env-file (which may contain secrets) and
    # this script itself on exit, regardless of success/failure.
    parts.append(f"trap 'rm -f {shlex.quote(env_file_path)} \"$0\"' EXIT")
    parts.append("")

    # GPU locking section
    # Sort GPU indices to ensure deadlock-free lock acquisition order,
    # even if the caller forgot to normalize.
    if gpu_indices is not None:
        gpu_indices = sorted(set(gpu_indices))

    needs_locks = (
        gpu_indices is not None and len(gpu_indices) > 0 and use_gpu_locks
    )
    if needs_locks:
        assert gpu_indices is not None  # for type narrowing
        lock_dir_q = shlex.quote(gpu_lock_dir)
        parts.append(f"mkdir -p {lock_dir_q}")
        parts.append("")

        # Open one FD per GPU lock file and acquire each lock.
        # FDs start at 200 to avoid clashing with stdin/stdout/stderr
        # and any other FDs the shell may have open.
        for fd_offset, gpu_idx in enumerate(gpu_indices):
            fd = 200 + fd_offset
            lock_path = f"{gpu_lock_dir}/gpu-{gpu_idx}.lock"
            lock_path_q = shlex.quote(lock_path)
            parts.append(f"exec {fd}>{lock_path_q}")
            parts.append(f"flock {fd}")
        parts.append("")

    # Build the docker run command
    docker_cmd_parts: List[str] = [
        docker_binary,
        "run",
        "--rm",
        f"--env-file {shlex.quote(env_file_path)}",
    ]

    if gpu_indices is not None and len(gpu_indices) > 0:
        gpus_value = build_docker_gpus_flag(gpu_indices)
        docker_cmd_parts.append(f"--gpus {gpus_value}")

    if extra_docker_run_args:
        for arg in extra_docker_run_args:
            docker_cmd_parts.append(shlex.quote(arg))

    docker_cmd_parts.append(shlex.quote(image))
    for arg in entrypoint_command:
        docker_cmd_parts.append(shlex.quote(arg))

    # Use exec so docker run replaces the shell process, ensuring
    # signals (SIGTERM, SIGINT) reach the container directly.
    parts.append("exec " + " \\\n  ".join(docker_cmd_parts))
    parts.append("")

    return "\n".join(parts)
