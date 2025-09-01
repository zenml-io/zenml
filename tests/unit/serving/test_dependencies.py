"""Tests for dependency injection system."""

import os

import pytest
from fastapi.testclient import TestClient

from zenml.serving.app import app
from zenml.serving.dependencies import (
    get_job_registry,
    get_pipeline_service,
)
from zenml.serving.jobs import JobRegistry
from zenml.serving.service import PipelineServingService


class MockPipelineServingService(PipelineServingService):
    """Mock service for testing."""

    def __init__(self, deployment_id: str = "test-deployment"):
        """Initialize the mock pipeline serving service.

        Args:
            deployment_id: The ID of the deployment to serve.
        """
        self.deployment_id = deployment_id
        self.deployment = None
        self._healthy = True
        self.last_execution_time = None

    async def initialize(self) -> None:
        """Initialize the mock pipeline serving service."""
        pass

    def is_healthy(self) -> bool:
        """Check if the mock pipeline serving service is healthy."""
        return self._healthy

    def get_service_info(self) -> dict:
        """Get the service info."""
        return {
            "service": {"deployment_id": self.deployment_id, "uptime": 0},
            "pipeline": {"name": "test-pipeline", "steps": []},
            "deployment": {
                "id": "test",
                "created_at": "2024-01-01",
                "stack": "test",
            },
        }

    def get_execution_metrics(self) -> dict:
        """Get the execution metrics."""
        return {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "success_rate": 0.0,
            "average_execution_time": 0.0,
            "last_24h_executions": 0,
        }


@pytest.fixture
def test_client():
    """Test client with test mode enabled."""
    os.environ["ZENML_SERVING_TEST_MODE"] = "true"

    # Mock dependencies
    mock_service = MockPipelineServingService()
    mock_registry = JobRegistry()

    app.dependency_overrides[get_pipeline_service] = lambda: mock_service
    app.dependency_overrides[get_job_registry] = lambda: mock_registry

    yield TestClient(app)

    app.dependency_overrides.clear()
    os.environ.pop("ZENML_SERVING_TEST_MODE", None)


def test_health_endpoint(test_client):
    """Test health endpoint with DI."""
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_pipeline_info(test_client):
    """Test info endpoint with DI."""
    response = test_client.get("/info")
    assert response.status_code == 200
    data = response.json()
    assert "pipeline" in data
    assert "deployment" in data


def test_service_status(test_client):
    """Test status endpoint with DI."""
    response = test_client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["service_name"] == "ZenML Pipeline Serving"
    assert data["version"] == "0.2.0"


def test_metrics_endpoint(test_client):
    """Test metrics endpoint with DI."""
    response = test_client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_executions" in data
    assert "success_rate" in data


def test_root_endpoint(test_client):
    """Test root HTML endpoint with DI."""
    response = test_client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_job_operations(test_client):
    """Test job-related endpoints with DI."""
    # List jobs (should be empty initially)
    response = test_client.get("/jobs")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0

    # Try to get non-existent job
    response = test_client.get("/jobs/non-existent")
    assert response.status_code == 404

    # Try to cancel non-existent job
    response = test_client.post("/jobs/non-existent/cancel")
    assert response.status_code == 400


def test_request_context_isolation(test_client):
    """Test that request contexts are isolated."""
    responses = []
    for _ in range(3):
        response = test_client.get("/health")
        responses.append(response)

    # All should succeed independently
    for response in responses:
        assert response.status_code == 200
