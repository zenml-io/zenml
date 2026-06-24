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
"""Tests for step launcher resource request lease handling."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from zenml.config.resource_settings import ResourceSettings
from zenml.enums import ResourceRequestReclaimTolerance, ResourceRequestStatus
from zenml.models import (
    ResourceRequestRenewalRequest,
    ResourceRequestResponse,
    ResourceRequestResponseBody,
    ResourceRequestResponseMetadata,
    ResourceRequestResponseResources,
)
from zenml.orchestrators.step_launcher import StepLauncher


def _launcher() -> StepLauncher:
    return object.__new__(StepLauncher)


def _resource_request(
    *,
    status: ResourceRequestStatus,
    lease_expires_at: datetime | None,
) -> ResourceRequestResponse:
    request_id = uuid4()
    return ResourceRequestResponse(
        id=request_id,
        name=str(request_id),
        body=ResourceRequestResponseBody(
            status=status,
            user=uuid4(),
            created=datetime.now(tz=timezone.utc),
            updated=datetime.now(tz=timezone.utc),
            version=1,
            lease_expires_at=lease_expires_at,
            reclaim_tolerance=ResourceRequestReclaimTolerance.NONE,
        ),
        metadata=ResourceRequestResponseMetadata(),
        resources=ResourceRequestResponseResources(),
    )


def _step_run_info(
    *,
    resource_request_id,
    resource_request: ResourceRequestResponse | None = None,
    resource_settings: ResourceSettings | None = None,
) -> MagicMock:
    if resource_request_id is None and resource_request is not None:
        resource_request_id = resource_request.id
    return MagicMock(
        pipeline_step_name="step",
        step_run_id=uuid4(),
        config=MagicMock(
            resource_settings=resource_settings or ResourceSettings(),
        ),
        step_run=MagicMock(
            resource_request=resource_request,
            resource_request_id=resource_request_id,
        ),
    )


def test_wait_only_calls_renew(monkeypatch):
    """Resource request polling renews the request instead of fetching it."""
    launcher = _launcher()
    request_id = uuid4()
    allocated = _resource_request(
        status=ResourceRequestStatus.ALLOCATED,
        lease_expires_at=datetime.now(tz=timezone.utc),
    )
    zen_store = MagicMock(
        renew_resource_request=MagicMock(return_value=allocated)
    )
    monkeypatch.setattr(
        "zenml.orchestrators.step_launcher.Client",
        lambda: MagicMock(zen_store=zen_store),
    )
    monkeypatch.setattr(
        "zenml.orchestrators.step_launcher.publish_utils.publish_step_run_status_update",
        MagicMock(),
    )

    result = launcher._wait_until_resources_acquired(
        _step_run_info(resource_request_id=request_id)
    )

    assert result == allocated
    assert zen_store.renew_resource_request.call_count == 2
    assert not hasattr(zen_store, "get_resource_request") or (
        not zen_store.get_resource_request.called
    )
    polling_renewal = zen_store.renew_resource_request.call_args_list[0][0][1]
    initialization_renewal = zen_store.renew_resource_request.call_args_list[
        1
    ][0][1]
    assert isinstance(polling_renewal, ResourceRequestRenewalRequest)
    assert isinstance(initialization_renewal, ResourceRequestRenewalRequest)


@patch(
    "zenml.orchestrators.step_launcher.utc_now",
    return_value=datetime(2026, 1, 1, tzinfo=timezone.utc),
)
def test_wait_extends_initialization_lease_when_step_run_has_request(
    _utc_now_mock, monkeypatch
):
    """Hydrated allocated requests are renewed with the initialization lease."""
    launcher = _launcher()
    allocated = _resource_request(
        status=ResourceRequestStatus.ALLOCATED,
        lease_expires_at=datetime.now(tz=timezone.utc),
    )
    renewed = _resource_request(
        status=ResourceRequestStatus.ALLOCATED,
        lease_expires_at=datetime(2026, 1, 1, 1, 0, 0, tzinfo=timezone.utc),
    )
    zen_store = MagicMock(
        renew_resource_request=MagicMock(return_value=renewed)
    )
    monkeypatch.setattr(
        "zenml.orchestrators.step_launcher.Client",
        lambda: MagicMock(zen_store=zen_store),
    )
    monkeypatch.setattr(
        "zenml.orchestrators.step_launcher.publish_utils.publish_step_run_status_update",
        MagicMock(),
    )

    result = launcher._wait_until_resources_acquired(
        _step_run_info(
            resource_request=allocated,
            resource_request_id=allocated.id,
            resource_settings=ResourceSettings(
                initialization_lease_seconds=3600
            ),
        ),
    )

    assert result == renewed
    renewal_request = zen_store.renew_resource_request.call_args[0][1]
    assert renewal_request.lease_expires_at == datetime(
        2026, 1, 1, tzinfo=timezone.utc
    ) + timedelta(seconds=3600)


@patch(
    "zenml.orchestrators.step_launcher.StepHeartbeatWorker.resource_request_lease_expires_at",
    return_value=datetime(2026, 1, 1, tzinfo=timezone.utc),
)
@patch(
    "zenml.orchestrators.step_launcher.exponential_backoff_delays",
    return_value=iter([3.0, 0.0]),
)
def test_wait_renew_lease_includes_backoff_delay(
    _delays_mock, _lease_expires_at_mock, monkeypatch
):
    """Resource request lease renewal includes the next polling delay."""
    launcher = _launcher()
    request_id = uuid4()
    pending = _resource_request(
        status=ResourceRequestStatus.PENDING,
        lease_expires_at=datetime.now(tz=timezone.utc),
    )
    allocated = _resource_request(
        status=ResourceRequestStatus.ALLOCATED,
        lease_expires_at=datetime.now(tz=timezone.utc),
    )
    zen_store = MagicMock(
        renew_resource_request=MagicMock(
            side_effect=[pending, allocated, allocated]
        )
    )
    monkeypatch.setattr(
        "zenml.orchestrators.step_launcher.Client",
        lambda: MagicMock(zen_store=zen_store),
    )
    monkeypatch.setattr(
        "zenml.orchestrators.step_launcher.time.sleep", MagicMock()
    )
    monkeypatch.setattr(
        "zenml.orchestrators.step_launcher.publish_utils.publish_step_run_status_update",
        MagicMock(),
    )

    launcher._wait_until_resources_acquired(
        _step_run_info(resource_request_id=request_id)
    )

    first_renewal = zen_store.renew_resource_request.call_args_list[0][0][1]
    assert first_renewal.lease_expires_at == datetime(
        2026, 1, 1, tzinfo=timezone.utc
    ) + timedelta(seconds=3.0)


@patch(
    "zenml.orchestrators.step_launcher.exponential_backoff_delays",
    return_value=iter([0.0, 0.0]),
)
def test_wait_renews_each_poll(_delays_mock, monkeypatch):
    """Resource request polling renews the lease on each store read."""
    launcher = _launcher()
    request_id = uuid4()
    pending = _resource_request(
        status=ResourceRequestStatus.PENDING,
        lease_expires_at=datetime.now(tz=timezone.utc),
    )
    allocated = _resource_request(
        status=ResourceRequestStatus.ALLOCATED,
        lease_expires_at=datetime.now(tz=timezone.utc),
    )
    zen_store = MagicMock(
        renew_resource_request=MagicMock(
            side_effect=[pending, allocated, allocated]
        )
    )
    monkeypatch.setattr(
        "zenml.orchestrators.step_launcher.Client",
        lambda: MagicMock(zen_store=zen_store),
    )
    sleep_mock = MagicMock()
    monkeypatch.setattr(
        "zenml.orchestrators.step_launcher.time.sleep", sleep_mock
    )
    monkeypatch.setattr(
        "zenml.orchestrators.step_launcher.publish_utils.publish_step_run_status_update",
        MagicMock(),
    )

    launcher._wait_until_resources_acquired(
        _step_run_info(resource_request_id=request_id)
    )

    assert zen_store.renew_resource_request.call_count == 3
    sleep_mock.assert_called_once_with(0.0)


@patch(
    "zenml.orchestrators.step_launcher.exponential_backoff_delays",
    return_value=iter([0.0, 0.0]),
)
def test_wait_renews_after_first_cycle_with_cached_request(
    _delays_mock, monkeypatch
):
    """Pending cached requests are renewed after the first polling cycle."""
    launcher = _launcher()
    pending = _resource_request(
        status=ResourceRequestStatus.PENDING,
        lease_expires_at=datetime.now(tz=timezone.utc),
    )
    allocated = _resource_request(
        status=ResourceRequestStatus.ALLOCATED,
        lease_expires_at=datetime.now(tz=timezone.utc),
    )
    zen_store = MagicMock(
        renew_resource_request=MagicMock(return_value=allocated)
    )
    monkeypatch.setattr(
        "zenml.orchestrators.step_launcher.Client",
        lambda: MagicMock(zen_store=zen_store),
    )
    sleep_mock = MagicMock()
    monkeypatch.setattr(
        "zenml.orchestrators.step_launcher.time.sleep", sleep_mock
    )
    monkeypatch.setattr(
        "zenml.orchestrators.step_launcher.publish_utils.publish_step_run_status_update",
        MagicMock(),
    )

    launcher._wait_until_resources_acquired(
        _step_run_info(
            resource_request=pending,
            resource_request_id=pending.id,
        ),
    )

    assert zen_store.renew_resource_request.call_count == 2
    sleep_mock.assert_called_once_with(0.0)


@patch(
    "zenml.orchestrators.step_launcher.exponential_backoff_delays",
    return_value=iter([0.0, 0.0]),
)
def test_wait_raises_when_allocation_timeout_elapses(
    _delays_mock, monkeypatch
):
    """Resource request polling stops after the allocation wait timeout."""
    launcher = _launcher()
    request_id = uuid4()
    pending = _resource_request(
        status=ResourceRequestStatus.PENDING,
        lease_expires_at=datetime.now(tz=timezone.utc),
    )
    zen_store = MagicMock(
        renew_resource_request=MagicMock(return_value=pending)
    )
    started_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(
        "zenml.orchestrators.step_launcher.utc_now",
        MagicMock(
            side_effect=[
                started_at,
                started_at + timedelta(seconds=30),
                started_at + timedelta(seconds=60),
            ]
        ),
    )
    monkeypatch.setattr(
        "zenml.orchestrators.step_launcher.Client",
        lambda: MagicMock(zen_store=zen_store),
    )
    monkeypatch.setattr(
        "zenml.orchestrators.step_launcher.time.sleep", MagicMock()
    )

    with pytest.raises(RuntimeError, match="Timed out after 60 seconds"):
        launcher._wait_until_resources_acquired(
            _step_run_info(
                resource_request_id=request_id,
                resource_settings=ResourceSettings(
                    allocation_wait_timeout_seconds=60
                ),
            ),
        )


def test_dynamic_orchestrator_receives_allocated_resource_request(
    monkeypatch,
):
    """Dynamic orchestrator isolated-step submission receives allocations."""
    launcher = _launcher()
    allocated = _resource_request(
        status=ResourceRequestStatus.ALLOCATED,
        lease_expires_at=datetime.now(tz=timezone.utc),
    )
    submit_isolated_step = MagicMock()
    launcher._stack = MagicMock(
        orchestrator=MagicMock(
            submit_isolated_step=submit_isolated_step,
        )
    )
    launcher._wait = False

    monkeypatch.setattr(
        "zenml.orchestrators.step_launcher.orchestrator_utils.get_config_environment_vars",
        MagicMock(return_value=({}, {})),
    )
    monkeypatch.setattr(
        "zenml.orchestrators.step_launcher.env_utils.get_runtime_environment",
        MagicMock(return_value={}),
    )

    launcher._run_step_with_dynamic_orchestrator(
        step_run_info=MagicMock(run_id=uuid4(), config=MagicMock()),
        allocated_resource_request=allocated,
    )

    assert (
        submit_isolated_step.call_args.kwargs["allocated_resource_request"]
        == allocated
    )


def test_step_operator_receives_allocated_resource_request(monkeypatch):
    """Step operator submission receives the allocated resource request."""

    class EntrypointConfiguration:
        @staticmethod
        def get_entrypoint_command():
            return ["python", "-m", "zenml"]

        @staticmethod
        def get_entrypoint_arguments(step_name, snapshot_id, step_run_id):
            return [step_name, str(snapshot_id), step_run_id]

    launcher = _launcher()
    allocated = _resource_request(
        status=ResourceRequestStatus.ALLOCATED,
        lease_expires_at=datetime.now(tz=timezone.utc),
    )
    step_operator = MagicMock(
        name="step_operator",
        entrypoint_config_class=EntrypointConfiguration,
    )
    step_operator.submit = MagicMock()
    launcher._stack = MagicMock()
    launcher._snapshot = MagicMock(id=uuid4())
    launcher._invocation_id = "step"
    launcher._wait = False

    monkeypatch.setattr(
        "zenml.orchestrators.step_launcher._get_step_operator",
        MagicMock(return_value=step_operator),
    )
    monkeypatch.setattr(
        "zenml.orchestrators.step_launcher.orchestrator_utils.get_config_environment_vars",
        MagicMock(return_value=({}, {})),
    )
    monkeypatch.setattr(
        "zenml.orchestrators.step_launcher.env_utils.get_runtime_environment",
        MagicMock(return_value={}),
    )

    launcher._run_step_with_step_operator(
        step_operator_name=None,
        step_run_info=MagicMock(
            run_id=uuid4(),
            config=MagicMock(),
            step_run_id=uuid4(),
        ),
        allocated_resource_request=allocated,
    )

    assert (
        step_operator.submit.call_args.kwargs["allocated_resource_request"]
        == allocated
    )
