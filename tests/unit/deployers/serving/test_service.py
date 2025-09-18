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
"""Unit tests for the simplified PipelineServingService."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import BaseModel

from zenml.deployers.serving.service import PipelineServingService


class MockWeatherRequest(BaseModel):
    """Mock Pydantic model for testing."""

    city: str
    temperature: int = 20


@pytest.fixture
def snapshot_id():
    """Mock snapshot ID."""
    return uuid4()


@pytest.fixture
def mock_snapshot():
    """Mock snapshot response."""
    snapshot = MagicMock()
    snapshot.id = uuid4()
    snapshot.pipeline_configuration = MagicMock()
    snapshot.pipeline_configuration.name = "test_pipeline"
    snapshot.pipeline_configuration.init_hook_source = None
    snapshot.pipeline_configuration.cleanup_hook_source = None
    snapshot.pipeline_spec = MagicMock()
    snapshot.pipeline_spec.response_schema = None
    snapshot.step_configurations = {
        "step1": MagicMock(),
        "step2": MagicMock(),
    }
    snapshot.stack = MagicMock()
    snapshot.stack.name = "test_stack"
    return snapshot


@pytest.fixture
def mock_params_model():
    """Mock parameter model."""
    return MockWeatherRequest


class TestPipelineServingService:
    """Test cases for PipelineServingService."""

    def test_initialization(self, snapshot_id):
        """Test service initialization."""
        service = PipelineServingService(snapshot_id)

        assert service.snapshot_id == snapshot_id
        assert service.snapshot is None
        assert service.total_executions == 0
        assert service.last_execution_time is None
        assert service._orchestrator is None
        assert service._params_model is None
        assert service.pipeline_state is None

    def test_max_output_size_bytes_default(self, snapshot_id):
        """Test default max output size."""
        service = PipelineServingService(snapshot_id)

        # Should default to 1MB
        assert service._get_max_output_size_bytes() == 1024 * 1024

    def test_max_output_size_bytes_env_var(self, snapshot_id):
        """Test max output size from environment variable."""
        service = PipelineServingService(snapshot_id)

        with patch.dict(
            "os.environ", {"ZENML_SERVING_MAX_OUTPUT_SIZE_MB": "5"}
        ):
            assert service._get_max_output_size_bytes() == 5 * 1024 * 1024

    def test_max_output_size_bytes_bounds(self, snapshot_id):
        """Test max output size bounds checking."""
        service = PipelineServingService(snapshot_id)

        # Test zero value (should fall back to 1MB)
        with patch.dict(
            "os.environ", {"ZENML_SERVING_MAX_OUTPUT_SIZE_MB": "0"}
        ):
            assert service._get_max_output_size_bytes() == 1024 * 1024

        # Test over limit (should cap at 100MB)
        with patch.dict(
            "os.environ", {"ZENML_SERVING_MAX_OUTPUT_SIZE_MB": "200"}
        ):
            assert service._get_max_output_size_bytes() == 100 * 1024 * 1024

    def test_json_serialization_basic_types(self, snapshot_id):
        """Test JSON serialization of basic types."""
        service = PipelineServingService(snapshot_id)

        # Test basic types pass through
        assert service._serialize_json_safe("string") == "string"
        assert service._serialize_json_safe(42) == 42
        assert service._serialize_json_safe(3.14) == 3.14
        assert service._serialize_json_safe(True) is True
        assert service._serialize_json_safe([1, 2, 3]) == [1, 2, 3]
        assert service._serialize_json_safe({"key": "value"}) == {
            "key": "value"
        }

    def test_json_serialization_pydantic_models(self, snapshot_id):
        """Test JSON serialization of Pydantic models."""
        service = PipelineServingService(snapshot_id)

        # Test Pydantic model
        model = MockWeatherRequest(city="Paris", temperature=15)
        serialized = service._serialize_json_safe(model)

        # Should pass through for pydantic_encoder to handle
        assert isinstance(serialized, MockWeatherRequest)
        assert serialized.city == "Paris"
        assert serialized.temperature == 15

    def test_json_serialization_fallback(self, snapshot_id):
        """Test JSON serialization fallback for non-serializable types."""
        service = PipelineServingService(snapshot_id)

        # Test with a non-serializable object
        class NonSerializable:
            def __str__(self):
                return "NonSerializable object"

        obj = NonSerializable()
        result = service._serialize_json_safe(obj)

        # Should fallback to string representation
        assert isinstance(result, str)
        assert "NonSerializable object" in result

    def test_json_serialization_truncation(self, snapshot_id):
        """Test JSON serialization truncates long strings."""
        service = PipelineServingService(snapshot_id)

        # Create a very long non-serializable string
        class LongObject:
            def __str__(self):
                return "x" * 2000  # Over 1000 char limit

        obj = LongObject()
        result = service._serialize_json_safe(obj)

        # Should be truncated with ellipsis
        assert isinstance(result, str)
        assert len(result) <= 1020  # 1000 + "... [truncated]"
        assert result.endswith("... [truncated]")

    @patch(
        "zenml.deployers.serving.parameters.build_params_model_from_snapshot"
    )
    @patch("zenml.client.Client")
    def test_parameter_resolution(
        self,
        mock_client,
        mock_build_params,
        snapshot_id,
        mock_snapshot,
        mock_params_model,
    ):
        """Test parameter resolution with Pydantic model."""
        service = PipelineServingService(snapshot_id)
        service.snapshot = mock_snapshot
        service._params_model = mock_params_model

        # Test parameter validation and resolution - this uses the actual MockWeatherRequest
        request_params = {"city": "Berlin", "temperature": 25}

        result = service._resolve_parameters(request_params)

        # Should preserve the Pydantic object structure
        assert result["city"] == "Berlin"
        assert result["temperature"] == 25

    def test_map_outputs_with_runtime_data(self, snapshot_id):
        """Test output mapping using runtime in-memory data (fast path)."""
        from zenml.deployers.serving import runtime

        service = PipelineServingService(snapshot_id)

        # Mock run object (won't be used for fast path)
        mock_run = MagicMock()

        # Set up runtime context with in-memory outputs
        snapshot = MagicMock()
        snapshot.id = "test-snapshot"

        runtime.start(
            request_id="test-request",
            snapshot=snapshot,
            parameters={},
        )

        # Record outputs in memory
        runtime.record_step_outputs("step1", {"result": "fast_value"})
        runtime.record_step_outputs("step2", {"prediction": "class_a"})

        try:
            outputs = service._map_outputs(mock_run)

            # Should use fast in-memory data
            assert "step1.result" in outputs
            assert "step2.prediction" in outputs
            assert outputs["step1.result"] == "fast_value"
            assert outputs["step2.prediction"] == "class_a"
        finally:
            runtime.stop()

    @patch("zenml.artifacts.utils.load_artifact_from_response")
    def test_map_outputs_fallback_to_artifacts(self, mock_load, snapshot_id):
        """Test output mapping falls back to artifact loading when no runtime data."""
        from zenml.deployers.serving import runtime

        service = PipelineServingService(snapshot_id)

        # Ensure no serving context (should use fallback)
        runtime.stop()

        # Mock pipeline run with step outputs
        mock_run = MagicMock()
        mock_run.steps = {"step1": MagicMock(), "step2": MagicMock()}

        # Mock step outputs
        mock_artifact = MagicMock()
        mock_run.steps["step1"].outputs = {"result": [mock_artifact]}
        mock_run.steps["step2"].outputs = {"prediction": [mock_artifact]}

        # Mock artifact loading
        mock_load.return_value = "artifact_value"

        outputs = service._map_outputs(mock_run)

        assert "step1.result" in outputs
        assert "step2.prediction" in outputs
        assert outputs["step1.result"] == "artifact_value"
        assert outputs["step2.prediction"] == "artifact_value"

    def test_map_outputs_size_limiting(self, snapshot_id):
        """Test output mapping with size limiting for large data."""
        from zenml.deployers.serving import runtime

        service = PipelineServingService(snapshot_id)

        # Mock pipeline run
        mock_run = MagicMock()

        # Set up serving context
        snapshot = MagicMock()
        snapshot.id = "test-snapshot"

        runtime.start(
            request_id="test-request",
            snapshot=snapshot,
            parameters={},
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
            assert large_result["type"] == "str"

            # Small output should be included normally
            assert outputs["step2.small_output"] == small_data
        finally:
            runtime.stop()

    def test_map_outputs_serialization_failure(self, snapshot_id):
        """Test output mapping handles serialization failures."""
        from zenml.deployers.serving import runtime

        service = PipelineServingService(snapshot_id)

        # Mock pipeline run
        mock_run = MagicMock()

        # Set up serving context
        snapshot = MagicMock()
        snapshot.id = "test-snapshot"

        runtime.start(
            request_id="test-request",
            snapshot=snapshot,
            parameters={},
        )

        # Create object that will cause serialization to fail
        class UnserializableObject:
            def __str__(self):
                raise Exception("Cannot convert to string")

        bad_obj = UnserializableObject()

        # Record outputs
        runtime.record_step_outputs("step1", {"bad_output": bad_obj})

        # Mock the runtime serializer to fail
        with patch(
            "zenml.deployers.serving.runtime._make_json_safe",
            side_effect=Exception("Serialization failed"),
        ):
            try:
                outputs = service._map_outputs(mock_run)

                # Should handle the error gracefully
                assert "step1.bad_output" in outputs
                result = outputs["step1.bad_output"]
                assert isinstance(result, dict)
                assert result["serialization_failed"] is True
                assert "type" in result
                assert "note" in result
            finally:
                runtime.stop()

    @patch("zenml.client.Client")
    @patch("zenml.orchestrators.local.local_orchestrator.LocalOrchestrator")
    def test_execute_with_orchestrator(
        self,
        mock_orchestrator_class,
        mock_client,
        snapshot_id,
        mock_snapshot,
    ):
        """Test pipeline execution with orchestrator."""
        service = PipelineServingService(snapshot_id)
        service.snapshot = mock_snapshot
        service._orchestrator = MagicMock()

        # Mock client and stack
        mock_client_instance = mock_client.return_value
        mock_stack = MagicMock()
        mock_client_instance.active_stack = mock_stack

        # Mock placeholder run and final run
        with patch(
            "zenml.pipelines.run_utils.create_placeholder_run"
        ) as mock_create_run:
            mock_placeholder_run = MagicMock()
            mock_placeholder_run.id = "test-run-id"
            mock_create_run.return_value = mock_placeholder_run

            mock_final_run = MagicMock()
            mock_client_instance.get_pipeline_run.return_value = mock_final_run

            resolved_params = {"city": "Berlin", "temperature": 25}
            result = service._execute_with_orchestrator(resolved_params)

            # Verify orchestrator was called
            service._orchestrator.run.assert_called_once_with(
                snapshot=mock_snapshot,
                stack=mock_stack,
                placeholder_run=mock_placeholder_run,
            )

            # Verify final run was fetched
            mock_client_instance.get_pipeline_run.assert_called_once_with(
                name_id_or_prefix="test-run-id",
                hydrate=True,
                include_full_metadata=True,
            )

            assert result == mock_final_run

    def test_build_success_response(self, snapshot_id, mock_snapshot):
        """Test building success response."""
        service = PipelineServingService(snapshot_id)
        service.snapshot = mock_snapshot

        mapped_outputs = {"step1.result": "success"}
        resolved_params = {"city": "Berlin"}
        mock_run = MagicMock()
        mock_run.id = "run-123"
        mock_run.name = "test_run"

        start_time = 1234567890.0

        # Mock time.time() to return a fixed value
        with patch("time.time", return_value=1234567892.5):
            response = service._build_success_response(
                mapped_outputs=mapped_outputs,
                start_time=start_time,
                resolved_params=resolved_params,
                run=mock_run,
            )

        assert response["success"] is True
        assert response["outputs"] == mapped_outputs
        assert response["execution_time"] == 2.5
        assert response["metadata"]["pipeline_name"] == "test_pipeline"
        assert response["metadata"]["run_id"] == "run-123"
        assert response["metadata"]["run_name"] == "test_run"
        assert response["metadata"]["snapshot_id"] == str(mock_snapshot.id)

        # Verify counters are updated
        assert service.total_executions == 1
        assert service.last_execution_time is not None

    def test_build_error_response(self, snapshot_id):
        """Test building error response."""
        service = PipelineServingService(snapshot_id)

        error = Exception("Something went wrong")
        start_time = 1234567890.0

        with patch("time.time", return_value=1234567892.0):
            response = service._build_error_response(
                e=error, start_time=start_time
            )

        assert response["success"] is False
        assert response["job_id"] is None
        assert response["error"] == "Something went wrong"
        assert response["execution_time"] == 2.0
        assert response["metadata"] == {}

    def test_service_info(self, snapshot_id, mock_snapshot):
        """Test service info generation."""
        service = PipelineServingService(snapshot_id)
        service.snapshot = mock_snapshot
        service.total_executions = 5

        info = service.get_service_info()

        assert info["snapshot_id"] == str(snapshot_id)
        assert info["pipeline_name"] == "test_pipeline"
        assert info["total_executions"] == 5
        assert info["status"] == "healthy"
        assert "last_execution_time" in info

    def test_service_info_uninitialized(self, snapshot_id):
        """Test service info when not initialized."""
        service = PipelineServingService(snapshot_id)

        info = service.get_service_info()
        assert "error" in info
        assert info["error"] == "Service not initialized"

    def test_execution_metrics(self, snapshot_id):
        """Test execution metrics."""
        service = PipelineServingService(snapshot_id)
        service.total_executions = 10

        metrics = service.get_execution_metrics()

        assert metrics["total_executions"] == 10
        assert "last_execution_time" in metrics

    def test_is_healthy(self, snapshot_id, mock_snapshot):
        """Test health check."""
        service = PipelineServingService(snapshot_id)

        # Not healthy when no snapshot
        assert not service.is_healthy()

        # Healthy when snapshot is set
        service.snapshot = mock_snapshot
        assert service.is_healthy()

    @patch(
        "zenml.deployers.serving.parameters.build_params_model_from_snapshot"
    )
    @patch("zenml.client.Client")
    @patch(
        "zenml.integrations.registry.integration_registry.activate_integrations"
    )
    def test_initialize_success(
        self,
        mock_activate,
        mock_client,
        mock_build_params,
        snapshot_id,
        mock_snapshot,
        mock_params_model,
    ):
        """Test successful service initialization."""
        service = PipelineServingService(snapshot_id)

        # Mock client and snapshot loading
        mock_client_instance = mock_client.return_value
        mock_client_instance.zen_store.get_snapshot.return_value = (
            mock_snapshot
        )

        # Mock parameter model building
        mock_build_params.return_value = mock_params_model

        # Test initialization
        import asyncio

        asyncio.run(service.initialize())

        # Verify snapshot was loaded
        mock_client_instance.zen_store.get_snapshot.assert_called_once_with(
            snapshot_id=snapshot_id
        )

        # Verify integrations were activated
        mock_activate.assert_called_once()

        # Verify parameter model was built
        mock_build_params.assert_called_once_with(mock_snapshot, strict=True)

        # Verify service state
        assert service.snapshot == mock_snapshot
        assert service._params_model == mock_params_model
        assert service._orchestrator is not None

    @patch(
        "zenml.deployers.serving.parameters.build_params_model_from_snapshot"
    )
    @patch("zenml.client.Client")
    def test_initialize_failure(
        self, mock_client, mock_build_params, snapshot_id
    ):
        """Test service initialization failure."""
        service = PipelineServingService(snapshot_id)

        # Mock client to raise exception
        mock_client_instance = mock_client.return_value
        mock_client_instance.zen_store.get_snapshot.side_effect = Exception(
            "Snapshot not found"
        )

        # Test initialization fails
        import asyncio

        with pytest.raises(Exception, match="Snapshot not found"):
            asyncio.run(service.initialize())

    def test_cleanup_no_hook(self, snapshot_id, mock_snapshot):
        """Test cleanup when no cleanup hook is configured."""
        service = PipelineServingService(snapshot_id)
        service.snapshot = mock_snapshot
        mock_snapshot.pipeline_configuration.cleanup_hook_source = None

        # Should complete without error
        import asyncio

        asyncio.run(service.cleanup())

    @patch("zenml.utils.source_utils.load")
    def test_cleanup_with_sync_hook(
        self, mock_load, snapshot_id, mock_snapshot
    ):
        """Test cleanup with synchronous cleanup hook."""
        service = PipelineServingService(snapshot_id)
        service.snapshot = mock_snapshot
        mock_snapshot.pipeline_configuration.cleanup_hook_source = (
            "mock.cleanup.hook"
        )

        # Mock cleanup hook
        mock_cleanup_hook = MagicMock()
        mock_load.return_value = mock_cleanup_hook

        # Test cleanup
        import asyncio

        asyncio.run(service.cleanup())

        mock_load.assert_called_once_with("mock.cleanup.hook")
        mock_cleanup_hook.assert_called_once()

    @patch("zenml.utils.source_utils.load")
    def test_cleanup_with_async_hook(
        self, mock_load, snapshot_id, mock_snapshot
    ):
        """Test cleanup with asynchronous cleanup hook."""
        service = PipelineServingService(snapshot_id)
        service.snapshot = mock_snapshot
        mock_snapshot.pipeline_configuration.cleanup_hook_source = (
            "mock.cleanup.hook"
        )

        # Mock async cleanup hook
        async def mock_cleanup_hook():
            pass

        mock_load.return_value = mock_cleanup_hook

        # Test cleanup
        import asyncio

        asyncio.run(service.cleanup())

        mock_load.assert_called_once_with("mock.cleanup.hook")
