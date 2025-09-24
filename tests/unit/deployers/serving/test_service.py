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

from contextlib import contextmanager
from types import SimpleNamespace
from typing import Dict, Iterator
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel
from pytest_mock import MockerFixture

from zenml.deployers.server.models import BasePipelineInvokeRequest
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
    )
    pipeline_spec = SimpleNamespace(
        parameters={"city": "London"},
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        outputs=[],
        source="test.module.pipeline",
    )
    stack = SimpleNamespace(name="test_stack")

    return SimpleNamespace(
        id=uuid4(),
        name="snapshot",
        pipeline_configuration=pipeline_configuration,
        pipeline_spec=pipeline_spec,
        step_configurations={},
        stack=stack,
    )


def _make_deployment(snapshot: SimpleNamespace) -> SimpleNamespace:
    """Create a deployment stub with the attributes accessed by the service."""
    return SimpleNamespace(id=uuid4(), name="deployment", snapshot=snapshot)


def _make_service_stub(
    deployment: SimpleNamespace, mocker: MockerFixture
) -> PipelineDeploymentService:
    """Create a service instance without running __init__ for isolated tests."""
    service = PipelineDeploymentService.__new__(PipelineDeploymentService)
    service._client = mocker.MagicMock()
    service._orchestrator = mocker.MagicMock()
    service._params_model = WeatherParams
    service.pipeline_state = None
    service.service_start_time = 100.0
    service.last_execution_time = None
    service.total_executions = 0
    service.deployment = deployment
    service.snapshot = deployment.snapshot
    return service


def test_initialization_loads_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """__init__ should load the snapshot from the store."""
    snapshot_id = uuid4()
    snapshot = _make_snapshot()

    class DummyZenStore:
        """In-memory zen store stub that records requested snapshot IDs."""

        def __init__(self) -> None:
            self.requested: UUID | None = None

        def get_snapshot(self, snapshot_id: UUID) -> SimpleNamespace:  # noqa: D401
            """Return the stored snapshot and remember the requested ID."""

            self.requested = snapshot_id
            return snapshot

    dummy_store = DummyZenStore()

    class DummyClient:
        """Client stub providing access to the dummy zen store."""

        def __init__(self) -> None:
            self.zen_store = dummy_store

    monkeypatch.setattr("zenml.deployers.server.service.Client", DummyClient)

    service = PipelineDeploymentService(snapshot_id)

    assert service.snapshot is snapshot
    assert dummy_store.requested == snapshot_id


def test_initialize_sets_up_orchestrator(
    monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> None:
    """initialize should activate integrations and build orchestrator."""
    snapshot = _make_snapshot()

    class DummyZenStore:
        """Zen store stub that supplies the prepared snapshot."""

        def get_snapshot(self, snapshot_id: UUID) -> SimpleNamespace:  # noqa: D401
            return snapshot

    class DummyClient:
        """Client stub exposing only the attributes required by the service."""

        def __init__(self) -> None:
            self.zen_store = DummyZenStore()

    monkeypatch.setattr("zenml.deployers.server.service.Client", DummyClient)

    mock_registry = mocker.MagicMock()
    monkeypatch.setattr(
        "zenml.deployers.server.service.integration_registry", mock_registry
    )

    monkeypatch.setattr(
        "zenml.deployers.server.service.build_params_model_from_snapshot",
        lambda *, snapshot: WeatherParams,
    )

    mock_orchestrator = mocker.MagicMock()
    monkeypatch.setattr(
        "zenml.deployers.server.service.SharedLocalOrchestrator",
        mocker.MagicMock(return_value=mock_orchestrator),
    )

    @contextmanager
    def _noop_env(_: object) -> Iterator[None]:
        """Provide a no-op temporary environment context manager for tests."""

        yield

    monkeypatch.setattr(
        "zenml.deployers.server.service.env_utils.temporary_environment",
        _noop_env,
    )

    service = PipelineDeploymentService(uuid4())
    service.initialize()

    mock_registry.activate_integrations.assert_called_once()
    assert service.params_model is WeatherParams
    assert service._orchestrator is mock_orchestrator
    mock_orchestrator.set_shared_run_state.assert_called_once_with(
        service.pipeline_state
    )


def test_execute_pipeline_calls_subroutines(mocker: MockerFixture) -> None:
    """execute_pipeline should orchestrate helper methods and return response."""
    snapshot = _make_snapshot()
    service = _make_service_stub(snapshot, mocker)

    placeholder_run = mocker.MagicMock()
    captured_outputs: Dict[str, Dict[str, object]] = {
        "step1": {"result": "value"}
    }
    mapped_outputs = {"result": "value"}

    service._execute_with_orchestrator = mocker.MagicMock(
        return_value=(placeholder_run, captured_outputs)
    )
    service._map_outputs = mocker.MagicMock(return_value=mapped_outputs)
    service._build_response = mocker.MagicMock(return_value="response")

    request = BasePipelineInvokeRequest(
        parameters=WeatherParams(city="Berlin")
    )
    result = service.execute_pipeline(request)

    assert result == "response"
    service._execute_with_orchestrator.assert_called_once_with(
        resolved_params={"city": "Berlin", "temperature": 20},
        use_in_memory=False,
    )
    service._map_outputs.assert_called_once_with(captured_outputs)
    service._build_response.assert_called_once()


def test_map_outputs_returns_filtered_mapping(mocker: MockerFixture) -> None:
    """_map_outputs should align runtime outputs to pipeline spec."""
    snapshot = _make_snapshot()
    snapshot.pipeline_spec.outputs = [
        SimpleNamespace(step_name="trainer", output_name="model"),
        SimpleNamespace(step_name="trainer", output_name="metrics"),
        SimpleNamespace(step_name="evaluator", output_name="report"),
    ]

    service = _make_service_stub(snapshot, mocker)

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
    snapshot = _make_snapshot()
    service = _make_service_stub(snapshot, mocker)

    assert service._map_outputs(None) == {}


def test_build_response_success(
    monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> None:
    """_build_response should return a successful response payload."""
    snapshot = _make_snapshot()
    service = _make_service_stub(snapshot, mocker)

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
    snapshot = _make_snapshot()
    service = _make_service_stub(snapshot, mocker)

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
    snapshot = _make_snapshot()
    service = _make_service_stub(snapshot, mocker)

    info = service.get_service_info()

    assert info.pipeline.name == "test_pipeline"
    assert info.snapshot.id == snapshot.id
    assert info.pipeline.parameters == {"city": "London"}
    assert info.pipeline.input_schema == {"type": "object"}


def test_execution_metrics_reflect_counters(mocker: MockerFixture) -> None:
    """get_execution_metrics should return counters from service state."""
    snapshot = _make_snapshot()
    service = _make_service_stub(snapshot, mocker)
    service.total_executions = 5
    service.last_execution_time = None

    metrics = service.get_execution_metrics()
    assert metrics.total_executions == 5
    assert metrics.last_execution_time is None


def test_input_output_schema_properties(mocker: MockerFixture) -> None:
    """input_schema and output_schema expose snapshot schemas."""
    snapshot = _make_snapshot()
    service = _make_service_stub(snapshot, mocker)

    assert service.input_schema == {"type": "object"}
    assert service.output_schema == {"type": "object"}
