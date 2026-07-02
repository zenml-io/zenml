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
"""SSH integration utilities."""

import re
import shlex
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional, Sequence

from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.container_registries.base_container_registry import (
        BaseContainerRegistry,
    )
    from zenml.integrations.ssh.ssh_client import SSHClient

logger = get_logger(__name__)

# Allow only absolute POSIX/Windows paths in bind mounts so settings can't
# inject extra Compose/shell tokens.
_MOUNT_PATH_PATTERN = re.compile(r"^(/[^:\n]*|[A-Za-z]:\\[^:\n]*)$")


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


def validate_mount_path(path: str) -> str:
    """Validate a bind-mount path against injection.

    Args:
        path: The host or container path.

    Returns:
        The validated path.

    Raises:
        RuntimeError: If the path is not a plain absolute path.
    """
    if not _MOUNT_PATH_PATTERN.match(path):
        raise RuntimeError(
            f"Invalid mount path {path!r}: only absolute POSIX or Windows "
            "paths without ':' are allowed."
        )
    return path


def build_mount_mappings(mounts: Mapping[str, str]) -> List[str]:
    """Build validated host:container bind-mount mappings.

    Args:
        mounts: Mapping of host paths to container paths.

    Returns:
        List of validated "host:container" mapping strings.
    """
    return [
        f"{validate_mount_path(host)}:{validate_mount_path(container)}"
        for host, container in mounts.items()
    ]


def build_compose_gpu_deploy(gpu_indices: Sequence[int]) -> Dict[str, Any]:
    """Build the Compose deploy section reserving the given GPUs.

    Args:
        gpu_indices: GPU device indices to reserve.

    Returns:
        A Compose service deploy section.
    """
    device_ids = [str(i) for i in normalize_gpu_indices(gpu_indices)]
    return {
        "resources": {
            "reservations": {
                "devices": [
                    {
                        "driver": "nvidia",
                        "device_ids": device_ids,
                        "capabilities": ["gpu"],
                    }
                ]
            }
        }
    }


def build_docker_run_command(
    *,
    docker_binary: str,
    image: str,
    args: Sequence[str],
    container_name: str,
    env_file: Optional[str] = None,
    network: Optional[str] = None,
    entrypoint: Optional[str] = None,
    gpu_indices: Optional[Sequence[int]] = None,
    mounts: Optional[Mapping[str, str]] = None,
    extra_args: Optional[Sequence[str]] = None,
) -> str:
    """Build a detached ``docker run`` command.

    Args:
        docker_binary: Path to the Docker binary on the remote host.
        image: Fully-qualified image to run.
        args: Arguments passed after the image.
        container_name: Container name.
        env_file: Path to a Docker env-file.
        network: Docker network mode.
        entrypoint: Entrypoint override.
        gpu_indices: GPU device indices to attach, or None for CPU.
        mounts: Host-path to container-path bind mounts.
        extra_args: Additional `docker run` arguments, inserted before the
            image name.

    Returns:
        The full ``docker run -d`` command string.
    """
    parts: List[str] = [
        shlex.quote(docker_binary),
        "run",
        "-d",
        "--name",
        shlex.quote(container_name),
    ]
    if network:
        parts += ["--network", shlex.quote(network)]
    if env_file:
        parts += ["--env-file", shlex.quote(env_file)]
    if gpu_indices:
        # The flag value carries its own quotes and is interpreted by the
        # remote shell, e.g. --gpus "device=0,1".
        parts += [
            "--gpus",
            build_docker_gpus_flag(normalize_gpu_indices(gpu_indices)),
        ]
    for mapping in build_mount_mappings(mounts or {}):
        parts += ["-v", shlex.quote(mapping)]
    if extra_args:
        parts += [shlex.quote(arg) for arg in extra_args]
    if entrypoint:
        parts += ["--entrypoint", shlex.quote(entrypoint)]
    parts.append(shlex.quote(image))
    parts += [shlex.quote(arg) for arg in args]
    return " ".join(parts)


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


def get_free_disk_bytes(ssh: "SSHClient", remote_path: str) -> Optional[int]:
    """Get free disk space on the filesystem holding a remote path.

    Args:
        ssh: An open SSH connection.
        remote_path: An existing path on the remote host.

    Returns:
        Free bytes available to a non-root user, or None if the SFTP server
        does not support statvfs.
    """
    with ssh.sftp() as sftp:
        try:
            # statvfs is a paramiko SFTP extension present at runtime but
            # missing from the type stubs.
            stats = sftp.statvfs(remote_path)  # type: ignore[attr-defined]
            return int(stats.f_bavail * stats.f_frsize)
        except Exception:
            logger.debug(
                "Could not query free disk space on the remote host via "
                "SFTP statvfs.",
                exc_info=True,
            )
            return None


