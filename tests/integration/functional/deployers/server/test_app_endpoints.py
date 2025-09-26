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
"""Integration tests for FastAPI deployment application endpoints."""

import importlib
from types import ModuleType, SimpleNamespace
from typing import Generator, Optional, Tuple
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

import zenml.deployers.server.app as deployment_app
from zenml.deployers.server.models import (
    BaseDeploymentInvocationRequest,
    BaseDeploymentInvocationResponse,
    DeploymentInfo,
    DeploymentInvocationResponseMetadata,
    ExecutionMetrics,
    PipelineInfo,
    ServiceInfo,
    SnapshotInfo,
)


class MockWeatherRequest(BaseModel):
    """Mock Pydantic model for testing."""

    city: str
    temperature: int = 20


class StubDeploymentService:
    """Stub service implementing the interface used by the FastAPI app."""

    def __init__(self, deployment_id: str) -> None:
        """Initialize the stub service.

        Args:
            snapshot_id: The ID of the snapshot to use for the service.
        """
        self._healthy = True
        self.initialized = False
        self.cleaned_up = False
        self.last_request: Optional[BaseDeploymentInvocationRequest] = None
        self.input_schema = {
            "type": "object",
            "properties": {"city": {"type": "string"}},
        }
        self.output_schema = {
            "type": "object",
            "properties": {"result": {"type": "string"}},
        }
        self.snapshot = SimpleNamespace(
            id=uuid4(),
            name="snapshot",
            pipeline_configuration=SimpleNamespace(
                name="test_pipeline",
                environment={},
                init_hook_source=None,
                init_hook_kwargs=None,
                cleanup_hook_source=None,
            ),
            pipeline_spec=SimpleNamespace(
                parameters={"city": "London"},
                input_schema=self.input_schema,
                output_schema=self.output_schema,
            ),
        )
        self.deployment = SimpleNamespace(
            id=uuid4(),
            name="deployment",
            snapshot=self.snapshot,
        )

    @property
    def input_model(self) -> type[BaseModel]:  # noqa: D401
        """Expose the request model expected by the service.

        Returns:
            The request model expected by the service.
        """

        return MockWeatherRequest

    def initialize(self) -> None:  # noqa: D401
        """Mark the service as initialized for verification in tests."""

        self.initialized = True

    def cleanup(self) -> None:  # noqa: D401
        """Mark the service as cleaned up for shutdown assertions."""

        self.cleaned_up = True

    def is_healthy(self) -> bool:  # noqa: D401
        """Return the current health flag used by tests."""

        return self._healthy

    def set_health(self, healthy: bool) -> None:  # noqa: D401
        """Set the health of the service.

        Args:
            healthy: The health of the service.
        """
        self._healthy = healthy

    def get_service_info(self) -> ServiceInfo:  # noqa: D401
        """Retrieve public metadata describing the stub deployment."""

        return ServiceInfo(
            deployment=DeploymentInfo(
                id=self.deployment.id,
                name=self.deployment.name,
            ),
            snapshot=SnapshotInfo(
                id=self.snapshot.id, name=self.snapshot.name
            ),
            pipeline=PipelineInfo(
                name=self.snapshot.pipeline_configuration.name,
                parameters=self.snapshot.pipeline_spec.parameters,
                input_schema=self.input_schema,
                output_schema=self.output_schema,
            ),
            total_executions=1,
            last_execution_time=None,
            status="healthy" if self._healthy else "unhealthy",
            uptime=1.0,
        )

    def get_execution_metrics(self) -> ExecutionMetrics:  # noqa: D401
        """Return execution metrics describing recent pipeline activity."""

        return ExecutionMetrics(total_executions=1, last_execution_time=None)

    def execute_pipeline(
        self, request: BaseDeploymentInvocationRequest
    ) -> BaseDeploymentInvocationResponse:  # noqa: D401
        """Execute the pipeline.

        Args:
            request: The request to execute the pipeline.

        Returns:
            The response from the pipeline.
        """
        self.last_request = request
        return BaseDeploymentInvocationResponse(
            success=True,
            outputs={"result": "ok"},
            execution_time=0.5,
            metadata=DeploymentInvocationResponseMetadata(
                deployment_id=self.deployment.id,
                deployment_name=self.deployment.name,
                pipeline_name="test_pipeline",
                run_id=None,
                run_name=None,
                parameters_used=request.parameters.model_dump(),
                snapshot_id=self.snapshot.id,
                snapshot_name=self.snapshot.name,
            ),
            error=None,
        )


@pytest.fixture
def client_service_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[
    Tuple[TestClient, StubDeploymentService, ModuleType], None, None
]:
    """Provide a fresh FastAPI client and stub service per test.

    Args:
        monkeypatch: The monkeypatch fixture.

    Yields:
        A tuple containing the FastAPI client, the stub service, and the reloaded app.
    """
    reloaded_app = importlib.reload(deployment_app)
    service = StubDeploymentService(str(uuid4()))

    monkeypatch.setenv("ZENML_DEPLOYMENT_ID", str(service.deployment.id))
    monkeypatch.delenv("ZENML_DEPLOYMENT_TEST_MODE", raising=False)

    def _service_factory(_: str) -> StubDeploymentService:
        """Factory function for creating a stub service.

        Args:
            _: The snapshot ID to use for the service.

        Returns:
            The stub service.
        """
        return service

    monkeypatch.setattr(
        reloaded_app,
        "PipelineDeploymentService",
        _service_factory,
    )

    with TestClient(reloaded_app.app) as client:
        yield client, service, reloaded_app


