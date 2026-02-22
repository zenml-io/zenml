#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Tests for Modal sandbox cost estimation metadata."""

from typing import Optional

import pytest

from zenml.integrations.modal.sandboxes.modal_sandbox import (
    ModalSandboxSession,
)
from zenml.sandboxes import SandboxSessionMetadata


def _create_session(
    *,
    metadata: SandboxSessionMetadata,
    cpu_cost_per_core_second_usd: Optional[float],
    memory_cost_per_gib_second_usd: Optional[float],
) -> ModalSandboxSession:
    """Creates a Modal sandbox session object for metadata tests."""
    return ModalSandboxSession(
        sandbox=object(),
        app_run_context=object(),
        app_run_context_is_async=False,
        raise_on_failure=False,
        metadata=metadata,
        cpu=2.0,
        memory_mb=2048,
        gpu=None,
        cpu_cost_per_core_second_usd=cpu_cost_per_core_second_usd,
        memory_cost_per_gib_second_usd=memory_cost_per_gib_second_usd,
    )


def test_modal_sandbox_cost_estimation_is_computed(mocker) -> None:
    """Ensures estimated cost is computed when rates are configured."""
    metadata = SandboxSessionMetadata(session_id="session-1", provider="modal")
    session = _create_session(
        metadata=metadata,
        cpu_cost_per_core_second_usd=0.001,
        memory_cost_per_gib_second_usd=0.0002,
    )
    session._created_at = 100.0
    mocker.patch(
        "zenml.integrations.modal.sandboxes.modal_sandbox.time.monotonic",
        return_value=112.5,
    )

    session._finalize_metadata()

    assert metadata.duration_seconds == 12.5
    assert metadata.estimated_cost_usd == pytest.approx(0.03)

    breakdown = metadata.extra["estimated_cost_breakdown"]
    assert breakdown["duration_seconds"] == 12.5
    assert breakdown["cpu"] == 2.0
    assert breakdown["memory_mb"] == 2048
    assert breakdown["memory_gib"] == 2.0
    assert breakdown["cpu_cost_per_core_second_usd"] == 0.001
    assert breakdown["memory_cost_per_gib_second_usd"] == 0.0002
    assert breakdown["estimated_cost_usd"] == pytest.approx(0.03)


def test_modal_sandbox_cost_estimation_missing_rates(mocker) -> None:
    """Ensures estimated cost remains empty without pricing rates."""
    metadata = SandboxSessionMetadata(session_id="session-2", provider="modal")
    session = _create_session(
        metadata=metadata,
        cpu_cost_per_core_second_usd=None,
        memory_cost_per_gib_second_usd=0.0002,
    )
    session._created_at = 10.0
    mocker.patch(
        "zenml.integrations.modal.sandboxes.modal_sandbox.time.monotonic",
        return_value=11.0,
    )

    session._finalize_metadata()

    assert metadata.estimated_cost_usd is None
    assert metadata.extra["estimated_cost_reason"] == (
        "missing resource values or pricing rates"
    )
