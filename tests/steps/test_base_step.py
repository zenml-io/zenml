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
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.materializers.built_in_materializer import BuiltInMaterializer
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


def test_configure_step_with_wrong_materializer_class():
    """Tests that passing a random class as a materializer raises a
    StepInterfaceError."""

    @step
    def some_step() -> Output(some_output=int):
        pass

    with pytest.raises(StepInterfaceError):
        some_step().with_return_materializers(str)  # noqa


def test_configure_step_with_wrong_materializer_key():
    """Tests that passing a materializer for a non-existent argument raises a
    StepInterfaceError."""

    @step
    def some_step() -> Output(some_output=int):
        pass

    with pytest.raises(StepInterfaceError):
        materializers = {"some_nonexistent_output": BaseMaterializer}
        some_step().with_return_materializers(materializers)


def test_configure_step_with_wrong_materializer_class_in_dict():
    """Tests that passing a wrong class as materializer for a specific output
    raises a StepInterfaceError."""

    @step
    def some_step() -> Output(some_output=int):
        pass

    with pytest.raises(StepInterfaceError):
        materializers = {"some_output": "not_a_materializer_class"}
        some_step().with_return_materializers(materializers)  # noqa


def test_setting_a_materializer_for_a_step_with_multiple_outputs():
    """Tests that setting a materializer for a step with multiple outputs
    sets the materializer for all the outputs."""

    @step
    def some_step() -> Output(some_output=int, some_other_output=str):
        pass

    step_instance = some_step().with_return_materializers(BaseMaterializer)
    assert step_instance.materializers["some_output"] is BaseMaterializer
    assert step_instance.materializers["some_other_output"] is BaseMaterializer


def test_overwriting_step_materializers():
    """Tests that calling `with_return_materializers` multiple times allows
    overwriting of the step materializers."""

    @step
    def some_step() -> Output(some_output=int, some_other_output=str):
        pass

    step_instance = some_step()
    assert not step_instance.materializers

    step_instance = step_instance.with_return_materializers(
        {"some_output": BaseMaterializer}
    )
    assert step_instance.materializers["some_output"] is BaseMaterializer
    assert "some_other_output" not in step_instance.materializers

    step_instance = step_instance.with_return_materializers(
        {"some_other_output": BuiltInMaterializer}
    )
    assert (
        step_instance.materializers["some_other_output"] is BuiltInMaterializer
    )
    assert step_instance.materializers["some_output"] is BaseMaterializer

    step_instance = step_instance.with_return_materializers(
        {"some_output": BuiltInMaterializer}
    )
    assert step_instance.materializers["some_output"] is BuiltInMaterializer

    step_instance.with_return_materializers(BaseMaterializer)
    assert step_instance.materializers["some_output"] is BaseMaterializer
    assert step_instance.materializers["some_other_output"] is BaseMaterializer


def test_step_with_disabled_cache_has_random_string_as_execution_property():
    """Tests that a step with disabled caching adds a random string as
    execution property to disable caching."""

    @step(enable_cache=False)
    def some_step():
        pass

    step_instance_1 = some_step()
    step_instance_2 = some_step()

    assert (
        step_instance_1._internal_execution_properties["zenml-disable_cache"]
        != step_instance_2._internal_execution_properties["zenml-disable_cache"]
    )


def test_step_source_execution_property_stays_the_same_if_step_is_not_modified():
    """Tests that the step source execution property remains constant when
    creating multiple steps from the same source code."""

    @step
    def some_step():
        pass

    step_1 = some_step()
    step_2 = some_step()

    assert (
        step_1._internal_execution_properties["zenml-step_source"]
        == step_2._internal_execution_properties["zenml-step_source"]
    )


def test_step_source_execution_property_changes_when_signature_changes():
    """Tests that modifying the input arguments or outputs of a step
    function changes the step source execution property."""

    @step
    def some_step(some_argument: int) -> int:
        pass

    step_1 = some_step()

    @step
    def some_step(some_argument_with_new_name: int) -> int:
        pass

    step_2 = some_step()

    assert (
        step_1._internal_execution_properties["zenml-step_source"]
        != step_2._internal_execution_properties["zenml-step_source"]
    )

    @step
    def some_step(some_argument: int) -> str:
        pass

    step_3 = some_step()

    assert (
        step_1._internal_execution_properties["zenml-step_source"]
        != step_3._internal_execution_properties["zenml-step_source"]
    )


def test_step_source_execution_property_changes_when_function_body_changes():
    """Tests that modifying the step function code changes the step
    source execution property."""

    @step
    def some_step():
        pass

    step_1 = some_step()

    @step
    def some_step():
        # this is new
        pass

    step_2 = some_step()

    assert (
        step_1._internal_execution_properties["zenml-step_source"]
        != step_2._internal_execution_properties["zenml-step_source"]
    )
