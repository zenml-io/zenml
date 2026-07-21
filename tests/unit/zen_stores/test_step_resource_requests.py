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
"""Tests for step-run resource request helpers."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from zenml.config.resource_settings import ResourceSettings
from zenml.enums import (
    ExecutionStatus,
    ResourceRequestReclaimTolerance,
    ResourceRequestRuntimeState,
    ResourceRequestStatus,
    StepRuntime,
)
from zenml.exceptions import IllegalOperationError
from zenml.zen_stores.sql_zen_store import SqlZenStore


def _sql_store_with_resource_pools() -> SqlZenStore:
    store = object.__new__(SqlZenStore)
    resource_pools = MagicMock()
    renewed_request = MagicMock()
    renewed_request.status = ResourceRequestStatus.ALLOCATED
    resource_pools.renew_resource_request.return_value = renewed_request
    store._resource_pools = resource_pools
    return store


def _heartbeat_step_run() -> MagicMock:
    return MagicMock(
        status=ExecutionStatus.RUNNING.value,
        resource_request_id=uuid4(),
        heartbeat_threshold=30,
        name="step",
    )


def test_omitted_inline_reclaim_tolerance_is_none() -> None:
    """Inline runtime requests use none when the user did not set tolerance."""
    assert (
        ResourceSettings().effective_reclaim_tolerance(StepRuntime.INLINE)
        is ResourceRequestReclaimTolerance.NONE
    )


def test_omitted_isolated_reclaim_tolerance_is_any() -> None:
    """Isolated runtime requests use any when the user did not set tolerance."""
    assert (
        ResourceSettings().effective_reclaim_tolerance(StepRuntime.ISOLATED)
        is ResourceRequestReclaimTolerance.ANY
    )


def test_explicit_reclaim_tolerance_is_effective_value() -> None:
    """Explicit reclaim tolerance is preserved for resource requests."""
    resource_settings = ResourceSettings(
        reclaim_tolerance=ResourceRequestReclaimTolerance.ANY
    )

    assert (
        resource_settings.effective_reclaim_tolerance(StepRuntime.INLINE)
        is ResourceRequestReclaimTolerance.ANY
    )


def test_implicit_inline_steps_use_none_reclaim_tolerance() -> None:
    """Inline dynamic steps treat omitted reclaim tolerance as none."""
    SqlZenStore._validate_reclaim_tolerance_for_resource_request(
        resource_settings=ResourceSettings(),
        runtime=StepRuntime.INLINE,
        heartbeat_enabled=False,
        step_name="step",
    )


def test_explicit_inline_reclaimable_steps_fail_validation() -> None:
    """Inline dynamic steps cannot be explicitly configured as reclaimable."""
    with pytest.raises(IllegalOperationError):
        SqlZenStore._validate_reclaim_tolerance_for_resource_request(
            resource_settings=ResourceSettings(
                reclaim_tolerance=ResourceRequestReclaimTolerance.ANY
            ),
            runtime=StepRuntime.INLINE,
            heartbeat_enabled=True,
            step_name="step",
        )


def test_isolated_reclaimable_steps_require_heartbeat() -> None:
    """Heartbeat is required for reclaimable isolated dynamic steps."""
    with pytest.raises(IllegalOperationError):
        SqlZenStore._validate_reclaim_tolerance_for_resource_request(
            resource_settings=ResourceSettings(
                reclaim_tolerance=ResourceRequestReclaimTolerance.COORDINATED
            ),
            runtime=StepRuntime.ISOLATED,
            heartbeat_enabled=False,
            step_name="step",
        )


def test_isolated_non_reclaimable_steps_do_not_require_heartbeat() -> None:
    """Non-reclaimable isolated steps can run without heartbeat."""
    SqlZenStore._validate_reclaim_tolerance_for_resource_request(
        resource_settings=ResourceSettings(),
        runtime=StepRuntime.ISOLATED,
        heartbeat_enabled=False,
        step_name="step",
    )


def test_heartbeat_renewal_uses_expected_heartbeat_interval(
    monkeypatch,
) -> None:
    """Heartbeat renewal leases use the timeout reported by the caller."""
    fixed_now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(
        "zenml.zen_stores.sql_zen_store.utc_now", lambda: fixed_now
    )
    store = _sql_store_with_resource_pools()
    step_run = _heartbeat_step_run()

    status = store._renew_step_resource_request_from_heartbeat(
        session=MagicMock(),
        step_run=step_run,
        heartbeat_liveness_timeout_seconds=42,
    )

    assert status == ExecutionStatus.RUNNING
    renewal_request = store.resource_pools.renew_resource_request.call_args[0][
        1
    ]
    assert renewal_request.lease_expires_at == fixed_now + timedelta(
        seconds=42
    )
    assert renewal_request.runtime_state == ResourceRequestRuntimeState.RUNNING


def test_heartbeat_renewal_without_expected_interval_uses_step_threshold(
    monkeypatch,
) -> None:
    """Legacy heartbeat calls renew leases from the stored step threshold."""
    fixed_now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(
        "zenml.zen_stores.sql_zen_store.utc_now", lambda: fixed_now
    )
    store = _sql_store_with_resource_pools()
    step_run = _heartbeat_step_run()

    store._renew_step_resource_request_from_heartbeat(
        session=MagicMock(),
        step_run=step_run,
    )

    renewal_request = store.resource_pools.renew_resource_request.call_args[0][
        1
    ]
    assert renewal_request.lease_expires_at == fixed_now + timedelta(
        minutes=step_run.heartbeat_threshold
    )
