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
"""Unit tests for step-level capture annotations."""

from typing import Annotated

import pytest

from zenml.serving.capture import (
    Cap,
    Capture,
    CaptureMode,
    EffectiveCapture,
    overlay_capture,
    parse_capture_annotation,
    should_capture_value_artifacts,
    should_capture_value_payload,
)
from zenml.serving.policy import (
    ArtifactCaptureMode,
    CapturePolicy,
    CapturePolicyMode,
)


class TestCaptureAnnotation:
    """Test the Capture dataclass and validation."""

    def test_capture_creation(self):
        """Test basic capture annotation creation."""
        capture = Capture("full", max_bytes=64000)

        assert capture.mode == CaptureMode.FULL
        assert capture.max_bytes == 64000
        assert capture.sample_rate is None
        assert capture.redact is None
        assert capture.artifacts is None

    def test_capture_validation(self):
        """Test capture validation."""
        # Valid capture
        capture = Capture("sampled", sample_rate=0.5, artifacts="full")
        assert capture.mode == CaptureMode.SAMPLED
        assert capture.sample_rate == 0.5
        assert capture.artifacts == "full"

        # Invalid sample rate
        with pytest.raises(
            ValueError, match="sample_rate must be between 0.0 and 1.0"
        ):
            Capture("sampled", sample_rate=1.5)

        # Invalid max_bytes
        with pytest.raises(
            ValueError, match="max_bytes must be at least 1024"
        ):
            Capture("full", max_bytes=512)

        # Invalid artifacts mode
        with pytest.raises(ValueError, match="artifacts must be one of"):
            Capture("full", artifacts="invalid")

    def test_capture_string_mode_conversion(self):
        """Test that string modes are converted to enum."""
        capture = Capture("none")
        assert capture.mode == CaptureMode.NONE
        assert isinstance(capture.mode, CaptureMode)


class TestAnnotationParsing:
    """Test annotation parsing functionality."""

    def test_parse_simple_annotation(self):
        """Test parsing typing.Annotated with Capture metadata."""
        annotation = Annotated[str, Capture("none")]
        capture = parse_capture_annotation(annotation)

        assert capture is not None
        assert capture.mode == CaptureMode.NONE

    def test_parse_multiple_metadata(self):
        """Test parsing with multiple metadata items."""
        annotation = Annotated[str, "some_other_metadata", Capture("full")]
        capture = parse_capture_annotation(annotation)

        assert capture is not None
        assert capture.mode == CaptureMode.FULL

    def test_parse_no_capture_metadata(self):
        """Test parsing annotation without Capture metadata."""
        annotation = Annotated[str, "some_metadata"]
        capture = parse_capture_annotation(annotation)

        assert capture is None

    def test_parse_non_annotated(self):
        """Test parsing regular type annotation."""
        annotation = str
        capture = parse_capture_annotation(annotation)

        assert capture is None


class TestCaptureOverlay:
    """Test capture overlay functionality."""

    def test_overlay_no_annotation(self):
        """Test overlay with no annotation."""
        base_policy = CapturePolicy(
            mode=CapturePolicyMode.METADATA,
            artifacts=ArtifactCaptureMode.NONE,
            max_bytes=1024,
            redact=["password"],
        )

        effective = overlay_capture(base_policy, None)

        assert effective.mode == CaptureMode.METADATA
        assert effective.artifacts == "none"
        assert effective.max_bytes == 1024
        assert effective.redact == ["password"]

    def test_overlay_with_annotation(self):
        """Test overlay with capture annotation."""
        base_policy = CapturePolicy(
            mode=CapturePolicyMode.METADATA,
            artifacts=ArtifactCaptureMode.NONE,
            max_bytes=1024,
            redact=["password"],
            sample_rate=0.1,
        )

        annotation = Capture(
            "full",
            max_bytes=64000,
            redact=["secret", "token"],
            artifacts="sampled",
        )

        effective = overlay_capture(base_policy, annotation)

        assert effective.mode == CaptureMode.FULL
        assert effective.artifacts == "sampled"
        assert effective.max_bytes == 64000
        assert effective.redact == ["secret", "token"]
        assert effective.sample_rate == 0.1  # Not overridden

    def test_overlay_partial_override(self):
        """Test overlay with partial annotation override."""
        base_policy = CapturePolicy(
            mode=CapturePolicyMode.SAMPLED,
            artifacts=ArtifactCaptureMode.FULL,
            max_bytes=2048,
            redact=["password"],
            sample_rate=0.2,
        )

        annotation = Capture(
            "none", sample_rate=0.8
        )  # Only override mode and sample_rate

        effective = overlay_capture(base_policy, annotation)

        assert effective.mode == CaptureMode.NONE
        assert effective.artifacts == "full"  # From base
        assert effective.max_bytes == 2048  # From base
        assert effective.redact == ["password"]  # From base
        assert effective.sample_rate == 0.8  # Overridden


