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
"""Unit tests for deployment app functionality."""

from __future__ import annotations

import asyncio
import json
from typing import cast
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from pydantic import BaseModel
from pytest_mock import MockerFixture

from zenml.deployers.server.app import (
    _build_invoke_router,
    app,
    get_pipeline_service,
    lifespan,
    runtime_error_handler,
    value_error_handler,
    verify_token,
)
from zenml.deployers.server.models import (
    BaseDeploymentInvocationResponse,
    DeploymentInfo,
    DeploymentInvocationResponseMetadata,
    ExecutionMetrics,
    PipelineInfo,
    ServiceInfo,
    SnapshotInfo,
)
from zenml.deployers.server.service import PipelineDeploymentService


class MockWeatherRequest(BaseModel):
    """Mock Pydantic model for testing."""

    city: str
    temperature: int = 20


@pytest.fixture
def mock_service(mocker: MockerFixture) -> PipelineDeploymentService:
    """Mock pipeline deployment service configured for the app tests."""

    service = cast(
        PipelineDeploymentService,
        mocker.MagicMock(spec=PipelineDeploymentService),
    )
    snapshot_id = uuid4()
    deployment_id = uuid4()

    service.input_model = MockWeatherRequest
    service.is_healthy.return_value = True
    service.input_schema = {
        "type": "object",
        "properties": {"city": {"type": "string"}},
    }
    service.output_schema = {
        "type": "object",
        "properties": {"result": {"type": "string"}},
    }

    service.get_service_info.return_value = ServiceInfo(
        deployment=DeploymentInfo(id=deployment_id, name="deployment"),
        snapshot=SnapshotInfo(id=snapshot_id, name="snapshot"),
        pipeline=PipelineInfo(
            name="test_pipeline",
            parameters={"city": "London"},
            input_schema=service.input_schema,
            output_schema=service.output_schema,
        ),
        total_executions=3,
        last_execution_time=None,
        status="healthy",
        uptime=12.34,
    )
    service.get_execution_metrics.return_value = ExecutionMetrics(
        total_executions=3,
        last_execution_time=None,
    )
    service.execute_pipeline.return_value = BaseDeploymentInvocationResponse(
        success=True,
        outputs={"result": "ok"},
        execution_time=0.5,
        metadata=DeploymentInvocationResponseMetadata(
            deployment_id=deployment_id,
            deployment_name="deployment",
            pipeline_name="test_pipeline",
            run_id=None,
            run_name=None,
            parameters_used={"city": "Paris", "temperature": 25},
            snapshot_id=snapshot_id,
            snapshot_name="snapshot",
        ),
        error=None,
    )
    return service


