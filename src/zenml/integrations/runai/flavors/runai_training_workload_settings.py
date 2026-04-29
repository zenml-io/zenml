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
"""Run:AI training workload settings."""

import re
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

RunAIServiceType = Literal["LoadBalancer", "NodePort", "ClusterIP"]
RunAIExternalURLAuthorizationType = Literal[
    "authenticatedUsers", "authorizedUsers", "authorizedGroups"
]
RunAISeccompProfileType = Literal["RuntimeDefault", "Unconfined", "Localhost"]
RunAIUIDGIDSource = Literal["fromTheImage", "fromIdpToken", "custom"]
RunAITolerationOperator = Literal["Equal", "Exists"]
RunAITolerationEffect = Literal["NoSchedule", "PreferNoSchedule", "NoExecute"]

_OCTAL_MODE_RE = re.compile(r"^0[0-7]{3}$")


def _validate_absolute_path(value: str) -> str:
    if not value or not value.startswith("/"):
        raise ValueError("Mount paths must be absolute paths.")
    return value


def _validate_default_mode(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if not _OCTAL_MODE_RE.match(value):
        raise ValueError(
            "default_mode must be a four-character octal string like "
            "'0644' or '0400'."
        )
    return value


class RunAIBaseSettings(BaseModel):
    """Common base for Run:AI workload settings models.

    Forbids unknown fields so typos in user settings surface as
    validation errors rather than being silently dropped.
    """

    model_config = ConfigDict(extra="forbid")


class RunAIMountBase(RunAIBaseSettings):
    """Common fields for Run:AI workload storage mount settings."""

    name: Optional[str] = Field(default=None, description="Run:AI mount name.")
    exclude: Optional[bool] = Field(
        default=None, description="Whether to exclude this mount."
    )

    @property
    def container_mount_path(self) -> str:
        """The absolute container path where this mount is exposed.

        Returns:
            The absolute container mount path.
        """
        raise NotImplementedError


class RunAITolerationSettings(RunAIMountBase):
    """Settings for a Kubernetes toleration on a Run:AI workload."""

    key: Optional[str] = Field(
        default=None, description="Taint key that the toleration applies to."
    )
    operator: Optional[RunAITolerationOperator] = Field(
        default=None,
        description="Toleration operator. One of 'Equal' or 'Exists'.",
    )
    value: Optional[str] = Field(
        default=None,
        description="Taint value tolerated when operator='Equal'.",
    )
    effect: Optional[RunAITolerationEffect] = Field(
        default=None,
        description="Taint effect tolerated by the workload.",
    )


class RunAIPVCMountSettings(RunAIMountBase):
    """Settings for a Run:AI PVC storage mount."""

    path: str = Field(description="Absolute container path for the PVC mount.")
    existing_pvc: Optional[bool] = Field(
        default=True,
        description="Whether to use an existing persistent volume claim.",
    )
    claim_name: Optional[str] = Field(
        default=None,
        description="Name of the existing persistent volume claim.",
    )
    read_only: Optional[bool] = Field(
        default=None, description="Whether the mount is read-only."
    )
    ephemeral: Optional[bool] = Field(
        default=None, description="Whether the PVC should be ephemeral."
    )
    claim_info: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Run:AI claim information for dynamically created PVCs.",
    )
    data_sharing: Optional[bool] = Field(
        default=None, description="Whether to enable Run:AI data sharing."
    )

    _validate_path = field_validator("path")(_validate_absolute_path)

    @property
    def container_mount_path(self) -> str:
        """The absolute container path for this PVC mount.

        Returns:
            The absolute container mount path.
        """
        return self.path


class RunAIConfigMapMountSettings(RunAIMountBase):
    """Settings for a Run:AI ConfigMap storage mount."""

    config_map: str = Field(description="Name of the existing ConfigMap.")
    mount_path: str = Field(
        description="Absolute container path for the ConfigMap mount."
    )
    sub_path: Optional[str] = Field(
        default=None, description="Optional sub-path within the ConfigMap."
    )
    default_mode: Optional[str] = Field(
        default=None,
        description="Four-character octal default file mode for mounted ConfigMap files, e.g. '0644'.",
    )

    _validate_mount_path = field_validator("mount_path")(
        _validate_absolute_path
    )
    _validate_default_mode = field_validator("default_mode")(
        _validate_default_mode
    )

    @property
    def container_mount_path(self) -> str:
        """The absolute container path for this ConfigMap mount.

        Returns:
            The absolute container mount path.
        """
        return self.mount_path


