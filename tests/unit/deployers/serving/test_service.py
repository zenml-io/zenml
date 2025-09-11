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
"""Unit tests for PipelineServingService."""

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import BaseModel

from zenml.deployers.serving.service import PipelineServingService


class MockWeatherRequest(BaseModel):
    """Mock Pydantic model for testing."""

    city: str
    activities: List[str]
    extra: Optional[Dict[str, Any]] = None


class MockSimpleRequest(BaseModel):
    """Simple mock request for testing."""

    name: str
    age: int
    active: bool = True


@pytest.fixture
def deployment_id():
    """Mock deployment ID."""
    return str(uuid4())


@pytest.fixture
def mock_pipeline_class():
    """Mock pipeline class with different parameter signatures."""

    class MockPipeline:
        @staticmethod
        def entrypoint_simple(name: str = "test") -> str:
            return f"Hello {name}"

        @staticmethod
        def entrypoint_pydantic(
            request: MockWeatherRequest = MockWeatherRequest(
                city="London", activities=["walking"], extra={"temp": 20}
            ),
        ) -> str:
            return f"Weather for {request.city}"

        @staticmethod
        def entrypoint_mixed(
            name: str = "test",
            request: MockSimpleRequest = MockSimpleRequest(
                name="John", age=25
            ),
            count: int = 5,
        ) -> Dict[str, Any]:
            return {"name": name, "request": request, "count": count}

    return MockPipeline


@pytest.fixture
def mock_deployment(mock_pipeline_class):
    """Mock deployment response."""
    deployment = MagicMock()
    deployment.id = uuid4()

    # Mock pipeline configuration
    deployment.pipeline_configuration = MagicMock()

    # Mock pipeline spec
    deployment.pipeline_spec = MagicMock()
    deployment.pipeline_spec.source = "mock.pipeline.source"
    deployment.pipeline_spec.parameters = {
        "name": "test_param",
        "count": 42,
        "active": True,
    }

    return deployment


@pytest.fixture
def mock_pydantic_deployment(mock_pipeline_class):
    """Mock deployment with Pydantic parameter."""
    deployment = MagicMock()
    deployment.id = uuid4()

    # Mock pipeline configuration with Pydantic model
    deployment.pipeline_configuration = MagicMock()

    # Mock pipeline spec
    deployment.pipeline_spec = MagicMock()
    deployment.pipeline_spec.source = "mock.pipeline.source"
    deployment.pipeline_spec.parameters = {
        "request": MockWeatherRequest(
            city="London",
            activities=["walking", "reading"],
            extra={"temperature": 20},
        )
    }

    return deployment


