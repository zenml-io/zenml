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
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from zenml.deployers.server import runtime
from zenml.deployers.server.service import PipelineDeploymentService


class WeatherRequest(BaseModel):
    """Mock WeatherRequest for testing."""

    city: str
    activities: List[str]
    extra: Optional[Dict[str, Any]] = None


class TestParameterResolution:
    """Test parameter resolution in serving context."""

    @pytest.fixture(autouse=True)
    def setup_serving_state(self):
        """Set up deployment state for each test."""
        runtime.stop()  # Ensure clean state
        yield
        runtime.stop()  # Clean up after test

    def test_get_parameter_override_direct_only(self):
        """Test that only direct parameters are returned (no nested extraction)."""
        # Set up deployment state with WeatherRequest
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

    def test_inactive_deployment_context(self):
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
        """Set up deployment state for each test."""
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
        assert isinstance(request_param, WeatherRequest)
        assert request_param.city == "munich"
        assert country_param == "Germany"

        # This is exactly what should happen in the serving pipeline:
        # get_weather(city="munich", country="Germany")
        # instead of the compiled defaults: get_weather(city="London", country="UK")


class TestOutputRecording:
    """Test output recording and retrieval functionality."""

    @pytest.fixture(autouse=True)
    def setup_serving_state(self):
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
