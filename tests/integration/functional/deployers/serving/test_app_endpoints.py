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

from __future__ import annotations

import importlib
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

import zenml.deployers.serving.app as serving_app


class MockWeatherRequest(BaseModel):
    """Mock Pydantic model for testing."""

    city: str
    activities: list[str]
    extra: Dict[str, Any] | None = None


class StubPipelineServingService:
    """Stub service implementing the interface used by the FastAPI app."""

    def __init__(self, snapshot_id: str) -> None:
        self.snapshot_id = snapshot_id
        self._healthy = True
        self._params_model = MockWeatherRequest
        self.execute_response: Dict[str, Any] = {
            "success": True,
            "outputs": {"step1.result": "ok"},
            "execution_time": 0.5,
            "metadata": {"pipeline_name": "test_pipeline"},
        }
        self.last_invocation: Optional[Dict[str, Any]] = None
        self.snapshot = MagicMock()
        self.snapshot.pipeline_spec = MagicMock()
        self.snapshot.pipeline_spec.parameters = {"city": "London"}
        self.snapshot.pipeline_spec.input_schema = {
            "type": "object",
            "properties": {"city": {"type": "string"}},
        }
        self.snapshot.pipeline_spec.output_schema = {
            "type": "object",
            "properties": {"result": {"type": "string"}},
        }
        self.snapshot.pipeline_configuration = MagicMock()
        self.snapshot.pipeline_configuration.name = "test_pipeline"
        self.initialized = False
        self.cleaned_up = False

    @property
    def params_model(self) -> type[BaseModel]:
        return self._params_model

    def initialize(self) -> None:  # noqa: D401
        self.initialized = True

    def cleanup(self) -> None:  # noqa: D401
        self.cleaned_up = True

    def is_healthy(self) -> bool:  # noqa: D401
        return self._healthy

    def set_health(self, healthy: bool) -> None:
        self._healthy = healthy

    def get_service_info(self) -> Dict[str, Any]:  # noqa: D401
        return {
            "snapshot_id": self.snapshot_id,
            "pipeline_name": self.snapshot.pipeline_configuration.name,
            "total_executions": 0,
            "last_execution_time": None,
            "status": "healthy" if self._healthy else "unhealthy",
        }

    def get_execution_metrics(self) -> Dict[str, Any]:  # noqa: D401
        return {
            "total_executions": 0,
            "last_execution_time": None,
        }

    def execute_pipeline(
        self,
        parameters: Dict[str, Any],
        run_name: Optional[str] = None,
        timeout: Optional[int] = None,
        use_in_memory: Optional[bool] = None,
    ) -> Dict[str, Any]:
        self.last_invocation = {
            "parameters": parameters,
            "run_name": run_name,
            "timeout": timeout,
            "use_in_memory": use_in_memory,
        }
        return self.execute_response

    @property
    def request_schema(self) -> Dict[str, Any]:  # noqa: D401
        return self.snapshot.pipeline_spec.input_schema

    @property
    def output_schema(self) -> Dict[str, Any]:  # noqa: D401
        return self.snapshot.pipeline_spec.output_schema


@pytest.fixture
def client_service_pair(monkeypatch: pytest.MonkeyPatch):
    """Provide a fresh FastAPI client and stub service per test."""

    reloaded_app = importlib.reload(serving_app)
    service = StubPipelineServingService(str(uuid4()))

    monkeypatch.setenv("ZENML_SNAPSHOT_ID", service.snapshot_id)
    monkeypatch.delenv("ZENML_SERVING_TEST_MODE", raising=False)

    with patch.object(
        reloaded_app, "PipelineServingService", return_value=service
    ):
        with TestClient(reloaded_app.app) as client:
            yield client, service, reloaded_app


@pytest.fixture
def mock_service():
    """Mock service used for OpenAPI schema assertions."""

    service = MagicMock()
    service.request_schema = {
        "type": "object",
        "properties": {"city": {"type": "string"}},
    }
    service.output_schema = {
        "type": "object",
        "properties": {"result": {"type": "string"}},
    }
    return service