class TestPipelineServingService:
    """Test cases for PipelineServingService."""

    def test_initialization(self, deployment_id):
        """Test service initialization."""
        service = PipelineServingService(deployment_id)

        assert service.deployment_id == deployment_id
        assert service.deployment is None
        assert service.total_executions == 0
        assert service.last_execution_time is None
        assert service._cached_orchestrator is None

    def test_json_serialization_basic_types(self, deployment_id):
        """Test JSON serialization of basic types."""
        service = PipelineServingService(deployment_id)

        # Test basic types
        assert service._serialize_json_safe("string") == "string"
        assert service._serialize_json_safe(42) == 42
        assert service._serialize_json_safe(3.14) == 3.14
        assert service._serialize_json_safe(True) is True
        assert service._serialize_json_safe([1, 2, 3]) == [1, 2, 3]
        assert service._serialize_json_safe({"key": "value"}) == {
            "key": "value"
        }

    def test_json_serialization_complex_types(self, deployment_id):
        """Test JSON serialization of complex types."""
        service = PipelineServingService(deployment_id)

        # Test Pydantic model
        model = MockWeatherRequest(city="Paris", activities=["shopping"])
        serialized = service._serialize_json_safe(model)

        # Should be JSON-serializable (will pass through pydantic_encoder)
        assert isinstance(serialized, MockWeatherRequest)

    def test_json_serialization_fallback(self, deployment_id):
        """Test JSON serialization fallback for non-serializable types."""
        service = PipelineServingService(deployment_id)

        # Test with a non-serializable object
        class NonSerializable:
            def __str__(self):
                return "NonSerializable object"

        obj = NonSerializable()
        result = service._serialize_json_safe(obj)

        # Should fallback to string representation
        assert isinstance(result, str)
        assert "NonSerializable object" in result

    def test_parameter_resolution_simple(self, deployment_id, mock_deployment):
        """Test parameter resolution with simple types."""
        service = PipelineServingService(deployment_id)
        service.deployment = mock_deployment

        # Test merging request params with defaults
        request_params = {"name": "override", "new_param": "added"}
        resolved = service._resolve_parameters(request_params)

        assert resolved["name"] == "override"  # Request overrides default
        assert resolved["count"] == 42  # Default preserved
        assert resolved["active"] is True  # Default preserved
        assert resolved["new_param"] == "added"  # New param added

    @patch("zenml.utils.source_utils.load")
    def test_convert_parameter_types_pydantic(
        self,
        mock_load,
        deployment_id,
        mock_pydantic_deployment,
        mock_pipeline_class,
    ):
        """Test parameter type conversion for Pydantic models."""
        service = PipelineServingService(deployment_id)
        service.deployment = mock_pydantic_deployment

        # Mock source_utils.load to return our mock pipeline
        mock_pipeline_class.entrypoint = (
            mock_pipeline_class.entrypoint_pydantic
        )
        mock_load.return_value = mock_pipeline_class

        # Test converting dict to Pydantic model
        params = {
            "request": {
                "city": "Paris",
                "activities": ["shopping", "dining"],
                "extra": {"temperature": 15},
            }
        }

        converted = service._convert_parameter_types(params)

        assert isinstance(converted["request"], MockWeatherRequest)
        assert converted["request"].city == "Paris"
        assert converted["request"].activities == ["shopping", "dining"]
        assert converted["request"].extra == {"temperature": 15}

    @patch("zenml.utils.source_utils.load")
    def test_convert_parameter_types_mixed(
        self, mock_load, deployment_id, mock_deployment, mock_pipeline_class
    ):
        """Test parameter type conversion with mixed types."""
        service = PipelineServingService(deployment_id)
        service.deployment = mock_deployment

        # Mock source_utils.load to return our mock pipeline
        mock_pipeline_class.entrypoint = mock_pipeline_class.entrypoint_mixed
        mock_load.return_value = mock_pipeline_class

        # Test converting mixed parameters
        params = {
            "name": "test_user",
            "request": {"name": "Jane", "age": 30, "active": False},
            "count": 10,
        }

        converted = service._convert_parameter_types(params)

        assert converted["name"] == "test_user"  # String unchanged
        assert converted["count"] == 10  # Int unchanged
        assert isinstance(converted["request"], MockSimpleRequest)
        assert converted["request"].name == "Jane"
        assert converted["request"].age == 30
        assert converted["request"].active is False

    def test_convert_parameter_types_fallback(
        self, deployment_id, mock_deployment
    ):
        """Test parameter type conversion fallback when signature loading fails."""
        service = PipelineServingService(deployment_id)
        service.deployment = mock_deployment

        # No pipeline_spec source - should fallback
        service.deployment.pipeline_spec.source = None

        params = {"name": "test", "value": 123}
        converted = service._convert_parameter_types(params)

        # Should return unchanged
        assert converted == params

    @patch("zenml.utils.source_utils.load")
    def test_request_schema_simple(
        self, mock_load, deployment_id, mock_deployment, mock_pipeline_class
    ):
        """Test request schema generation for simple types."""
        service = PipelineServingService(deployment_id)
        service.deployment = mock_deployment

        # Mock source_utils.load to return our mock pipeline
        mock_pipeline_class.entrypoint = mock_pipeline_class.entrypoint_simple
        mock_load.return_value = mock_pipeline_class

        schema = service.request_schema

        assert schema is not None
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "name" in schema["properties"]
        assert schema["properties"]["name"]["type"] == "string"
        assert schema["properties"]["name"]["default"] == "test_param"

    @patch("zenml.utils.source_utils.load")
    def test_request_schema_pydantic(
        self,
        mock_load,
        deployment_id,
        mock_pydantic_deployment,
        mock_pipeline_class,
    ):
        """Test request schema generation for Pydantic models."""
        service = PipelineServingService(deployment_id)
        service.deployment = mock_pydantic_deployment

        # Mock source_utils.load to return our mock pipeline
        mock_pipeline_class.entrypoint = (
            mock_pipeline_class.entrypoint_pydantic
        )
        mock_load.return_value = mock_pipeline_class

        schema = service.request_schema

        assert schema is not None
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "request" in schema["properties"]

        # Check that Pydantic model schema is properly embedded
        request_schema = schema["properties"]["request"]
        assert "properties" in request_schema
        assert "city" in request_schema["properties"]
        assert "activities" in request_schema["properties"]
        assert request_schema["properties"]["city"]["type"] == "string"
        assert request_schema["properties"]["activities"]["type"] == "array"

    def test_request_schema_fallback(self, deployment_id, mock_deployment):
        """Test request schema generation fallback."""
        service = PipelineServingService(deployment_id)
        service.deployment = mock_deployment

        # No pipeline_spec - should use fallback
        service.deployment.pipeline_spec = None

        schema = service.request_schema
        assert schema is None

    def test_response_schema(self, deployment_id):
        """Test response schema generation."""
        service = PipelineServingService(deployment_id)

        schema = service.response_schema

        assert schema is not None
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is True
        assert "Pipeline execution outputs" in schema["description"]

    def test_service_info(self, deployment_id, mock_deployment):
        """Test service info generation."""
        service = PipelineServingService(deployment_id)
        service.deployment = mock_deployment
        service.total_executions = 5

        # Mock pipeline name
        mock_deployment.pipeline_configuration.name = "test_pipeline"

        info = service.get_service_info()

        assert info["deployment_id"] == str(deployment_id)
        assert info["pipeline_name"] == "test_pipeline"
        assert info["total_executions"] == 5
        assert info["status"] == "healthy"

    def test_service_info_uninitialized(self, deployment_id):
        """Test service info when not initialized."""
        service = PipelineServingService(deployment_id)

        info = service.get_service_info()
        assert "error" in info
        assert info["error"] == "Service not initialized"

    def test_execution_metrics(self, deployment_id):
        """Test execution metrics."""
        service = PipelineServingService(deployment_id)
        service.total_executions = 10

        metrics = service.get_execution_metrics()

        assert metrics["total_executions"] == 10
        assert "last_execution_time" in metrics

    def test_is_healthy(self, deployment_id, mock_deployment):
        """Test health check."""
        service = PipelineServingService(deployment_id)

        # Not healthy when no deployment
        assert not service.is_healthy()

        # Healthy when deployment is set
        service.deployment = mock_deployment
        assert service.is_healthy()

    def test_map_outputs_with_memory_data(self, deployment_id):
        """Test output mapping using in-memory data (fast path)."""
        from zenml.deployers.serving import runtime

        service = PipelineServingService(deployment_id)
        service.deployment = MagicMock()

        # Mock pipeline run
        mock_run = MagicMock()

        # Set up serving context with in-memory outputs
        deployment = MagicMock()
        deployment.id = "test-deployment"

        runtime.start(
            request_id="test-request", deployment=deployment, parameters={}
        )

        # Record outputs in memory
        runtime.record_step_outputs("step1", {"output1": "fast_value1"})
        runtime.record_step_outputs("step2", {"result": "fast_value2"})

        try:
            outputs = service._map_outputs(mock_run)

            # Should use fast in-memory data
            assert "step1.output1" in outputs
            assert "step2.result" in outputs
            assert outputs["step1.output1"] == "fast_value1"
            assert outputs["step2.result"] == "fast_value2"
        finally:
            runtime.stop()

    def test_map_outputs_fallback_to_artifacts(self, deployment_id):
        """Test output mapping falls back to artifact loading when no memory data."""
        service = PipelineServingService(deployment_id)
        service.deployment = MagicMock()

        # Mock pipeline run with step outputs
        mock_run = MagicMock()
        mock_run.steps = {"step1": MagicMock(), "step2": MagicMock()}

        # Mock step outputs
        mock_artifact = MagicMock()
        mock_run.steps["step1"].outputs = {"output1": [mock_artifact]}
        mock_run.steps["step2"].outputs = {"result": [mock_artifact]}

        # Ensure no serving context (should use fallback)
        from zenml.deployers.serving import runtime

        runtime.stop()

        with patch(
            "zenml.artifacts.utils.load_artifact_from_response"
        ) as mock_load:
            mock_load.return_value = "artifact_value"

            outputs = service._map_outputs(mock_run)

            assert "step1.output1" in outputs
            assert "step2.result" in outputs
            assert outputs["step1.output1"] == "artifact_value"
            assert outputs["step2.result"] == "artifact_value"

    def test_map_outputs_with_error(self, deployment_id):
        """Test output mapping with artifact loading error."""
        service = PipelineServingService(deployment_id)
        service.deployment = MagicMock()

        # Mock pipeline run with step outputs
        mock_run = MagicMock()
        mock_run.steps = {"step1": MagicMock()}

        # Mock step outputs
        mock_artifact = MagicMock()
        mock_run.steps["step1"].outputs = {"output1": [mock_artifact]}

        # Ensure no serving context (should use fallback)
        from zenml.deployers.serving import runtime

        runtime.stop()

        with patch(
            "zenml.artifacts.utils.load_artifact_from_response"
        ) as mock_load:
            mock_load.side_effect = Exception("Loading failed")

            outputs = service._map_outputs(mock_run)

            # Should skip failed artifacts and return empty dict
            assert outputs == {}

    def test_map_outputs_size_limiting(self, deployment_id):
        """Test output mapping with size limiting."""
        from zenml.deployers.serving import runtime

        service = PipelineServingService(deployment_id)
        service.deployment = MagicMock()

        # Mock pipeline run
        mock_run = MagicMock()

        # Set up serving context
        deployment = MagicMock()
        deployment.id = "test-deployment"

        runtime.start(
            request_id="test-request", deployment=deployment, parameters={}
        )

        # Create large data that exceeds default 1MB limit
        large_data = "x" * (2 * 1024 * 1024)  # 2MB string
        small_data = "small_value"

        # Record outputs
        runtime.record_step_outputs("step1", {"large_output": large_data})
        runtime.record_step_outputs("step2", {"small_output": small_data})

        try:
            outputs = service._map_outputs(mock_run)

            # Large output should be replaced with metadata
            assert "step1.large_output" in outputs
            large_result = outputs["step1.large_output"]
            assert isinstance(large_result, dict)
            assert large_result["data_too_large"] is True
            assert "size_estimate" in large_result
            assert "max_size_mb" in large_result

            # Small output should be included normally
            assert outputs["step2.small_output"] == small_data
        finally:
            runtime.stop()

    def test_get_max_output_size_bytes_default(self, deployment_id):
        """Test default max output size."""
        service = PipelineServingService(deployment_id)

        # Should default to 1MB
        assert service._get_max_output_size_bytes() == 1024 * 1024

    def test_get_max_output_size_bytes_env_var(self, deployment_id):
        """Test max output size from environment variable."""
        service = PipelineServingService(deployment_id)

        with patch.dict(
            "os.environ", {"ZENML_SERVING_MAX_OUTPUT_SIZE_MB": "5"}
        ):
            assert service._get_max_output_size_bytes() == 5 * 1024 * 1024

    def test_get_max_output_size_bytes_invalid_values(self, deployment_id):
        """Test max output size with invalid environment values."""
        service = PipelineServingService(deployment_id)

        # Test zero value
        with patch.dict(
            "os.environ", {"ZENML_SERVING_MAX_OUTPUT_SIZE_MB": "0"}
        ):
            assert (
                service._get_max_output_size_bytes() == 1024 * 1024
            )  # Falls back to 1MB

        # Test negative value
        with patch.dict(
            "os.environ", {"ZENML_SERVING_MAX_OUTPUT_SIZE_MB": "-5"}
        ):
            assert (
                service._get_max_output_size_bytes() == 1024 * 1024
            )  # Falls back to 1MB

        # Test non-numeric value
        with patch.dict(
            "os.environ", {"ZENML_SERVING_MAX_OUTPUT_SIZE_MB": "invalid"}
        ):
            assert (
                service._get_max_output_size_bytes() == 1024 * 1024
            )  # Falls back to 1MB


