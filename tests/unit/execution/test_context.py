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
from unittest.mock import patch

from zenml.constants import (
    ENV_ZENML_EXECUTION_CONTEXT_STEP_RUN_CACHE_SIZE,
    ENV_ZENML_PREVENT_EXECUTION_CONTEXT_CACHING,
)
from zenml.enums import ExecutionStatus
from zenml.execution.context import (
    ExecutionContext,
    record_step_run,
    setup_execution_context,
)


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
