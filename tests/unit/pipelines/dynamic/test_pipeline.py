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
import os
import threading
import time
from contextlib import ExitStack as does_not_raise

import pytest

from zenml import pipeline, step
from zenml.constants import ENV_ZENML_DYNAMIC_PIPELINE_WORKER_COUNT


_DEFERRED_TEST_STATE = {}


@pipeline(dynamic=True, environment={"TEST_RUNTIME_ENV": "test_value"})
def pipeline_with_runtime_environment() -> None:
    assert os.environ["TEST_RUNTIME_ENV"] == "test_value"


def test_pipeline_runtime_environment() -> None:
    pipeline_with_runtime_environment()


@step
def step_with_none_input(a: int | None) -> None:
    pass


@pipeline(dynamic=True, enable_cache=False)
def pipeline_with_none_step_input() -> None:
    step_with_none_input(a=None)


def test_step_with_none_input_works() -> None:
    with does_not_raise():
        pipeline_with_none_step_input()


@step
def producer() -> int:
    return 1


@step
def consumer(input_: int, expected_input: int) -> None:
    assert input_ == expected_input


@pipeline(enable_cache=False, dynamic=True)
def replay_pipeline(expected_consumer_input: int) -> None:
    consumer(producer(), expected_input=expected_consumer_input)


@step
def step_with_default_parameter(value: str = "default_from_signature") -> None:
    assert value == "value_from_configuration"


@pipeline(
    enable_cache=False, dynamic=True, depends_on=[step_with_default_parameter]
)
def pipeline_with_config_template() -> None:
    step_with_default_parameter()


@step
def blocking_int_producer() -> int:
    _DEFERRED_TEST_STATE["release_upstream"].wait(timeout=2)
    return 1


@step
def blocking_list_producer() -> list[int]:
    _DEFERRED_TEST_STATE["release_upstream"].wait(timeout=2)
    return [1, 2]


@step
def increment_step(value: int) -> int:
    return value + 1


@step
def double_step(value: int) -> int:
    return value * 2


@step
def waiting_step() -> int:
    _DEFERRED_TEST_STATE["release_upstream"].wait(timeout=2)
    return 1


@step
def failing_step() -> int:
    raise ValueError("upstream failed")


@pipeline(dynamic=True, enable_cache=False)
def pending_input_submit_test_pipeline() -> None:
    upstream = blocking_int_producer.submit()

    start = time.perf_counter()
    downstream = increment_step.submit(upstream)
    _DEFERRED_TEST_STATE["submit_elapsed"] = time.perf_counter() - start

    _DEFERRED_TEST_STATE["release_upstream"].set()
    _DEFERRED_TEST_STATE["submit_result"] = downstream.load()


@pipeline(dynamic=True, enable_cache=False)
def pending_input_map_test_pipeline() -> None:
    upstream = blocking_list_producer.submit()

    start = time.perf_counter()
    mapped = double_step.map(value=upstream)
    _DEFERRED_TEST_STATE["map_elapsed"] = time.perf_counter() - start

    _DEFERRED_TEST_STATE["release_upstream"].set()
    _DEFERRED_TEST_STATE["map_length"] = len(mapped)
    _DEFERRED_TEST_STATE["map_result"] = mapped.load()


@pipeline(dynamic=True, enable_cache=False)
def invocation_id_test_pipeline() -> None:
    first = waiting_step.submit()
    second = waiting_step.submit()

    _DEFERRED_TEST_STATE["invocation_ids"] = [
        first.invocation_id,
        second.invocation_id,
    ]
    _DEFERRED_TEST_STATE["release_upstream"].set()


@pipeline(dynamic=True, enable_cache=False)
def duplicate_id_test_pipeline() -> None:
    waiting_step.submit(id="duplicate")
    with pytest.raises(RuntimeError, match="Duplicate step ID `duplicate`"):
        waiting_step.submit(id="duplicate")

    _DEFERRED_TEST_STATE["release_upstream"].set()


@pipeline(dynamic=True, enable_cache=False)
def failed_dependency_test_pipeline() -> None:
    upstream = failing_step.submit()
    downstream = increment_step.submit(upstream)
    _DEFERRED_TEST_STATE["failed_downstream_future"] = downstream


def test_step_config_template_parameters_override_step_signature_defaults() -> (
    None
):
    with does_not_raise():
        pipeline_with_config_template.with_options(
            steps={
                "step_with_default_parameter": {
                    "parameters": {"value": "value_from_configuration"}
                }
            }
        )()


def test_replay_skips_first_step_and_overrides_second_step_input() -> None:
    original_run = replay_pipeline(expected_consumer_input=1)

    replay_pipeline.replay(
        pipeline_run=original_run.id,
        input_overrides={"expected_consumer_input": 42},
        skip={"producer"},
        step_input_overrides={"consumer": {"input_": 42}},
    )


def test_submit_with_pending_input_returns_immediately() -> None:
    _DEFERRED_TEST_STATE["release_upstream"] = threading.Event()

    pending_input_submit_test_pipeline()

    assert _DEFERRED_TEST_STATE["submit_elapsed"] < 1
    assert _DEFERRED_TEST_STATE["submit_result"] == 2


def test_map_with_pending_input_returns_immediately() -> None:
    _DEFERRED_TEST_STATE["release_upstream"] = threading.Event()

    pending_input_map_test_pipeline()

    assert _DEFERRED_TEST_STATE["map_elapsed"] < 1
    assert _DEFERRED_TEST_STATE["map_length"] == 2
    assert _DEFERRED_TEST_STATE["map_result"] == [2, 4]


def test_submit_reserves_invocation_ids_immediately() -> None:
    _DEFERRED_TEST_STATE["release_upstream"] = threading.Event()

    invocation_id_test_pipeline()

    assert _DEFERRED_TEST_STATE["invocation_ids"] == [
        "waiting_step",
        "waiting_step_2",
    ]


def test_submit_duplicate_explicit_id_fails_immediately() -> None:
    _DEFERRED_TEST_STATE["release_upstream"] = threading.Event()

    duplicate_id_test_pipeline()


def test_downstream_future_raises_original_upstream_exception() -> None:
    with pytest.raises(ValueError, match="upstream failed"):
        failed_dependency_test_pipeline()

    with pytest.raises(ValueError, match="upstream failed"):
        _DEFERRED_TEST_STATE["failed_downstream_future"].load()


def test_submit_with_single_worker_does_not_deadlock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ENV_ZENML_DYNAMIC_PIPELINE_WORKER_COUNT, "1")
    _DEFERRED_TEST_STATE["release_upstream"] = threading.Event()

    pending_input_submit_test_pipeline()

    assert _DEFERRED_TEST_STATE["submit_result"] == 2
