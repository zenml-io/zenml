#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Unit tests for SkyPilot orchestrator entrypoint helpers."""

import importlib
import sys
import types
from typing import Any, Dict, List

import pytest

from zenml.enums import ExecutionStatus
from zenml.integrations.skypilot.flavors.skypilot_orchestrator_base_vm_config import (
    SkypilotBaseOrchestratorSettings,
)


def _load_entrypoint_module(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Loads the SkyPilot entrypoint module with a stubbed `sky` module."""
    fake_sky = types.ModuleType("sky")
    fake_sky.StatusRefreshMode = types.SimpleNamespace(AUTO="AUTO")
    fake_sky.clouds = types.SimpleNamespace(
        Cloud=object,
        Kubernetes=type("Kubernetes", (), {}),
    )
    fake_sky.status = lambda *args, **kwargs: "request"
    fake_sky.stream_and_get = lambda request_id: []
    fake_sky.launch = lambda *args, **kwargs: "request"
    fake_sky.exec = lambda *args, **kwargs: "request"
    fake_sky.start = lambda *args, **kwargs: "request"
    fake_sky.down = lambda *args, **kwargs: "request"
    fake_sky.get = lambda request_id: (0, object())
    fake_sky.tail_logs = lambda **kwargs: 0

    class _Task:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

        def set_resources(self, resources: Any) -> "_Task":
            return self

    class _Resources:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    fake_sky.Task = _Task
    fake_sky.Resources = _Resources
    monkeypatch.setitem(sys.modules, "sky", fake_sky)

    import zenml.integrations.skypilot.orchestrators.skypilot_orchestrator_entrypoint as entrypoint
    import zenml.integrations.skypilot.utils as utils

    importlib.reload(utils)
    return importlib.reload(entrypoint)


def test_generate_cluster_name_is_deterministic_and_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tests deterministic cluster name generation with bounded length."""
    entrypoint = _load_entrypoint_module(monkeypatch)
    settings = SkypilotBaseOrchestratorSettings(
        instance_type="m5.large",
        disk_size=50,
        network_tier="best",
        resources_settings={"custom": "value"},
    )

    name_one = entrypoint._generate_cluster_name(
        orchestrator_run_id="host-name-123",
        settings=settings,
        default_instance_type=None,
    )
    name_two = entrypoint._generate_cluster_name(
        orchestrator_run_id="host-name-123",
        settings=settings,
        default_instance_type=None,
    )
    changed_name = entrypoint._generate_cluster_name(
        orchestrator_run_id="host-name-123",
        settings=settings.model_copy(update={"num_nodes": 2}),
        default_instance_type=None,
    )

    assert name_one == name_two
    assert name_one != changed_name
    assert name_one.startswith("cluster-host-name-123-")
    assert len(name_one) <= entrypoint._MAX_CLUSTER_NAME_LENGTH


def test_resolve_pipeline_run_prefers_explicit_run_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tests explicit run_id path avoids the fragile list query."""
    entrypoint = _load_entrypoint_module(monkeypatch)
    expected_run = types.SimpleNamespace(id="run-123")

    class _Client:
        def __init__(self) -> None:
            self.list_called = False

        def get_pipeline_run(self, run_id: str) -> Any:
            assert run_id == "run-123"
            return expected_run

        def list_pipeline_runs(self, **kwargs: Any) -> Any:
            self.list_called = True
            return []

    client = _Client()
    run = entrypoint._resolve_pipeline_run(
        client=client,
        run_name="my-run",
        snapshot_id="snapshot-1",
        run_id="run-123",
    )

    assert run is expected_run
    assert client.list_called is False


def test_resolve_pipeline_run_raises_for_missing_explicit_run_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tests explicit run lookup failures are surfaced clearly."""
    entrypoint = _load_entrypoint_module(monkeypatch)

    class _Client:
        def get_pipeline_run(self, run_id: str) -> Any:
            raise RuntimeError("not found")

    with pytest.raises(RuntimeError, match="Unable to fetch pipeline run"):
        entrypoint._resolve_pipeline_run(
            client=_Client(),
            run_name="my-run",
            snapshot_id="snapshot-1",
            run_id="missing-run-id",
        )


def test_resolve_pipeline_run_fallback_uses_latest_initializing_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tests fallback query when run_id is not provided."""
    entrypoint = _load_entrypoint_module(monkeypatch)
    run = types.SimpleNamespace(id="resolved-run-id")

    class _Page:
        def __init__(self, items: List[Any]) -> None:
            self._items = items
            self.total = len(items)

        def __getitem__(self, index: int) -> Any:
            return self._items[index]

    class _Client:
        def __init__(self) -> None:
            self.kwargs: Dict[str, Any] = {}

        def list_pipeline_runs(self, **kwargs: Any) -> Any:
            self.kwargs = kwargs
            return _Page([run])

    client = _Client()
    resolved = entrypoint._resolve_pipeline_run(
        client=client,
        run_name="my-run",
        snapshot_id="snapshot-1",
        run_id=None,
    )

    assert resolved is run
    assert client.kwargs["sort_by"] == "desc:created"
    assert client.kwargs["size"] == 1
    assert client.kwargs["snapshot_id"] == "snapshot-1"
    assert client.kwargs["status"] == ExecutionStatus.INITIALIZING


def test_resolve_pipeline_run_fallback_raises_for_empty_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tests fallback query raises when no initializing run can be found."""
    entrypoint = _load_entrypoint_module(monkeypatch)

    class _Page:
        total = 0

        def __getitem__(self, index: int) -> Any:
            raise IndexError("empty")

    class _Client:
        def list_pipeline_runs(self, **kwargs: Any) -> Any:
            return _Page()

    with pytest.raises(RuntimeError, match="Unable to resolve a pipeline run"):
        entrypoint._resolve_pipeline_run(
            client=_Client(),
            run_name="my-run",
            snapshot_id="snapshot-1",
            run_id=None,
        )
