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
"""Step-level capture annotations for fine-grained tracking control."""

from enum import Enum
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Union,
    get_args,
    get_origin,
)

from pydantic import BaseModel, Field, field_validator, model_validator

from zenml.deployers.serving.policy import CapturePolicy


class CaptureMode(str, Enum):
    """Fine-grained capture modes for step-level annotations."""

    NONE = "none"
    METADATA = "metadata"
    ERRORS_ONLY = "errors_only"
    SAMPLED = "sampled"
    FULL = "full"


class ArtifactCaptureMode(str, Enum):
    """Artifact capture modes for step-level annotations."""

    NONE = "none"
    ERRORS_ONLY = "errors_only"
    SAMPLED = "sampled"
    FULL = "full"


class Capture(BaseModel):
    """Unified capture configuration for annotations, steps, and pipelines.

    This class serves multiple purposes:
    1. Parameter/output annotations (most specific)
    2. Step-level capture settings
    3. Pipeline-level capture policies

    Usage:
        # Parameter annotations (most specific)
        @step
        def process(
            sensitive_data: Annotated[str, Capture.OFF],      # Never capture
            city: Annotated[str, Capture.FULL],               # Always capture
            optional_param: Annotated[str, Capture.METADATA], # Metadata only
        ) -> Annotated[str, Capture.SAMPLED()]:               # Sampled
            return process_data(sensitive_data, city, optional_param)

        # Step-level settings
        @step(settings={"capture_policy": Capture.ERRORS_ONLY})
        def risky_step(data: str) -> str:
            return process_data(data)

        # Pipeline-level policy
        capture_policy = Capture(
            mode="sampled",            # or use string modes directly
            sample_rate=0.1,
            max_bytes=2048,
            redact_patterns=[r"\\b[\\w.-]+@[\\w.-]+\\.[a-zA-Z]{2,}\\b"]  # emails
        )
        @pipeline(settings={"capture_policy": capture_policy})
        def my_pipeline():
            pass

        # Custom annotation configuration
        def step(data: str) -> Annotated[Dict[str, Any], Capture("full", max_bytes=4096)]:
            return {"result": data}
    """

    # Note: Not frozen since we need to modify fields during validation

    mode: Union[CaptureMode, str] = Field(description="Capture mode")
    sample_rate: Optional[float] = Field(
        None, description="Sampling rate for sampled mode (0.0-1.0)"
    )
    max_bytes: Optional[int] = Field(
        None, description="Maximum bytes to capture"
    )
    redact_patterns: Optional[List[str]] = Field(
        None, description="Regex patterns for PII redaction"
    )
    artifacts: Optional[Union[ArtifactCaptureMode, str]] = Field(
        None, description="Artifact capture mode"
    )

    # Legacy field name support (will be deprecated)
    redact: Optional[List[str]] = Field(
        None, description="Legacy field, use redact_patterns instead"
    )

    def __init__(
        self,
        mode: Union[CaptureMode, str, None] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize Capture with backward compatibility for positional args.

        Supports both:
        - New style: Capture(mode="full", max_bytes=2048)
        - Old style: Capture("full", max_bytes=2048).

        Args:
            mode: Capture mode
            kwargs: Additional keyword arguments
        """
        if mode is not None:
            kwargs["mode"] = mode
        super().__init__(**kwargs)

    @field_validator("mode", mode="before")
    @classmethod
    def validate_mode(cls, v: Union[CaptureMode, str]) -> CaptureMode:
        """Convert string mode to enum."""
        if isinstance(v, str):
            try:
                return CaptureMode(v)
            except ValueError:
                valid_modes = [mode.value for mode in CaptureMode]
                raise ValueError(
                    f"Invalid capture mode '{v}'. Must be one of: {valid_modes}"
                )
        return v

    @field_validator("artifacts", mode="before")
    @classmethod
    def validate_artifacts(
        cls, v: Optional[Union[ArtifactCaptureMode, str]]
    ) -> Optional[ArtifactCaptureMode]:
        """Convert string artifacts to enum."""
        if v is not None and isinstance(v, str):
            try:
                return ArtifactCaptureMode(v)
            except ValueError:
                valid_artifacts = [mode.value for mode in ArtifactCaptureMode]
                raise ValueError(
                    f"Invalid artifacts mode '{v}'. Must be one of: {valid_artifacts}"
                )
        return v

    @field_validator("sample_rate")
    @classmethod
    def validate_sample_rate(cls, v: Optional[float]) -> Optional[float]:
        """Validate sample rate is between 0.0 and 1.0."""
        if v is not None:
            if not (0.0 <= v <= 1.0):
                raise ValueError(
                    f"sample_rate must be between 0.0 and 1.0, got {v}"
                )
        return v

    @field_validator("max_bytes")
    @classmethod
    def validate_max_bytes(cls, v: Optional[int]) -> Optional[int]:
        """Validate max bytes is at least 1024."""
        if v is not None:
            if v < 1024:
                raise ValueError(f"max_bytes must be at least 1024, got {v}")
        return v

    @model_validator(mode="after")
    def handle_legacy_fields(self) -> "Capture":
        """Handle legacy redact field and normalize redact_patterns."""
        # Handle legacy redact field (migrate to redact_patterns)
        if self.redact is not None and self.redact_patterns is None:
            self.redact_patterns = self.redact
            self.redact = None  # Clear legacy field
        elif self.redact is not None and self.redact_patterns is not None:
            raise ValueError(
                "Cannot specify both 'redact' (deprecated) and 'redact_patterns'. "
                "Please use 'redact_patterns' only."
            )

        # Normalize redact_patterns
        if self.redact_patterns is not None:
            # For backwards compatibility, support both field names and regex patterns
            normalized = []
            for pattern in self.redact_patterns:
                if pattern.startswith(r"\b") or "(" in pattern:
                    # Already a regex pattern
                    normalized.append(pattern)
                else:
                    # Legacy field name, convert to lowercase
                    normalized.append(pattern.lower())
            self.redact_patterns = normalized

        return self

    def __repr__(self) -> str:
        """Provide clear representation for logging and debugging."""
        mode_str = (
            self.mode.value
            if isinstance(self.mode, CaptureMode)
            else str(self.mode)
        )
        parts = [f"mode={mode_str}"]

        if self.sample_rate is not None:
            parts.append(f"sample_rate={self.sample_rate}")
        if self.max_bytes is not None:
            parts.append(f"max_bytes={self.max_bytes}")
        if self.artifacts is not None:
            artifacts_str = (
                self.artifacts.value
                if isinstance(self.artifacts, ArtifactCaptureMode)
                else str(self.artifacts)
            )
            parts.append(f"artifacts={artifacts_str}")
        if self.redact_patterns:
            parts.append(f"redact_patterns={self.redact_patterns}")

        return f"Capture({', '.join(parts)})"

    # Common capture constants for easy access
    FULL: ClassVar[Optional["Capture"]] = (
        None  # Will be set after class definition
    )
    OFF: ClassVar[Optional["Capture"]] = (
        None  # Will be set after class definition
    )
    METADATA: ClassVar[Optional["Capture"]] = (
        None  # Will be set after class definition
    )
    ERRORS_ONLY: ClassVar[Optional["Capture"]] = (
        None  # Will be set after class definition
    )

    @classmethod
    def SAMPLED(cls) -> "Capture":
        """Create a sampled capture configuration.

        Returns:
            Capture instance configured for sampling
        """
        return cls(mode="sampled")


def parse_capture_annotation(annotation: Any) -> Optional[Capture]:
    """Parse a typing annotation to extract Capture metadata with comprehensive error handling.

    This function handles all known edge cases including:
    - typing.Annotated vs typing_extensions.Annotated compatibility
    - Nested annotations in Union/Optional types
    - Malformed or incomplete annotation structures
    - Forward references and string annotations
    - Generic types with complex parameter structures
    - Runtime annotation modifications

    Args:
        annotation: Type annotation from function signature

    Returns:
        Capture instance if found in annotation metadata, None otherwise
    """
    if annotation is None:
        return None

    # Handle string annotations (forward references)
    if isinstance(annotation, str):
        return None  # Cannot parse string annotations for metadata

    try:
        # Method 1: Direct __metadata__ access (most reliable for typing.Annotated)
        if hasattr(annotation, "__metadata__") and annotation.__metadata__:
            for metadata in annotation.__metadata__:
                if isinstance(metadata, Capture):
                    return metadata

        # Method 2: typing.get_origin/get_args (handles both typing and typing_extensions)
        origin = get_origin(annotation)
        if origin is not None:
            args = get_args(annotation)
            if args and len(args) > 1:
                # Skip the first arg (the actual type), check metadata args
                for metadata in args[1:]:
                    if isinstance(metadata, Capture):
                        return metadata
                    # Handle nested Capture in complex metadata structures
                    elif hasattr(metadata, "__dict__"):
                        # Check if metadata object contains a Capture attribute
                        for attr_value in getattr(
                            metadata, "__dict__", {}
                        ).values():
                            if isinstance(attr_value, Capture):
                                return attr_value

        # Method 3: Direct __args__ inspection (fallback for edge cases)
        if hasattr(annotation, "__args__"):
            args = getattr(annotation, "__args__", ())
            if args and len(args) > 1:
                for metadata in args[1:]:
                    if isinstance(metadata, Capture):
                        return metadata

        # Method 4: Handle Union/Optional and container types
        if origin and hasattr(origin, "__name__"):
            origin_name = getattr(origin, "__name__", "")
            if origin_name in ("Union", "_UnionGenericAlias", "_GenericAlias"):
                # Check each union/container member for annotations
                args = get_args(annotation)
                for member in args:
                    # Recursively check members (handles Optional[Annotated[T, Capture]])
                    nested_capture = parse_capture_annotation(member)
                    if nested_capture:
                        return nested_capture

        # Method 5: Handle generic containers (List, Dict, Tuple, etc.) that may wrap Annotated types
        if origin in (list, dict, tuple, set) or (
            origin and str(origin).startswith("typing.")
        ):
            args = get_args(annotation)
            for arg in args:
                # Recursively check type arguments (handles List[Annotated[T, Capture]])
                nested_capture = parse_capture_annotation(arg)
                if nested_capture:
                    return nested_capture

    except (
        AttributeError,
        TypeError,
        ValueError,
        IndexError,
        RecursionError,
    ) as e:
        # Comprehensive error handling for all possible parsing failures:
        # - AttributeError: Missing __metadata__, __args__, etc.
        # - TypeError: Invalid type operations or comparisons
        # - ValueError: Invalid enum values or malformed structures
        # - IndexError: Invalid access to args/metadata sequences
        # - RecursionError: Circular annotation references
        import logging

        logger = logging.getLogger(__name__)
        logger.debug(
            f"Failed to parse annotation {annotation} (type: {type(annotation)}): {e}"
        )

        # Try one last fallback: check if annotation is directly a Capture instance
        # (handles cases where annotation parsing is bypassed)
        try:
            if isinstance(annotation, Capture):
                return annotation
        except Exception:
            pass  # Even this basic check can fail in extreme edge cases

    return None


class EffectiveCapture(BaseModel):
    """Resolved capture configuration for a specific value."""

    model_config = {
        "frozen": True
    }  # Make immutable like the original dataclass

    mode: CaptureMode
    max_bytes: int
    redact: List[str]
    artifacts: str
    sample_rate: float


class ValueCapturePlan(BaseModel):
    """Immutable capture plan for a specific step's inputs and outputs."""

    model_config = {
        "frozen": True
    }  # Make immutable like the original dataclass

    step_name: str
    inputs: Dict[str, EffectiveCapture]  # param_name -> capture config
    outputs: Dict[str, EffectiveCapture]  # output_name -> capture config


def overlay_capture(
    base_policy: CapturePolicy, capture: Optional[Capture]
) -> EffectiveCapture:
    """Overlay annotation capture settings on base policy.

    Only overrides fields that are explicitly provided in the annotation.
    This preserves the principle that annotations should only change what
    they explicitly specify.

    Args:
        base_policy: Base capture policy from endpoint/pipeline/request
        capture: Step-level capture annotation (if any)

    Returns:
        Effective capture configuration with annotation overlays applied
    """
    # Start with base policy values
    mode = CaptureMode(base_policy.mode.value)
    max_bytes = base_policy.max_bytes
    redact = base_policy.redact.copy()
    artifacts = base_policy.artifacts.value
    sample_rate = base_policy.sample_rate

    # Apply annotation overlays ONLY for explicitly provided fields
    if capture:
        # Mode is always provided (required field), so always override
        mode = (
            capture.mode
            if isinstance(capture.mode, CaptureMode)
            else CaptureMode(capture.mode)
        )

        # Only override optional fields if they were explicitly provided
        if capture.max_bytes is not None:
            max_bytes = capture.max_bytes
        if capture.redact_patterns is not None:
            redact = (
                capture.redact_patterns
            )  # Already normalized via model_validator
        if capture.artifacts is not None:
            artifacts = (
                capture.artifacts.value
                if isinstance(capture.artifacts, ArtifactCaptureMode)
                else capture.artifacts
            )
        if capture.sample_rate is not None:
            sample_rate = capture.sample_rate

    return EffectiveCapture(
        mode=mode,
        max_bytes=max_bytes,
        redact=redact,
        artifacts=artifacts,
        sample_rate=sample_rate,
    )


def should_capture_value_payload(
    effective: EffectiveCapture, is_sampled: bool = False
) -> bool:
    """Check if payload should be captured for a specific value.

    Args:
        effective: Effective capture configuration for this value
        is_sampled: Whether this invocation is sampled (for sampled mode)

    Returns:
        True if payload should be captured
    """
    if effective.mode == CaptureMode.FULL:
        return True
    elif effective.mode == CaptureMode.SAMPLED:
        return is_sampled
    else:
        return False


def should_capture_value_artifacts(
    effective: EffectiveCapture,
    is_error: bool = False,
    is_sampled: bool = False,
) -> bool:
    """Check if artifacts should be captured for a specific value.

    Artifacts are controlled by the artifacts policy independent of mode.
    Mode only affects payload capture (previews), not artifacts.

    Args:
        effective: Effective capture configuration for this value
        is_error: Whether this is for a failed step execution
        is_sampled: Whether this invocation is sampled (for sampled mode)

    Returns:
        True if artifacts should be persisted
    """
    # Artifacts are controlled independently of mode (previews)
    if effective.artifacts == "none":
        return False
    elif effective.artifacts == "errors_only":
        return is_error
    elif effective.artifacts == "full":
        return True
    else:  # sampled
        return is_sampled


# Set the Capture class constants after class definition
Capture.FULL = Capture(mode="full")
Capture.OFF = Capture(mode="none")
Capture.METADATA = Capture(mode="metadata")
Capture.ERRORS_ONLY = Capture(mode="errors_only")
