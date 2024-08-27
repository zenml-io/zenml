#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
import sys
from contextlib import ExitStack as does_not_raise
from typing import Dict, List, Optional, Tuple, Union

import pytest
from pydantic import BaseModel

from zenml import pipeline, step
from zenml.exceptions import StepInterfaceError


@step
def step_with_int_input(input_: int) -> int:
    return input_


def test_input_validation_outside_of_pipeline():
    with pytest.raises(Exception):
        # Missing input
        step_with_int_input()

    with pytest.raises(Exception):
        # Wrong type
        step_with_int_input(input_="wrong_type")

    output = step_with_int_input(input_=1)
    assert output == 1
    assert isinstance(output, int)

    output = step_with_int_input(input_=3.0)
    assert output == 3
    assert isinstance(output, int)


def test_input_validation_inside_pipeline():
    @pipeline
    def test_pipeline(step_input):
        return step_with_int_input(step_input)

    with pytest.raises(ValueError):
        test_pipeline(step_input="wrong_type")

    with does_not_raise():
        test_pipeline(step_input=1)
        test_pipeline(step_input=3.0)


def test_passing_invalid_parameters():
    class UnsupportedClass:
        # This class is not supported as a parameter as it's not JSON
        # serializable
        pass

    @step
    def s(a: UnsupportedClass) -> None:
        pass

    @pipeline
    def test_pipeline():
        s(a=UnsupportedClass())

    with pytest.raises(StepInterfaceError):
        test_pipeline()


class BaseModelSubclass(BaseModel):
    pass


@step
def step_with_valid_parameter_inputs(
    a: BaseModelSubclass,
    b: int,
    c: Dict[str, float],
    d: Tuple[int, ...],
    e: List[int],
) -> None:
    pass


def test_passing_valid_parameters():
    @pipeline
    def test_pipeline():
        step_with_valid_parameter_inputs(
            a=BaseModelSubclass(), b=1, c={"key": 0.1}, d=(1, 2), e=[3, 4]
        )

    with does_not_raise():
        test_pipeline()


def test_step_parameter_from_file_and_code_fails_on_conflict():
    """Tests that parameters defined in the run config and the code
    raises, if conflict and pass if no conflict."""
    from zenml.client import Client
    from zenml.config.compiler import Compiler
    from zenml.config.pipeline_run_configuration import (
        PipelineRunConfiguration,
    )

    @pipeline
    def test_pipeline():
        step_with_int_input(input_=1)

    test_pipeline.prepare()

    # conflict 5 and 1
    run_config = PipelineRunConfiguration.model_validate(
        {"steps": {"step_with_int_input": {"parameters": {"input_": 5}}}}
    )
    with pytest.raises(
        RuntimeError,
        match="Configured parameter for the step 'step_with_int_input' conflict with parameter passed in runtime",
    ):
        deployment = Compiler().compile(
            pipeline=test_pipeline,
            stack=Client().active_stack,
            run_configuration=run_config,
        )

    # no conflict 1 and 1
    run_config = PipelineRunConfiguration.model_validate(
        {"steps": {"step_with_int_input": {"parameters": {"input_": 1}}}}
    )
    deployment = Compiler().compile(
        pipeline=test_pipeline,
        stack=Client().active_stack,
        run_configuration=run_config,
    )
    assert (
        deployment.step_configurations[
            "step_with_int_input"
        ].config.parameters["input_"]
        == 1
    )


if sys.version_info >= (3, 9):

    @step
    def step_with_non_generic_inputs(
        a: dict[str, int], b: list[float]
    ) -> set[bytes]:
        return set()


@pytest.mark.skipif(
    sys.version_info < (3, 9), reason="Only works on python>=3.9"
)
def test_step_allows_dict_list_annotations():
    """Tests that a step can use `list`, `dict` annotations instead of
    `typing.Dict`/`typing.List`"""

    @pipeline
    def test_pipeline():
        step_with_non_generic_inputs(a={"key": 1}, b=[2.1])

    with does_not_raise():
        test_pipeline()


@step
def step_with_single_output() -> int:
    return 1


def test_unpacking_step_artifact_raises_custom_exception():
    """Tests that unpacking an artifact returned by a step inside a pipeline
    raises a custom exception with explanation on how to solve the issue."""

    @pipeline
    def test_pipeline():
        a, b = step_with_single_output()

    with pytest.raises(StepInterfaceError):
        test_pipeline()



# ------------------------ Optional Input types
@step
def some_step(some_optional_int: Optional[int]) -> None:
    pass


def test_step_can_have_optional_input_types():
    """Tests that a step allows None values for optional input types"""

    @pipeline
    def p():
        some_step(some_optional_int=None)

    with does_not_raise():
        p()


def test_step_fails_on_none_inputs_for_non_optional_input_types():
    """Tests that a step does not allow None values for non-optional input types"""

    @step
    def some_step(some_optional_int: int) -> None:
        pass

    @pipeline
    def p():
        some_step(some_optional_int=None)

    with pytest.raises(TypeError):
        p().run(unlisted=True)


# --------- Test type coercion


@step
def coerce_step(some_int: int, some_float: float) -> None:
    pass


def test_step_with_type_coercion():
    """Tests that a step can coerce types when possible"""

    @pipeline
    def p():
        coerce_step(some_int="42", some_float="3.14")

    with does_not_raise():
        p()


def test_step_fails_on_invalid_type_coercion():
    """Tests that a step fails when type coercion is not possible"""

    @step
    def coerce_step(some_int: int) -> None:
        pass

    @pipeline
    def p():
        coerce_step(some_int="not an int")

    with pytest.raises(ValueError):
        p().run(unlisted=True)


# ------------- Non-Json-Serializable types


class NonSerializable:
    def __init__(self, value):
        self.value = value


@step
def non_serializable_step(some_obj: NonSerializable) -> None:
    pass


def test_step_with_non_serializable_type_as_parameter_fails():
    """Tests that a step can handle non-JSON serializable types, but fails if these are passed as parameters"""

    @pipeline
    def p():
        non_serializable_step(some_obj=NonSerializable(42))

    with pytest.raises(StepInterfaceError):
        p().run(unlisted=True)


def test_step_fails_on_wrong_non_serializable_type():
    """Tests that a step fails when given the wrong non-serializable type"""

    @step
    def non_serializable_step(some_obj: NonSerializable) -> None:
        pass

    @pipeline
    def p():
        non_serializable_step(some_obj=None)

    with pytest.raises(TypeError):
        p().run(unlisted=True)


# --------- Test union types


@step
def union_step(some_union: Union[int, str]) -> None:
    pass


def test_step_with_union_type():
    """Tests that a step can handle Union types"""

    @pipeline
    def p():
        union_step(some_union=42)

    with does_not_raise():
        p()

    @pipeline
    def p():
        union_step(some_union="fourtytwo")

    with does_not_raise():
        p()
