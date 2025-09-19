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
"""Unit tests for serving app functionality."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel

from zenml.deployers.serving.app import (
    _build_invoke_router,
    _install_runtime_openapi,
    app,
    get_pipeline_service,
    lifespan,
    runtime_error_handler,
    value_error_handler,
    verify_token,
)
from zenml.deployers.serving.service import PipelineServingService


class MockWeatherRequest(BaseModel):
    """Mock Pydantic model for testing."""

    city: str = "London"
    temperature: int = 20


@pytest.fixture
def mock_service() -> MagicMock:
    """Mock pipeline serving service configured for the app tests."""

    service = MagicMock(spec=PipelineServingService)
    service.snapshot_id = str(uuid4())
    service.params_model = MockWeatherRequest
    service.last_execution_time = None
    service.total_executions = 0
    service.is_healthy.return_value = True
    service.get_service_info.return_value = {
        "snapshot_id": service.snapshot_id,
        "pipeline_name": "test_pipeline",
        "total_executions": 0,
        "status": "healthy",
        "last_execution_time": None,
    }
    service.get_execution_metrics.return_value = {
        "total_executions": 0,
        "last_execution_time": None,
    }
    service.execute_pipeline.return_value = {
        "success": True,
        "outputs": {"step1.result": "test_output"},
        "execution_time": 1.5,
        "metadata": {
            "pipeline_name": "test_pipeline",
            "run_id": "run-123",
            "run_name": "test_run",
            "parameters_used": {"city": "London", "temperature": 20},
            "snapshot_id": service.snapshot_id,
        },
    }
    service.request_schema = {
        "type": "object",
        "properties": {"city": {"type": "string"}},
    }
    service.output_schema = {
        "type": "object",
        "properties": {"result": {"type": "string"}},
    }
    service.snapshot = MagicMock()
    service.snapshot.pipeline_spec = MagicMock()
    service.snapshot.pipeline_spec.parameters = {"city": "London"}
    service.snapshot.pipeline_configuration = MagicMock()
    service.snapshot.pipeline_configuration.name = "test_pipeline"
    return service


class TestServingAppRoutes:
    """Test FastAPI app routes."""

    def test_root_endpoint(self, mock_service: MagicMock) -> None:
        """Test root endpoint returns HTML."""
        with patch.dict(os.environ, {"ZENML_SERVING_TEST_MODE": "true"}):
            with patch("zenml.deployers.serving.app._service", mock_service):
                with TestClient(app) as client:
                    response = client.get("/")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"
        assert "ZenML Pipeline Serving" in response.text
        assert "test_pipeline" in response.text

    def test_health_endpoint(self, mock_service: MagicMock) -> None:
        """Test health check endpoint."""
        with patch.dict(os.environ, {"ZENML_SERVING_TEST_MODE": "true"}):
            with patch("zenml.deployers.serving.app._service", mock_service):
                with TestClient(app) as client:
                    response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["snapshot_id"] == mock_service.snapshot_id
        assert data["pipeline_name"] == "test_pipeline"
        assert "uptime" in data

    def test_health_endpoint_unhealthy(self, mock_service: MagicMock) -> None:
        """Test health check endpoint when service is unhealthy."""
        mock_service.is_healthy.return_value = False

        with patch.dict(os.environ, {"ZENML_SERVING_TEST_MODE": "true"}):
            with patch("zenml.deployers.serving.app._service", mock_service):
                with TestClient(app) as client:
                    response = client.get("/health")

        assert response.status_code == 503
        assert response.json()["detail"] == "Service is unhealthy"

    def test_info_endpoint(self, mock_service: MagicMock) -> None:
        """Test info endpoint."""
        mock_service.snapshot.pipeline_spec.parameters = {
            "city": "London",
            "temperature": 20,
        }

        with patch.dict(os.environ, {"ZENML_SERVING_TEST_MODE": "true"}):
            with patch("zenml.deployers.serving.app._service", mock_service):
                with TestClient(app) as client:
                    response = client.get("/info")

        assert response.status_code == 200
        data = response.json()
        assert data["pipeline"]["name"] == "test_pipeline"
        assert data["pipeline"]["parameters"] == {
            "city": "London",
            "temperature": 20,
        }
        assert data["snapshot"]["id"] == mock_service.snapshot_id

    def test_metrics_endpoint(self, mock_service: MagicMock) -> None:
        """Test metrics endpoint."""
        with patch.dict(os.environ, {"ZENML_SERVING_TEST_MODE": "true"}):
            with patch("zenml.deployers.serving.app._service", mock_service):
                with TestClient(app) as client:
                    response = client.get("/metrics")

        assert response.status_code == 200
        data = response.json()
        assert data["total_executions"] == 0
        assert "last_execution_time" in data

    def test_schema_endpoint(self, mock_service: MagicMock) -> None:
        """Test schema endpoint exposes request/response schemas."""
        with patch.dict(os.environ, {"ZENML_SERVING_TEST_MODE": "true"}):
            with patch("zenml.deployers.serving.app._service", mock_service):
                with TestClient(app) as client:
                    response = client.get("/schema")

        assert response.status_code == 200
        data = response.json()
        assert data["request_schema"] == mock_service.request_schema
        assert data["output_schema"] == mock_service.output_schema

    def test_status_endpoint(self, mock_service: MagicMock) -> None:
        """Test status endpoint."""
        with (
            patch.dict(
                os.environ,
                {
                    "ZENML_SERVING_TEST_MODE": "true",
                    "ZENML_SNAPSHOT_ID": mock_service.snapshot_id,
                    "ZENML_SERVICE_HOST": "127.0.0.1",
                    "ZENML_SERVICE_PORT": "9000",
                },
            ),
            patch("zenml.deployers.serving.app._service", mock_service),
            patch(
                "zenml.deployers.serving.app.service_start_time", 1234567890.0
            ),
        ):
            with TestClient(app) as client:
                response = client.get("/status")

        assert response.status_code == 200
        data = response.json()
        assert data["service_name"] == "ZenML Pipeline Serving"
        assert data["version"] == "0.2.0"
        assert data["snapshot_id"] == mock_service.snapshot_id
        assert data["status"] == "running"
        assert data["configuration"]["snapshot_id"] == mock_service.snapshot_id
        assert data["configuration"]["host"] == "127.0.0.1"
        assert data["configuration"]["port"] == 9000

    def test_get_pipeline_service_returns_current_instance(
        self, mock_service: MagicMock
    ) -> None:
        """Ensure get_pipeline_service exposes the underlying instance."""

        with patch("zenml.deployers.serving.app._service", mock_service):
            assert get_pipeline_service() is mock_service


class TestServingAppInvoke:
    """Test pipeline invocation via FastAPI."""

    @patch.dict("os.environ", {}, clear=True)  # No auth by default
    def test_invoke_endpoint_executes_service(
        self, mock_service: MagicMock
    ) -> None:
        """Test that the invoke router validates payloads and calls the service."""

        fast_app = FastAPI()
        fast_app.include_router(_build_invoke_router(mock_service))

        with TestClient(fast_app) as client:
            payload = {"parameters": {"city": "Paris", "temperature": 25}}
            response = client.post("/invoke", json=payload)

        assert response.status_code == 200
        assert response.json() == mock_service.execute_pipeline.return_value
        mock_service.execute_pipeline.assert_called_once_with(
            {"city": "Paris", "temperature": 25}, None, None, None
        )

    @patch.dict("os.environ", {}, clear=True)
    def test_invoke_endpoint_validation_error(
        self, mock_service: MagicMock
    ) -> None:
        """Test that invalid payloads trigger validation errors."""

        fast_app = FastAPI()
        fast_app.include_router(_build_invoke_router(mock_service))

        with TestClient(fast_app) as client:
            response = client.post("/invoke", json={"parameters": {}})

        assert response.status_code == 422
        mock_service.execute_pipeline.assert_not_called()

    @patch.dict("os.environ", {"ZENML_SERVING_AUTH_KEY": "test-auth-key"})
    def test_verify_token_with_auth_enabled(self) -> None:
        """Test token verification when authentication is enabled."""
        from fastapi.security import HTTPAuthorizationCredentials

        # Valid token
        valid_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="test-auth-key"
        )
        result = verify_token(valid_credentials)
        assert result is None  # No exception raised

        # Invalid token
        invalid_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="wrong-key"
        )
        with pytest.raises(HTTPException):
            verify_token(invalid_credentials)

        # Missing token
        with pytest.raises(HTTPException):
            verify_token(None)

    @patch.dict("os.environ", {}, clear=True)
    def test_verify_token_with_auth_disabled(self) -> None:
        """Test token verification when authentication is disabled."""

        # Should pass with no token when auth is disabled
        result = verify_token(None)
        assert result is None

    @patch.dict("os.environ", {"ZENML_SERVING_AUTH_KEY": ""})
    def test_verify_token_with_empty_auth_key(self) -> None:
        """Test token verification with empty auth key."""

        # Empty auth key should disable authentication
        result = verify_token(None)
        assert result is None


class TestServingAppLifecycle:
    """Test app lifecycle management."""

    @patch.dict("os.environ", {"ZENML_SERVING_TEST_MODE": "true"})
    def test_lifespan_test_mode(self) -> None:
        """Test lifespan in test mode."""

        async def run_lifespan() -> None:
            async with lifespan(app):
                pass

        asyncio.run(run_lifespan())

    @patch("zenml.deployers.serving.app.PipelineServingService")
    @patch.dict("os.environ", {"ZENML_SNAPSHOT_ID": "test-snapshot-id"})
    def test_lifespan_normal_mode(self, mock_service_class: MagicMock) -> None:
        """Test lifespan in normal mode."""
        mock_service = MagicMock()
        mock_service.params_model = MockWeatherRequest
        mock_service.initialize = MagicMock()
        mock_service.cleanup = MagicMock()
        mock_service.request_schema = None
        mock_service.output_schema = None
        mock_service_class.return_value = mock_service

        async def run_lifespan() -> None:
            with (
                patch.object(app, "include_router") as mock_include,
                patch(
                    "zenml.deployers.serving.app._install_runtime_openapi"
                ) as mock_openapi,
            ):
                async with lifespan(app):
                    pass
            mock_include.assert_called_once()
            mock_openapi.assert_called_once()

        asyncio.run(run_lifespan())

        mock_service_class.assert_called_once_with("test-snapshot-id")
        mock_service.initialize.assert_called_once()
        mock_service.cleanup.assert_called_once()

    @patch.dict("os.environ", {}, clear=True)
    def test_lifespan_missing_snapshot_id(self) -> None:
        """Test lifespan with missing snapshot ID."""

        async def run_lifespan() -> None:
            with pytest.raises(ValueError, match="ZENML_SNAPSHOT_ID"):
                async with lifespan(app):
                    pass

        asyncio.run(run_lifespan())


class TestServingAppErrorHandling:
    """Test app error handling."""

    def test_value_error_handler(self, mock_service: MagicMock) -> None:
        """Test ValueError exception handler."""
        request = Request(
            {"type": "http", "method": "POST", "url": "http://test"}
        )
        error = ValueError("Test error")

        response = value_error_handler(request, error)
        assert response.status_code == 400
        payload = json.loads(response.body)
        assert payload["detail"] == "Test error"

    def test_runtime_error_handler(self) -> None:
        """Test RuntimeError exception handler."""
        request = Request(
            {"type": "http", "method": "POST", "url": "http://test"}
        )
        error = RuntimeError("Runtime error")

        response = runtime_error_handler(request, error)
        assert response.status_code == 500
        payload = json.loads(response.body)
        assert payload["detail"] == "Runtime error"


class TestBuildInvokeRouter:
    """Test the invoke router building functionality."""

    def test_build_invoke_router(self, mock_service: MagicMock) -> None:
        """Test building the invoke router."""
        router = _build_invoke_router(mock_service)

        assert router is not None
        routes = [route.path for route in router.routes]
        assert "/invoke" in routes


def test_install_runtime_openapi_gracefully_handles_missing_schema(
    mock_service: MagicMock,
) -> None:
    """Ensure OpenAPI installation works when schemas are unavailable."""

    fast_api_app = FastAPI()

    @fast_api_app.post("/invoke")
    def invoke() -> Dict[str, Any]:
        return {}

    mock_service.request_schema = None
    mock_service.output_schema = None

    _install_runtime_openapi(fast_api_app, mock_service)

    schema = fast_api_app.openapi()
    assert "/invoke" in schema["paths"]
