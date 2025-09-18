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

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from zenml.deployers.serving.service import PipelineServingService


class MockWeatherRequest(BaseModel):
    """Mock Pydantic model for testing."""

    city: str = "London"
    temperature: int = 20


@pytest.fixture
def mock_service():
    """Mock pipeline serving service."""
    service = MagicMock(spec=PipelineServingService)
    service.snapshot_id = uuid4()
    service._params_model = MockWeatherRequest
    service.last_execution_time = None
    service.total_executions = 0
    service.is_healthy.return_value = True
    service.get_service_info.return_value = {
        "snapshot_id": str(service.snapshot_id),
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
            "snapshot_id": str(service.snapshot_id),
        },
    }
    return service


class TestServingAppRoutes:
    """Test FastAPI app routes."""

    def test_root_endpoint(self, mock_service):
        """Test root endpoint returns HTML."""
        from zenml.deployers.serving.app import app

        with patch("zenml.deployers.serving.app._service", mock_service):
            client = TestClient(app)
            response = client.get("/")

            assert response.status_code == 200
            assert (
                response.headers["content-type"] == "text/html; charset=utf-8"
            )
            assert "ZenML Pipeline Serving" in response.text
            assert "test_pipeline" in response.text

    def test_health_endpoint(self, mock_service):
        """Test health check endpoint."""
        from zenml.deployers.serving.app import app

        with patch("zenml.deployers.serving.app._service", mock_service):
            client = TestClient(app)
            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["snapshot_id"] == str(mock_service.snapshot_id)
            assert data["pipeline_name"] == "test_pipeline"
            assert "uptime" in data

    def test_health_endpoint_unhealthy(self, mock_service):
        """Test health check endpoint when service is unhealthy."""
        mock_service.is_healthy.return_value = False

        from zenml.deployers.serving.app import app

        with patch("zenml.deployers.serving.app._service", mock_service):
            client = TestClient(app)
            response = client.get("/health")

            assert response.status_code == 503
            assert response.json()["detail"] == "Service is unhealthy"

    def test_info_endpoint(self, mock_service):
        """Test info endpoint."""
        # Mock snapshot with pipeline spec
        mock_service.snapshot = MagicMock()
        mock_service.snapshot.pipeline_spec = MagicMock()
        mock_service.snapshot.pipeline_spec.parameters = {
            "city": "London",
            "temperature": 20,
        }

        from zenml.deployers.serving.app import app

        with patch("zenml.deployers.serving.app._service", mock_service):
            client = TestClient(app)
            response = client.get("/info")

            assert response.status_code == 200
            data = response.json()
            assert "pipeline" in data
            assert "snapshot" in data
            assert data["pipeline"]["name"] == "test_pipeline"
            assert data["snapshot"]["id"] == str(mock_service.snapshot_id)

    def test_metrics_endpoint(self, mock_service):
        """Test metrics endpoint."""
        from zenml.deployers.serving.app import app

        with patch("zenml.deployers.serving.app._service", mock_service):
            client = TestClient(app)
            response = client.get("/metrics")

            assert response.status_code == 200
            data = response.json()
            assert data["total_executions"] == 0
            assert "last_execution_time" in data

    def test_status_endpoint(self, mock_service):
        """Test status endpoint."""
        from zenml.deployers.serving.app import app

        with (
            patch("zenml.deployers.serving.app._service", mock_service),
            patch(
                "zenml.deployers.serving.app.service_start_time", 1234567890.0
            ),
            patch("time.time", return_value=1234567900.0),
        ):
            client = TestClient(app)
            response = client.get("/status")

            assert response.status_code == 200
            data = response.json()
            assert data["service_name"] == "ZenML Pipeline Serving"
            assert data["version"] == "0.2.0"
            assert data["snapshot_id"] == str(mock_service.snapshot_id)
            assert data["status"] == "running"


