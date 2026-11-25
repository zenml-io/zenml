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
"""Tests for record_hook_invocation."""

import pytest

from zenml.client import Client
from zenml.enums import ExecutionStatus, HookType
from zenml.hooks.recording import record_hook_invocation
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


def test_record_hook_invocation_records_a_row(clean_client_with_run: Client):
    """Test that a direct call records a fully-formed hook invocation."""
    client = clean_client_with_run
    context = _step_context(client)

    with context:
        response = record_hook_invocation(
            name="pre_tool_call",
            outputs={"result": "value"},
        )

    assert response.hook_type == HookType.CUSTOM
    assert response.name == "pre_tool_call"
    assert response.status == ExecutionStatus.COMPLETED
    assert response.pipeline_run_id == context.pipeline_run.id
    assert response.step_run_id == context.step_run.id
    assert response.start_time is not None
    assert response.end_time is not None
    assert "result" in response.outputs
    assert response.outputs["result"][0].load() == "value"


def test_record_hook_invocation_without_context_raises(clean_client: Client):
    """Test that recording outside a run context raises."""
    with pytest.raises(RuntimeError):
        record_hook_invocation(name="pre_tool_call")
