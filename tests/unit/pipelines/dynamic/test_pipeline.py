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
from typing import Tuple

from typing_extensions import Annotated

from zenml import ArtifactConfig, pipeline, step


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


@step
def step_with_default_parameter(value: str = "default_from_signature") -> None:
    assert value == "value_from_configuration"


@pipeline(
    enable_cache=False, dynamic=True, depends_on=[step_with_default_parameter]
)
def pipeline_with_config_template() -> None:
    step_with_default_parameter()


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


@step(substitutions={"artifact_suffix": "substituted"})
def multi_output_producer_with_substituted_artifact_name() -> Tuple[
    Annotated[int, ArtifactConfig(name="static_output")],
    Annotated[int, ArtifactConfig(name="dynamic_output_{artifact_suffix}")],
]:
    return 1, 2


@pipeline(enable_cache=False, dynamic=True)
def pipeline_with_substituted_output_as_step_input() -> None:
    _, dynamic_output = multi_output_producer_with_substituted_artifact_name()
    consumer(input_=dynamic_output, expected_input=2)


def test_substituted_output_artifact_can_be_used_as_step_input() -> None:
    """Tests that substituted output artifacts can be used as step inputs."""
    with does_not_raise():
        pipeline_with_substituted_output_as_step_input()


@step
def list_consumer(input_: list[int]) -> None:
    assert input_ == [1]


@pipeline(enable_cache=False, dynamic=True)
def pipeline_with_single_artifact_list_input() -> None:
    list_consumer([producer()])


def test_step_with_single_artifact_list_input_works() -> None:
    """Tests that a single artifact wrapped in a list stays a list."""
    with does_not_raise():
        pipeline_with_single_artifact_list_input()


@step
def bare_list_consumer(input_: list) -> None:
    assert input_ == [1, 1]


@pipeline(enable_cache=False, dynamic=True)
def pipeline_with_bare_list_input() -> None:
    bare_list_consumer([producer(), producer()])


def test_step_with_bare_list_input_annotation_works() -> None:
    """Tests that a step input annotated with bare `list` works."""
    with does_not_raise():
        pipeline_with_bare_list_input()


def test_replay_skips_first_step_and_overrides_second_step_input():
    """Tests that replaying a pipeline and overriding step inputs works."""
    original_run = replay_pipeline(expected_consumer_input=1)

    replay_pipeline.replay(
        pipeline_run=original_run.id,
        input_overrides={"expected_consumer_input": 42},
        skip={"producer"},
        step_input_overrides={"consumer": {"input_": 42}},
    )


def pipeline_function_definition() -> None:
    producer()


def test_pipeline_run_with_nested_pipeline_definition() -> None:
    """Tests that a dynamic pipeline run succeeds when the pipeline is defined
    inside a function rather than at module top level."""
    nested_pipeline = pipeline(dynamic=True, enable_cache=False)(
        pipeline_function_definition
    )
    with does_not_raise():
        nested_pipeline()
