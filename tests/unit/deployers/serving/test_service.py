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
"""Unit tests for the simplified PipelineDeploymentService."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import BaseModel

from zenml.deployers.server import runtime
from zenml.deployers.server.service import PipelineDeploymentService


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
    snapshot.pipeline_spec.output_schema = None
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
    """Test cases for PipelineDeploymentService."""

    def test_initialization(self, snapshot_id):
        """Test service initialization."""
        service = PipelineDeploymentService(snapshot_id)

        assert service.snapshot_id == snapshot_id
        assert service.snapshot is None
        assert service.total_executions == 0
        assert service.last_execution_time is None
        assert service._orchestrator is None
        assert service._params_model is None
        assert service.pipeline_state is None

    def test_max_output_size_bytes_default(self, snapshot_id):
        """Test default max output size."""
        service = PipelineDeploymentService(snapshot_id)

        # Should default to 1MB
        assert service._get_max_output_size_bytes() == 1024 * 1024

    def test_max_output_size_bytes_env_var(self, snapshot_id):
        """Test max output size from environment variable."""
        service = PipelineDeploymentService(snapshot_id)

        with patch.dict(
            "os.environ", {"ZENML_SERVING_MAX_OUTPUT_SIZE_MB": "5"}
        ):
            assert service._get_max_output_size_bytes() == 5 * 1024 * 1024

    def test_max_output_size_bytes_bounds(self, snapshot_id):
        """Test max output size bounds checking."""
        service = PipelineDeploymentService(snapshot_id)

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

    def test_map_outputs_with_runtime_data(self, snapshot_id):
        """Test output mapping using runtime in-memory data (fast path)."""
        service = PipelineDeploymentService(snapshot_id)

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
            outputs = service._map_outputs(runtime.get_outputs())

            # Should use fast in-memory data
            assert "step1.result" in outputs
            assert "step2.prediction" in outputs
            assert outputs["step1.result"] == "fast_value"
            assert outputs["step2.prediction"] == "class_a"
        finally:
            runtime.stop()

    def test_map_outputs_empty_when_no_runtime_data(self, snapshot_id) -> None:
        """Test output mapping returns empty dict when no runtime data."""
        service = PipelineDeploymentService(snapshot_id)

        runtime.stop()

        outputs = service._map_outputs(None)

        assert outputs == {}

    def test_map_outputs_serialization_failure(self, snapshot_id):
        """Test output mapping handles serialization failures."""
        service = PipelineDeploymentService(snapshot_id)

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

        # Service leaves values unchanged; FastAPI will handle serialization.
        outputs = service._map_outputs(runtime.get_outputs())
        assert "step1.bad_output" in outputs

    @patch("zenml.client.Client")
    def test_execute_with_orchestrator(
        self,
        mock_client,
        snapshot_id,
        mock_snapshot,
    ):
        """Test pipeline execution with orchestrator."""
        service = PipelineDeploymentService(snapshot_id)
        service.snapshot = mock_snapshot
        service._orchestrator = MagicMock()

        # Mock client and stack
        mock_client_instance = mock_client.return_value
        mock_stack = MagicMock()
        mock_client_instance.active_stack = mock_stack

        mock_placeholder_run = MagicMock()
        mock_placeholder_run.id = "test-run-id"

        with (
            patch(
                "zenml.pipelines.run_utils.create_placeholder_run",
                return_value=mock_placeholder_run,
            ),
            patch(
                "zenml.deployers.server.service.runtime.start"
            ) as mock_start,
            patch("zenml.deployers.server.service.runtime.stop") as mock_stop,
            patch(
                "zenml.deployers.server.service.runtime.is_active",
                return_value=True,
            ) as mock_is_active,
            patch(
                "zenml.deployers.server.service.runtime.get_outputs",
                return_value={"step1": {"result": "fast_value"}},
            ) as mock_get_outputs,
        ):
            mock_final_run = MagicMock()
            mock_client_instance.get_pipeline_run.return_value = mock_final_run

            resolved_params = {"city": "Berlin", "temperature": 25}
            run, captured_outputs = service._execute_with_orchestrator(
                resolved_params, use_in_memory=True
            )

        # Verify runtime lifecycle hooks
        mock_start.assert_called_once()
        _, start_kwargs = mock_start.call_args
        assert start_kwargs["use_in_memory"] is True
        mock_is_active.assert_called()
        mock_get_outputs.assert_called_once()
        mock_stop.assert_called_once()

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

        assert run == mock_final_run
        assert captured_outputs == {"step1": {"result": "fast_value"}}

    def test_build_success_response(self, snapshot_id, mock_snapshot):
        """Test building success response."""
        service = PipelineDeploymentService(snapshot_id)
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
        service = PipelineDeploymentService(snapshot_id)

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
        service = PipelineDeploymentService(snapshot_id)
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
        service = PipelineDeploymentService(snapshot_id)

        info = service.get_service_info()
        assert "error" in info
        assert info["error"] == "Service not initialized"

    def test_execution_metrics(self, snapshot_id):
        """Test execution metrics."""
        service = PipelineDeploymentService(snapshot_id)
        service.total_executions = 10

        metrics = service.get_execution_metrics()

        assert metrics["total_executions"] == 10
        assert "last_execution_time" in metrics

    def test_is_healthy(self, snapshot_id, mock_snapshot):
        """Test health check."""
        service = PipelineDeploymentService(snapshot_id)

        # Not healthy when no snapshot
        assert not service.is_healthy()

        # Healthy when snapshot is set
        service.snapshot = mock_snapshot
        assert service.is_healthy()

    @patch(
        "zenml.deployers.server.parameters.build_params_model_from_snapshot"
    )
    @patch("zenml.client.Client")
    @patch("zenml.orchestrators.local.local_orchestrator.LocalOrchestrator")
    @patch(
        "zenml.integrations.registry.integration_registry.activate_integrations"
    )
    def test_initialize_success(
        self,
        mock_activate,
        mock_orchestrator,
        mock_client,
        mock_build_params,
        snapshot_id,
        mock_snapshot,
        mock_params_model,
    ):
        """Test successful service initialization."""
        service = PipelineDeploymentService(snapshot_id)

        # Mock client and snapshot loading
        mock_client_instance = mock_client.return_value
        mock_client_instance.zen_store.get_snapshot.return_value = (
            mock_snapshot
        )

        # Mock parameter model building
        mock_build_params.return_value = mock_params_model

        # Mock orchestrator
        mock_orchestrator_instance = MagicMock()
        mock_orchestrator.return_value = mock_orchestrator_instance

        # Test initialization
        service.initialize()

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
        assert service._orchestrator is mock_orchestrator_instance
        mock_orchestrator_instance.set_shared_run_state.assert_called_once_with(
            service.pipeline_state
        )

    @patch(
        "zenml.deployers.server.parameters.build_params_model_from_snapshot"
    )
    @patch("zenml.client.Client")
    def test_initialize_failure(
        self, mock_client, mock_build_params, snapshot_id
    ):
        """Test service initialization failure."""
        service = PipelineDeploymentService(snapshot_id)

        # Mock client to raise exception
        mock_client_instance = mock_client.return_value
        mock_client_instance.zen_store.get_snapshot.side_effect = Exception(
            "Snapshot not found"
        )

        # Test initialization fails
        with pytest.raises(Exception, match="Snapshot not found"):
            service.initialize()

    def test_cleanup_no_hook(self, snapshot_id, mock_snapshot):
        """Test cleanup when no cleanup hook is configured."""
        service = PipelineDeploymentService(snapshot_id)
        service.snapshot = mock_snapshot
        mock_snapshot.pipeline_configuration.cleanup_hook_source = None

        # Should complete without error
        service.cleanup()

    @patch("zenml.deployers.server.service.load_and_run_hook")
    def test_cleanup_with_sync_hook(
        self, mock_load_and_run, snapshot_id, mock_snapshot
    ):
        """Test cleanup with synchronous cleanup hook."""
        service = PipelineDeploymentService(snapshot_id)
        service.snapshot = mock_snapshot
        mock_snapshot.pipeline_configuration.cleanup_hook_source = (
            "mock.cleanup.hook"
        )

        service.cleanup()

        mock_load_and_run.assert_called_once_with("mock.cleanup.hook")

    @patch("zenml.deployers.server.service.load_and_run_hook")
    def test_cleanup_with_async_hook(
        self, mock_load_and_run, snapshot_id, mock_snapshot
    ):
        """Test cleanup with asynchronous cleanup hook."""
        service = PipelineDeploymentService(snapshot_id)
        service.snapshot = mock_snapshot
        mock_snapshot.pipeline_configuration.cleanup_hook_source = (
            "mock.cleanup.hook"
        )

        service.cleanup()

        mock_load_and_run.assert_called_once_with("mock.cleanup.hook")