class TestPipelineServingServiceIntegration:
    """Integration tests for complete workflow."""

    @patch("zenml.utils.source_utils.load")
    def test_full_parameter_conversion_workflow(
        self, mock_load, deployment_id, mock_pipeline_class
    ):
        """Test the complete parameter conversion workflow."""
        service = PipelineServingService(deployment_id)

        # Set up mock deployment
        service.deployment = MagicMock()
        service.deployment.pipeline_configuration = MagicMock()
        service.deployment.pipeline_configuration.parameters = {
            "request": MockWeatherRequest(
                city="London", activities=["walking"]
            )
        }
        service.deployment.pipeline_spec = MagicMock()
        service.deployment.pipeline_spec.source = "test.source"

        # Mock source loading
        mock_pipeline_class.entrypoint = (
            mock_pipeline_class.entrypoint_pydantic
        )
        mock_load.return_value = mock_pipeline_class

        # Test the full workflow
        request_params = {
            "request": {
                "city": "Tokyo",
                "activities": ["sightseeing", "eating"],
                "extra": {"budget": 500},
            }
        }

        resolved = service._resolve_parameters(request_params)

        # Verify the parameter was converted to Pydantic model
        assert isinstance(resolved["request"], MockWeatherRequest)
        assert resolved["request"].city == "Tokyo"
        assert resolved["request"].activities == ["sightseeing", "eating"]
        assert resolved["request"].extra == {"budget": 500}

    @patch("zenml.utils.source_utils.load")
    def test_partial_pydantic_parameter_update(
        self,
        mock_load,
        deployment_id,
        mock_pydantic_deployment,
        mock_pipeline_class,
    ):
        """Test that partial Pydantic model updates are merged correctly."""
        service = PipelineServingService(deployment_id)
        service.deployment = mock_pydantic_deployment

        # Mock source loading
        mock_pipeline_class.entrypoint = (
            mock_pipeline_class.entrypoint_pydantic
        )
        mock_load.return_value = mock_pipeline_class

        # Send a request that only updates one field of the Pydantic model
        request_params = {"request": {"city": "Tokyo"}}

        resolved = service._resolve_parameters(request_params)

        # Verify the parameter was converted to a Pydantic model
        assert isinstance(resolved["request"], MockWeatherRequest)
        # Verify the specified field was updated
        assert resolved["request"].city == "Tokyo"
        # Verify the other fields were preserved from the default
        assert resolved["request"].activities == ["walking", "reading"]
        assert resolved["request"].extra == {"temperature": 20}

    @patch("zenml.utils.source_utils.load")
    def test_schema_generation_with_pydantic_defaults(
        self, mock_load, deployment_id, mock_pipeline_class
    ):
        """Test schema generation includes Pydantic model defaults."""
        service = PipelineServingService(deployment_id)

        # Set up mock deployment with Pydantic default
        default_request = MockWeatherRequest(
            city="London",
            activities=["walking", "reading"],
            extra={"temperature": 20},
        )

        service.deployment = MagicMock()
        service.deployment.pipeline_spec = MagicMock()
        service.deployment.pipeline_spec.parameters = {
            "request": default_request
        }
        service.deployment.pipeline_spec.source = "test.source"
        service.deployment.pipeline_configuration = MagicMock()

        # Mock source loading
        mock_pipeline_class.entrypoint = (
            mock_pipeline_class.entrypoint_pydantic
        )
        mock_load.return_value = mock_pipeline_class

        schema = service.request_schema

        # Verify schema includes default values
        assert schema is not None
        request_prop = schema["properties"]["request"]
        assert "default" in request_prop
        assert request_prop["default"]["city"] == "London"
        assert request_prop["default"]["activities"] == ["walking", "reading"]
        assert request_prop["default"]["extra"]["temperature"] == 20
