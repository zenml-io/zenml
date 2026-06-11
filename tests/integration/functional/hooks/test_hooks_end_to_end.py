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
"""End-to-end tests for hooks fired from inside a running pipeline."""

from zenml import pipeline, run_hook, step
from zenml.client import Client
from zenml.enums import HookType
from zenml.hooks.recording import record_hook_invocation


def _double(value: int) -> int:
    return value * 2


@step(enable_cache=False)
def step_calling_run_hook() -> None:
    run_hook(_double, 21, store_return=True)


@step(enable_cache=False)
def step_calling_record_hook_invocation() -> None:
    record_hook_invocation(name="pre_tool_call", outputs={"result": "value"})


@pipeline(enable_cache=False)
def run_hook_pipeline() -> None:
    step_calling_run_hook()


@pipeline(enable_cache=False)
def record_hook_invocation_pipeline() -> None:
    step_calling_record_hook_invocation()


def test_run_hook_inside_step_records_invocation_with_output(
    clean_client: Client,
):
    """Tests that run_hook from a running step records a materialized output."""
    run = run_hook_pipeline()

    invocations = clean_client.list_hook_invocations(
        pipeline_run_id=run.id, hook_type=HookType.CUSTOM
    )
    assert invocations.total == 1
    invocation = invocations.items[0]
    assert invocation.name == "_double"
    assert invocation.step_run_id is not None
    assert set(invocation.outputs.keys()) == {"output"}
    assert invocation.outputs["output"][0].load() == 42


def test_record_hook_invocation_inside_step(clean_client: Client):
    """Tests that record_hook_invocation from a running step records a row."""
    run = record_hook_invocation_pipeline()

    invocations = clean_client.list_hook_invocations(
        pipeline_run_id=run.id, hook_type=HookType.CUSTOM
    )
    assert invocations.total == 1
    invocation = invocations.items[0]
    assert invocation.name == "pre_tool_call"
    assert invocation.step_run_id is not None
    assert invocation.outputs["result"][0].load() == "value"
