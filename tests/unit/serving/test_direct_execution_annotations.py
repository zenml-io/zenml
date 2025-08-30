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
"""Unit tests for DirectExecutionEngine annotation parsing."""

from typing import Annotated
from unittest.mock import Mock, patch

from zenml.serving.capture import Capture
from zenml.serving.direct_execution import DirectExecutionEngine


class MockStepClass:
    """Mock step class for testing annotation parsing."""

    def __init__(self, entrypoint_func):
        self.entrypoint = entrypoint_func


class TestDirectExecutionEngineAnnotations:
    """Test annotation parsing in DirectExecutionEngine."""

    def test_parse_input_annotations(self):
        """Test parsing input parameter annotations."""

        # Create a mock step function with annotations
        def mock_step_func(
            data: Annotated[str, Capture("none")],
            config: Annotated[dict, Capture("full", max_bytes=32000)],
            regular_param: str,
        ) -> str:
            return "result"

        step_class = MockStepClass(mock_step_func)

        # Create a mock engine
        engine = Mock(spec=DirectExecutionEngine)
        engine._step_capture_overrides = {}

        # Call the method directly
        DirectExecutionEngine._parse_step_capture_annotations(
            engine, "test_step", step_class
        )

        # Check that annotations were parsed correctly
        overrides = engine._step_capture_overrides["test_step"]

        # Input annotations should be captured
        assert "data" in overrides["inputs"]
        assert overrides["inputs"]["data"].mode.value == "none"

        assert "config" in overrides["inputs"]
        assert overrides["inputs"]["config"].mode.value == "full"
        assert overrides["inputs"]["config"].max_bytes == 32000

        # Regular parameter should have None annotation
        assert "regular_param" in overrides["inputs"]
        assert overrides["inputs"]["regular_param"] is None

    def test_parse_output_annotations(self):
        """Test parsing return type annotations."""

        # Create a mock step function with return annotation
        def mock_step_func(
            data: str,
        ) -> Annotated[dict, Capture("sampled", artifacts="full")]:
            return {"result": data}

        step_class = MockStepClass(mock_step_func)

        # Create a mock engine
        engine = Mock(spec=DirectExecutionEngine)
        engine._step_capture_overrides = {}

        # Call the method directly
        DirectExecutionEngine._parse_step_capture_annotations(
            engine, "test_step", step_class
        )

        # Check that output annotation was parsed correctly
        overrides = engine._step_capture_overrides["test_step"]

        assert "output" in overrides["outputs"]
        assert overrides["outputs"]["output"].mode.value == "sampled"
        assert overrides["outputs"]["output"].artifacts == "full"

    def test_parse_no_annotations(self):
        """Test parsing step with no annotations."""

        def mock_step_func(data: str, config: dict) -> str:
            return "result"

        step_class = MockStepClass(mock_step_func)

        # Create a mock engine
        engine = Mock(spec=DirectExecutionEngine)
        engine._step_capture_overrides = {}

        # Call the method directly
        DirectExecutionEngine._parse_step_capture_annotations(
            engine, "test_step", step_class
        )

        # Check that no annotations were found
        overrides = engine._step_capture_overrides["test_step"]

        # All inputs should have None annotations
        assert overrides["inputs"]["data"] is None
        assert overrides["inputs"]["config"] is None

        # No output annotations
        assert len(overrides["outputs"]) == 0

    def test_parse_mixed_annotations(self):
        """Test parsing with some annotated and some regular parameters."""

        def mock_step_func(
            annotated_input: Annotated[str, Capture("none")],
            regular_input: str,
            another_annotated: Annotated[dict, Capture("full")],
        ) -> Annotated[str, Capture("errors_only", artifacts="sampled")]:
            return "result"

        step_class = MockStepClass(mock_step_func)

        # Create a mock engine
        engine = Mock(spec=DirectExecutionEngine)
        engine._step_capture_overrides = {}

        # Call the method directly
        DirectExecutionEngine._parse_step_capture_annotations(
            engine, "test_step", step_class
        )

        overrides = engine._step_capture_overrides["test_step"]

        # Check mixed inputs
        assert overrides["inputs"]["annotated_input"].mode.value == "none"
        assert overrides["inputs"]["regular_input"] is None
        assert overrides["inputs"]["another_annotated"].mode.value == "full"

        # Check output
        assert overrides["outputs"]["output"].mode.value == "errors_only"
        assert overrides["outputs"]["output"].artifacts == "sampled"

    def test_parse_error_handling(self):
        """Test error handling during annotation parsing."""
        # Create a step class without entrypoint
        step_class = Mock()
        del step_class.entrypoint  # Remove entrypoint attribute

        # Create a mock engine
        engine = Mock(spec=DirectExecutionEngine)
        engine._step_capture_overrides = {}

        # Should not raise exception, should set empty overrides
        DirectExecutionEngine._parse_step_capture_annotations(
            engine, "test_step", step_class
        )

        # Should have empty overrides
        overrides = engine._step_capture_overrides["test_step"]
        assert overrides["inputs"] == {}
        assert overrides["outputs"] == {}

    @patch("zenml.serving.direct_execution.logger")
    def test_parse_annotation_warning_on_failure(self, mock_logger):
        """Test that parsing failures are logged as warnings."""
        # Create a step class that will cause an exception during parsing
        step_class = Mock()
        step_class.entrypoint = Mock()

        # Make inspect.signature raise an exception
        with patch(
            "zenml.serving.direct_execution.inspect.signature",
            side_effect=Exception("Test error"),
        ):
            # Create a mock engine
            engine = Mock(spec=DirectExecutionEngine)
            engine._step_capture_overrides = {}

            # Call the method - should not raise
            DirectExecutionEngine._parse_step_capture_annotations(
                engine, "test_step", step_class
            )

            # Should log warning
            mock_logger.warning.assert_called_once()
            assert "Failed to parse capture annotations" in str(
                mock_logger.warning.call_args
            )

            # Should still set empty overrides
            overrides = engine._step_capture_overrides["test_step"]
            assert overrides["inputs"] == {}
            assert overrides["outputs"] == {}


class TestCaptureOverridesRetrieval:
    """Test getting capture overrides from engine."""

    def test_get_step_capture_overrides(self):
        """Test retrieving step capture overrides."""
        # Create a mock engine with some overrides
        engine = Mock(spec=DirectExecutionEngine)
        test_overrides = {
            "step1": {
                "inputs": {"param1": Capture("none")},
                "outputs": {"output": Capture("full")},
            },
            "step2": {"inputs": {"param2": None}, "outputs": {}},
        }
        engine._step_capture_overrides = test_overrides

        # Call the method
        result = DirectExecutionEngine.get_step_capture_overrides(engine)

        # Should return a copy of the overrides
        assert result == test_overrides
        # Should be a different object (copy, not reference)
        assert result is not test_overrides
