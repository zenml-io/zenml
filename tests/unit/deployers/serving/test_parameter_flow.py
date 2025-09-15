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
"""Comprehensive test for parameter resolution and flow in serving."""

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from zenml.deployers.serving import runtime
from zenml.deployers.serving.service import PipelineServingService


class WeatherRequest(BaseModel):
    """Mock WeatherRequest for testing."""

    city: str
    activities: List[str]
    extra: Optional[Dict[str, Any]] = None


class TestParameterResolution:
    """Test parameter resolution in serving context."""

    @pytest.fixture(autouse=True)
    def setup_serving_state(self):
        """Set up serving state for each test."""
        runtime.stop()  # Ensure clean state
        yield
        runtime.stop()  # Clean up after test

    def test_get_step_parameters_basic(self):
        """Test basic step parameter resolution."""
        # Start serving context
        snapshot = MagicMock()
        snapshot.id = "test-snapshot"

        runtime.start(
            request_id="test-request",
            snapshot=snapshot,
            parameters={
                "country": "Germany",
                "temperature": 20,
                "active": True,
            },
        )

        # Test direct parameter access
        params = runtime.get_step_parameters("test_step")
        assert params["country"] == "Germany"
        assert params["temperature"] == 20
        assert params["active"] is True

        # Test filtered access
        filtered = runtime.get_step_parameters(
            "test_step", ["country", "temperature"]
        )
        assert filtered == {"country": "Germany", "temperature": 20}
        assert "active" not in filtered

    def test_get_parameter_override_direct_only(self):
        """Test that only direct parameters are returned (no nested extraction)."""
        # Set up serving state with WeatherRequest
        request_obj = WeatherRequest(
            city="munich",
            activities=["sightseeing", "eating"],
            extra={"budget": 500},
        )

        snapshot = MagicMock()
        snapshot.id = "test-snapshot"

        runtime.start(
            request_id="test-request",
            snapshot=snapshot,
            parameters={
                "request": request_obj,
                "country": "Germany",
            },
        )

        # Direct parameter only
        assert runtime.get_parameter_override("country") == "Germany"
        # Nested attributes are not extracted automatically
        assert runtime.get_parameter_override("city") is None
        assert runtime.get_parameter_override("activities") is None
        assert runtime.get_parameter_override("extra") is None

    # Removed precedence test: nested extraction no longer supported

    def test_inactive_serving_context(self):
        """Test parameter resolution when serving is not active."""
        # Don't start serving context
        assert runtime.get_parameter_override("city") is None

    def test_empty_pipeline_parameters(self):
        """Test parameter resolution with empty pipeline parameters."""
        snapshot = MagicMock()
        snapshot.id = "test-snapshot"

        runtime.start(
            request_id="test-request", snapshot=snapshot, parameters={}
        )

        # Should return None when no parameters are available
        assert runtime.get_parameter_override("city") is None

    # Removed complex object extraction test: not supported


