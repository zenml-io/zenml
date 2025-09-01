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
"""Unit tests for serving tracking manager."""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from zenml.deployers.serving.events import EventType, ServingEvent
from zenml.deployers.serving.policy import (
    ArtifactCaptureMode,
    CapturePolicy,
    CapturePolicyMode,
)
from zenml.deployers.serving.tracking import TrackingManager
from zenml.enums import ExecutionStatus
from zenml.models import (
    PipelineDeploymentResponse,
    PipelineRunResponse,
    StepRunResponse,
)


@pytest.fixture
def mock_deployment():
    """Create a mock pipeline deployment."""
    deployment = Mock(spec=PipelineDeploymentResponse)
    deployment.id = uuid4()
    deployment.project_id = uuid4()
    deployment.run_name_template = "test-run-{date}-{time}"

    # Mock pipeline configuration
    deployment.pipeline = Mock()
    deployment.pipeline.id = uuid4()
    deployment.pipeline_configuration = Mock()
    deployment.pipeline_configuration.tags = ["serving", "test"]
    deployment.pipeline_configuration.finalize_substitutions = Mock(
        return_value={}
    )

    return deployment


@pytest.fixture
def mock_client():
    """Create a mock ZenML client."""
    with patch("zenml.deployers.serving.tracking.Client") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock zen store
        mock_client.zen_store = Mock()
        mock_client.active_project = Mock()
        mock_client.active_project.id = uuid4()

        yield mock_client


