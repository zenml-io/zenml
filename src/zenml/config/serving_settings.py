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
"""Serving settings for ZenML pipeline serving."""

from typing import Any, Dict, Literal, Optional, Union

from pydantic import Field, field_validator

from zenml.config.base_settings import BaseSettings

# Import enums for user convenience

# Type aliases for capture modes
CaptureModeType = Literal["full", "sampled", "errors_only", "metadata", "none"]
CaptureValueMode = Union[CaptureModeType, Dict[str, CaptureModeType]]


class ServingCaptureSettings(BaseSettings):
    """Simplified settings for pipeline serving capture configuration.

    This provides a flat, user-friendly interface for configuring capture policies.
    Replaces the nested `settings["serving"]["capture"]` structure.
    """

    mode: CaptureModeType = Field(
        default="full",
        description="Global capture mode for the pipeline. Controls what level of "
        "run tracking is performed: 'full' captures all payloads and outputs, "
        "'sampled' captures a fraction based on sample_rate, 'errors_only' captures "
        "only when steps fail, 'metadata' creates run records with basic metadata "
        "only, 'none' records nothing",
    )

    sample_rate: Optional[float] = Field(
        default=None,
        description="Sampling rate for 'sampled' mode (0.0 to 1.0). Determines the "
        "fraction of pipeline runs that will have full payload and artifact capture. "
        "Only valid when mode='sampled'",
        ge=0.0,
        le=1.0,
    )

    inputs: Optional[Dict[str, CaptureModeType]] = Field(
        default=None,
        description="Per-input parameter capture modes. Keys are parameter names, "
        "values are capture modes. Overrides the global mode for specific inputs",
    )

    outputs: Optional[CaptureValueMode] = Field(
        default=None,
        description="Per-output capture modes. Can be a single mode string (applied "
        "to the default output) or a dictionary mapping output names to modes. "
        "Overrides the global mode for specific outputs",
    )

    # Advanced settings (preserved but not prominently documented)
    max_bytes: Optional[int] = Field(
        default=None,
        description="Maximum size in bytes for payload data stored in run metadata. "
        "Larger payloads will be truncated",
        ge=1024,
        le=10485760,
    )

    redact: Optional[list[str]] = Field(
        default=None,
        description="List of field names to redact from payload metadata. "
        "Case-insensitive substring matching applied",
    )

    retention_days: Optional[int] = Field(
        default=None,
        description="Retention period in days for run/step records and artifacts",
        ge=1,
    )

    @field_validator("sample_rate")
    @classmethod
    def validate_sample_rate(cls, v: Optional[float], info) -> Optional[float]:
        """Validate that sample_rate is only provided when mode is sampled."""
        if v is not None:
            # Note: We can't access other fields during validation in this context
            # The actual validation will be done at the service level
            pass
        return v


class ServingSettings(BaseSettings):
    """Settings for pipeline serving configuration.

    These settings control serving-specific behavior like capture policies
    for step-level data tracking and artifact persistence.
    """

    capture: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Step-level capture configuration for fine-grained data tracking control. "
        "Supports 'inputs' and 'outputs' mappings with per-parameter capture settings including "
        "mode, artifacts, sample_rate, max_bytes, and redact fields",
    )
