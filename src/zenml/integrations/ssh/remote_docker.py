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

Two script builders are provided:

- ``build_remote_wrapper_script`` generates a **foreground** script where
  ``exec docker run`` replaces the shell.  Used by the legacy blocking
  ``launch()`` path.

- ``build_remote_supervisor_script`` generates a **background** supervisor
  that starts Docker detached, blocks on ``docker wait`` (holding GPU
  locks), and writes a JSON status file.  Used by the async
  ``submit()``/``get_status()``/``cancel()`` path.
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


def _build_gpu_locking_lines(
    gpu_indices: Optional[Sequence[int]],
    gpu_lock_dir: str,
    use_gpu_locks: bool,
) -> List[str]:
    """Build bash lines that acquire per-GPU flock locks.

    Locks are acquired in index order (deadlock avoidance via resource
    ordering).  File descriptors start at 200 to avoid clashing with
    stdin/stdout/stderr.

    Args:
        gpu_indices: Normalized GPU indices, or None for CPU-only.
        gpu_lock_dir: Directory where per-GPU lock files are created.
        use_gpu_locks: Whether to actually acquire locks.

    Returns:
        List of bash script lines (may be empty if no locking is needed).
    """
    if not gpu_indices or not use_gpu_locks:
        return []

    # Sort for deadlock-free lock acquisition order.
    gpu_indices = sorted(set(gpu_indices))

    lock_dir_q = shlex.quote(gpu_lock_dir)
    lines: List[str] = [f"mkdir -p {lock_dir_q}", ""]

    for fd_offset, gpu_idx in enumerate(gpu_indices):
        fd = 200 + fd_offset
        lock_path_q = shlex.quote(f"{gpu_lock_dir}/gpu-{gpu_idx}.lock")
        lines.append(f"exec {fd}>{lock_path_q}")
        lines.append(f"flock {fd}")
    lines.append("")

    return lines


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

    parts.extend(
        _build_gpu_locking_lines(gpu_indices, gpu_lock_dir, use_gpu_locks)
    )

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


def build_remote_supervisor_script(
    *,
    image: str,
    entrypoint_command: Sequence[str],
    env_file_path: str,
    status_file_path: str,
    cancel_file_path: str,
    container_name: str,
    gpu_lock_dir: str,
    gpu_indices: Optional[Sequence[int]],
    use_gpu_locks: bool,
    docker_binary: str,
    extra_docker_run_args: Optional[Sequence[str]] = None,
) -> str:
    """Generate a supervisor script for async SSH step execution.

    Unlike ``build_remote_wrapper_script`` (which ``exec``s into Docker
    and blocks), this script runs **in the background** and:

    1. Writes an initial ``{"state":"running"}`` status file.
    2. Pulls the Docker image.
    3. Acquires GPU flock locks (same deadlock-free ordering).
    4. Starts the container **detached** (``docker run -d``).
    5. Blocks on ``docker wait`` (locks held for the container lifetime).
    6. Writes a final status file (``completed``, ``failed``, or
       ``stopped`` if a cancel marker was detected).
    7. Removes the container and temporary files.

    The status file is the durable state store that ``get_status()`` reads
    over SSH.  A cancel marker file enables cooperative cancellation.

    Args:
        image: Fully-qualified Docker image name (with registry and tag).
        entrypoint_command: The ZenML step entrypoint command as a list
            of arguments.
        env_file_path: Absolute path on the remote host to the env-file.
        status_file_path: Absolute path for the JSON status file.
        cancel_file_path: Absolute path for the cancel marker file.
        container_name: Deterministic Docker container name.
        gpu_lock_dir: Directory where per-GPU lock files are created.
        gpu_indices: Normalized GPU indices, or None for CPU-only.
        use_gpu_locks: Whether to acquire flock locks for the GPUs.
        docker_binary: Path to the docker binary on the remote host.
        extra_docker_run_args: Optional extra arguments for docker run.

    Returns:
        Complete bash script as a string.
    """
    status_q = shlex.quote(status_file_path)
    cancel_q = shlex.quote(cancel_file_path)
    env_q = shlex.quote(env_file_path)
    name_q = shlex.quote(container_name)
    docker_q = shlex.quote(docker_binary)

    parts: List[str] = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
    ]

    # Helper: write JSON status file atomically (write-then-rename).
    parts.append("write_status() {")
    parts.append(f'  echo "$1" > {status_q}.tmp')
    parts.append(f"  mv {status_q}.tmp {status_q}")
    parts.append("}")
    parts.append("")

    # Cleanup trap: remove env-file and this script on exit.
    parts.append(f"trap 'rm -f {env_q} \"$0\"' EXIT")
    parts.append("")

    # Initial status.
    parts.append('write_status \'{"state":"running"}\'')
    parts.append("")

    # Early cancellation check.
    parts.append(f"if [ -f {cancel_q} ]; then")
    parts.append('  write_status \'{"state":"stopped"}\'')
    parts.append("  exit 0")
    parts.append("fi")
    parts.append("")

    # Pull the image.
    parts.append(f"{docker_q} pull {shlex.quote(image)}")
    parts.append("")

    parts.extend(
        _build_gpu_locking_lines(gpu_indices, gpu_lock_dir, use_gpu_locks)
    )

    # Build docker run command (detached, no --rm).
    docker_cmd_parts: List[str] = [
        docker_binary,
        "run",
        "-d",
        f"--name {name_q}",
        f"--env-file {env_q}",
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

    # Start container detached; capture container ID (unused but validates
    # that docker run succeeded).
    parts.append(" \\\n  ".join(docker_cmd_parts))
    parts.append("")

    # Remove env-file immediately to reduce secret exposure window.
    parts.append(f"rm -f {env_q}")
    parts.append("")

    # Block on docker wait (GPU locks held for the container lifetime).
    parts.append(f"EXIT_CODE=$({docker_q} wait {name_q}) || EXIT_CODE=1")
    parts.append("")

    # Determine final state.
    parts.append(f"if [ -f {cancel_q} ]; then")
    parts.append('  FINAL_STATE="stopped"')
    parts.append('elif [ "$EXIT_CODE" = "0" ]; then')
    parts.append('  FINAL_STATE="completed"')
    parts.append("else")
    parts.append('  FINAL_STATE="failed"')
    parts.append("fi")
    parts.append("")

    # Write final status as JSON (state + exit_code only; logs are
    # available via ``docker logs`` or the supervisor log file).
    parts.append(
        "write_status "
        '"$(printf \'{\\"state\\":\\"%s\\",\\"exit_code\\":%s}\\n\' '
        '"$FINAL_STATE" "$EXIT_CODE")"'
    )
    parts.append("")

    # Clean up container.
    parts.append(f"{docker_q} rm {name_q} >/dev/null 2>&1 || true")
    parts.append("")

    return "\n".join(parts)