class RunAISecretMountSettings(RunAIMountBase):
    """Settings for a Run:AI Secret storage mount."""

    mount_path: str = Field(
        description="Absolute container path for the Secret mount."
    )
    default_mode: Optional[str] = Field(
        default=None,
        description="Four-character octal default file mode for mounted Secret files, e.g. '0644'.",
    )
    secret: str = Field(description="Name of the existing Secret.")

    _validate_mount_path = field_validator("mount_path")(
        _validate_absolute_path
    )
    _validate_default_mode = field_validator("default_mode")(
        _validate_default_mode
    )

    @property
    def container_mount_path(self) -> str:
        """The absolute container path for this Secret mount.

        Returns:
            The absolute container mount path.
        """
        return self.mount_path


class RunAINFSMountSettings(RunAIMountBase):
    """Settings for a Run:AI NFS storage mount."""

    path: str = Field(description="Path exported by the NFS server.")
    read_only: Optional[bool] = Field(
        default=None, description="Whether the mount is read-only."
    )
    server: str = Field(description="NFS server hostname or address.")
    mount_path: str = Field(
        description="Absolute container path for the NFS mount."
    )

    _validate_mount_path = field_validator("mount_path")(
        _validate_absolute_path
    )

    @property
    def container_mount_path(self) -> str:
        """The absolute container path for this NFS mount.

        Returns:
            The absolute container mount path.
        """
        return self.mount_path


class RunAIS3MountSettings(RunAIMountBase):
    """Settings for a Run:AI S3 storage mount."""

    bucket: str = Field(description="S3 bucket name.")
    path: str = Field(description="Absolute container path for the S3 mount.")
    url: Optional[str] = Field(
        default=None, description="Optional S3 endpoint URL."
    )
    access_key_secret: Optional[str] = Field(
        default=None, description="Secret that stores S3 access credentials."
    )
    secret_key_of_access_key_id: Optional[str] = Field(
        default=None,
        description="Secret key containing the S3 access key ID.",
    )
    secret_key_of_secret_key: Optional[str] = Field(
        default=None,
        description="Secret key containing the S3 secret access key.",
    )

    _validate_path = field_validator("path")(_validate_absolute_path)

    @property
    def container_mount_path(self) -> str:
        """The absolute container path for this S3 mount.

        Returns:
            The absolute container mount path.
        """
        return self.path


class RunAIHostPathMountSettings(RunAIMountBase):
    """Settings for a Run:AI HostPath storage mount."""

    path: str = Field(description="Absolute path on the host node.")
    read_only: Optional[bool] = Field(
        default=None, description="Whether the mount is read-only."
    )
    mount_path: str = Field(
        description="Absolute container path for the HostPath mount."
    )
    mount_propagation: Optional[str] = Field(
        default=None, description="Kubernetes mount propagation mode."
    )

    _validate_path = field_validator("path")(_validate_absolute_path)
    _validate_mount_path = field_validator("mount_path")(
        _validate_absolute_path
    )

    @property
    def container_mount_path(self) -> str:
        """The absolute container path for this HostPath mount.

        Returns:
            The absolute container mount path.
        """
        return self.mount_path


