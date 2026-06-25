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
"""Shared SSH configuration."""

from typing import Dict, List, Optional

from pydantic import Field

from zenml.config.base_settings import BaseSettings
from zenml.utils.secret_utils import PlainSerializedSecretStr, SecretField


class SSHConnectionConfigMixin(BaseSettings):
    """Shared SSH connection configuration."""

    hostname: str = Field(
        min_length=1,
        description="Hostname or IP address of the remote SSH server. Must be "
        "reachable from the machine submitting the pipeline",
    )
    username: str = Field(
        description="SSH username for authentication on the remote host",
    )
    port: int = Field(
        default=22,
        ge=1,
        le=65535,
        description="SSH port on the remote host. Standard SSH port is 22",
    )
    ssh_key_path: Optional[str] = Field(
        default=None,
        description="Path to the SSH private key file on the submitting "
        "machine. Supports RSA, Ed25519, and ECDSA keys",
    )
    ssh_private_key: Optional[PlainSerializedSecretStr] = SecretField(
        default=None,
        description="SSH private key content, used instead of ssh_key_path "
        "when the key is stored in a ZenML secret. Supports {{secret.key}} "
        "references",
    )
    ssh_key_passphrase: Optional[PlainSerializedSecretStr] = SecretField(
        default=None,
        description="Passphrase for an encrypted SSH private key. Leave unset "
        "if the key is not encrypted",
    )
    verify_host_key: bool = Field(
        default=True,
        description="Require the remote host key to be present in known_hosts "
        "(paramiko RejectPolicy). Set to False to auto-accept unknown host "
        "keys (less secure, convenient for ephemeral hosts)",
    )
    known_hosts_path: Optional[str] = Field(
        default=None,
        description="Path to a known_hosts file for host-key verification. "
        "Defaults to ~/.ssh/known_hosts. Only used when verify_host_key is "
        "True",
    )
    connection_timeout: float = Field(
        default=10.0,
        gt=0,
        description="Timeout in seconds for establishing the SSH connection. "
        "Increase for high-latency links",
    )
    keepalive_interval: int = Field(
        default=30,
        ge=0,
        description="Interval in seconds between SSH keepalive packets, so "
        "long-running launches survive idle timeouts. Set to 0 to disable",
    )


class BaseSSHComponentConfig(SSHConnectionConfigMixin):
    """Shared SSH component configuration."""

    remote_workdir: str = Field(
        default="/tmp/zenml-ssh",
        description="Base directory on the remote host's filesystem for "
        "per-run files. Created automatically",
    )
    docker_binary: str = Field(
        default="docker",
        description="Path to the Docker binary on the remote host. Override "
        "if Docker is installed in a non-standard location",
    )
    authenticate_docker: bool = Field(
        default=False,
        description="Run `docker login` on the remote host using the active "
        "stack's container registry credentials before pulling images, so "
        "private images can be pulled",
    )
    cleanup_old_files: bool = Field(
        default=True,
        description="Remove files left in remote_workdir that are older than "
        "7 days. These accumulate when launches crash before cleanup runs",
    )
    minimum_free_disk_gb: float = Field(
        default=5.0,
        ge=0,
        description="Pre-flight guard that fails a submission if the "
        "remote_workdir filesystem has less free disk than this (in GB). Set "
        "to 0 to disable the check. Example: 10.0 for image-heavy pipelines",
    )


class BaseSSHComponentSettings(BaseSettings):
    """Shared SSH component settings."""

    mounts: Dict[str, str] = Field(
        default_factory=dict,
        description="Host-path to container-path bind mounts applied to every "
        "container. Keys are absolute paths on the remote host, values are "
        "absolute paths inside the container. Example: "
        "{'/data/datasets': '/datasets'}",
    )
    gpu_indices: Optional[List[int]] = Field(
        default=None,
        description="GPU device indices to expose inside the container via the "
        "Docker --gpus flag, or None for CPU-only execution. Give concurrent "
        "workloads on the same host distinct indices to avoid oversubscribing "
        "a GPU",
    )
    docker_run_args: Optional[List[str]] = Field(
        default=None,
        description="Additional arguments for the docker run command, inserted "
        "before the image name.",
    )
