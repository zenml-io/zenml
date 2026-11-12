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
"""Tests for how the Kubernetes orchestrator pod handles its errors."""

import argparse
from typing import Optional
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from zenml.integrations.kubernetes.orchestrators import (
    kubernetes_orchestrator_entrypoint,
)


@pytest.mark.parametrize("run_id", [uuid4(), None])
def test_main_checks_errors_before_the_pod_gets_restarted(
    monkeypatch: pytest.MonkeyPatch, run_id: Optional[UUID]
) -> None:
    """Tests that errors reach the unrecoverable error check with the run.

    Scheduled runs don't pass a run ID to the orchestrator pod.
    """
    error = RuntimeError("Server unavailable")
    exit_check = MagicMock()
    monkeypatch.setattr(
        kubernetes_orchestrator_entrypoint,
        "parse_args",
        lambda: argparse.Namespace(
            snapshot_id=str(uuid4()),
            run_id=str(run_id) if run_id else None,
        ),
    )
    monkeypatch.setattr(
        kubernetes_orchestrator_entrypoint,
        "_run_orchestrator",
        MagicMock(side_effect=error),
    )
    monkeypatch.setattr(
        kubernetes_orchestrator_entrypoint,
        "exit_on_unrecoverable_error",
        exit_check,
    )

    with pytest.raises(RuntimeError, match="Server unavailable"):
        kubernetes_orchestrator_entrypoint.main()

    exit_check.assert_called_once_with(error, run_id=run_id)
