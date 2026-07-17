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
"""Tests for implicit dependencies on the last successful sync step."""

from typing import List

from zenml import pipeline, step


@step
def step_a() -> int:
    return 1


@step
def step_b() -> int:
    return 2


@step
def step_c() -> int:
    return 3


@step
def consume_int(value: int) -> int:
    return value


@step
def make_list() -> List[int]:
    return [1, 2]


@step
def failing_step() -> None:
    raise RuntimeError("boom")


@pipeline(dynamic=True, enable_cache=False)
def two_sync_steps_pipeline() -> None:
    step_a()
    step_b()


def test_sync_step_depends_on_previous_sync_step() -> None:
    run = two_sync_steps_pipeline()

    assert run.steps["step_a"].spec.upstream_steps == []
    assert run.steps["step_b"].spec.upstream_steps == ["step_a"]


@pipeline(dynamic=True, enable_cache=False)
def sync_submit_sync_pipeline() -> None:
    step_a()
    step_b.submit()
    step_c()


def test_submitted_step_depends_on_previous_sync_step() -> None:
    run = sync_submit_sync_pipeline()

    assert run.steps["step_b"].spec.upstream_steps == ["step_a"]
    assert run.steps["step_c"].spec.upstream_steps == ["step_a"]


@pipeline(dynamic=True, enable_cache=False)
def submit_before_sync_pipeline() -> None:
    step_b.submit()
    step_a()


def test_step_submitted_before_sync_step_gets_no_dependency() -> None:
    run = submit_before_sync_pipeline()

    assert run.steps["step_a"].spec.upstream_steps == []
    assert run.steps["step_b"].spec.upstream_steps == []


@pipeline(dynamic=True, enable_cache=False)
def sync_data_dependency_pipeline() -> None:
    value = step_a()
    consume_int(value)


def test_no_duplicate_dependency_for_sync_step_with_data_dependency() -> None:
    run = sync_data_dependency_pipeline()

    assert run.steps["consume_int"].spec.upstream_steps == ["step_a"]


@pipeline(dynamic=True, enable_cache=False)
def sync_then_map_pipeline() -> None:
    values = make_list()
    step_a()
    consume_int.map(value=values)


def test_mapped_steps_depend_on_previous_sync_step() -> None:
    run = sync_then_map_pipeline()

    for invocation_id in ["map:consume_int:0", "map:consume_int:1"]:
        assert run.steps[invocation_id].spec.upstream_steps == [
            "make_list",
            "step_a",
        ]


@pipeline(dynamic=True, enable_cache=False)
def dependent_submits_pipeline() -> None:
    step_a()
    future = step_b.submit()
    consume_int.submit(future)


def test_no_dependency_if_carried_by_existing_upstream_step() -> None:
    run = dependent_submits_pipeline()

    assert run.steps["step_b"].spec.upstream_steps == ["step_a"]
    assert run.steps["consume_int"].spec.upstream_steps == ["step_b"]


@pipeline(dynamic=True, enable_cache=False)
def upstream_submitted_before_sync_pipeline() -> None:
    future = step_b.submit()
    step_a()
    consume_int(future)


def test_dependency_if_not_carried_by_existing_upstream_step() -> None:
    run = upstream_submitted_before_sync_pipeline()

    assert run.steps["consume_int"].spec.upstream_steps == [
        "step_a",
        "step_b",
    ]


@pipeline(dynamic=True, enable_cache=False)
def sync_failure_chain_pipeline() -> None:
    try:
        failing_step()
    except RuntimeError:
        pass

    step_a()


def test_failed_sync_step_does_not_become_dependency() -> None:
    run = sync_failure_chain_pipeline()

    assert run.steps["step_a"].spec.upstream_steps == []
