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
"""Tests for the execution context."""

import os
from contextlib import nullcontext
from unittest.mock import MagicMock, patch
from uuid import uuid4

from zenml.constants import (
    ENV_ZENML_EXECUTION_CONTEXT_STEP_RUN_CACHE_SIZE,
    ENV_ZENML_PREVENT_EXECUTION_CONTEXT_CACHING,
)
from zenml.enums import ExecutionStatus
from zenml.execution.context import (
    ActiveRunContext,
    ExecutionContext,
    get_active_run_context,
    record_step_run,
    setup_execution_context,
)
from zenml.execution.pipeline.dynamic.run_context import (
    DynamicPipelineRunContext,
)
from zenml.steps.step_context import StepContext


def test_setup_can_be_disabled_via_environment_variable():
    """Tests that the environment variable disables the execution context."""
    assert isinstance(setup_execution_context(), ExecutionContext)

    with patch.dict(
        os.environ, {ENV_ZENML_PREVENT_EXECUTION_CONTEXT_CACHING: "True"}
    ):
        assert isinstance(setup_execution_context(), nullcontext)


def test_recording_only_stores_successful_step_runs(create_step_run):
    """Tests that only successful step runs are recorded."""
    with ExecutionContext() as context:
        completed_step_run = create_step_run(step_run_name="completed")
        record_step_run(completed_step_run)

        running_step_run = create_step_run(step_run_name="running")
        running_step_run.get_body().status = ExecutionStatus.RUNNING
        record_step_run(running_step_run)

        assert context.step_runs == {"completed": completed_step_run}


def test_step_run_eviction(create_step_run):
    """Tests that the oldest step runs are evicted beyond the cache size."""
    with patch.dict(
        os.environ, {ENV_ZENML_EXECUTION_CONTEXT_STEP_RUN_CACHE_SIZE: "2"}
    ):
        context = ExecutionContext()

    for name in ["step_1", "step_2", "step_3"]:
        context.step_runs[name] = create_step_run(step_run_name=name)

    assert list(context.step_runs) == ["step_2", "step_3"]

    context.step_runs.update(
        {
            "step_4": create_step_run(step_run_name="step_4"),
            "step_5": create_step_run(step_run_name="step_5"),
        }
    )

    assert list(context.step_runs) == ["step_4", "step_5"]


def test_active_run_context_prefers_step_over_dynamic_run():
    """Tests that the step context wins when both contexts are active."""
    step_context = MagicMock(step_name="trainer")
    run_context = MagicMock()

    with (
        patch.object(StepContext, "get", return_value=step_context),
        patch.object(
            DynamicPipelineRunContext, "get", return_value=run_context
        ),
    ):
        assert get_active_run_context() == ActiveRunContext(
            pipeline_run_id=step_context.pipeline_run.id,
            step_run_id=step_context.step_run.id,
            step_name="trainer",
        )


def test_active_run_context_falls_back_to_dynamic_run():
    """Tests the fallback to the dynamic pipeline run outside of a step."""
    run_context = MagicMock()
    run_context.run.id = uuid4()

    with (
        patch.object(StepContext, "get", return_value=None),
        patch.object(
            DynamicPipelineRunContext, "get", return_value=run_context
        ),
    ):
        assert get_active_run_context() == ActiveRunContext(
            pipeline_run_id=run_context.run.id,
            step_run_id=None,
            step_name=None,
        )


def test_active_run_context_is_none_without_any_context():
    """Tests that no active context resolves to None."""
    assert get_active_run_context() is None