class TestFastAPIAppEndpoints:
    """Integration tests for FastAPI application endpoints."""

    def test_root_endpoint(self, client_service_pair):
        """Root endpoint renders HTML."""
        client, service, _ = client_service_pair
        service.set_health(True)

        response = client.get("/")

        assert response.status_code == 200
        assert "ZenML Pipeline Serving" in response.text
        assert "text/html" in response.headers["content-type"]

    def test_health_endpoint_healthy(self, client_service_pair):
        """Test health endpoint when service is healthy."""
        client, service, _ = client_service_pair
        service.set_health(True)

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["snapshot_id"] == service.snapshot_id
        assert data["pipeline_name"] == "test_pipeline"

    def test_health_endpoint_unhealthy(self, client_service_pair):
        """Test health endpoint when service is unhealthy."""
        client, service, _ = client_service_pair
        service.set_health(False)

        response = client.get("/health")

        assert response.status_code == 503

    def test_info_endpoint(self, client_service_pair):
        """Test info endpoint."""
        client, service, _ = client_service_pair

        response = client.get("/info")

        assert response.status_code == 200
        data = response.json()
        assert data["pipeline"]["name"] == "test_pipeline"
        assert data["pipeline"]["parameters"] == {"city": "London"}
        assert data["snapshot"]["id"] == service.snapshot_id

    def test_metrics_endpoint(self, client_service_pair):
        """Test metrics endpoint."""
        client, _, _ = client_service_pair

        response = client.get("/metrics")

        assert response.status_code == 200
        data = response.json()
        assert data["total_executions"] == 0
        assert "last_execution_time" in data

    def test_status_endpoint(
        self, client_service_pair, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test status endpoint."""
        client, service, module = client_service_pair
        monkeypatch.setenv("ZENML_SERVICE_HOST", "127.0.0.1")
        monkeypatch.setenv("ZENML_SERVICE_PORT", "9000")

        with patch.object(module, "service_start_time", 1000.0):
            response = client.get("/status")

        assert response.status_code == 200
        data = response.json()
        assert data["service_name"] == "ZenML Pipeline Serving"
        assert data["version"] == "0.2.0"
        assert data["snapshot_id"] == service.snapshot_id
        assert data["configuration"]["host"] == "127.0.0.1"
        assert data["configuration"]["port"] == 9000

    def test_schema_endpoint(self, client_service_pair):
        """Test schema endpoint returns request and response schemas."""
        client, service, _ = client_service_pair

        response = client.get("/schema")

        assert response.status_code == 200
        data = response.json()
        assert data["request_schema"] == service.request_schema
        assert data["output_schema"] == service.output_schema

    def test_invoke_endpoint_success(self, client_service_pair):
        """Test invoke endpoint with successful execution."""
        client, service, _ = client_service_pair
        payload = {"parameters": {"city": "Paris", "activities": ["walk"]}}

        response = client.post("/invoke", json=payload)

        assert response.status_code == 200
        assert response.json() == service.execute_response
        assert service.last_invocation["parameters"] == payload["parameters"]

    def test_invoke_endpoint_execution_failure(self, client_service_pair):
        """Test invoke endpoint when pipeline execution fails."""
        client, service, _ = client_service_pair
        service.execute_response = {
            "success": False,
            "error": "Pipeline execution failed",
            "execution_time": 0.5,
            "metadata": {},
        }

        response = client.post(
            "/invoke", json={"parameters": {"city": "Paris"}}
        )

        assert response.status_code == 200
        assert response.json()["success"] is False

    def test_invoke_requires_auth_when_enabled(
        self, client_service_pair, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that authentication is enforced when enabled."""

        client, _, _ = client_service_pair
        monkeypatch.setenv("ZENML_SERVING_AUTH_KEY", "secret")

        response = client.post(
            "/invoke", json={"parameters": {"city": "Paris"}}
        )
        assert response.status_code == 401

        response = client.post(
            "/invoke",
            json={"parameters": {"city": "Paris"}},
            headers={"Authorization": "Bearer secret"},
        )
        assert response.status_code == 200
        monkeypatch.delenv("ZENML_SERVING_AUTH_KEY")


class TestOpenAPIIntegration:
    """Integration tests for OpenAPI schema installation."""

    def test_install_runtime_openapi_basic(self, mock_service):
        """Test OpenAPI schema installation with basic service."""
        test_app = FastAPI()

        # Add the invoke route
        @test_app.post("/invoke")
        def invoke():
            return {}

        serving_app._install_runtime_openapi(test_app, mock_service)

        # Generate the schema
        schema = test_app.openapi()

        assert schema is not None
        assert "paths" in schema
        assert "/invoke" in schema["paths"]
        assert "post" in schema["paths"]["/invoke"]

    def test_install_runtime_openapi_with_schemas(self, mock_service):
        """Test OpenAPI schema installation with custom schemas."""
        # Mock service with custom schemas
        mock_service.request_schema = {
            "type": "object",
            "properties": {
                "city": {"type": "string"},
                "activities": {"type": "array"},
            },
        }
        mock_service.output_schema = {
            "type": "object",
            "properties": {"weather": {"type": "string"}},
        }

        test_app = FastAPI()

        # Add the invoke route
        @test_app.post("/invoke")
        def invoke():
            return {}

        serving_app._install_runtime_openapi(test_app, mock_service)

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
        output_schema = invoke_schema["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        assert (
            output_schema["properties"]["outputs"]
            == mock_service.output_schema
        )

    def test_install_runtime_openapi_error_handling(self, mock_service):
        """Test OpenAPI schema installation error handling."""
        # Mock service that raises error during schema access
        mock_service.request_schema = None
        mock_service.output_schema = None

        test_app = FastAPI()

        # This should not raise an exception even if schemas are None
        serving_app._install_runtime_openapi(test_app, mock_service)

        # Should still be able to generate basic schema
        schema = test_app.openapi()
        assert schema is not None
