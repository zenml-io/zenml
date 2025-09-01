#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Capture policy models and resolution for pipeline serving."""

import os
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class CapturePolicyMode(str, Enum):
    """Capture policy modes for pipeline run tracking."""

    NONE = "none"
    METADATA = "metadata"
    ERRORS_ONLY = "errors_only"
    SAMPLED = "sampled"
    FULL = "full"


class ArtifactCaptureMode(str, Enum):
    """Artifact capture modes for output persistence."""

    NONE = "none"
    ERRORS_ONLY = "errors_only"
    SAMPLED = "sampled"
    FULL = "full"


class CapturePolicy(BaseModel):
    """Policy configuration for pipeline run and artifact capture."""

    mode: CapturePolicyMode = Field(
        default=CapturePolicyMode.FULL,
        description="Controls what level of run tracking is performed. 'metadata' "
        "creates run/step records with basic metadata only. 'errors_only' adds error "
        "context on failures. 'sampled' captures payloads/outputs for a fraction of "
        "calls. 'full' captures all payloads and outputs",
    )

    artifacts: ArtifactCaptureMode = Field(
        default=ArtifactCaptureMode.NONE,
        description="Controls artifact persistence for step outputs. Independent of "
        "'mode' setting. 'none' stores no artifacts, 'errors_only' persists failed "
        "outputs, 'sampled' persists outputs for sampled runs, 'full' persists all outputs",
    )

    sample_rate: float = Field(
        default=0.1,
        description="Sampling rate for 'sampled' mode (0.0 to 1.0). Determines the "
        "fraction of pipeline runs that will have full payload and artifact capture",
        ge=0.0,
        le=1.0,
    )

    max_bytes: int = Field(
        default=262144,  # 256KB
        description="Maximum size in bytes for payload data stored in run metadata. "
        "Larger payloads will be truncated. Applies to input parameters and output previews",
        ge=1024,  # Min 1KB
        le=10485760,  # Max 10MB
    )

    redact: List[str] = Field(
        default_factory=lambda: [
            # Authentication & Authorization
            "password",
            "passwd",
            "pwd",
            "token",
            "access_token",
            "refresh_token",
            "id_token",
            "auth_token",
            "bearer_token",
            "api_key",
            "apikey",
            "authorization",
            "auth",
            "credential",
            "credentials",
            "secret",
            "private_key",
            "key",
            # OAuth & SSO
            "oauth",
            "client_secret",
            "client_id",
            # Database & Connection strings
            "connection_string",
            "conn_str",
            "database_url",
            "db_password",
            "db_pass",
            # Security & Encryption
            "encryption_key",
            "private",
            "certificate",
            "cert",
            "signature",
            "hash",
            # Session & Cookies
            "session",
            "session_id",
            "cookie",
            "csrf",
            "xsrf",
            # Infrastructure
            "aws_secret_access_key",
            "gcp_service_account",
            "azure_client_secret",
        ],
        description="List of field names to redact from payload metadata. Case-insensitive "
        "substring matching applied to both top-level and nested field names. Security-focused "
        "defaults include common authentication, authorization, and credential patterns",
    )

    retention_days: Optional[int] = Field(
        default=None,
        description="Optional retention period in days for run/step records and artifacts. "
        "If specified, records older than this will be eligible for cleanup. Dashboard-editable",
        ge=1,
    )

    @field_validator("redact")
    @classmethod
    def normalize_redact_fields(cls, v: List[str]) -> List[str]:
        """Normalize redaction fields to lowercase for consistent matching."""
        return [field.lower() for field in v] if v else []


class CaptureOverride(BaseModel):
    """Validation model for per-request capture policy overrides.

    Provides better DX by rejecting unknown keys early and enabling mypy validation.
    """

    mode: Optional[CapturePolicyMode] = Field(
        None, description="Override the capture mode for this request"
    )

    artifacts: Optional[ArtifactCaptureMode] = Field(
        None, description="Override the artifact capture mode for this request"
    )

    sample_rate: Optional[float] = Field(
        None,
        description="Override the sampling rate for this request",
        ge=0.0,
        le=1.0,
    )

    max_bytes: Optional[int] = Field(
        None,
        description="Override the payload size limit for this request",
        ge=1024,
        le=10485760,
    )

    redact: Optional[List[str]] = Field(
        None, description="Override the redaction list for this request"
    )

    retention_days: Optional[int] = Field(
        None,
        description="Override the retention period for this request",
        ge=1,
    )


