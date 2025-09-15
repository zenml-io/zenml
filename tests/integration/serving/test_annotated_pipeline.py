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
"""Integration tests for annotated pipeline serving."""

from typing import Annotated, Any, Dict
from unittest.mock import Mock, patch

from zenml.deployers.serving.capture import Capture
from zenml.deployers.serving.direct_execution import DirectExecutionEngine
from zenml.deployers.serving.policy import (
    ArtifactCaptureMode,
    CapturePolicy,
    CapturePolicyMode,
)
from zenml.deployers.serving.tracking import TrackingManager


# Sample annotated step functions for testing
def sensitive_input_step(
    secret_data: Annotated[str, Capture("none")],  # Never capture
    public_data: Annotated[str, Capture("full")],  # Always capture
) -> str:
    """Step with sensitive input that should not be captured."""
    return f"processed: {public_data}"


def error_capture_step(
    data: str,
) -> Annotated[
    Dict[str, Any], Capture("errors_only", artifacts="errors_only")
]:
    """Step that only captures outputs on errors."""
    if "error" in data:
        raise ValueError("Simulated error")
    return {"result": data, "status": "success"}


def sampled_output_step(
    data: str,
) -> Annotated[
    Dict[str, Any], Capture("sampled", artifacts="sampled", sample_rate=0.8)
]:
    """Step with sampled output capture."""
    return {"processed": data, "timestamp": "2024-01-01"}


def mixed_outputs_step(data: str) -> Dict[str, Any]:
    """Step with multiple outputs - demonstrates dict output handling."""
    return {
        "sensitive_result": "secret_value",
        "public_result": data,
        "metadata": {"version": "1.0"},
    }