def run_preflight_checks(ssh: "SSHClient", docker_binary: str) -> None:
    """Verify the remote host has the required tools installed.

    Args:
        ssh: The open SSH connection.
        docker_binary: Path to the Docker binary on the remote host.

    Raises:
        RuntimeError: If a required tool is missing.
    """
    result = ssh.exec(f"{shlex.quote(docker_binary)} --version")
    if result.exit_code != 0:
        raise RuntimeError(
            f"Preflight check failed: Docker is not available on "
            f"host. Install Docker on the remote host: "
            f"https://docs.docker.com/engine/install/\n"
            f"stderr: {result.stderr.strip()}"
        )
    logger.debug("Preflight OK: Docker -> %s", result.stdout.strip())


def check_remote_disk(
    ssh: "SSHClient",
    remote_path: str,
    minimum_free_disk_gb: float,
) -> None:
    """Fail fast if the remote host is low on disk for the given path.

    Args:
        ssh: The open SSH connection.
        remote_path: An existing remote path on the filesystem to check.
        minimum_free_disk_gb: Minimum free space required, in GB. Values of 0
            or below disable the check.

    Raises:
        RuntimeError: If free disk is below minimum_free_disk_gb.
    """
    if minimum_free_disk_gb <= 0:
        return
    free_bytes = get_free_disk_bytes(ssh, remote_path)
    if free_bytes is None:
        # SFTP statvfs unsupported on this host; skip rather than block.
        return
    free_gb = free_bytes / (1024**3)
    if free_gb < minimum_free_disk_gb:
        raise RuntimeError(
            f"The remote host has only {free_gb:.1f} GB free on "
            f"the filesystem holding {remote_path}, below the required "
            f"{minimum_free_disk_gb:.1f} GB. The SSH integration stores a "
            f"Docker image per pipeline version, which accumulates over time. "
            f"Free space on the host (e.g. `docker image prune -a`), grow the "
            f"disk, or lower `minimum_free_disk_gb`."
        )


def docker_login(
    ssh: "SSHClient",
    container_registry: "BaseContainerRegistry",
    docker_binary: str,
) -> None:
    """Log the remote Docker into the container registry.

    Args:
        ssh: The open SSH connection.
        container_registry: The container registry to authenticate against.
        docker_binary: Path to the Docker binary on the remote host.

    Raises:
        RuntimeError: If registry credentials are missing or the remote
            `docker login` fails.
    """
    if not container_registry.credentials:
        raise RuntimeError(
            "The container registry in the stack has no credentials or "
            "service connector configured, but `authenticate_docker` "
            "is enabled. Configure registry credentials or disable "
            "`authenticate_docker`."
        )
    username, password = container_registry.credentials
    # --password-stdin keeps the password out of docker's argv. The remote
    # shell still handles it briefly, so users must opt in explicitly.
    command = (
        f"printf %s {shlex.quote(password)} | "
        f"{shlex.quote(docker_binary)} login -u {shlex.quote(username)} "
        f"--password-stdin {shlex.quote(container_registry.config.uri)}"
    )
    result = ssh.exec(command)
    if result.exit_code != 0:
        raise RuntimeError(
            f"`docker login` failed on host: {result.stderr or result.stdout}"
        )


def prepare_remote_workdir(
    ssh: "SSHClient",
    *,
    docker_binary: str,
    workdir: str,
    minimum_free_disk_gb: float,
    cleanup_command: Optional[str] = None,
    container_registry: Optional["BaseContainerRegistry"] = None,
) -> None:
    """Run preflight checks and prepare a remote working directory.

    Args:
        ssh: The open SSH connection.
        docker_binary: Path to the Docker binary on the remote host.
        workdir: Remote directory to create and disk-check.
        minimum_free_disk_gb: Minimum free space required, in GB.
        cleanup_command: Command removing stale files, or None to skip.
        container_registry: Container registry to authenticate Docker against,
            or None to skip.

    Raises:
        RuntimeError: If a required tool is missing or a remote command fails.
    """
    run_preflight_checks(ssh=ssh, docker_binary=docker_binary)
    mkdir = ssh.exec(f"mkdir -p {shlex.quote(workdir)}")
    if mkdir.exit_code != 0:
        raise RuntimeError(
            f"Failed to create remote directory {workdir} on "
            f"host: {mkdir.stderr}"
        )
    check_remote_disk(
        ssh=ssh,
        remote_path=workdir,
        minimum_free_disk_gb=minimum_free_disk_gb,
    )
    if cleanup_command is not None:
        cleanup = ssh.exec(cleanup_command)
        if cleanup.exit_code != 0:
            logger.warning(
                "Failed to clean old SSH files on host: %s",
                cleanup.stderr or cleanup.stdout,
            )
    if container_registry is not None:
        docker_login(
            ssh=ssh,
            container_registry=container_registry,
            docker_binary=docker_binary,
        )
