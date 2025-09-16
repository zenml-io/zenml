"""Tests ensuring serving mode disables step operator and retries."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from zenml.orchestrators.step_launcher import StepLauncher


def test_step_operator_disabled_in_serving(monkeypatch: pytest.MonkeyPatch):
    """Even if step config has operator, serving mode must bypass it."""
    snapshot = MagicMock()
    step = MagicMock()
    step.config.step_operator = "dummy-operator"

    launcher = StepLauncher(
        snapshot=snapshot,
        step=step,
        orchestrator_run_id="run-id",
    )

    # Minimal stack and run objects
    launcher._stack = MagicMock()
    pipeline_run = MagicMock(id="rid", name="rname")
    step_run = MagicMock(id="sid")

    # Stub utilities used inside _run_step and force serving mode active
    monkeypatch.setattr(
        "zenml.deployers.serving.runtime.is_active",
        lambda: True,
    )
    monkeypatch.setattr(
        "zenml.orchestrators.step_launcher.output_utils.prepare_output_artifact_uris",
        lambda **kwargs: {},
    )

    # Intercept the operator/non-operator paths
    called = {"with_operator": False, "without_operator": False}

    def _with_op(**kwargs: Any) -> None:
        called["with_operator"] = True

    def _without_op(**kwargs: Any) -> None:
        called["without_operator"] = True

    launcher._run_step_with_step_operator = _with_op  # type: ignore[assignment]
    launcher._run_step_without_step_operator = _without_op  # type: ignore[assignment]

    # Execute
    launcher._run_step(
        pipeline_run=pipeline_run,
        step_run=step_run,
        force_write_logs=lambda: None,
    )

    # In serving mode, operator must be bypassed
    assert called["with_operator"] is False
    assert called["without_operator"] is True
