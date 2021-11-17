#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
import pytest

from zenml.exceptions import StepInterfaceError
from zenml.steps import step
from zenml.steps.base_step_config import BaseStepConfig
from zenml.steps.step_output import Output


def test_define_step_with_shared_input_and_output_name():
    """Tests that defining a step with a shared input and output name raises
    a StepInterfaceError."""
    with pytest.raises(StepInterfaceError):

        @step
        def some_step(shared_name: int) -> Output(shared_name=int):
            return shared_name


def test_define_step_with_multiple_configs():
    """Tests that defining a step with multiple configs raises
    a StepInterfaceError."""
    with pytest.raises(StepInterfaceError):

        @step
        def some_step(
            first_config: BaseStepConfig, second_config: BaseStepConfig
        ):
            pass


def test_define_step_without_input_annotation():
    """Tests that defining a step with a missing input annotation raises
    a StepInterfaceError."""
    with pytest.raises(StepInterfaceError):

        @step
        def some_step(some_argument, some_other_argument: int):
            pass


def test_define_step_with_variable_args():
    """Tests that defining a step with variable arguments raises
    a StepInterfaceError."""
    with pytest.raises(StepInterfaceError):

        @step
        def some_step(*args: int):
            pass


def test_define_step_with_variable_kwargs():
    """Tests that defining a step with variable keyword arguments raises
    a StepInterfaceError."""
    with pytest.raises(StepInterfaceError):

        @step
        def some_step(**kwargs: int):
            pass


def test_define_step_with_keyword_only_arguments():
    """Tests that keyword-only arguments get included in the input signature
    or a step."""

    @step
    def some_step(some_argument: int, *, keyword_only_argument: int):
        pass

    assert "keyword_only_argument" in some_step.INPUT_SIGNATURE


def test_initialize_step_with_unexpected_config():
    """Tests that passing a config to a step that was defined without
    config raises an Exception."""

    @step
    def step_without_config() -> None:
        pass

    with pytest.raises(StepInterfaceError):
        step_without_config(config=BaseStepConfig())


def test_initialize_step_with_config():
    """Tests that a step can only be initialized with it's defined
    config class."""

    class StepConfig(BaseStepConfig):
        pass

    class DifferentConfig(BaseStepConfig):
        pass

    @step
    def step_with_config(config: StepConfig) -> None:
        pass

    # initialize with wrong config classes
    with pytest.raises(StepInterfaceError):
        step_with_config(config=BaseStepConfig())  # noqa

    with pytest.raises(StepInterfaceError):
        step_with_config(config=DifferentConfig())  # noqa

    # initialize with wrong key
    with pytest.raises(StepInterfaceError):
        step_with_config(wrong_config_key=StepConfig())  # noqa

    # initializing with correct key should work
    step_with_config(config=StepConfig())

    # initializing as non-kwarg should work as well
    step_with_config(StepConfig())

    # initializing with multiple args or kwargs should fail
    with pytest.raises(StepInterfaceError):
        step_with_config(StepConfig(), config=StepConfig())

    with pytest.raises(StepInterfaceError):
        step_with_config(StepConfig(), StepConfig())

    with pytest.raises(StepInterfaceError):
        step_with_config(config=StepConfig(), config2=StepConfig())


def test_access_step_component_before_calling():
    """Tests that accessing a steps component before calling it raises
    a StepInterfaceError."""

    @step
    def some_step():
        pass

    with pytest.raises(StepInterfaceError):
        _ = some_step().component


def test_access_step_component_after_calling():
    """Tests that a step component exists after the step was called."""

    @step
    def some_step():
        pass

    step_instance = some_step()
    step_instance()
    _ = step_instance.component
