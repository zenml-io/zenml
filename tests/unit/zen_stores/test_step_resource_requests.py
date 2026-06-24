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

import pytest

from zenml.config.resource_settings import ResourceSettings
from zenml.enums import ResourceRequestReclaimTolerance, StepRuntime
from zenml.exceptions import IllegalOperationError
from zenml.zen_stores.sql_zen_store import SqlZenStore


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
