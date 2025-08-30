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
"""Integration tests for capture policy precedence rules."""

from unittest.mock import Mock

from zenml.serving.capture import Capture, CaptureMode
from zenml.serving.policy import CapturePolicy, CapturePolicyMode
from zenml.serving.tracking import TrackingManager


class TestPrecedenceIntegration:
    """Test full precedence integration in TrackingManager."""

    def test_per_value_precedence_step_over_pipeline(self):
        """Test Step > Pipeline per-value precedence."""
        # Create mock deployment
        deployment = Mock()
        policy = CapturePolicy(mode=CapturePolicyMode.FULL)

        tracking_manager = TrackingManager(
            deployment=deployment,
            policy=policy,
            create_runs=False,
            invocation_id="test",
        )

        # Set pipeline-level per-value overrides
        pipeline_overrides = {
            "inputs": {"city": "metadata"},
            "outputs": {"result": "full"},
        }
        tracking_manager.set_pipeline_capture_overrides(pipeline_overrides)

        # Set step-level per-value overrides (should win)
        step_overrides = {
            "test_step": {
                "inputs": {
                    "city": Capture(mode="none")
                },  # Step overrides pipeline
                "outputs": {},
            }
        }
        tracking_manager.set_step_capture_overrides(step_overrides)

        # Test that step-level override wins for city input
        effective = tracking_manager._get_effective_capture_for_value(
            "test_step", "city", "input"
        )
        assert effective.mode == CaptureMode.NONE  # Step override wins

        # Test that pipeline override is used for non-step-overridden values
        effective = tracking_manager._get_effective_capture_for_value(
            "other_step", "city", "input"
        )
        assert effective.mode == CaptureMode.METADATA  # Pipeline override wins

    def test_per_value_precedence_pipeline_over_annotation(self):
        """Test Pipeline > Annotation per-value precedence."""
        deployment = Mock()
        policy = CapturePolicy(mode=CapturePolicyMode.FULL)

        tracking_manager = TrackingManager(
            deployment=deployment,
            policy=policy,
            create_runs=False,
            invocation_id="test",
        )

        # Set pipeline-level per-value overrides
        pipeline_overrides = {"inputs": {"data": "metadata"}}
        tracking_manager.set_pipeline_capture_overrides(pipeline_overrides)

        # Test that pipeline override is used (would beat annotation if present)
        effective = tracking_manager._get_effective_capture_for_value(
            "test_step", "data", "input"
        )
        assert effective.mode == CaptureMode.METADATA  # Pipeline override

    def test_step_level_global_mode_integration(self):
        """Test step-level global mode affects base policy."""
        deployment = Mock()
        policy = CapturePolicy(mode=CapturePolicyMode.FULL)

        tracking_manager = TrackingManager(
            deployment=deployment,
            policy=policy,
            create_runs=False,
            invocation_id="test",
        )

        # Set step-level global mode overrides
        step_mode_overrides = {
            "sensitive_step": "none",
            "debug_step": "metadata",
        }
        tracking_manager.set_step_mode_overrides(step_mode_overrides)

        # Test that step-specific policy is used
        step_policy = tracking_manager._get_effective_policy_for_step(
            "sensitive_step"
        )
        assert step_policy.mode == CapturePolicyMode.NONE

        # Test that regular policy is used for non-overridden steps
        regular_policy = tracking_manager._get_effective_policy_for_step(
            "regular_step"
        )
        assert regular_policy.mode == CapturePolicyMode.FULL  # Original policy

    def test_full_precedence_chain(self):
        """Test complete precedence: Step per-value > Pipeline per-value > Step global > Base."""
        deployment = Mock()
        base_policy = CapturePolicy(mode=CapturePolicyMode.FULL)

        tracking_manager = TrackingManager(
            deployment=deployment,
            policy=base_policy,
            create_runs=False,
            invocation_id="test",
        )

        # Set up all levels of overrides

        # 1. Step-level global mode (affects base for this step)
        tracking_manager.set_step_mode_overrides({"test_step": "metadata"})

        # 2. Pipeline-level per-value
        tracking_manager.set_pipeline_capture_overrides(
            {"inputs": {"param1": "errors_only", "param2": "sampled"}}
        )

        # 3. Step-level per-value (highest priority for specific values)
        tracking_manager.set_step_capture_overrides(
            {
                "test_step": {
                    "inputs": {
                        "param1": Capture(mode="full")
                    },  # Overrides pipeline
                    "outputs": {},
                }
            }
        )

        # Test step per-value wins over pipeline per-value
        effective = tracking_manager._get_effective_capture_for_value(
            "test_step", "param1", "input"
        )
        assert effective.mode == CaptureMode.FULL  # Step per-value wins

        # Test pipeline per-value wins over step global mode for param2
        effective = tracking_manager._get_effective_capture_for_value(
            "test_step", "param2", "input"
        )
        assert (
            effective.mode == CaptureMode.ERRORS_ONLY
        )  # Pipeline per-value wins

        # Test step global mode wins over base policy for param3 (no per-value overrides)
        effective = tracking_manager._get_effective_capture_for_value(
            "test_step", "param3", "input"
        )
        assert effective.mode == CaptureMode.METADATA  # Step global mode wins

        # Test base policy for other steps
        effective = tracking_manager._get_effective_capture_for_value(
            "other_step", "param1", "input"
        )
        assert (
            effective.mode == CaptureMode.FULL
        )  # Base policy for other steps

    def test_step_global_mode_affects_artifacts_derivation(self):
        """Test that step-level global mode properly derives artifacts."""
        deployment = Mock()
        base_policy = CapturePolicy(mode=CapturePolicyMode.FULL)

        tracking_manager = TrackingManager(
            deployment=deployment,
            policy=base_policy,
            create_runs=False,
            invocation_id="test",
        )

        # Set step to metadata mode (should derive artifacts=none)
        tracking_manager.set_step_mode_overrides({"metadata_step": "metadata"})

        step_policy = tracking_manager._get_effective_policy_for_step(
            "metadata_step"
        )
        assert step_policy.mode == CapturePolicyMode.METADATA

        # Check that artifacts is correctly derived
        from zenml.serving.policy import ArtifactCaptureMode

        assert (
            step_policy.artifacts == ArtifactCaptureMode.NONE
        )  # Derived from metadata mode