class TestValueCaptureLogic:
    """Test per-value capture decision logic."""

    def test_should_capture_value_payload(self):
        """Test payload capture decisions."""
        # Full mode - always capture
        effective = EffectiveCapture(
            mode=CaptureMode.FULL,
            max_bytes=1024,
            redact=[],
            artifacts="none",
            sample_rate=0.1,
        )
        assert should_capture_value_payload(effective, is_sampled=False)
        assert should_capture_value_payload(effective, is_sampled=True)

        # Sampled mode - depends on sampling
        effective = EffectiveCapture(
            mode=CaptureMode.SAMPLED,
            max_bytes=1024,
            redact=[],
            artifacts="none",
            sample_rate=0.1,
        )
        assert not should_capture_value_payload(effective, is_sampled=False)
        assert should_capture_value_payload(effective, is_sampled=True)

        # None mode - never capture
        effective = EffectiveCapture(
            mode=CaptureMode.NONE,
            max_bytes=1024,
            redact=[],
            artifacts="none",
            sample_rate=0.1,
        )
        assert not should_capture_value_payload(effective, is_sampled=False)
        assert not should_capture_value_payload(effective, is_sampled=True)

        # Metadata mode - never capture payloads
        effective = EffectiveCapture(
            mode=CaptureMode.METADATA,
            max_bytes=1024,
            redact=[],
            artifacts="none",
            sample_rate=0.1,
        )
        assert not should_capture_value_payload(effective, is_sampled=False)
        assert not should_capture_value_payload(effective, is_sampled=True)

    def test_should_capture_value_artifacts(self):
        """Test artifact capture decisions."""
        # Mode NONE - never capture artifacts
        effective = EffectiveCapture(
            mode=CaptureMode.NONE,
            max_bytes=1024,
            redact=[],
            artifacts="full",
            sample_rate=0.1,
        )
        assert not should_capture_value_artifacts(effective, is_error=False)
        assert not should_capture_value_artifacts(effective, is_error=True)

        # Artifacts NONE - never capture
        effective = EffectiveCapture(
            mode=CaptureMode.FULL,
            max_bytes=1024,
            redact=[],
            artifacts="none",
            sample_rate=0.1,
        )
        assert not should_capture_value_artifacts(effective, is_error=False)
        assert not should_capture_value_artifacts(effective, is_error=True)

        # Artifacts ERRORS_ONLY - only on errors
        effective = EffectiveCapture(
            mode=CaptureMode.FULL,
            max_bytes=1024,
            redact=[],
            artifacts="errors_only",
            sample_rate=0.1,
        )
        assert not should_capture_value_artifacts(effective, is_error=False)
        assert should_capture_value_artifacts(effective, is_error=True)

        # Artifacts FULL - always capture
        effective = EffectiveCapture(
            mode=CaptureMode.FULL,
            max_bytes=1024,
            redact=[],
            artifacts="full",
            sample_rate=0.1,
        )
        assert should_capture_value_artifacts(effective, is_error=False)
        assert should_capture_value_artifacts(effective, is_error=True)

        # Artifacts SAMPLED - depends on sampling
        effective = EffectiveCapture(
            mode=CaptureMode.FULL,
            max_bytes=1024,
            redact=[],
            artifacts="sampled",
            sample_rate=0.1,
        )
        assert not should_capture_value_artifacts(
            effective, is_error=False, is_sampled=False
        )
        assert should_capture_value_artifacts(
            effective, is_error=False, is_sampled=True
        )


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_precedence_annotation_over_policy(self):
        """Test that annotations take precedence over base policy."""
        # Base policy: capture metadata only
        base_policy = CapturePolicy(
            mode=CapturePolicyMode.METADATA,
            artifacts=ArtifactCaptureMode.NONE,
            max_bytes=1024,
        )

        # Annotation: capture full with artifacts
        annotation = Capture("full", artifacts="sampled", max_bytes=32000)

        effective = overlay_capture(base_policy, annotation)

        # Annotation should override
        assert effective.mode == CaptureMode.FULL
        assert effective.artifacts == "sampled"
        assert effective.max_bytes == 32000

    def test_mixed_capture_scenario(self):
        """Test scenario with different capture modes for inputs/outputs."""
        base_policy = CapturePolicy(
            mode=CapturePolicyMode.SAMPLED,
            artifacts=ArtifactCaptureMode.NONE,
            sample_rate=0.3,
        )

        # Input annotation: no capture
        input_annotation = Capture("none")
        input_effective = overlay_capture(base_policy, input_annotation)

        # Output annotation: full capture with artifacts
        output_annotation = Capture("full", artifacts="full")
        output_effective = overlay_capture(base_policy, output_annotation)

        # Input should never be captured
        assert not should_capture_value_payload(
            input_effective, is_sampled=True
        )

        # Output should always be captured
        assert should_capture_value_payload(output_effective, is_sampled=False)
        assert should_capture_value_artifacts(output_effective, is_error=False)

    def test_errors_only_annotation(self):
        """Test errors_only capture annotation behavior."""
        base_policy = CapturePolicy(mode=CapturePolicyMode.FULL)
        annotation = Capture("errors_only", artifacts="errors_only")

        effective = overlay_capture(base_policy, annotation)

        # Should not capture on success
        assert not should_capture_value_payload(effective, is_sampled=True)
        assert not should_capture_value_artifacts(effective, is_error=False)

        # Should capture on error (Note: errors_only mode doesn't exist for payloads,
        # so this tests that the overlay correctly handles the mode)
        assert should_capture_value_artifacts(effective, is_error=True)