class TestAnnotatedPipelineIntegration:
    """Test end-to-end annotation functionality."""

    def create_mock_step_class(self, func):
        """Create a mock step class with the given function as entrypoint."""
        step_class = Mock()
        step_class.entrypoint = func
        return step_class

    def create_mock_snapshot(self, step_funcs):
        """Create a mock snapshot with the given step functions."""
        snapshot = Mock()
        snapshot.pipeline_configuration.name = "test_pipeline"
        snapshot.step_configurations = {}

        for i, func in enumerate(step_funcs):
            step_name = f"step_{i}"
            step_config = Mock()
            step_config.spec.source = f"test.{func.__name__}"
            step_config.spec.inputs = {}
            snapshot.step_configurations[step_name] = step_config

        return snapshot

    @patch("zenml.deployers.serving.direct_execution.source_utils.load")
    def test_sensitive_input_annotation_parsing(self, mock_load):
        """Test that sensitive input annotations are parsed correctly."""
        # Setup mocks
        step_class = self.create_mock_step_class(sensitive_input_step)
        mock_load.return_value = step_class
        snapshot = self.create_mock_snapshot([sensitive_input_step])

        # Create engine - this should parse the annotations
        engine = DirectExecutionEngine(snapshot)

        # Get the parsed annotations
        overrides = engine.get_step_capture_overrides()

        # Check that annotations were parsed correctly
        step_0_overrides = overrides["step_0"]

        # secret_data should have "none" capture
        assert step_0_overrides["inputs"]["secret_data"].mode.value == "none"

        # public_data should have "full" capture
        assert step_0_overrides["inputs"]["public_data"].mode.value == "full"

    @patch("zenml.deployers.serving.direct_execution.source_utils.load")
    def test_error_capture_annotation_parsing(self, mock_load):
        """Test that error-only output annotations are parsed correctly."""
        step_class = self.create_mock_step_class(error_capture_step)
        mock_load.return_value = step_class
        snapshot = self.create_mock_snapshot([error_capture_step])

        engine = DirectExecutionEngine(snapshot)
        overrides = engine.get_step_capture_overrides()

        step_0_overrides = overrides["step_0"]

        # Output should have "errors_only" capture
        assert (
            step_0_overrides["outputs"]["output"].mode.value == "errors_only"
        )
        assert step_0_overrides["outputs"]["output"].artifacts == "errors_only"

    @patch("zenml.deployers.serving.direct_execution.source_utils.load")
    def test_sampled_annotation_parsing(self, mock_load):
        """Test that sampled annotations are parsed correctly."""
        step_class = self.create_mock_step_class(sampled_output_step)
        mock_load.return_value = step_class
        snapshot = self.create_mock_snapshot([sampled_output_step])

        engine = DirectExecutionEngine(snapshot)
        overrides = engine.get_step_capture_overrides()

        step_0_overrides = overrides["step_0"]

        # Output should have "sampled" capture with custom rate
        assert step_0_overrides["outputs"]["output"].mode.value == "sampled"
        assert step_0_overrides["outputs"]["output"].artifacts == "sampled"
        assert step_0_overrides["outputs"]["output"].sample_rate == 0.8

    def test_tracking_manager_per_value_capture_logic(self):
        """Test TrackingManager applies per-value capture correctly."""
        # Create base policy
        base_policy = CapturePolicy(
            mode=CapturePolicyMode.METADATA,
            artifacts=ArtifactCaptureMode.NONE,
            max_bytes=1024,
        )

        # Create tracking manager
        mock_snapshot = Mock()
        tracking_manager = TrackingManager(
            snapshot=mock_snapshot,
            policy=base_policy,
            create_runs=True,
            invocation_id="test_invocation",
        )

        # Set up step capture overrides
        step_overrides = {
            "step_0": {
                "inputs": {
                    "secret_data": Capture("none"),
                    "public_data": Capture("full"),
                },
                "outputs": {"output": Capture("full", artifacts="sampled")},
            }
        }
        tracking_manager.set_step_capture_overrides(step_overrides)

        # Test input capture logic
        secret_effective = tracking_manager._get_effective_capture_for_value(
            "step_0", "secret_data", "input"
        )
        public_effective = tracking_manager._get_effective_capture_for_value(
            "step_0", "public_data", "input"
        )

        # secret_data should never be captured
        assert secret_effective.mode.value == "none"

        # public_data should always be captured
        assert public_effective.mode.value == "full"

        # Test output capture logic
        output_effective = tracking_manager._get_effective_capture_for_value(
            "step_0", "output", "output"
        )

        # Output should have full mode with sampled artifacts
        assert output_effective.mode.value == "full"
        assert output_effective.artifacts == "sampled"

    def test_precedence_annotation_over_policy(self):
        """Test that annotations take precedence over base policy."""
        # Base policy: very restrictive
        base_policy = CapturePolicy(
            mode=CapturePolicyMode.NONE, artifacts=ArtifactCaptureMode.NONE
        )

        mock_snapshot = Mock()
        tracking_manager = TrackingManager(
            snapshot=mock_snapshot,
            policy=base_policy,
            create_runs=True,
            invocation_id="test_invocation",
        )

        # Annotation: very permissive
        step_overrides = {
            "step_0": {
                "inputs": {},
                "outputs": {"output": Capture("full", artifacts="full")},
            }
        }
        tracking_manager.set_step_capture_overrides(step_overrides)

        # Get effective capture - annotation should override
        output_effective = tracking_manager._get_effective_capture_for_value(
            "step_0", "output", "output"
        )

        # Should use annotation values, not policy
        assert output_effective.mode.value == "full"
        assert output_effective.artifacts == "full"

    def test_fallback_to_policy_without_annotation(self):
        """Test fallback to base policy when no annotation exists."""
        base_policy = CapturePolicy(
            mode=CapturePolicyMode.SAMPLED,
            artifacts=ArtifactCaptureMode.ERRORS_ONLY,
            sample_rate=0.3,
        )

        mock_snapshot = Mock()
        tracking_manager = TrackingManager(
            snapshot=mock_snapshot,
            policy=base_policy,
            create_runs=True,
            invocation_id="test_invocation",
        )

        # No step overrides - should use base policy
        step_overrides = {"step_0": {"inputs": {}, "outputs": {}}}
        tracking_manager.set_step_capture_overrides(step_overrides)

        # Get effective capture for non-annotated value
        output_effective = tracking_manager._get_effective_capture_for_value(
            "step_0", "output", "output"
        )

        # Should use base policy values
        assert output_effective.mode.value == "sampled"
        assert output_effective.artifacts == "errors_only"
        assert output_effective.sample_rate == 0.3

    def test_multiple_steps_different_annotations(self):
        """Test handling multiple steps with different annotations."""
        base_policy = CapturePolicy(mode=CapturePolicyMode.METADATA)

        mock_snapshot = Mock()
        tracking_manager = TrackingManager(
            snapshot=mock_snapshot,
            policy=base_policy,
            create_runs=True,
            invocation_id="test_invocation",
        )

        # Different annotations per step
        step_overrides = {
            "sensitive_step": {
                "inputs": {"data": Capture("none")},
                "outputs": {"output": Capture("none")},
            },
            "public_step": {
                "inputs": {"data": Capture("full")},
                "outputs": {"output": Capture("full", artifacts="full")},
            },
            "error_step": {
                "inputs": {},
                "outputs": {
                    "output": Capture("errors_only", artifacts="errors_only")
                },
            },
        }
        tracking_manager.set_step_capture_overrides(step_overrides)

        # Test each step's effective capture
        sensitive_output = tracking_manager._get_effective_capture_for_value(
            "sensitive_step", "output", "output"
        )
        public_output = tracking_manager._get_effective_capture_for_value(
            "public_step", "output", "output"
        )
        error_output = tracking_manager._get_effective_capture_for_value(
            "error_step", "output", "output"
        )

        # Each should have different capture behavior
        assert sensitive_output.mode.value == "none"
        assert public_output.mode.value == "full"
        assert public_output.artifacts == "full"
        assert error_output.mode.value == "errors_only"
        assert error_output.artifacts == "errors_only"


