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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Cancellation during step preparation and resource acquisition."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from zenml.config.resource_settings import ResourceSettings
from zenml.enums import (
    ExecutionStatus,
    PipelineRunStopMode,
    ResourceRequestRuntimeState,
    ResourceRequestStatus,
)
from zenml.exceptions import IllegalOperationError, RunStoppedException
from zenml.orchestrators.step_launcher import StepLauncher


@pytest.fixture
def launcher() -> StepLauncher:
    """Construct a launcher without loading configuration or a real store."""
    value = object.__new__(StepLauncher)
    value._snapshot = MagicMock(id=uuid4(), is_dynamic=False)
    value._step = MagicMock(config=MagicMock(step_operator=None))
    value._stack = MagicMock()
    value._invocation_id = "step"
    value._wait = False
    value._admitted_step_run_id = None
    return value


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Replace the store and polling delays with deterministic mocks."""
    value = MagicMock()
    monkeypatch.setattr(
        "zenml.orchestrators.step_launcher.Client",
        lambda: SimpleNamespace(zen_store=value),
    )
    monkeypatch.setattr(
        "zenml.orchestrators.step_launcher.time.sleep", MagicMock()
    )
    monkeypatch.setattr(
        "zenml.orchestrators.step_launcher.exponential_backoff_delays",
        lambda **_: iter([0.0, 0.0]),
    )
    return value


@pytest.fixture
def step_run_info() -> MagicMock:
    """Represent an admitted attempt waiting for resource allocation."""
    return MagicMock(
        pipeline_step_name="step",
        run_id=uuid4(),
        step_run_id=uuid4(),
        config=SimpleNamespace(resource_settings=ResourceSettings()),
        step_run=SimpleNamespace(
            resource_request_id=uuid4(), resource_request=None
        ),
    )


@pytest.mark.parametrize(
    "current_status",
    [
        ExecutionStatus.QUEUED,
        ExecutionStatus.STOPPED,
        ExecutionStatus.FAILED,
        ExecutionStatus.COMPLETED,
    ],
)
def test_immediate_stop_does_not_renew_or_overwrite_terminal_attempt(
    launcher: StepLauncher,
    store: MagicMock,
    step_run_info: MagicMock,
    current_status: ExecutionStatus,
) -> None:
    """Concurrent cleanup can settle the queued attempt before its poller."""
    store.get_run.return_value = SimpleNamespace(
        stop_mode=PipelineRunStopMode.IMMEDIATE
    )
    store.get_run_step.return_value = SimpleNamespace(status=current_status)

    with pytest.raises(RunStoppedException, match="waiting for resources"):
        launcher._wait_until_resources_acquired(step_run_info)

    store.renew_resource_request.assert_not_called()
    if current_status.is_finished:
        store.update_run_step.assert_not_called()
    else:
        store.update_run_step.assert_called_once()
        update = store.update_run_step.call_args.args[1]
        assert update.status == ExecutionStatus.STOPPED


def test_immediate_stop_interrupts_an_existing_allocation_wait(
    launcher: StepLauncher, store: MagicMock, step_run_info: MagicMock
) -> None:
    """A new stop request interrupts queuing before the next lease renewal."""
    store.get_run.side_effect = [
        SimpleNamespace(stop_mode=None),
        SimpleNamespace(stop_mode=PipelineRunStopMode.IMMEDIATE),
    ]
    store.get_run_step.return_value = SimpleNamespace(
        status=ExecutionStatus.QUEUED
    )
    store.renew_resource_request.return_value = SimpleNamespace(
        id=step_run_info.step_run.resource_request_id,
        status=ResourceRequestStatus.PENDING,
    )

    with pytest.raises(RunStoppedException):
        launcher._wait_until_resources_acquired(step_run_info)

    store.renew_resource_request.assert_called_once()
    assert store.get_run.call_count == 2


def test_graceful_stop_allows_admitted_attempt_to_acquire_resources(
    launcher: StepLauncher, store: MagicMock, step_run_info: MagicMock
) -> None:
    """Graceful cancellation lets the admitted queued attempt execute."""
    store.get_run.return_value = SimpleNamespace(
        stop_mode=PipelineRunStopMode.GRACEFUL
    )
    allocated = SimpleNamespace(
        id=step_run_info.step_run.resource_request_id,
        status=ResourceRequestStatus.ALLOCATED,
    )
    store.renew_resource_request.side_effect = [
        SimpleNamespace(id=allocated.id, status=ResourceRequestStatus.PENDING),
        allocated,
        allocated,
    ]

    result = launcher._wait_until_resources_acquired(step_run_info)

    assert result is allocated
    assert store.renew_resource_request.call_count == 3
    last_renewal = store.renew_resource_request.call_args.args[1]
    assert last_renewal.runtime_state == ResourceRequestRuntimeState.SUBMITTED
    store.update_run_step.assert_called_once()
    update = store.update_run_step.call_args.kwargs["step_run_update"]
    assert update.status == ExecutionStatus.RUNNING
    assert update.claim_execution


def test_preparation_failure_survives_concurrent_admission_refusal(
    launcher: StepLauncher,
    store: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recording a preparation error must not replace its original cause."""
    current_run = MagicMock(stop_mode=None)
    current_run.get_body.return_value.model_fields_set = {"stop_mode"}
    store.get_run.return_value = current_run
    store.create_run_step.side_effect = IllegalOperationError(
        "Stop closed admission during preparation"
    )
    factory = MagicMock()
    original = ValueError("Preparing the step failed")
    factory.populate_request.side_effect = original
    monkeypatch.setattr(
        "zenml.orchestrators.step_launcher.step_run_utils.StepRunRequestFactory",
        lambda **_: factory,
    )

    with pytest.raises(ValueError) as raised:
        launcher._prepare_step_run(
            pipeline_run=MagicMock(id=uuid4()), logs_context=nullcontext()
        )

    assert raised.value is original
    store.create_run_step.assert_called_once()