class TestDeploymentAppRoutes:
    """Test FastAPI app routes."""

    def test_root_endpoint(
        self,
        mock_service: PipelineDeploymentService,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Root endpoint returns HTML with pipeline information."""
        monkeypatch.setenv("ZENML_DEPLOYMENT_TEST_MODE", "true")
        monkeypatch.setattr(
            "zenml.deployers.server.app._service", mock_service
        )
        with TestClient(app) as client:
            response = client.get("/")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert "ZenML Pipeline Deployment" in response.text
        assert "test_pipeline" in response.text

    def test_health_endpoint(
        self,
        mock_service: PipelineDeploymentService,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Health endpoint returns OK when service is healthy."""
        monkeypatch.setenv("ZENML_DEPLOYMENT_TEST_MODE", "true")
        monkeypatch.setattr(
            "zenml.deployers.server.app._service", mock_service
        )
        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == "OK"

    def test_health_endpoint_unhealthy(
        self,
        mock_service: PipelineDeploymentService,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Health endpoint raises when service reports unhealthy state."""
        mock_service.is_healthy.return_value = False

        monkeypatch.setenv("ZENML_DEPLOYMENT_TEST_MODE", "true")
        monkeypatch.setattr(
            "zenml.deployers.server.app._service", mock_service
        )
        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 503
        assert response.json()["detail"] == "Service is unhealthy"

    def test_info_endpoint(
        self,
        mock_service: PipelineDeploymentService,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Info endpoint returns service metadata."""
        monkeypatch.setenv("ZENML_DEPLOYMENT_TEST_MODE", "true")
        monkeypatch.setattr(
            "zenml.deployers.server.app._service", mock_service
        )
        with TestClient(app) as client:
            response = client.get("/info")

        assert response.status_code == 200
        data = response.json()
        assert data["pipeline"]["name"] == "test_pipeline"
        assert data["pipeline"]["parameters"] == {"city": "London"}
        assert data["status"] == "healthy"
        assert data["snapshot"]["name"] == "snapshot"

    def test_metrics_endpoint(
        self,
        mock_service: PipelineDeploymentService,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Metrics endpoint exposes execution metrics."""
        monkeypatch.setenv("ZENML_DEPLOYMENT_TEST_MODE", "true")
        monkeypatch.setattr(
            "zenml.deployers.server.app._service", mock_service
        )
        with TestClient(app) as client:
            response = client.get("/metrics")

        assert response.status_code == 200
        data = response.json()
        assert data["total_executions"] == 3
        assert data["last_execution_time"] is None

    def test_info_endpoint_includes_schemas(
        self,
        mock_service: PipelineDeploymentService,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Info endpoint includes input/output schemas."""
        monkeypatch.setenv("ZENML_DEPLOYMENT_TEST_MODE", "true")
        monkeypatch.setattr(
            "zenml.deployers.server.app._service", mock_service
        )
        with TestClient(app) as client:
            response = client.get("/info")

        data = response.json()
        assert data["pipeline"]["input_schema"] == mock_service.input_schema
        assert data["pipeline"]["output_schema"] == mock_service.output_schema

    def test_get_pipeline_service_returns_current_instance(
        self,
        mock_service: PipelineDeploymentService,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Ensure get_pipeline_service exposes the underlying instance."""
        monkeypatch.setattr(
            "zenml.deployers.server.app._service", mock_service
        )
        assert get_pipeline_service() is mock_service


class TestDeploymentAppInvoke:
    """Test pipeline invocation via FastAPI."""

    def test_invoke_endpoint_executes_service(
        self, mock_service: PipelineDeploymentService
    ) -> None:
        """Invoke router validates payloads and calls the service."""
        fast_app = FastAPI()
        fast_app.include_router(_build_invoke_router(mock_service))

        with TestClient(fast_app) as client:
            payload = {"parameters": {"city": "Paris", "temperature": 25}}
            response = client.post("/invoke", json=payload)

        assert response.status_code == 200
        assert response.json()["success"] is True
        mock_service.execute_pipeline.assert_called_once()
        request_arg = mock_service.execute_pipeline.call_args.args[0]
        assert request_arg.parameters.city == "Paris"
        assert request_arg.skip_artifact_materialization is False

    def test_invoke_endpoint_validation_error(
        self, mock_service: PipelineDeploymentService
    ) -> None:
        """Invalid payloads trigger validation errors."""
        fast_app = FastAPI()
        fast_app.include_router(_build_invoke_router(mock_service))

        with TestClient(fast_app) as client:
            response = client.post("/invoke", json={"parameters": {}})

        assert response.status_code == 422
        mock_service.execute_pipeline.assert_not_called()

    def test_verify_token_with_auth_enabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Token verification when authentication is enabled."""
        monkeypatch.setenv("ZENML_DEPLOYMENT_AUTH_KEY", "test-auth-key")

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="test-auth-key"
        )
        assert verify_token(credentials) is None

        with pytest.raises(HTTPException):
            verify_token(
                HTTPAuthorizationCredentials(
                    scheme="Bearer", credentials="wrong"
                )
            )

        with pytest.raises(HTTPException):
            verify_token(None)

    def test_verify_token_with_auth_disabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Token verification when authentication is disabled."""
        monkeypatch.delenv("ZENML_DEPLOYMENT_AUTH_KEY", raising=False)
        assert verify_token(None) is None


class TestDeploymentAppLifecycle:
    """Test app lifecycle management."""

    def test_lifespan_test_mode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Lifespan exits early in test mode."""
        monkeypatch.setenv("ZENML_DEPLOYMENT_TEST_MODE", "true")

        async def _run() -> None:
            async with lifespan(app):
                pass

        asyncio.run(_run())

    def test_lifespan_normal_mode(
        self,
        monkeypatch: pytest.MonkeyPatch,
        mocker: MockerFixture,
    ) -> None:
        """Lifespan initializes and cleans up service in normal mode."""
        monkeypatch.setenv("ZENML_DEPLOYMENT_ID", "test-deployment-id")

        mock_service = cast(
            PipelineDeploymentService,
            mocker.MagicMock(spec=PipelineDeploymentService),
        )
        mock_service.input_model = MockWeatherRequest
        mock_service.initialize = mocker.MagicMock()
        mock_service.cleanup = mocker.MagicMock()

        mocker.patch(
            "zenml.deployers.server.app.PipelineDeploymentService",
            return_value=mock_service,
        )
        mock_include = mocker.patch.object(app, "include_router")

        async def _run() -> None:
            async with lifespan(app):
                pass

        asyncio.run(_run())

        mock_include.assert_called()
        mock_service.initialize.assert_called_once()
        mock_service.cleanup.assert_called_once()

    def test_lifespan_missing_snapshot_id(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Lifespan raises when no snapshot id is configured."""
        monkeypatch.delenv("ZENML_DEPLOYMENT_ID", raising=False)

        async def _run() -> None:
            with pytest.raises(ValueError, match="ZENML_DEPLOYMENT_ID"):
                async with lifespan(app):
                    pass

        asyncio.run(_run())


class TestDeploymentAppErrorHandling:
    """Test app error handling."""

    def test_value_error_handler(self) -> None:
        """ValueError exception handler returns 400 with message."""
        request = Request(
            {"type": "http", "method": "POST", "url": "http://test"}
        )
        error = ValueError("Test error")

        response = value_error_handler(request, error)
        assert response.status_code == 400
        payload = json.loads(response.body)
        assert payload["detail"] == "Test error"

    def test_runtime_error_handler(self) -> None:
        """RuntimeError exception handler returns 500 with message."""
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

    def test_build_invoke_router(
        self, mock_service: PipelineDeploymentService
    ) -> None:
        """Building the invoke router exposes /invoke route."""
        router = _build_invoke_router(mock_service)

        assert router is not None
        routes = [route.path for route in router.routes]
        assert "/invoke" in routes
