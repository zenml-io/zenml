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
"""Tests for run_hook."""

import time

import pytest

from zenml.client import Client
from zenml.enums import ExecutionStatus, HookType
from zenml.hooks import run_hook
from zenml.steps.step_context import StepContext


def _step_context(client: Client) -> StepContext:
    """Build a step context from the run and step of a clean client."""
    run = client.list_pipeline_runs().items[0]
    step = client.list_run_steps(pipeline_run_id=run.id).items[0]
    return StepContext(
        pipeline_run=run,
        step_run=step,
        output_materializers={},
        output_artifact_uris={},
        output_artifact_configs={},
    )


def _add(a: int, b: int) -> int:
    time.sleep(0.001)
    return a + b


def _boom() -> None:
    raise ValueError("boom")


def _hooks(client: Client) -> list:
    run = client.list_pipeline_runs().items[0]
    return client.list_hook_invocations(pipeline_run_id=run.id).items


def test_run_hook_records_custom_completed(clean_client_with_run: Client):
    """Test that run_hook records a completed custom invocation."""
    client = clean_client_with_run

    with _step_context(client):
        result = run_hook(_add, 2, 3)

    assert result == 5
    hooks = _hooks(client)
    assert len(hooks) == 1
    hook = hooks[0]
    assert hook.hook_type == HookType.CUSTOM
    assert hook.status == ExecutionStatus.COMPLETED
    assert hook.name == "_add"
    assert hook.end_time > hook.start_time
    # store_return defaults to False, so no outputs are linked.
    assert hook.outputs == {}


def test_run_hook_store_return_links_output(clean_client_with_run: Client):
    """Test that store_return materializes the return value as an output."""
    client = clean_client_with_run

    with _step_context(client):
        result = run_hook(_add, 2, 3, store_return=True)

    assert result == 5
    hooks = _hooks(client)
    assert len(hooks) == 1
    assert set(hooks[0].outputs.keys()) == {"output"}
    assert hooks[0].outputs["output"][0].load() == 5


def test_run_hook_failure_records_failed_and_reraises(
    clean_client_with_run: Client,
):
    """Test that a failing hook records FAILED and re-raises."""
    client = clean_client_with_run

    with _step_context(client):
        with pytest.raises(ValueError):
            run_hook(_boom)

    hooks = _hooks(client)
    assert len(hooks) == 1
    hook = hooks[0]
    assert hook.status == ExecutionStatus.FAILED
    assert hook.exception_info is not None
    assert "boom" in (hook.exception_info.message or "")
