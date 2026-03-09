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
from contextlib import ExitStack as does_not_raise

from zenml import pipeline, step


@pipeline(dynamic=True, environment={"TEST_RUNTIME_ENV": "test_value"})
def pipeline_with_runtime_environment() -> None:
    assert os.environ["TEST_RUNTIME_ENV"] == "test_value"


def test_pipeline_runtime_environment() -> None:
    """Tests that the runtime env is set correctly inside the pipeline function."""
    pipeline_with_runtime_environment()


@step
def step_with_none_input(a: int | None) -> None:
    pass


@pipeline(dynamic=True, enable_cache=False)
def pipeline_with_none_step_input() -> None:
    step_with_none_input(a=None)


def test_step_with_none_input_works() -> None:
    """Tests that a step with a None input works."""
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


def test_replay_skips_first_step_and_overwrites_second_step_input():
    """Tests that replaying a pipeline and overwriting step inputs works."""
    original_run = replay_pipeline(expected_consumer_input=1)

    replay_pipeline.replay(
        pipeline_run=original_run.id,
        input_overrides={"expected_consumer_input": 42},
        skip={"producer"},
        step_input_overrides={"consumer": {"input_": 42}},
    )
