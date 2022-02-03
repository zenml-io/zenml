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
import pytest

from zenml.exceptions import StepInterfaceError
from zenml.steps import BaseStepConfig, Output, StepContext, step


def test_returning_an_object_of_the_wrong_type_raises_an_error(
        clean_repo, one_step_pipeline
):
    """Tests that returning an object of a type that wasn't specified (either
    directly or as part of the `Output` tuple annotation) raises an error."""

    @step
    def some_step_1() -> int:
        return "not_an_int"

    @step
    def some_step_2() -> Output(some_output_name=int):
        return "not_an_int"

    @step
    def some_step_3() -> Output(out1=int, out2=int):
        return 1, "not_an_int"

    for step_function in [some_step_1, some_step_2, some_step_3]:
        pipeline_ = one_step_pipeline(step_function())

        with pytest.raises(StepInterfaceError):
            pipeline_.run()


def test_returning_wrong_amount_of_objects_raises_an_error(
        clean_repo, one_step_pipeline
):
    """Tests that returning a different amount of objects than defined (either
    directly or as part of the `Output` tuple annotation) raises an error."""

    @step
    def some_step_1() -> int:
        return 1, 2

    @step
    def some_step_2() -> Output(some_output_name=int):
        return 1, 2

    @step
    def some_step_3() -> Output(out1=list):
        return 1, 2, 3

    @step
    def some_step_4() -> Output(out1=int, out2=int):
        return 1, 2, 3

    @step
    def some_step_5() -> Output(out1=int, out2=int, out3=int):
        return 1, 2

    @step
    def some_step_6() -> Output(out1=tuple, out2=tuple):
        return (1, 2), (3, 4), (5, 6)

    @step
    def some_step_7() -> Output(a=list, b=int):
        return [2, 1]

    steps = [some_step_1, some_step_2, some_step_3, some_step_4, some_step_5,
             some_step_6, some_step_7]

    for step_function in steps:
        pipeline_ = one_step_pipeline(step_function())

        with pytest.raises(StepInterfaceError):
            pipeline_.run()
