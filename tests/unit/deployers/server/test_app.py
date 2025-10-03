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

import zenml.deployers.server.app as deployment_app
from zenml.deployers.server.app import (
    DeploymentAppConfig,
    _build_invoke_router,
    app,
    create_app,
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

        # Build a minimal Request carrying an app.state.service reference; this mimics
        # FastAPI's injection so the dependency can resolve without relying on globals.
        class _State:
            pass

        state = _State()
        state.service = mock_service

        class _App:
            pass

        app_like = _App()
        app_like.state = state

        request = Request(
            {
                "type": "http",
                "method": "GET",
                "url": "http://test",
                "app": app_like,
            }
        )
        assert get_pipeline_service(request) is mock_service


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


class TestCreateAppFactory:
    """Tests for the create_app() factory ensuring per-instance isolation and behavior."""

    def test_create_app_test_mode_no_init_no_global_touch(
        self,
        monkeypatch: pytest.MonkeyPatch,
        mocker: MockerFixture,
    ) -> None:
        """Test mode doesn't initialize service or touch module-level _service."""
        # Ensure env does not force test mode or auth behavior unexpectedly
        monkeypatch.delenv("ZENML_DEPLOYMENT_TEST_MODE", raising=False)
        monkeypatch.delenv("ZENML_DEPLOYMENT_AUTH_KEY", raising=False)

        # Prepare a sentinel for the legacy global and assert it remains unchanged
        sentinel = object()
        monkeypatch.setattr(
            deployment_app, "_service", sentinel, raising=False
        )

        # A service factory that should NOT be called in test mode
        sf = mocker.MagicMock(name="service_factory")

        cfg = DeploymentAppConfig(
            test_mode=True,
            deployment_id="dep-ignored",
            auth_key="alpha",
        )
        app_instance = create_app(config=cfg, service_factory=sf)

        # Startup and shutdown via TestClient should not initialize or attach service / invoke router
        with TestClient(app_instance) as client:
            schema = client.get("/openapi.json").json()
            # In test mode, the invoke router is not included
            assert "/invoke" not in schema.get("paths", {})

        sf.assert_not_called()
        assert getattr(app_instance.state, "service", None) is None
        # Global legacy _service must remain untouched
        assert deployment_app._service is sentinel

    def test_create_app_initializes_and_sets_state(
        self,
        monkeypatch: pytest.MonkeyPatch,
        mocker: MockerFixture,
    ) -> None:
        """Normal mode initializes service and stores it on app.state; includes /invoke."""
        # Ensure env does not force test mode
        monkeypatch.delenv("ZENML_DEPLOYMENT_TEST_MODE", raising=False)

        # Keep legacy global isolated and verify it's never changed
        sentinel = object()
        monkeypatch.setattr(
            deployment_app, "_service", sentinel, raising=False
        )

        # Mock service implementing the minimal interface required
        svc = mocker.MagicMock(spec=PipelineDeploymentService)
        # Required for _build_invoke_router to construct request/response models
        svc.input_model = MockWeatherRequest
        svc.initialize = mocker.MagicMock()
        svc.cleanup = mocker.MagicMock()

        sf = mocker.MagicMock(return_value=svc)

        cfg = DeploymentAppConfig(deployment_id="dep-1", test_mode=False)
        app_instance = create_app(config=cfg, service_factory=sf)

        with TestClient(app_instance) as client:
            # Service should be constructed and initialized once with the provided deployment_id
            sf.assert_called_once_with("dep-1")
            svc.initialize.assert_called_once()
            # Service should be stored on app.state
            assert app_instance.state.service is svc

            # The invoke route should be available in the OpenAPI schema
            schema = client.get("/openapi.json").json()
            assert "/invoke" in schema.get("paths", {})

        # Service cleanup should be called on shutdown
        svc.cleanup.assert_called_once()
        # Legacy global must remain unchanged
        assert deployment_app._service is sentinel

    def test_per_app_auth_isolation(
        self,
        monkeypatch: pytest.MonkeyPatch,
        mocker: MockerFixture,
    ) -> None:
        """Two apps with different auth keys enforce independent auth policies."""
        # Ensure no module-level auth env interferes
        monkeypatch.delenv("ZENML_DEPLOYMENT_AUTH_KEY", raising=False)

        def _success_response() -> BaseDeploymentInvocationResponse:
            # Response structure matching what's expected by response_model
            return BaseDeploymentInvocationResponse(
                success=True,
                outputs={"result": "ok"},
                execution_time=0.1,
                metadata=DeploymentInvocationResponseMetadata(
                    deployment_id=uuid4(),
                    deployment_name="deployment",
                    pipeline_name="pipeline",
                    run_id=None,
                    run_name=None,
                    parameters_used={"city": "Paris", "temperature": 25},
                    snapshot_id=uuid4(),
                    snapshot_name="snapshot",
                ),
                error=None,
            )

        # App 1 uses key 'alpha'
        svc1 = mocker.MagicMock(spec=PipelineDeploymentService)
        svc1.input_model = MockWeatherRequest
        svc1.execute_pipeline.return_value = _success_response()

        # App 2 uses key 'beta'
        svc2 = mocker.MagicMock(spec=PipelineDeploymentService)
        svc2.input_model = MockWeatherRequest
        svc2.execute_pipeline.return_value = _success_response()

        app1 = create_app(
            config=DeploymentAppConfig(
                deployment_id="dep-a", test_mode=False, auth_key="alpha"
            ),
            service_factory=lambda _: svc1,
        )
        app2 = create_app(
            config=DeploymentAppConfig(
                deployment_id="dep-b", test_mode=False, auth_key="beta"
            ),
            service_factory=lambda _: svc2,
        )

        payload = {"parameters": {"city": "Paris", "temperature": 25}}
        with TestClient(app1) as c1, TestClient(app2) as c2:
            # App1 should accept 'alpha' and reject 'beta'
            r = c1.post(
                "/invoke",
                headers={"Authorization": "Bearer alpha"},
                json=payload,
            )
            assert r.status_code == 200
            r = c1.post(
                "/invoke",
                headers={"Authorization": "Bearer beta"},
                json=payload,
            )
            assert r.status_code == 401

            # App2 should accept 'beta' and reject 'alpha'
            r = c2.post(
                "/invoke",
                headers={"Authorization": "Bearer beta"},
                json=payload,
            )
            assert r.status_code == 200
            r = c2.post(
                "/invoke",
                headers={"Authorization": "Bearer alpha"},
                json=payload,
            )
            assert r.status_code == 401

        # Only successful, authorized requests should have triggered execution
        assert svc1.execute_pipeline.call_count == 1
        assert svc2.execute_pipeline.call_count == 1

    def test_factory_never_modifies_module_global_service(
        self,
        monkeypatch: pytest.MonkeyPatch,
        mocker: MockerFixture,
    ) -> None:
        """create_app must never modify the module-level _service global."""
        sentinel = object()
        monkeypatch.setattr(
            deployment_app, "_service", sentinel, raising=False
        )

        svc1 = mocker.MagicMock(spec=PipelineDeploymentService)
        svc1.input_model = MockWeatherRequest

        svc2 = mocker.MagicMock(spec=PipelineDeploymentService)
        svc2.input_model = MockWeatherRequest

        app1 = create_app(
            config=DeploymentAppConfig(deployment_id="dep-1", test_mode=False),
            service_factory=lambda _: svc1,
        )
        app2 = create_app(
            config=DeploymentAppConfig(deployment_id="dep-2", test_mode=False),
            service_factory=lambda _: svc2,
        )

        # Spin both apps up and down to ensure no global state is mutated
        with TestClient(app1), TestClient(app2):
            pass

        assert deployment_app._service is sentinel

    def test_get_pipeline_service_prefers_app_state(
        self,
        monkeypatch: pytest.MonkeyPatch,
        mocker: MockerFixture,
    ) -> None:
        """get_pipeline_service prefers app.state.service over legacy _service within factory apps."""
        # Prepare a legacy global service that should NOT be used
        legacy_service = mocker.MagicMock(spec=PipelineDeploymentService)
        monkeypatch.setattr(
            deployment_app, "_service", legacy_service, raising=False
        )

        # The per-app service should be resolved by the dependency during requests
        svc = mocker.MagicMock(spec=PipelineDeploymentService)
        svc.input_model = MockWeatherRequest
        svc.is_healthy = mocker.MagicMock(return_value=True)

        app_instance = create_app(
            config=DeploymentAppConfig(deployment_id="dep-x", test_mode=False),
            service_factory=lambda _: svc,
        )

        with TestClient(app_instance) as client:
            resp = client.get("/health")
            assert resp.status_code == 200

        # Ensure per-app service was called and the legacy global was not
        svc.is_healthy.assert_called_once()
        legacy_service.is_healthy.assert_not_called()