def derive_artifacts_from_mode(mode: CapturePolicyMode) -> ArtifactCaptureMode:
    """Derive the default artifacts capture mode from the policy mode.

    Args:
        mode: The capture policy mode

    Returns:
        The corresponding artifact capture mode
    """
    if mode == CapturePolicyMode.FULL:
        return ArtifactCaptureMode.FULL
    elif mode == CapturePolicyMode.SAMPLED:
        return ArtifactCaptureMode.SAMPLED
    elif mode == CapturePolicyMode.ERRORS_ONLY:
        return ArtifactCaptureMode.ERRORS_ONLY
    else:  # METADATA or NONE
        return ArtifactCaptureMode.NONE


def get_endpoint_default_policy() -> CapturePolicy:
    """Get the default capture policy from environment variables.

    Returns:
        CapturePolicy configured from environment variables with safe defaults
    """
    mode_str = os.getenv("ZENML_SERVING_CAPTURE_DEFAULT", "full").lower()
    try:
        mode = CapturePolicyMode(mode_str)
    except ValueError:
        mode = CapturePolicyMode.FULL

    artifacts_str = os.getenv(
        "ZENML_SERVING_CAPTURE_ARTIFACTS", "none"
    ).lower()
    try:
        artifacts = ArtifactCaptureMode(artifacts_str)
    except ValueError:
        artifacts = ArtifactCaptureMode.NONE

    sample_rate = float(os.getenv("ZENML_SERVING_CAPTURE_SAMPLE_RATE", "0.1"))
    sample_rate = max(0.0, min(1.0, sample_rate))  # Clamp to valid range

    max_bytes = int(os.getenv("ZENML_SERVING_CAPTURE_MAX_BYTES", "262144"))
    max_bytes = max(1024, min(10485760, max_bytes))  # Clamp to valid range

    redact_str = os.getenv("ZENML_SERVING_CAPTURE_REDACT", "")
    redact = (
        [field.strip() for field in redact_str.split(",") if field.strip()]
        if redact_str
        else None
    )

    return CapturePolicy(
        mode=mode,
        artifacts=artifacts,
        sample_rate=sample_rate,
        max_bytes=max_bytes,
        redact=redact
        if redact is not None
        else ["password", "token", "key", "secret", "auth", "credential"],
    )


def resolve_effective_policy(
    endpoint_default: CapturePolicy,
    request_override: Optional[Union[Dict[str, Any], CaptureOverride]] = None,
    code_override: Optional[Dict[str, Any]] = None,
) -> CapturePolicy:
    """Resolve the effective capture policy using precedence rules.

    Precedence (highest to lowest): request_override > code_override > endpoint_default

    Args:
        endpoint_default: Base policy from endpoint configuration
        request_override: Per-request policy overrides (dict or validated CaptureOverride)
        code_override: Code-level policy overrides from annotations (future)

    Returns:
        Effective capture policy with all overrides applied
    """
    # Start with endpoint default
    policy_dict = endpoint_default.model_dump()

    # Apply code-level overrides (reserved for future annotation support)
    if code_override:
        for key, value in code_override.items():
            if key in policy_dict:
                policy_dict[key] = value

    # Track if artifacts was explicitly set by any override
    artifacts_explicitly_set = False

    # Apply request-level overrides (highest precedence)
    override_dict = {}
    if request_override:
        if isinstance(request_override, CaptureOverride):
            # Convert validated model to dict, excluding None values
            override_dict = {
                k: v
                for k, v in request_override.model_dump().items()
                if v is not None
            }
        else:
            override_dict = request_override

        for key, value in override_dict.items():
            if key in policy_dict:
                policy_dict[key] = value
                if key == "artifacts":
                    artifacts_explicitly_set = True

    # Check if code_override set artifacts
    if code_override and "artifacts" in code_override:
        artifacts_explicitly_set = True

    # If artifacts wasn't explicitly set by any override, derive it from mode
    if not artifacts_explicitly_set:
        policy_dict["artifacts"] = derive_artifacts_from_mode(
            CapturePolicyMode(policy_dict["mode"])
        )

    # Reconstruct policy with validated fields
    return CapturePolicy(**policy_dict)