class TestTrackingManager:
    """Test the TrackingManager class."""

    def test_init_disabled(self, mock_deployment):
        """Test TrackingManager initialization when tracking is disabled."""
        policy = CapturePolicy(mode=CapturePolicyMode.NONE)

        with patch("zenml.deployers.serving.tracking.Client"):
            manager = TrackingManager(
                deployment=mock_deployment, policy=policy, create_runs=False
            )

        assert manager.deployment == mock_deployment
        assert manager.policy == policy
        assert not manager.create_runs
        assert manager.pipeline_run is None

    def test_init_enabled(self, mock_deployment):
        """Test TrackingManager initialization when tracking is enabled."""
        policy = CapturePolicy(mode=CapturePolicyMode.METADATA)

        with patch("zenml.deployers.serving.tracking.Client"):
            manager = TrackingManager(
                deployment=mock_deployment, policy=policy, create_runs=True
            )

        assert manager.deployment == mock_deployment
        assert manager.policy == policy
        assert manager.create_runs
        assert manager.invocation_id.startswith("serving-")

    def test_sampling_decision(self, mock_deployment):
        """Test sampling decision logic."""
        # Test non-sampled mode
        policy = CapturePolicy(mode=CapturePolicyMode.METADATA)

        with patch("zenml.deployers.serving.tracking.Client"):
            manager = TrackingManager(
                deployment=mock_deployment, policy=policy, create_runs=True
            )

        assert not manager.is_sampled

        # Test sampled mode with controlled randomness
        policy = CapturePolicy(mode=CapturePolicyMode.SAMPLED, sample_rate=0.5)

        with (
            patch("zenml.deployers.serving.tracking.Client"),
            patch(
                "zenml.deployers.serving.tracking.random.random",
                return_value=0.3,
            ),
        ):
            manager = TrackingManager(
                deployment=mock_deployment, policy=policy, create_runs=True
            )

        assert manager.is_sampled

        # Test sampled mode not triggered
        with (
            patch("zenml.deployers.serving.tracking.Client"),
            patch(
                "zenml.deployers.serving.tracking.random.random",
                return_value=0.7,
            ),
        ):
            manager = TrackingManager(
                deployment=mock_deployment, policy=policy, create_runs=True
            )

        assert not manager.is_sampled

    def test_start_pipeline_disabled(self, mock_deployment, mock_client):
        """Test start_pipeline when tracking is disabled."""
        policy = CapturePolicy(mode=CapturePolicyMode.NONE)

        manager = TrackingManager(
            deployment=mock_deployment, policy=policy, create_runs=False
        )

        result = manager.start_pipeline(params={"test": "value"})

        assert result is None
        assert manager.pipeline_run is None

    def test_start_pipeline_success(self, mock_deployment, mock_client):
        """Test successful pipeline start."""
        policy = CapturePolicy(mode=CapturePolicyMode.METADATA)

        # Mock pipeline run creation
        mock_run = Mock(spec=PipelineRunResponse)
        mock_run.id = uuid4()
        mock_run.name = "test-run"
        mock_client.zen_store.get_or_create_run.return_value = (mock_run, True)

        manager = TrackingManager(
            deployment=mock_deployment, policy=policy, create_runs=True
        )

        with patch(
            "zenml.deployers.serving.tracking.string_utils.format_name_template",
            return_value="test-run",
        ):
            result = manager.start_pipeline(params={"test": "value"})

        assert result == mock_run.id
        assert manager.pipeline_run == mock_run
        mock_client.zen_store.get_or_create_run.assert_called_once()

    def test_start_pipeline_with_payloads(self, mock_deployment, mock_client):
        """Test pipeline start with payload capture."""
        policy = CapturePolicy(mode=CapturePolicyMode.FULL)

        mock_run = Mock(spec=PipelineRunResponse)
        mock_run.id = uuid4()
        mock_client.zen_store.get_or_create_run.return_value = (mock_run, True)

        manager = TrackingManager(
            deployment=mock_deployment, policy=policy, create_runs=True
        )

        with patch(
            "zenml.deployers.serving.tracking.string_utils.format_name_template",
            return_value="test-run",
        ):
            manager.start_pipeline(
                params={"password": "secret", "user": "alice"}
            )

        # Check that the run was created with redacted parameters
        call_args = mock_client.zen_store.get_or_create_run.call_args[0][0]
        assert "parameters_preview" in call_args.config
        # Password should be redacted
        assert "[REDACTED]" in call_args.config["parameters_preview"]
        assert "alice" in call_args.config["parameters_preview"]

    def test_start_pipeline_error_handling(self, mock_deployment, mock_client):
        """Test pipeline start error handling."""
        policy = CapturePolicy(mode=CapturePolicyMode.METADATA)

        # Mock an exception during run creation
        mock_client.zen_store.get_or_create_run.side_effect = Exception(
            "DB error"
        )

        manager = TrackingManager(
            deployment=mock_deployment, policy=policy, create_runs=True
        )

        with patch(
            "zenml.deployers.serving.tracking.string_utils.format_name_template",
            return_value="test-run",
        ):
            result = manager.start_pipeline()

        assert result is None
        assert manager.pipeline_run is None

    def test_start_step_success(self, mock_deployment, mock_client):
        """Test successful step start."""
        policy = CapturePolicy(mode=CapturePolicyMode.METADATA)

        # Set up existing pipeline run
        mock_run = Mock(spec=PipelineRunResponse)
        mock_run.id = uuid4()

        # Mock step run creation
        mock_step_run = Mock(spec=StepRunResponse)
        mock_step_run.id = uuid4()
        mock_client.zen_store.create_run_step.return_value = mock_step_run

        manager = TrackingManager(
            deployment=mock_deployment, policy=policy, create_runs=True
        )
        manager.pipeline_run = mock_run

        result = manager.start_step("test_step")

        assert result == mock_step_run.id
        assert "test_step" in manager.step_runs
        assert manager.step_runs["test_step"] == mock_step_run
        assert "test_step" in manager.step_timings

    def test_start_step_no_pipeline_run(self, mock_deployment, mock_client):
        """Test step start when no pipeline run exists."""
        policy = CapturePolicy(mode=CapturePolicyMode.METADATA)

        manager = TrackingManager(
            deployment=mock_deployment, policy=policy, create_runs=True
        )

        result = manager.start_step("test_step")

        assert result is None
        assert "test_step" not in manager.step_runs

    def test_complete_step_success(self, mock_deployment, mock_client):
        """Test successful step completion."""
        policy = CapturePolicy(mode=CapturePolicyMode.METADATA)

        # Set up existing step run
        mock_step_run = Mock(spec=StepRunResponse)
        mock_step_run.id = uuid4()

        manager = TrackingManager(
            deployment=mock_deployment, policy=policy, create_runs=True
        )
        manager.step_runs["test_step"] = mock_step_run
        manager.step_timings["test_step"] = {"start": 1000.0}

        with patch("time.time", return_value=1005.0):
            manager.complete_step(
                step_name="test_step",
                output={"result": "success"},
                success=True,
            )

        mock_client.zen_store.update_run_step.assert_called_once()
        call_args = mock_client.zen_store.update_run_step.call_args[1][
            "step_run_update"
        ]
        assert call_args["status"] == ExecutionStatus.COMPLETED

        # Check timing was recorded
        assert manager.step_timings["test_step"]["duration"] == 5.0

    def test_complete_step_with_artifacts(self, mock_deployment, mock_client):
        """Test step completion with artifact persistence."""
        policy = CapturePolicy(
            mode=CapturePolicyMode.METADATA, artifacts=ArtifactCaptureMode.FULL
        )

        mock_step_run = Mock(spec=StepRunResponse)
        mock_step_run.id = uuid4()

        manager = TrackingManager(
            deployment=mock_deployment, policy=policy, create_runs=True
        )
        manager.step_runs["test_step"] = mock_step_run
        manager.step_timings["test_step"] = {"start": 1000.0}

        # Mock save_artifact
        with (
            patch(
                "zenml.deployers.serving.tracking.save_artifact"
            ) as mock_save_artifact,
            patch("time.time", return_value=1005.0),
        ):
            mock_artifact = Mock()
            mock_artifact.id = uuid4()
            mock_save_artifact.return_value = mock_artifact

            manager.complete_step(
                step_name="test_step",
                output={
                    "model": "trained_model",
                    "metrics": {"accuracy": 0.95},
                },
                success=True,
            )

        # Check artifacts were saved
        assert mock_save_artifact.call_count == 2  # One for each output

        # Check outputs mapping was passed to step update
        call_args = mock_client.zen_store.update_run_step.call_args[1][
            "step_run_update"
        ]
        assert "outputs" in call_args
        assert len(call_args["outputs"]) == 2

    def test_complete_step_error(self, mock_deployment, mock_client):
        """Test step completion on error."""
        policy = CapturePolicy(
            mode=CapturePolicyMode.METADATA,
            artifacts=ArtifactCaptureMode.ERRORS_ONLY,
        )

        mock_step_run = Mock(spec=StepRunResponse)
        mock_step_run.id = uuid4()

        manager = TrackingManager(
            deployment=mock_deployment, policy=policy, create_runs=True
        )
        manager.step_runs["test_step"] = mock_step_run
        manager.step_timings["test_step"] = {"start": 1000.0}

        with (
            patch(
                "zenml.deployers.serving.tracking.save_artifact"
            ) as mock_save_artifact,
            patch("time.time", return_value=1005.0),
        ):
            mock_artifact = Mock()
            mock_artifact.id = uuid4()
            mock_save_artifact.return_value = mock_artifact

            manager.complete_step(
                step_name="test_step",
                output={"error_context": "Failed validation"},
                success=False,
                error="Validation failed",
            )

        # Check error artifact was saved
        mock_save_artifact.assert_called_once()

        # Check status and error message
        call_args = mock_client.zen_store.update_run_step.call_args[1][
            "step_run_update"
        ]
        assert call_args["status"] == ExecutionStatus.FAILED
        assert "error_message" in call_args["metadata"]

    def test_complete_pipeline_success(self, mock_deployment, mock_client):
        """Test successful pipeline completion."""
        policy = CapturePolicy(mode=CapturePolicyMode.METADATA)

        mock_run = Mock(spec=PipelineRunResponse)
        mock_run.id = uuid4()
        mock_run.config = {"existing": "config"}

        manager = TrackingManager(
            deployment=mock_deployment, policy=policy, create_runs=True
        )
        manager.pipeline_run = mock_run
        manager.step_timings = {
            "step1": {"duration": 2.5},
            "step2": {"duration": 3.0},
        }

        with patch(
            "zenml.deployers.serving.tracking.publish_pipeline_run_status_update"
        ) as mock_publish:
            manager.complete_pipeline(
                success=True,
                execution_time=10.5,
                steps_executed=2,
                results={"final": "result"},
            )

        mock_publish.assert_called_once()
        call_args = mock_publish.call_args[1]
        assert call_args["status"] == ExecutionStatus.COMPLETED
        assert "steps_executed" in call_args["metadata"]
        assert call_args["metadata"]["steps_executed"] == 2

    def test_complete_pipeline_with_results_capture(
        self, mock_deployment, mock_client
    ):
        """Test pipeline completion with results capture."""
        policy = CapturePolicy(mode=CapturePolicyMode.FULL)

        mock_run = Mock(spec=PipelineRunResponse)
        mock_run.id = uuid4()
        mock_run.config = {}

        manager = TrackingManager(
            deployment=mock_deployment, policy=policy, create_runs=True
        )
        manager.pipeline_run = mock_run
        manager.is_sampled = True

        with patch(
            "zenml.deployers.serving.tracking.publish_pipeline_run_status_update"
        ) as mock_publish:
            manager.complete_pipeline(
                success=True,
                execution_time=10.5,
                steps_executed=2,
                results={"password": "secret", "result": "success"},
            )

        # Check that results were captured and redacted
        call_args = mock_publish.call_args[1]
        metadata = call_args["metadata"]
        assert "results_preview" in metadata
        # Password should be redacted
        assert "[REDACTED]" in metadata["results_preview"]
        assert "success" in metadata["results_preview"]

    def test_handle_event_step_started(self, mock_deployment, mock_client):
        """Test handling step_started events."""
        policy = CapturePolicy(mode=CapturePolicyMode.METADATA)

        manager = TrackingManager(
            deployment=mock_deployment, policy=policy, create_runs=True
        )

        # Mock the start_step method
        with patch.object(manager, "start_step") as mock_start_step:
            event = ServingEvent(
                event_type=EventType.STEP_STARTED,
                job_id="test-job-123",
                step_name="test_step",
                data={},
            )

            manager.handle_event(event)

            mock_start_step.assert_called_once_with("test_step")

    def test_handle_event_step_completed(self, mock_deployment, mock_client):
        """Test handling step_completed events."""
        policy = CapturePolicy(mode=CapturePolicyMode.METADATA)

        manager = TrackingManager(
            deployment=mock_deployment, policy=policy, create_runs=True
        )

        with patch.object(manager, "complete_step") as mock_complete_step:
            event = ServingEvent(
                event_type=EventType.STEP_COMPLETED,
                job_id="test-job-123",
                step_name="test_step",
                data={"output": {"result": "success"}},
            )

            manager.handle_event(event)

            mock_complete_step.assert_called_once_with(
                step_name="test_step",
                output={"result": "success"},
                success=True,
            )

    def test_handle_event_disabled(self, mock_deployment, mock_client):
        """Test that events are ignored when tracking is disabled."""
        policy = CapturePolicy(mode=CapturePolicyMode.NONE)

        manager = TrackingManager(
            deployment=mock_deployment, policy=policy, create_runs=False
        )

        with patch.object(manager, "start_step") as mock_start_step:
            event = ServingEvent(
                event_type=EventType.STEP_STARTED,
                job_id="test-job-123",
                step_name="test_step",
            )

            manager.handle_event(event)

            mock_start_step.assert_not_called()