class TestServingAppInvoke:
    """Test pipeline invocation via FastAPI."""

    @patch.dict("os.environ", {}, clear=True)  # No auth by default
    def test_invoke_endpoint_basic(self, mock_service):
        """Test basic pipeline invocation."""
        # Build the invoke router explicitly and include it in the app
        from zenml.deployers.serving.app import _build_invoke_router, app

        router = _build_invoke_router(mock_service)
        assert router is not None
        app.include_router(router)

    @patch.dict("os.environ", {"ZENML_SERVING_AUTH_KEY": "test-auth-key"})
    def test_verify_token_with_auth_enabled(self):
        """Test token verification when authentication is enabled."""
        from fastapi.security import HTTPAuthorizationCredentials

        from zenml.deployers.serving.app import verify_token

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
        with pytest.raises(Exception):  # HTTPException
            verify_token(invalid_credentials)

        # Missing token
        with pytest.raises(Exception):  # HTTPException
            verify_token(None)

    @patch.dict("os.environ", {}, clear=True)
    def test_verify_token_with_auth_disabled(self):
        """Test token verification when authentication is disabled."""
        from zenml.deployers.serving.app import verify_token

        # Should pass with no token when auth is disabled
        result = verify_token(None)
        assert result is None

    @patch.dict("os.environ", {"ZENML_SERVING_AUTH_KEY": ""})
    def test_verify_token_with_empty_auth_key(self):
        """Test token verification with empty auth key."""
        from zenml.deployers.serving.app import verify_token

        # Empty auth key should disable authentication
        result = verify_token(None)
        assert result is None


class TestServingAppLifecycle:
    """Test app lifecycle management."""

    @patch.dict("os.environ", {"ZENML_SERVING_TEST_MODE": "true"})
    def test_lifespan_test_mode(self):
        """Test lifespan in test mode."""
        import asyncio

        from zenml.deployers.serving.app import app, lifespan

        async def test_lifespan():
            async with lifespan(app):
                # In test mode, should skip initialization
                pass

        # Should complete without error
        asyncio.run(test_lifespan())

    @patch("zenml.deployers.serving.app.PipelineServingService")
    @patch.dict("os.environ", {"ZENML_SNAPSHOT_ID": "test-snapshot-id"})
    def test_lifespan_normal_mode(self, mock_service_class):
        """Test lifespan in normal mode."""
        import asyncio

        from zenml.deployers.serving.app import app, lifespan

        # Mock service initialization
        mock_service = MagicMock()
        mock_service.initialize = MagicMock()
        mock_service.cleanup = MagicMock()
        mock_service_class.return_value = mock_service

        async def test_lifespan():
            async with lifespan(app):
                # Service should be initialized
                pass

        asyncio.run(test_lifespan())

        # Verify service was created with the correct snapshot ID
        mock_service_class.assert_called_once_with("test-snapshot-id")
        mock_service.initialize.assert_called_once()
        mock_service.cleanup.assert_called_once()

    @patch.dict("os.environ", {}, clear=True)
    def test_lifespan_missing_snapshot_id(self):
        """Test lifespan with missing snapshot ID."""
        import asyncio

        from zenml.deployers.serving.app import app, lifespan

        async def test_lifespan():
            with pytest.raises(ValueError, match="ZENML_SNAPSHOT_ID"):
                async with lifespan(app):
                    pass

        asyncio.run(test_lifespan())


class TestServingAppErrorHandling:
    """Test app error handling."""

    def test_value_error_handler(self, mock_service):
        """Test ValueError exception handler."""
        # Test the handler directly
        from fastapi import Request

        from zenml.deployers.serving.app import value_error_handler

        request = Request(
            {"type": "http", "method": "POST", "url": "http://test"}
        )
        error = ValueError("Test error")

        result = value_error_handler(request, error)
        assert result.status_code == 400
        assert result.detail == "Test error"

    def test_runtime_error_handler(self):
        """Test RuntimeError exception handler."""
        from fastapi import Request

        from zenml.deployers.serving.app import runtime_error_handler

        request = Request(
            {"type": "http", "method": "POST", "url": "http://test"}
        )
        error = RuntimeError("Runtime error")

        result = runtime_error_handler(request, error)
        assert result.status_code == 500
        assert result.detail == "Runtime error"


class TestBuildInvokeRouter:
    """Test the invoke router building functionality."""

    def test_build_invoke_router(self, mock_service):
        """Test building the invoke router."""
        from zenml.deployers.serving.app import _build_invoke_router

        router = _build_invoke_router(mock_service)

        assert router is not None
        # Router should have the invoke endpoint registered
        # We can't easily test the dynamic model creation without integration tests
