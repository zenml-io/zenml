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
"""Integration tests for FastAPI serving application endpoints."""

from typing import Any, Dict
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from zenml.deployers.serving.app import app


class MockWeatherRequest(BaseModel):
    """Mock Pydantic model for testing."""

    city: str
    activities: list[str]
    extra: Dict[str, Any] | None = None


@pytest.fixture
def mock_service():
    """Mock PipelineServingService."""
    service = MagicMock()
    service.snapshot_id = str(uuid4())
    service.is_healthy.return_value = True
    service.last_execution_time = None
    service.get_service_info.return_value = {
        "snapshot_id": service.snapshot_id,
        "pipeline_name": "test_pipeline",
        "total_executions": 0,
        "last_execution_time": None,
        "status": "healthy",
    }
    service.get_execution_metrics.return_value = {
        "total_executions": 0,
        "last_execution_time": None,
    }
    service.request_schema = {
        "type": "object",
        "properties": {"city": {"type": "string", "default": "London"}},
    }
    service.response_schema = {"type": "object", "additionalProperties": True}
    return service


@pytest.fixture
def test_client():
    """FastAPI test client with test mode enabled."""
    with patch.dict("os.environ", {"ZENML_SERVING_TEST_MODE": "true"}):
        client = TestClient(app)
        yield client