def should_create_runs(policy: CapturePolicy) -> bool:
    """Check if runs should be created based on policy mode."""
    return policy.mode != CapturePolicyMode.NONE


def should_capture_artifacts(
    policy: CapturePolicy, is_error: bool = False, is_sampled: bool = False
) -> bool:
    """Check if artifacts should be captured based on policy and execution status.

    Args:
        policy: Effective capture policy
        is_error: Whether this is for a failed step execution
        is_sampled: Whether this invocation is sampled (for sampled mode)

    Returns:
        True if artifacts should be persisted
    """
    # If mode is NONE, never capture artifacts regardless of artifacts policy
    if policy.mode == CapturePolicyMode.NONE:
        return False

    if policy.artifacts == ArtifactCaptureMode.NONE:
        return False
    elif policy.artifacts == ArtifactCaptureMode.ERRORS_ONLY:
        return is_error
    elif policy.artifacts == ArtifactCaptureMode.FULL:
        return True
    else:  # SAMPLED
        return is_sampled


def should_capture_payloads(
    policy: CapturePolicy, is_sampled: bool = False
) -> bool:
    """Check if input/output payloads should be captured in run metadata.

    Args:
        policy: The capture policy
        is_sampled: Whether this invocation is sampled (for sampled mode)

    Returns:
        True if payloads should be captured
    """
    if policy.mode == CapturePolicyMode.FULL:
        return True
    elif policy.mode == CapturePolicyMode.SAMPLED:
        return is_sampled
    else:
        return False


def redact_fields(
    data: Dict[str, Any], redact_list: List[str]
) -> Dict[str, Any]:
    """Redact sensitive fields from a dictionary.

    Args:
        data: Dictionary to redact fields from
        redact_list: List of field names to redact (case-insensitive substring match)

    Returns:
        Dictionary with sensitive fields replaced by '[REDACTED]'
    """
    if not redact_list:
        return data

    redacted: Dict[str, Any] = {}
    for key, value in data.items():
        key_lower = key.lower()
        should_redact = any(
            redact_field in key_lower for redact_field in redact_list
        )

        if should_redact:
            redacted[key] = "[REDACTED]"
        elif isinstance(value, dict):
            redacted[key] = redact_fields(value, redact_list)
        else:
            redacted[key] = value

    return redacted


def truncate_payload(data: Any, max_bytes: int) -> str:
    """Truncate payload data to fit within size limits.

    Args:
        data: Data to truncate (will be JSON serialized)
        max_bytes: Maximum size in bytes

    Returns:
        Truncated string representation
    """
    try:
        import json

        serialized = json.dumps(data, default=str, separators=(",", ":"))

        if len(serialized.encode("utf-8")) <= max_bytes:
            return serialized

        # Truncate and add indicator
        truncated_bytes = (
            max_bytes - 50
        )  # Reserve space for truncation message
        truncated = serialized.encode("utf-8")[:truncated_bytes].decode(
            "utf-8", errors="ignore"
        )
        return f"{truncated}... [TRUNCATED - original size: {len(serialized)} chars]"
    except Exception:
        # Fallback to string representation
        str_repr = str(data)
        if len(str_repr.encode("utf-8")) <= max_bytes:
            return str_repr

        truncated_bytes = max_bytes - 30
        truncated = str_repr.encode("utf-8")[:truncated_bytes].decode(
            "utf-8", errors="ignore"
        )
        return f"{truncated}... [TRUNCATED]"