class TestCompleteParameterFlow:
    """Test complete parameter flow from request to step execution."""

    @pytest.fixture(autouse=True)
    def setup_serving_state(self):
        """Set up serving state for each test."""
        runtime.stop()
        yield
        runtime.stop()

    @pytest.fixture
    def mock_pipeline_class(self):
        """Mock pipeline class with WeatherRequest signature."""

        class MockWeatherPipeline:
            @staticmethod
            def entrypoint(
                request: WeatherRequest = WeatherRequest(
                    city="London",
                    activities=["walking", "reading"],
                    extra={"temperature": 20},
                ),
                country: str = "UK",
            ) -> str:
                return f"Weather for {request.city} in {country}"

        return MockWeatherPipeline

    @pytest.fixture
    def mock_snapshot(self, mock_pipeline_class):
        """Mock snapshot with WeatherRequest defaults."""
        snapshot = MagicMock()
        snapshot.id = "test-snapshot-id"
        snapshot.pipeline_spec = MagicMock()
        snapshot.pipeline_spec.source = "mock.pipeline.source"
        snapshot.pipeline_spec.parameters = {
            "request": {
                "city": "London",
                "activities": ["walking", "reading"],
                "extra": {"temperature": 20},
            },
            "country": "UK",
        }
        return snapshot

    @patch(
        "zenml.deployers.serving.parameters.build_params_model_from_snapshot"
    )
    @patch("zenml.utils.source_utils.load")
    def test_complete_parameter_resolution_flow(
        self,
        mock_load,
        mock_build_params,
        mock_snapshot,
        mock_pipeline_class,
    ):
        """Test the complete parameter resolution flow from request to step execution."""
        # Set up mocks
        mock_load.return_value = mock_pipeline_class
        # Provide a real params model for validation
        from pydantic import BaseModel

        class _Params(BaseModel):
            request: WeatherRequest
            country: str = "UK"

        mock_build_params.return_value = _Params

        # Create service
        service = PipelineServingService("test-snapshot-id")
        service.snapshot = mock_snapshot

        # Test 1: Parameter resolution in serving service
        request_params = {
            "request": {"city": "munich", "activities": ["whatever"]},
            "country": "Germany",
        }

        resolved_params = service._resolve_parameters(request_params)

        # Verify parameter resolution (no automatic merging of nested defaults)
        assert isinstance(resolved_params["request"], WeatherRequest)
        assert resolved_params["request"].city == "munich"
        assert resolved_params["request"].activities == ["whatever"]
        assert resolved_params["request"].extra is None
        assert resolved_params["country"] == "Germany"

        # Test 2: Runtime state setup
        runtime.start(
            request_id="test-request",
            snapshot=mock_snapshot,
            parameters=resolved_params,
        )

        # Test 3: Step parameter resolution (direct only)
        request_param = runtime.get_parameter_override("request")
        country_param = runtime.get_parameter_override("country")

        # Verify only direct parameters are resolved
        assert isinstance(request_param, WeatherRequest)
        assert request_param.city == "munich"
        assert request_param.activities == ["whatever"]
        assert country_param == "Germany"

    @patch(
        "zenml.deployers.serving.parameters.build_params_model_from_snapshot"
    )
    @patch("zenml.utils.source_utils.load")
    def test_partial_update_with_complex_nesting(
        self,
        mock_load,
        mock_build_params,
        mock_snapshot,
        mock_pipeline_class,
    ):
        """Test partial updates with complex nested structures."""
        mock_load.return_value = mock_pipeline_class
        # Note: mock_pipeline_class used via mock_load.return_value
        from pydantic import BaseModel

        class _Params(BaseModel):
            request: WeatherRequest
            country: str = "UK"

        mock_build_params.return_value = _Params

        service = PipelineServingService("test-snapshot-id")
        service.snapshot = mock_snapshot

        # Test update with required fields provided
        request_params = {"request": {"city": "paris", "activities": []}}

        resolved_params = service._resolve_parameters(request_params)

        # Verify partial update does not merge nested defaults automatically
        request_obj = resolved_params["request"]
        assert isinstance(request_obj, WeatherRequest)
        assert request_obj.city == "paris"  # Updated
        assert request_obj.activities == []
        assert request_obj.extra is None
        # country remains the default provided by the model if any; otherwise absent

    @patch("zenml.utils.source_utils.load")
    def test_error_handling_in_parameter_flow(
        self, mock_load, mock_snapshot, mock_pipeline_class
    ):
        """Test error handling throughout the parameter flow."""
        # Test with invalid pipeline source
        mock_load.side_effect = Exception("Cannot load pipeline")
        # Note: mock_pipeline_class not used in this test but required by fixture
        del mock_pipeline_class

        service = PipelineServingService("test-snapshot-id")
        service.snapshot = mock_snapshot

        request_params = {"request": {"city": "berlin"}}

        # Should gracefully fall back to original parameters
        resolved_params = service._resolve_parameters(request_params)

        # Should return fallback without crashing
        assert resolved_params is not None
        assert "request" in resolved_params

    def test_weather_pipeline_scenario(self):
        """Test the exact scenario from the weather pipeline."""
        # This simulates the exact case:
        # @pipeline
        # def weather_agent_pipeline(request: WeatherRequest = ..., country: str = "UK"):
        #     weather_data = get_weather(city=request.city, country=country)

        request_obj = WeatherRequest(
            city="munich", activities=["whatever"], extra=None
        )

        snapshot = MagicMock()
        snapshot.id = "test-snapshot"

        runtime.start(
            request_id="test-request",
            snapshot=snapshot,
            parameters={
                "request": request_obj,
                "country": "Germany",
            },
        )

        # Simulate the get_weather step trying to resolve its parameters
        request_param = runtime.get_parameter_override("request")
        country_param = runtime.get_parameter_override("country")

        # These should be the values that get passed to get_weather()
        assert request_param.city == "munich"
        assert country_param == "Germany"

        # This is exactly what should happen in the serving pipeline:
        # get_weather(city="munich", country="Germany")
        # instead of the compiled defaults: get_weather(city="London", country="UK")


class TestOutputRecording:
    """Test output recording and retrieval functionality."""

    @pytest.fixture(autouse=True)
    def setup_serving_state(self):
        """Set up serving state for each test."""
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