class TestCapConstants:
    """Test the Cap convenience constants for simple annotation syntax."""

    def test_cap_full(self):
        """Test Cap.full constant."""
        assert Cap.full.mode == CaptureMode.FULL
        assert Cap.full.sample_rate is None
        assert Cap.full.artifacts is None

    def test_cap_none(self):
        """Test Cap.none constant."""
        assert Cap.none.mode == CaptureMode.NONE
        assert Cap.none.sample_rate is None
        assert Cap.none.artifacts is None

    def test_cap_metadata(self):
        """Test Cap.metadata constant."""
        assert Cap.metadata.mode == CaptureMode.METADATA
        assert Cap.metadata.sample_rate is None
        assert Cap.metadata.artifacts is None

    def test_cap_errors_only(self):
        """Test Cap.errors_only constant."""
        assert Cap.errors_only.mode == CaptureMode.ERRORS_ONLY
        assert Cap.errors_only.sample_rate is None
        assert Cap.errors_only.artifacts is None

    def test_cap_sampled(self):
        """Test Cap.sampled() constant."""
        sampled = Cap.sampled()
        assert sampled.mode == CaptureMode.SAMPLED
        assert sampled.sample_rate is None  # No per-value rate
        assert sampled.artifacts is None

    def test_cap_annotation_usage(self):
        """Test Cap constants work with type annotations."""
        # These should work with parse_capture_annotation
        full_annotation = Annotated[str, Cap.full]
        none_annotation = Annotated[str, Cap.none]
        sampled_annotation = Annotated[str, Cap.sampled()]

        parsed_full = parse_capture_annotation(full_annotation)
        parsed_none = parse_capture_annotation(none_annotation)
        parsed_sampled = parse_capture_annotation(sampled_annotation)

        assert parsed_full is not None
        assert parsed_full.mode == CaptureMode.FULL

        assert parsed_none is not None
        assert parsed_none.mode == CaptureMode.NONE

        assert parsed_sampled is not None
        assert parsed_sampled.mode == CaptureMode.SAMPLED
        assert parsed_sampled.sample_rate is None  # No per-value rate
