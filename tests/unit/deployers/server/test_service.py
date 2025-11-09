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
"""Unit tests for the pipeline deployment service."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, List, Type
from uuid import uuid4

import pytest
from pydantic import BaseModel
from pytest_mock import MockerFixture

from zenml.config import (
    AppExtensionSpec,
    DeploymentSettings,
    EndpointSpec,
    MiddlewareSpec,
)
from zenml.deployers.server.adapters import EndpointAdapter, MiddlewareAdapter
from zenml.deployers.server.app import (
    BaseDeploymentAppRunner,
    BaseDeploymentAppRunnerFlavor,
)
from zenml.deployers.server.models import BaseDeploymentInvocationRequest
from zenml.deployers.server.service import PipelineDeploymentService


class WeatherParams(BaseModel):
    """Minimal parameter model used for service tests."""

    city: str
    temperature: int = 20


def _make_snapshot() -> SimpleNamespace:
    """Create a snapshot stub with the attributes accessed by the service."""

    pipeline_configuration = SimpleNamespace(
        name="test_pipeline",
        environment={},
        init_hook_source=None,
        init_hook_kwargs={},
        cleanup_hook_source=None,
        deployment_settings=DeploymentSettings(),
    )
    pipeline_spec = SimpleNamespace(
        parameters={"city": "London"},
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        outputs=[],
        source="test.module.pipeline",
    )
    stack = SimpleNamespace(name="test_stack")
    pipeline = SimpleNamespace(id=uuid4(), name="test_pipeline")

    return SimpleNamespace(
        id=uuid4(),
        name="snapshot",
        pipeline_configuration=pipeline_configuration,
        pipeline_spec=pipeline_spec,
        step_configurations={},
        stack=stack,
        pipeline=pipeline,
    )


def _make_deployment() -> SimpleNamespace:
    """Create a deployment stub with the attributes accessed by the service."""
    return SimpleNamespace(
        id=uuid4(), name="deployment", snapshot=_make_snapshot(), auth_key=None
    )


class _DummyDeploymentAppRunnerFlavor(BaseDeploymentAppRunnerFlavor):
    @property
    def name(self) -> str:
        return "dummy"

    @property
    def implementation_class(self) -> Type[BaseDeploymentAppRunner]:
        return _DummyDeploymentAppRunner


class _DummyDeploymentAppRunner(BaseDeploymentAppRunner):
    @classmethod
    def load_deployment(cls, deployment):
        return deployment

    @property
    def flavor(cls) -> "BaseDeploymentAppRunnerFlavor":
        return _DummyDeploymentAppRunnerFlavor()

    def _create_endpoint_adapter(self) -> EndpointAdapter:
        return None

    def _create_middleware_adapter(self) -> MiddlewareAdapter:
        return None

    def _get_dashboard_endpoints(self) -> List[EndpointSpec]:
        return []

    def _build_cors_middleware(self) -> MiddlewareSpec:
        return None

    def build(
        self,
        middlewares: List[MiddlewareSpec],
        endpoints: List[EndpointSpec],
        extensions: List[AppExtensionSpec],
    ):
        return None


def _make_service_stub(mocker: MockerFixture) -> PipelineDeploymentService:
    """Create a service instance without running __init__ for isolated tests."""
    deployment = _make_deployment()
    app_runner = _DummyDeploymentAppRunner(deployment)
    service = PipelineDeploymentService(app_runner)
    service._client = mocker.MagicMock()
    service._orchestrator = mocker.MagicMock()
    service.session_manager = None
    mocker.patch.object(
        type(service),
        "input_model",
        new_callable=mocker.PropertyMock,
        return_value=WeatherParams,
    )
    service.service_start_time = 100.0
    service.last_execution_time = None
    service.total_executions = 0
    return service


def test_execute_pipeline_calls_subroutines(mocker: MockerFixture) -> None:
    """execute_pipeline should orchestrate helper methods and return response."""
    service = _make_service_stub(mocker)

    placeholder_run = mocker.MagicMock()
    deployment_snapshot = mocker.MagicMock()
    captured_outputs: Dict[str, Dict[str, object]] = {
        "step1": {"result": "value"}
    }
    session_state_snapshot: Dict[str, Any] = {}
    mapped_outputs = {"result": "value"}

    service._prepare_execute_with_orchestrator = mocker.MagicMock(
        return_value=(placeholder_run, deployment_snapshot)
    )
    service._execute_with_orchestrator = mocker.MagicMock(
        return_value=(captured_outputs, session_state_snapshot)
    )
    service._map_outputs = mocker.MagicMock(return_value=mapped_outputs)
    service._build_response = mocker.MagicMock(return_value="response")

    request = BaseDeploymentInvocationRequest(
        parameters=WeatherParams(city="Berlin")
    )
    result = service.execute_pipeline(request)

    assert result == "response"
    service._prepare_execute_with_orchestrator.assert_called_once_with(
        resolved_params={"city": "Berlin", "temperature": 20}
    )
    service._execute_with_orchestrator.assert_called_once_with(
        placeholder_run=placeholder_run,
        deployment_snapshot=deployment_snapshot,
        resolved_params={"city": "Berlin", "temperature": 20},
        skip_artifact_materialization=False,
        session=None,
    )
    service._map_outputs.assert_called_once_with(captured_outputs)
    service._build_response.assert_called_once()


def test_map_outputs_returns_filtered_mapping(mocker: MockerFixture) -> None:
    """_map_outputs should align runtime outputs to pipeline spec."""
    service = _make_service_stub(mocker)
    service.snapshot.pipeline_spec.outputs = [
        SimpleNamespace(step_name="trainer", output_name="model"),
        SimpleNamespace(step_name="trainer", output_name="metrics"),
        SimpleNamespace(step_name="evaluator", output_name="report"),
    ]

    runtime_outputs = {
        "trainer": {"model": "model-artifact", "metrics": {"f1": 0.9}},
        "evaluator": {"report": "report-artifact"},
    }

    mapped = service._map_outputs(runtime_outputs)
    assert mapped == {
        "model": "model-artifact",
        "metrics": {"f1": 0.9},
        "report": "report-artifact",
    }


def test_map_outputs_handles_missing_data(mocker: MockerFixture) -> None:
    """_map_outputs should return empty dict when no runtime outputs."""
    service = _make_service_stub(mocker)

    assert service._map_outputs(None) == {}


def test_build_response_success(
    monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> None:
    """_build_response should return a successful response payload."""
    service = _make_service_stub(mocker)

    placeholder_run = mocker.MagicMock()
    placeholder_run.id = uuid4()
    placeholder_run.name = "placeholder"

    resolved_params = {"city": "Berlin", "temperature": 20}

    concrete_run = mocker.MagicMock()
    concrete_run.id = uuid4()
    concrete_run.name = "run"
    service._client.get_pipeline_run.return_value = concrete_run

    monkeypatch.setattr(
        "zenml.deployers.server.service.time.time", lambda: 110.0
    )

    response = service._build_response(
        resolved_params=resolved_params,
        start_time=100.0,
        mapped_outputs={"result": "value"},
        placeholder_run=placeholder_run,
    )

    assert response.success is True
    assert response.outputs == {"result": "value"}
    assert response.metadata.pipeline_name == "test_pipeline"
    assert response.metadata.run_id == concrete_run.id
    assert service.total_executions == 1
    assert service.last_execution_time is not None


def test_build_response_error(
    monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> None:
    """_build_response should capture errors and omit outputs."""
    service = _make_service_stub(mocker)

    monkeypatch.setattr(
        "zenml.deployers.server.service.time.time", lambda: 105.0
    )

    response = service._build_response(
        resolved_params={"city": "Berlin"},
        start_time=100.0,
        mapped_outputs=None,
        placeholder_run=None,
        error=RuntimeError("failure"),
    )

    assert response.success is False
    assert response.outputs is None
    assert response.error == "failure"


def test_get_service_info_aggregates_snapshot(
    mocker: MockerFixture,
) -> None:
    """get_service_info should expose pipeline metadata and schemas."""
    service = _make_service_stub(mocker)

    info = service.get_service_info()

    assert info.pipeline.name == "test_pipeline"
    assert info.snapshot.id == service.snapshot.id
    assert info.pipeline.parameters == {"city": "London"}
    assert info.pipeline.input_schema == {"type": "object"}


def test_execution_metrics_reflect_counters(mocker: MockerFixture) -> None:
    """get_execution_metrics should return counters from service state."""
    service = _make_service_stub(mocker)
    service.total_executions = 5
    service.last_execution_time = None

    metrics = service.get_execution_metrics()
    assert metrics.total_executions == 5
    assert metrics.last_execution_time is None


def test_input_output_schema_properties(mocker: MockerFixture) -> None:
    """input_schema and output_schema expose snapshot schemas."""
    service = _make_service_stub(mocker)

    assert service.input_schema == {"type": "object"}
    assert service.output_schema == {"type": "object"}


def test_resolve_session_returns_none_without_manager(
    mocker: MockerFixture,
) -> None:
    """_resolve_session should return None when no session manager is configured."""
    service = _make_service_stub(mocker)

    # Ensure session_manager is None
    assert service.session_manager is None

    # Should return None without error
    session = service._resolve_session("some-session-id")
    assert session is None


def test_resolve_session_invokes_manager_with_ids(
    mocker: MockerFixture,
) -> None:
    """_resolve_session should forward request to session manager with correct IDs."""
    service = _make_service_stub(mocker)

    # Configure mock session manager
    mock_manager = mocker.MagicMock()
    mock_session = SimpleNamespace(
        id="session-123",
        deployment_id=str(service.deployment.id),
        state={"counter": 1},
    )
    mock_manager.resolve.return_value = mock_session
    service.session_manager = mock_manager

    # Call _resolve_session
    result = service._resolve_session("session-123")

    # Verify manager was called with correct arguments
    mock_manager.resolve.assert_called_once_with(
        requested_id="session-123",
        deployment_id=str(service.deployment.id),
        pipeline_id=str(service.snapshot.pipeline.id),
    )

    # Verify result matches mock return
    assert result == mock_session


def test_persist_session_state_noop_when_state_unchanged(
    mocker: MockerFixture,
) -> None:
    """_persist_session_state should skip persistence when state hasn't changed."""
    service = _make_service_stub(mocker)

    # Configure mock session manager
    mock_manager = mocker.MagicMock()
    service.session_manager = mock_manager

    # Create session with initial state
    session = SimpleNamespace(
        id="session-123",
        deployment_id=str(service.deployment.id),
        state={"counter": 1, "data": "value"},
    )

    # Call with identical state snapshot
    state_snapshot = {"counter": 1, "data": "value"}
    service._persist_session_state(session, state_snapshot)

    # Verify manager.persist_state was NOT called
    mock_manager.persist_state.assert_not_called()


def test_persist_session_state_persists_changes(
    mocker: MockerFixture,
) -> None:
    """_persist_session_state should delegate to manager when state differs."""
    service = _make_service_stub(mocker)

    # Configure mock session manager
    mock_manager = mocker.MagicMock()
    service.session_manager = mock_manager

    # Create session with initial state
    session = SimpleNamespace(
        id="session-123",
        deployment_id=str(service.deployment.id),
        state={"counter": 1},
    )

    # Call with modified state snapshot
    state_snapshot = {"counter": 2, "new_field": "added"}
    service._persist_session_state(session, state_snapshot)

    # Verify manager.persist_state was called with correct arguments
    mock_manager.persist_state.assert_called_once_with(session, state_snapshot)