class RunAISecurityContextSettings(RunAIMountBase):
    """Settings for the Run:AI workload security context."""

    allow_privilege_escalation: Optional[bool] = Field(
        default=None,
        description="Whether the container can gain more privileges than its parent process.",
    )
    capabilities: Optional[List[str]] = Field(
        default=None,
        description="Linux capabilities to add to the container, for example ['NET_ADMIN'].",
    )
    host_ipc: Optional[bool] = Field(
        default=None,
        description="Whether the workload shares the host IPC namespace.",
    )
    host_network: Optional[bool] = Field(
        default=None,
        description="Whether the workload uses the host network namespace.",
    )
    read_only_root_filesystem: Optional[bool] = Field(
        default=None,
        description="Whether the container root filesystem is read-only.",
    )
    run_as_gid: Optional[int] = Field(
        default=None,
        ge=0,
        description="GID to run the container as. Used together with uid_gid_source='custom'.",
    )
    run_as_non_root: Optional[bool] = Field(
        default=None,
        description="Whether the container must run as a non-root user.",
    )
    run_as_uid: Optional[int] = Field(
        default=None,
        ge=0,
        description="UID to run the container as. Used together with uid_gid_source='custom'.",
    )
    seccomp_profile_type: Optional[RunAISeccompProfileType] = Field(
        default=None,
        description="Seccomp profile type. One of 'RuntimeDefault', 'Unconfined', or 'Localhost'.",
    )
    supplemental_groups: Optional[List[int]] = Field(
        default=None,
        description="Supplemental group IDs. These are serialized as a semicolon-separated string for Run:AI.",
    )
    uid_gid_source: Optional[RunAIUIDGIDSource] = Field(
        default=None,
        description="Source of the UID/GID. One of 'fromTheImage', 'fromIdpToken', or 'custom'.",
    )

    @field_validator("supplemental_groups")
    @classmethod
    def _validate_supplemental_groups(
        cls, value: Optional[List[int]]
    ) -> Optional[List[int]]:
        if value is None:
            return None
        if any(group < 0 for group in value):
            raise ValueError(
                "supplemental_groups must contain non-negative IDs."
            )
        return value


class RunAIPortSettings(RunAIMountBase):
    """Settings for exposing a container port on the Run:AI workload."""

    container: int = Field(
        ge=1,
        le=65535,
        description="Container port to expose. Must be between 1 and 65535.",
    )
    service_type: Optional[RunAIServiceType] = Field(
        default=None,
        description="Kubernetes service type. One of 'LoadBalancer', 'NodePort', or 'ClusterIP'.",
    )
    external: Optional[int] = Field(
        default=None,
        ge=1,
        le=65535,
        description="External service port that maps to the container port.",
    )
    tool_type: Optional[str] = Field(
        default=None,
        description="Optional Run:AI tool type for the exposed port (for example 'jupyter').",
    )
    tool_name: Optional[str] = Field(
        default=None,
        description="Optional Run:AI tool name shown in the dashboard.",
    )
    name: Optional[str] = Field(
        default=None,
        description="Optional name for the port declaration.",
    )
    exclude: Optional[bool] = Field(
        default=None,
        description="Whether to exclude this port from the workload spec.",
    )


class RunAIExternalURLSettings(RunAIMountBase):
    """Settings for exposing a Run:AI workload external URL."""

    container: int = Field(
        ge=1,
        le=65535,
        description="Container port to expose externally. Must be between 1 and 65535.",
    )
    url: Optional[str] = Field(
        default=None,
        description="Optional explicit external URL to use instead of a generated one.",
    )
    authorization_type: Optional[RunAIExternalURLAuthorizationType] = Field(
        default=None,
        description="External URL authorization mode. One of 'authenticatedUsers', 'authorizedUsers', or 'authorizedGroups'.",
    )
    authorized_users: Optional[List[str]] = Field(
        default=None,
        description="List of usernames authorized to access the external URL when authorization_type='authorizedUsers'.",
    )
    authorized_groups: Optional[List[str]] = Field(
        default=None,
        description="List of group names authorized to access the external URL when authorization_type='authorizedGroups'.",
    )
    tool_type: Optional[str] = Field(
        default=None,
        description="Optional Run:AI tool type associated with the URL.",
    )
    tool_name: Optional[str] = Field(
        default=None,
        description="Optional Run:AI tool name shown in the dashboard.",
    )
    name: Optional[str] = Field(
        default=None,
        description="Optional name for the external URL declaration.",
    )
    exclude: Optional[bool] = Field(
        default=None,
        description="Whether to exclude this external URL from the workload spec.",
    )
