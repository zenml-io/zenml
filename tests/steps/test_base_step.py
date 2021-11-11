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
from zenml.steps.base_step_config import BaseStepConfig
from zenml.steps.step_decorator import step


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