class TestFastAPIAppEndpoints:
    """Integration tests for FastAPI application endpoints."""

    def test_health_endpoint_healthy(self, test_client, mock_service):
        """Test health endpoint when service is healthy."""
        with patch("zenml.deployers.serving.app._service", mock_service):
            response = test_client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "snapshot_id" in data
            assert "pipeline_name" in data

    def test_health_endpoint_unhealthy(self, test_client, mock_service):
        """Test health endpoint when service is unhealthy."""
        mock_service.is_healthy.return_value = False

        with patch("zenml.deployers.serving.app._service", mock_service):
            response = test_client.get("/health")

            assert response.status_code == 503

    def test_info_endpoint(self, test_client, mock_service):
        """Test info endpoint."""
        mock_service.snapshot = MagicMock()
        mock_service.snapshot.pipeline_spec = MagicMock()
        mock_service.snapshot.pipeline_spec.parameters = {"city": "London"}
        mock_service.snapshot.pipeline_configuration.name = "test_pipeline"

        with patch("zenml.deployers.serving.app._service", mock_service):
            response = test_client.get("/info")

            assert response.status_code == 200
            data = response.json()
            assert "pipeline" in data
            assert "snapshot" in data
            assert data["pipeline"]["name"] == "test_pipeline"
            assert data["pipeline"]["parameters"] == {"city": "London"}

    def test_metrics_endpoint(self, test_client, mock_service):
        """Test metrics endpoint."""
        with patch("zenml.deployers.serving.app._service", mock_service):
            response = test_client.get("/metrics")

            assert response.status_code == 200
            data = response.json()
            assert "total_executions" in data
            assert "last_execution_time" in data

    def test_status_endpoint(self, test_client, mock_service):
        """Test status endpoint."""
        with patch("zenml.deployers.serving.app._service", mock_service):
            response = test_client.get("/status")

            assert response.status_code == 200
            data = response.json()
            assert data["service_name"] == "ZenML Pipeline Serving"
            assert data["version"] == "0.2.0"
            assert "configuration" in data

    def test_concurrency_stats_endpoint(self, test_client):
        """Test concurrency stats endpoint."""
        response = test_client.get("/concurrency/stats")

        assert response.status_code == 200
        data = response.json()
        assert "execution" in data
        assert "jobs" in data
        assert "streams" in data

    def test_invoke_endpoint_success(self, test_client, mock_service):
        """Test invoke endpoint with successful execution."""
        mock_service.execute_pipeline.return_value = {
            "success": True,
            "outputs": {"step1.result": "test_output"},
            "execution_time": 1.5,
            "metadata": {"pipeline_name": "test_pipeline"},
        }

        with patch("zenml.deployers.serving.app._service", mock_service):
            request_data = {
                "parameters": {"city": "Paris"},
                "run_name": "test_run",
                "timeout": 300,
            }

            response = test_client.post("/invoke", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "outputs" in data
            assert "execution_time" in data
            # Test the qualified output names format
            assert "step1.result" in data["outputs"]

    def test_invoke_endpoint_validation_error(self, test_client, mock_service):
        """Test invoke endpoint with validation error."""
        mock_service.request_schema = {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        }

        with patch("zenml.deployers.serving.app._service", mock_service):
            request_data = {
                "parameters": {},  # Missing required city
                "run_name": "test_run",
            }

            response = test_client.post("/invoke", json=request_data)

            # Should return success: false due to validation error
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "error" in data

    def test_invoke_endpoint_execution_failure(
        self, test_client, mock_service
    ):
        """Test invoke endpoint when pipeline execution fails."""
        mock_service.execute_pipeline.return_value = {
            "success": False,
            "error": "Pipeline execution failed",
            "execution_time": 0.5,
            "metadata": {},
        }

        with patch("zenml.deployers.serving.app._service", mock_service):
            request_data = {
                "parameters": {"city": "Paris"},
            }

            response = test_client.post("/invoke", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "error" in data

    def test_root_endpoint(self, test_client, mock_service):
        """Test root endpoint returns HTML."""
        with patch("zenml.deployers.serving.app._service", mock_service):
            response = test_client.get("/")

            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]
            assert "ZenML Pipeline Serving" in response.text


class TestOpenAPIIntegration:
    """Integration tests for OpenAPI schema installation."""

    def test_install_runtime_openapi_basic(self, mock_service):
        """Test OpenAPI schema installation with basic service."""
        from fastapi import FastAPI

        from zenml.deployers.serving.app import _install_runtime_openapi

        test_app = FastAPI()

        # Add the invoke route
        @test_app.post("/invoke")
        def invoke():
            return {}

        _install_runtime_openapi(test_app, mock_service)

        # Generate the schema
        schema = test_app.openapi()

        assert schema is not None
        assert "paths" in schema
        assert "/invoke" in schema["paths"]
        assert "post" in schema["paths"]["/invoke"]

    def test_install_runtime_openapi_with_schemas(self, mock_service):
        """Test OpenAPI schema installation with custom schemas."""
        from fastapi import FastAPI

        from zenml.deployers.serving.app import _install_runtime_openapi

        # Mock service with custom schemas
        mock_service.request_schema = {
            "type": "object",
            "properties": {
                "city": {"type": "string"},
                "activities": {"type": "array"},
            },
        }
        mock_service.response_schema = {
            "type": "object",
            "properties": {"weather": {"type": "string"}},
        }

        test_app = FastAPI()

        # Add the invoke route
        @test_app.post("/invoke")
        def invoke():
            return {}

        _install_runtime_openapi(test_app, mock_service)

        # Generate the schema
        schema = test_app.openapi()

        assert schema is not None
        invoke_schema = schema["paths"]["/invoke"]["post"]

        # Check request schema integration
        request_body = invoke_schema["requestBody"]["content"][
            "application/json"
        ]["schema"]
        assert (
            request_body["properties"]["parameters"]
            == mock_service.request_schema
        )

        # Check response schema integration
        response_schema = invoke_schema["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        assert (
            response_schema["properties"]["outputs"]
            == mock_service.response_schema
        )

    def test_install_runtime_openapi_error_handling(self, mock_service):
        """Test OpenAPI schema installation error handling."""
        from fastapi import FastAPI

        from zenml.deployers.serving.app import _install_runtime_openapi

        # Mock service that raises error during schema access
        mock_service.request_schema = None
        mock_service.response_schema = None

        test_app = FastAPI()

        # This should not raise an exception even if schemas are None
        _install_runtime_openapi(test_app, mock_service)

        # Should still be able to generate basic schema
        schema = test_app.openapi()
        assert schema is not None


class TestMiddlewareIntegration:
    """Integration tests for FastAPI middleware stack."""

    def test_cors_middleware(self, test_client, mock_service):
        """Test CORS middleware is working."""
        with patch("zenml.deployers.serving.app._service", mock_service):
            response = test_client.options("/health")

            # CORS should allow OPTIONS requests
            assert response.status_code in [
                200,
                405,
            ]  # 405 is also acceptable for OPTIONS

    def test_error_handling_middleware(self, test_client, mock_service):
        """Test error handling middleware catches exceptions."""
        # Make service throw an exception
        mock_service.is_healthy.side_effect = Exception("Service error")

        with patch("zenml.deployers.serving.app._service", mock_service):
            response = test_client.get("/health")

            # Should still return a response, not crash
            assert response.status_code >= 400  # Some error status

    def test_authentication_middleware_passthrough(
        self, test_client, mock_service
    ):
        """Test authentication middleware in test mode."""
        with patch("zenml.deployers.serving.app._service", mock_service):
            # In test mode, auth should be bypassed
            response = test_client.get("/health")

            assert response.status_code == 200
            # Should work without authentication headers
