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
"""Run:AI training workload settings."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

RunAIServiceType = Literal["LoadBalancer", "NodePort", "ClusterIP"]
RunAIExternalURLAuthorizationType = Literal[
    "authenticatedUsers", "authorizedUsers", "authorizedGroups"
]
RunAISeccompProfileType = Literal["RuntimeDefault", "Unconfined", "Localhost"]
RunAIUIDGIDSource = Literal["fromTheImage", "fromIdpToken", "custom"]


def _validate_absolute_path(value: str) -> str:
    """Validate that a container mount path is absolute."""
    if not value or not value.startswith("/"):
        raise ValueError("Mount paths must be absolute paths.")
    return value


class RunAIPVCMountSettings(BaseModel):
    """Settings for a Run:AI PVC storage mount."""

    name: Optional[str] = Field(default=None, description="Run:AI mount name.")
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
    exclude: Optional[bool] = Field(
        default=None, description="Whether to exclude this mount."
    )

    _validate_path = field_validator("path")(_validate_absolute_path)


class RunAIConfigMapMountSettings(BaseModel):
    """Settings for a Run:AI ConfigMap storage mount."""

    name: Optional[str] = Field(default=None, description="Run:AI mount name.")
    config_map: str = Field(description="Name of the existing ConfigMap.")
    mount_path: str = Field(
        description="Absolute container path for the ConfigMap mount."
    )
    sub_path: Optional[str] = Field(
        default=None, description="Optional sub-path within the ConfigMap."
    )
    default_mode: Optional[str] = Field(
        default=None,
        min_length=4,
        max_length=4,
        description="Four-character default file mode for mounted ConfigMap files, e.g. '0644'.",
    )
    exclude: Optional[bool] = Field(
        default=None, description="Whether to exclude this mount."
    )

    _validate_mount_path = field_validator("mount_path")(
        _validate_absolute_path
    )


class RunAISecretMountSettings(BaseModel):
    """Settings for a Run:AI Secret storage mount."""

    name: Optional[str] = Field(default=None, description="Run:AI mount name.")
    mount_path: str = Field(
        description="Absolute container path for the Secret mount."
    )
    default_mode: Optional[str] = Field(
        default=None,
        min_length=4,
        max_length=4,
        description="Four-character default file mode for mounted Secret files, e.g. '0644'.",
    )
    secret: str = Field(description="Name of the existing Secret.")
    exclude: Optional[bool] = Field(
        default=None, description="Whether to exclude this mount."
    )

    _validate_mount_path = field_validator("mount_path")(
        _validate_absolute_path
    )


class RunAINFSMountSettings(BaseModel):
    """Settings for a Run:AI NFS storage mount."""

    name: Optional[str] = Field(default=None, description="Run:AI mount name.")
    path: str = Field(description="Path exported by the NFS server.")
    read_only: Optional[bool] = Field(
        default=None, description="Whether the mount is read-only."
    )
    server: str = Field(description="NFS server hostname or address.")
    mount_path: str = Field(
        description="Absolute container path for the NFS mount."
    )
    exclude: Optional[bool] = Field(
        default=None, description="Whether to exclude this mount."
    )

    _validate_mount_path = field_validator("mount_path")(
        _validate_absolute_path
    )


class RunAIS3MountSettings(BaseModel):
    """Settings for a Run:AI S3 storage mount."""

    name: Optional[str] = Field(default=None, description="Run:AI mount name.")
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
    exclude: Optional[bool] = Field(
        default=None, description="Whether to exclude this mount."
    )

    _validate_path = field_validator("path")(_validate_absolute_path)


class RunAIHostPathMountSettings(BaseModel):
    """Settings for a Run:AI HostPath storage mount."""

    name: Optional[str] = Field(default=None, description="Run:AI mount name.")
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
    exclude: Optional[bool] = Field(
        default=None, description="Whether to exclude this mount."
    )

    _validate_path = field_validator("path")(_validate_absolute_path)
    _validate_mount_path = field_validator("mount_path")(
        _validate_absolute_path
    )


class RunAIGitMountSettings(BaseModel):
    """Settings for a Run:AI Git storage mount."""

    name: Optional[str] = Field(default=None, description="Run:AI mount name.")
    repository: str = Field(description="Git repository URL.")
    branch: Optional[str] = Field(default=None, description="Git branch.")
    revision: Optional[str] = Field(default=None, description="Git revision.")
    path: str = Field(description="Absolute container path for the Git mount.")
    password_secret: Optional[str] = Field(
        default=None,
        description="Secret that stores Git credentials.",
    )
    secret_key_of_user: Optional[str] = Field(
        default=None, description="Secret key containing the Git username."
    )
    secret_key_of_password: Optional[str] = Field(
        default=None, description="Secret key containing the Git password."
    )
    exclude: Optional[bool] = Field(
        default=None, description="Whether to exclude this mount."
    )
    secret_ref: Optional[str] = Field(
        default=None,
        description="Run:AI secret reference for Git credentials.",
    )

    _validate_path = field_validator("path")(_validate_absolute_path)


class RunAISecurityContextSettings(BaseModel):
    """Settings for the Run:AI workload security context."""

    allow_privilege_escalation: Optional[bool] = Field(default=None)
    capabilities: Optional[List[str]] = Field(default=None)
    host_ipc: Optional[bool] = Field(default=None)
    host_network: Optional[bool] = Field(default=None)
    read_only_root_filesystem: Optional[bool] = Field(default=None)
    run_as_gid: Optional[int] = Field(default=None, ge=0)
    run_as_non_root: Optional[bool] = Field(default=None)
    run_as_uid: Optional[int] = Field(default=None, ge=0)
    seccomp_profile_type: Optional[RunAISeccompProfileType] = Field(
        default=None
    )
    supplemental_groups: Optional[List[int]] = Field(
        default=None,
        description="Supplemental group IDs. These are serialized as a semicolon-separated string for Run:AI.",
    )
    uid_gid_source: Optional[RunAIUIDGIDSource] = Field(default=None)

    @field_validator("supplemental_groups")
    @classmethod
    def _validate_supplemental_groups(
        cls, value: Optional[List[int]]
    ) -> Optional[List[int]]:
        """Validate supplemental group IDs."""
        if value is None:
            return None
        if any(group < 0 for group in value):
            raise ValueError(
                "supplemental_groups must contain non-negative IDs."
            )
        return value


class RunAIPortSettings(BaseModel):
    """Settings for exposing a container port on the Run:AI workload."""

    container: int = Field(ge=1, le=65535)
    service_type: Optional[RunAIServiceType] = Field(default=None)
    external: Optional[int] = Field(
        default=None,
        ge=1,
        le=65535,
        description="External service port that maps to the container port.",
    )
    tool_type: Optional[str] = Field(default=None)
    tool_name: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default=None)
    exclude: Optional[bool] = Field(default=None)


class RunAIExternalURLSettings(BaseModel):
    """Settings for exposing a Run:AI workload external URL."""

    container: int = Field(ge=1, le=65535)
    url: Optional[str] = Field(default=None)
    authorization_type: Optional[RunAIExternalURLAuthorizationType] = Field(
        default=None
    )
    authorized_users: Optional[List[str]] = Field(default=None)
    authorized_groups: Optional[List[str]] = Field(default=None)
    tool_type: Optional[str] = Field(default=None)
    tool_name: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default=None)
    exclude: Optional[bool] = Field(default=None)
