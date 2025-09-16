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
"""Unit tests for serving runtime context management."""

from unittest.mock import MagicMock, patch

import pytest

from zenml.deployers.serving import runtime


class TestServingRuntimeContext:
    """Test serving runtime context management."""

    @pytest.fixture(autouse=True)
    def setup_runtime(self):
        """Ensure clean runtime state before each test."""
        runtime.stop()
        yield
        runtime.stop()

    def test_context_lifecycle(self):
        """Test basic context start/stop lifecycle."""
        assert not runtime.is_active()

        snapshot = MagicMock()
        snapshot.id = "test-snapshot"

        # Start context
        runtime.start(
            request_id="test-request",
            snapshot=snapshot,
            parameters={"city": "Berlin", "temperature": 25},
            use_in_memory=True,
        )

        assert runtime.is_active()

        # Stop context
        runtime.stop()

        assert not runtime.is_active()

    def test_parameter_override_basic(self):
        """Test basic parameter override functionality."""
        snapshot = MagicMock()
        snapshot.id = "test-snapshot"

        runtime.start(
            request_id="test-request",
            snapshot=snapshot,
            parameters={
                "city": "Munich",
                "country": "Germany",
                "temperature": 20,
            },
        )

        # Test parameter retrieval
        assert runtime.get_parameter_override("city") == "Munich"
        assert runtime.get_parameter_override("country") == "Germany"
        assert runtime.get_parameter_override("temperature") == 20
        assert runtime.get_parameter_override("missing") is None

    def test_parameter_override_inactive_context(self):
        """Test parameter override when context is inactive."""
        # Don't start context
        assert runtime.get_parameter_override("city") is None

    def test_parameter_override_empty_parameters(self):
        """Test parameter override with empty parameters."""
        snapshot = MagicMock()
        snapshot.id = "test-snapshot"

        runtime.start(
            request_id="test-request",
            snapshot=snapshot,
            parameters={},
        )

        assert runtime.get_parameter_override("city") is None

    def test_step_outputs_recording(self):
        """Test step outputs recording and retrieval."""
        snapshot = MagicMock()
        snapshot.id = "test-snapshot"

        runtime.start(
            request_id="test-request",
            snapshot=snapshot,
            parameters={},
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

    def test_step_outputs_inactive_context(self):
        """Test that recording does nothing when context is inactive."""
        # Don't start context
        runtime.record_step_outputs("step1", {"result": "output1"})

        # Start context and check - should be empty
        snapshot = MagicMock()
        snapshot.id = "test-snapshot"

        runtime.start(
            request_id="test-request",
            snapshot=snapshot,
            parameters={},
        )

        outputs = runtime.get_outputs()
        assert outputs == {}

    def test_step_outputs_empty_data(self):
        """Test recording empty outputs."""
        snapshot = MagicMock()
        snapshot.id = "test-snapshot"

        runtime.start(
            request_id="test-request",
            snapshot=snapshot,
            parameters={},
        )

        # Record empty outputs
        runtime.record_step_outputs("step1", {})
        runtime.record_step_outputs("step2", None)

        outputs = runtime.get_outputs()
        assert outputs == {}

    def test_step_outputs_multiple_updates(self):
        """Test multiple updates to same step outputs."""
        snapshot = MagicMock()
        snapshot.id = "test-snapshot"

        runtime.start(
            request_id="test-request",
            snapshot=snapshot,
            parameters={},
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

    def test_in_memory_data_storage(self):
        """Test in-memory data storage and retrieval."""
        snapshot = MagicMock()
        snapshot.id = "test-snapshot"

        runtime.start(
            request_id="test-request",
            snapshot=snapshot,
            parameters={},
        )

        # Store some data
        runtime.put_in_memory_data("memory://artifact/1", {"data": "value1"})
        runtime.put_in_memory_data("memory://artifact/2", "string_value")

        # Retrieve data
        assert runtime.get_in_memory_data("memory://artifact/1") == {
            "data": "value1"
        }
        assert (
            runtime.get_in_memory_data("memory://artifact/2") == "string_value"
        )
        assert runtime.get_in_memory_data("memory://missing") is None

        # Check existence
        assert runtime.has_in_memory_data("memory://artifact/1")
        assert runtime.has_in_memory_data("memory://artifact/2")
        assert not runtime.has_in_memory_data("memory://missing")

    def test_in_memory_data_inactive_context(self):
        """Test in-memory data operations when context is inactive."""
        # Don't start context
        runtime.put_in_memory_data("memory://artifact/1", {"data": "value"})

        # Should not store anything
        assert runtime.get_in_memory_data("memory://artifact/1") is None
        assert not runtime.has_in_memory_data("memory://artifact/1")

    def test_context_isolation(self):
        """Test that multiple contexts don't interfere with each other."""
        snapshot1 = MagicMock()
        snapshot1.id = "snapshot-1"

        snapshot2 = MagicMock()
        snapshot2.id = "snapshot-2"

        # Start first context
        runtime.start(
            request_id="request-1",
            snapshot=snapshot1,
            parameters={"city": "Berlin"},
        )

        runtime.record_step_outputs("step1", {"result": "berlin_result"})
        runtime.put_in_memory_data("memory://artifact/1", "berlin_data")

        # Verify first context state
        assert runtime.get_parameter_override("city") == "Berlin"
        assert runtime.get_outputs()["step1"]["result"] == "berlin_result"
        assert (
            runtime.get_in_memory_data("memory://artifact/1") == "berlin_data"
        )

        # Stop first context
        runtime.stop()

        # Start second context
        runtime.start(
            request_id="request-2",
            snapshot=snapshot2,
            parameters={"city": "Munich"},
        )

        # Should have clean state
        assert runtime.get_parameter_override("city") == "Munich"
        assert runtime.get_outputs() == {}
        assert runtime.get_in_memory_data("memory://artifact/1") is None

    def test_use_in_memory_setting(self):
        """Test use_in_memory setting functionality."""
        snapshot = MagicMock()
        snapshot.id = "test-snapshot"

        # Test with use_in_memory=True
        runtime.start(
            request_id="test-request",
            snapshot=snapshot,
            parameters={},
            use_in_memory=True,
        )

        assert runtime.get_use_in_memory() is True
        assert runtime.should_use_in_memory() is True

        runtime.stop()

        # Test with use_in_memory=False
        runtime.start(
            request_id="test-request",
            snapshot=snapshot,
            parameters={},
            use_in_memory=False,
        )

        assert runtime.get_use_in_memory() is False
        assert runtime.should_use_in_memory() is False

        runtime.stop()

        # Test with use_in_memory=None (default)
        runtime.start(
            request_id="test-request",
            snapshot=snapshot,
            parameters={},
        )

        assert runtime.get_use_in_memory() is None
        assert runtime.should_use_in_memory() is False

    def test_use_in_memory_inactive_context(self):
        """Test use_in_memory functions when context is inactive."""
        assert runtime.get_use_in_memory() is None
        assert runtime.should_use_in_memory() is False

    def test_context_reset_clears_all_data(self):
        """Test that context reset clears all stored data."""
        snapshot = MagicMock()
        snapshot.id = "test-snapshot"

        runtime.start(
            request_id="test-request",
            snapshot=snapshot,
            parameters={"city": "Berlin"},
            use_in_memory=True,
        )

        # Store various types of data
        runtime.record_step_outputs("step1", {"result": "output"})
        runtime.put_in_memory_data("memory://artifact/1", "data")

        # Verify data is stored
        assert runtime.is_active()
        assert runtime.get_parameter_override("city") == "Berlin"
        assert runtime.get_outputs() != {}
        assert runtime.has_in_memory_data("memory://artifact/1")
        assert runtime.get_use_in_memory() is True

        # Stop context (triggers reset)
        runtime.stop()

        # Verify everything is cleared
        assert not runtime.is_active()

        # Start new context to verify clean state
        runtime.start(
            request_id="new-request",
            snapshot=snapshot,
            parameters={},
        )

        assert runtime.get_outputs() == {}
        assert runtime.get_in_memory_data("memory://artifact/1") is None
        assert not runtime.has_in_memory_data("memory://artifact/1")
        assert runtime.get_use_in_memory() is None


class TestRuntimeOutputProcessing:
    """Test runtime output processing functions."""

    def test_process_outputs_with_runtime_data(self):
        """Test processing outputs using runtime data (fast path)."""
        # Mock runtime outputs
        runtime_outputs = {
            "step1": {"result": "fast_value"},
            "step2": {"prediction": "class_a", "confidence": 0.95},
        }

        mock_run = MagicMock()  # Won't be used for fast path

        outputs = runtime.process_outputs(
            runtime_outputs=runtime_outputs,
            run=mock_run,
            enforce_size_limits=False,
            max_output_size_mb=1,
        )

        assert "step1.result" in outputs
        assert "step2.prediction" in outputs
        assert "step2.confidence" in outputs
        assert outputs["step1.result"] == "fast_value"
        assert outputs["step2.prediction"] == "class_a"
        assert outputs["step2.confidence"] == 0.95

    def test_process_outputs_size_limiting(self):
        """Test output processing with size limiting."""
        # Create large data exceeding 1MB
        large_data = "x" * (2 * 1024 * 1024)  # 2MB string
        small_data = "small"

        runtime_outputs = {
            "step1": {"large_output": large_data},
            "step2": {"small_output": small_data},
        }

        mock_run = MagicMock()

        outputs = runtime.process_outputs(
            runtime_outputs=runtime_outputs,
            run=mock_run,
            enforce_size_limits=True,
            max_output_size_mb=1,
        )

        # Large output should be metadata
        large_result = outputs["step1.large_output"]
        assert isinstance(large_result, dict)
        assert large_result["data_too_large"] is True
        assert "size_estimate" in large_result
        assert "max_size_mb" in large_result

        # Small output should pass through
        assert outputs["step2.small_output"] == small_data

    def test_process_outputs_fallback_to_artifacts(self):
        """Test output processing falls back to artifact loading."""
        mock_run = MagicMock()
        mock_run.steps = {"step1": MagicMock()}

        # Mock step outputs
        mock_artifact = MagicMock()
        mock_run.steps["step1"].outputs = {"result": [mock_artifact]}

        with patch(
            "zenml.artifacts.utils.load_artifact_from_response"
        ) as mock_load:
            mock_load.return_value = "artifact_value"

            outputs = runtime.process_outputs(
                runtime_outputs=None,  # No runtime data, should use fallback
                run=mock_run,
                enforce_size_limits=True,
                max_output_size_mb=1,
            )

            assert "step1.result" in outputs
            assert outputs["step1.result"] == "artifact_value"

    def test_serialize_json_safe_basic_types(self):
        """Test JSON serialization of basic types."""
        # Test basic types pass through
        assert runtime._make_json_safe("string") == "string"
        assert runtime._make_json_safe(42) == 42
        assert runtime._make_json_safe(3.14) == 3.14
        assert runtime._make_json_safe(True) is True
        assert runtime._make_json_safe([1, 2, 3]) == [1, 2, 3]
        assert runtime._make_json_safe({"key": "value"}) == {"key": "value"}

    def test_serialize_json_safe_fallback(self):
        """Test JSON serialization fallback for non-serializable types."""

        # Test with a non-serializable object
        class NonSerializable:
            def __str__(self):
                return "NonSerializable object"

        obj = NonSerializable()
        result = runtime._make_json_safe(obj)

        # Should fallback to string representation
        assert isinstance(result, str)
        assert "NonSerializable object" in result

    def test_serialize_json_safe_truncation(self):
        """Test JSON serialization truncates long strings."""

        # Create a very long non-serializable string
        class LongObject:
            def __str__(self):
                return "x" * 2000  # Over 1000 char limit

        obj = LongObject()
        result = runtime._make_json_safe(obj)

        # Should be truncated with ellipsis
        assert isinstance(result, str)
        assert len(result) <= 1020  # 1000 + "... [truncated]"
        assert result.endswith("... [truncated]")