class TestFastAPIAppEndpoints:
    """Integration tests for FastAPI application endpoints."""

    def test_root_endpoint(
        self,
        client_service_pair: Tuple[
            TestClient, StubDeploymentService, ModuleType
        ],
    ) -> None:
        """Ensure the root endpoint renders the deployment overview."""
        client, service, _ = client_service_pair
        response = client.get("/")
        assert response.status_code == 200
        assert "ZenML Pipeline Deployment" in response.text
        assert "test_pipeline" in response.text
        assert service.initialized is True

    def test_health_endpoint_healthy(
        self,
        client_service_pair: Tuple[
            TestClient, StubDeploymentService, ModuleType
        ],
    ) -> None:
        """Ensure the health endpoint returns OK for healthy services."""
        client, _, _ = client_service_pair
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == "OK"

    def test_health_endpoint_unhealthy(
        self,
        client_service_pair: Tuple[
            TestClient, StubDeploymentService, ModuleType
        ],
    ) -> None:
        """Return a 503 status when the service reports unhealthy."""
        client, service, _ = client_service_pair
        service.set_health(False)
        response = client.get("/health")
        assert response.status_code == 503

    def test_info_endpoint(
        self,
        client_service_pair: Tuple[
            TestClient, StubDeploymentService, ModuleType
        ],
    ) -> None:
        """Expose pipeline and snapshot metadata via /info."""
        client, service, _ = client_service_pair
        response = client.get("/info")
        assert response.status_code == 200
        data = response.json()
        assert data["pipeline"]["name"] == "test_pipeline"
        assert data["pipeline"]["input_schema"] == service.input_schema
        assert data["snapshot"]["name"] == "snapshot"

    def test_metrics_endpoint(
        self,
        client_service_pair: Tuple[
            TestClient, StubDeploymentService, ModuleType
        ],
    ) -> None:
        """Surface execution metrics through the metrics endpoint."""
        client, _, _ = client_service_pair
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["total_executions"] == 1
        assert data["last_execution_time"] is None

    def test_invoke_endpoint_success(
        self,
        client_service_pair: Tuple[
            TestClient, StubDeploymentService, ModuleType
        ],
    ) -> None:
        """Propagate successful execution responses for valid payloads."""
        client, service, _ = client_service_pair
        payload = {"parameters": {"city": "Paris", "temperature": 25}}

        response = client.post("/invoke", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["outputs"] == {"result": "ok"}
        assert service.last_request.parameters.city == "Paris"

    def test_invoke_endpoint_execution_failure(
        self,
        client_service_pair: Tuple[
            TestClient, StubDeploymentService, ModuleType
        ],
    ) -> None:
        """Propagate failure responses without raising errors."""
        client, service, module = client_service_pair
        failure_response = BaseDeploymentInvocationResponse(
            success=False,
            outputs=None,
            execution_time=0.1,
            metadata=DeploymentInvocationResponseMetadata(
                deployment_id=service.deployment.id,
                deployment_name=service.deployment.name,
                pipeline_name="test_pipeline",
                run_id=None,
                run_name=None,
                parameters_used={},
                snapshot_id=service.snapshot.id,
                snapshot_name=service.snapshot.name,
            ),
            error="Pipeline execution failed",
        )

        service.execute_pipeline = lambda request: failure_response

        response = client.post(
            "/invoke", json={"parameters": {"city": "Paris"}}
        )
        assert response.status_code == 200
        assert response.json()["success"] is False

    def test_cleanup_called_on_shutdown(
        self,
        monkeypatch: pytest.MonkeyPatch,
        client_service_pair: Tuple[
            TestClient, StubDeploymentService, ModuleType
        ],
    ) -> None:
        """Trigger service cleanup when the application shuts down."""
        reloaded_app = importlib.reload(deployment_app)
        service = StubDeploymentService(str(uuid4()))
        monkeypatch.setenv("ZENML_DEPLOYMENT_ID", str(service.deployment.id))
        monkeypatch.setattr(
            reloaded_app,
            "PipelineDeploymentService",
            lambda deployment_id: service,
        )
        with TestClient(reloaded_app.app):
            pass

        assert service.initialized is True
        assert service.cleaned_up is True


class TestOpenAPIIntegration:
    """Integration tests for OpenAPI schema installation."""

    def test_openapi_includes_invoke_models(
        self,
        client_service_pair: Tuple[
            TestClient, StubDeploymentService, ModuleType
        ],
    ) -> None:
        """Include invoke request / response models within the OpenAPI schema."""
        client, service, module = client_service_pair
        schema = client.get("/openapi.json").json()
        operation = schema["paths"]["/invoke"]["post"]

        request_schema = operation["requestBody"]["content"][
            "application/json"
        ]["schema"]
        if "$ref" in request_schema:
            ref = request_schema["$ref"].split("/")[-1]
            request_schema = schema["components"]["schemas"][ref]

        parameters_schema = request_schema["properties"]["parameters"]
        assert parameters_schema["properties"]["city"]["type"] == "string"

        response_schema = operation["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        if "$ref" in response_schema:
            ref = response_schema["$ref"].split("/")[-1]
            response_schema = schema["components"]["schemas"][ref]

        outputs_schema = response_schema["properties"]["outputs"]
        if "$ref" in outputs_schema:
            ref = outputs_schema["$ref"].split("/")[-1]
            outputs_schema = schema["components"]["schemas"][ref]

        assert outputs_schema["properties"]["result"]["type"] == "string"
