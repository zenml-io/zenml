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
"""Comprehensive test for parameter resolution and flow in deployment."""

from unittest.mock import MagicMock

import pytest

from zenml.deployers.server import runtime


class TestOutputRecording:
    """Test output recording and retrieval functionality."""

    @pytest.fixture(autouse=True)
    def setup_deployment_state(self):
        """Set up deployment state for each test."""
        runtime.stop()
        yield
        runtime.stop()

    def test_record_and_get_outputs(self):
        """Test recording and retrieving step outputs."""
        snapshot = MagicMock()
        snapshot.id = "test-snapshot"

        runtime.start(
            request_id="test-request",
            snapshot=snapshot,
            parameters={"param": "value"},
        )

        # Record some outputs
        runtime.record_step_outputs(
            "step1", {"result": "output1", "score": 0.95}
        )
        runtime.record_step_outputs("step2", {"prediction": "class_a"})

        # Retrieve all outputs
        all_outputs = runtime.get_outputs()

        assert "step1" in all_outputs
        assert "step2" in all_outputs
        assert all_outputs["step1"]["result"] == "output1"
        assert all_outputs["step1"]["score"] == 0.95
        assert all_outputs["step2"]["prediction"] == "class_a"

    def test_record_outputs_inactive_context(self):
        """Test that recording does nothing when context is inactive."""
        # Don't start context
        runtime.record_step_outputs("step1", {"result": "output1"})

        # Should not record anything
        snapshot = MagicMock()
        snapshot.id = "test-snapshot"

        runtime.start(
            request_id="test-request", snapshot=snapshot, parameters={}
        )

        outputs = runtime.get_outputs()
        assert outputs == {}

    def test_record_empty_outputs(self):
        """Test recording empty outputs."""
        snapshot = MagicMock()
        snapshot.id = "test-snapshot"

        runtime.start(
            request_id="test-request", snapshot=snapshot, parameters={}
        )

        # Record empty outputs
        runtime.record_step_outputs("step1", {})
        runtime.record_step_outputs("step2", None)

        outputs = runtime.get_outputs()
        assert outputs == {}

    def test_multiple_output_updates(self):
        """Test multiple updates to same step outputs."""
        snapshot = MagicMock()
        snapshot.id = "test-snapshot"

        runtime.start(
            request_id="test-request", snapshot=snapshot, parameters={}
        )

        # Record outputs in multiple calls
        runtime.record_step_outputs("step1", {"result": "first"})
        runtime.record_step_outputs("step1", {"score": 0.8})
        runtime.record_step_outputs(
            "step1", {"result": "updated"}
        )  # Should overwrite

        outputs = runtime.get_outputs()
        assert outputs["step1"]["result"] == "updated"
        assert outputs["step1"]["score"] == 0.8
