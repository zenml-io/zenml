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
"""Unit tests for async step entrypoints."""

import asyncio

from zenml import pipeline, step


@step
async def async_add_one(x: int) -> int:
    await asyncio.sleep(0.01)
    return x + 1


@step
def sync_add_one(x: int) -> int:
    return x + 1


@step
def assert_equals(value: int, expected: int) -> None:
    assert value == expected, f"{value} != {expected}"


@pipeline(enable_cache=False)
def static_pipeline_with_async_step() -> None:
    result = async_add_one(41)
    assert_equals(result, 42)


def test_async_step_runs_in_static_pipeline() -> None:
    """An async step inside a static pipeline runs and materializes output."""
    run = static_pipeline_with_async_step()
    assert run.status.is_successful
    output = run.steps["async_add_one"].output.load()
    assert output == 42


@pipeline(enable_cache=False)
def static_pipeline_with_mixed_steps() -> None:
    sync_result = sync_add_one(10)
    async_result = async_add_one(sync_result)
    assert_equals(async_result, 12)


def test_async_and_sync_steps_run_together() -> None:
    """A static pipeline mixing a sync and an async step both succeed."""
    run = static_pipeline_with_mixed_steps()
    assert run.status.is_successful
    assert run.steps["sync_add_one"].output.load() == 11
    assert run.steps["async_add_one"].output.load() == 12


def test_async_step_called_directly() -> None:
    """Calling an async step with no active pipeline returns the right value."""
    result = async_add_one(5)
    assert result == 6