class TestPerValueCaptureBehavior:
    """Test the actual capture behavior with per-value settings."""

    def test_parameter_capture_with_annotations(self):
        """Test that pipeline parameters respect input annotations."""
        from zenml.deployers.serving.capture import (
            overlay_capture,
            should_capture_value_payload,
        )

        # Base policy allows capture
        base_policy = CapturePolicy(
            mode=CapturePolicyMode.FULL, artifacts=ArtifactCaptureMode.FULL
        )

        # Annotation disables capture for sensitive parameter
        sensitive_annotation = Capture("none")
        sensitive_effective = overlay_capture(
            base_policy, sensitive_annotation
        )

        # Public parameter uses base policy
        public_effective = overlay_capture(base_policy, None)

        # Test capture decisions
        assert not should_capture_value_payload(sensitive_effective)
        assert should_capture_value_payload(public_effective)

    def test_output_capture_with_dict_outputs(self):
        """Test capture behavior with dictionary outputs."""
        from zenml.deployers.serving.capture import (
            overlay_capture,
            should_capture_value_artifacts,
        )

        base_policy = CapturePolicy(
            mode=CapturePolicyMode.FULL, artifacts=ArtifactCaptureMode.NONE
        )

        # Different annotations for different outputs
        sensitive_annotation = Capture("none", artifacts="none")
        public_annotation = Capture("full", artifacts="full")

        sensitive_effective = overlay_capture(
            base_policy, sensitive_annotation
        )
        public_effective = overlay_capture(base_policy, public_annotation)

        # Sensitive output should not persist artifacts
        assert not should_capture_value_artifacts(
            sensitive_effective, is_error=False
        )

        # Public output should persist artifacts
        assert should_capture_value_artifacts(public_effective, is_error=False)

    def test_sampled_annotation_deterministic_behavior(self):
        """Test that sampled annotations use deterministic sampling."""
        from zenml.deployers.serving.capture import overlay_capture

        base_policy = CapturePolicy(mode=CapturePolicyMode.METADATA)

        # High sample rate annotation
        high_sample_annotation = Capture("sampled", sample_rate=0.9)
        high_effective = overlay_capture(base_policy, high_sample_annotation)

        # Low sample rate annotation
        low_sample_annotation = Capture("sampled", sample_rate=0.1)
        low_effective = overlay_capture(base_policy, low_sample_annotation)

        # Note: actual sampling decision would be made by TrackingManager
        # using deterministic hash of invocation_id
        assert high_effective.sample_rate == 0.9
        assert low_effective.sample_rate == 0.1
