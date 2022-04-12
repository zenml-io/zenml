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
from contextlib import ExitStack as does_not_raise
from typing import Dict, List, Optional

import pytest
from tfx.orchestration.portable.python_executor_operator import (
    PythonExecutorOperator,
)

from zenml.artifacts import DataArtifact, ModelArtifact
from zenml.environment import Environment
from zenml.exceptions import MissingStepParameterError, StepInterfaceError
from zenml.materializers import BuiltInMaterializer
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.pipelines import pipeline
from zenml.step_operators.step_executor_operator import StepExecutorOperator
from zenml.steps import BaseStepConfig, Output, StepContext, step


def test_step_decorator_creates_class_in_same_module_as_decorated_function():
    """Tests that the `BaseStep` subclass created by our step decorator
    creates the class in the same module as the decorated function."""

    @step
    def some_step():
        pass

    assert some_step.__module__ == __name__


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


def test_define_step_with_multiple_contexts():
    """Tests that defining a step with multiple contexts raises
    a StepInterfaceError."""
    with pytest.raises(StepInterfaceError):

        @step
        def some_step(first_context: StepContext, second_context: StepContext):
            pass


def test_step_without_context_has_caching_enabled_by_default():
    """Tests that defining a step without a context enables caching by
    default."""

    @step
    def some_step():
        pass

    assert some_step().enable_cache is True


def test_step_with_context_has_caching_disabled_by_default():
    """Tests that defining a step with a context disables caching by
    default."""

    @step
    def some_step(context: StepContext):
        pass

    assert some_step().enable_cache is False


def test_enable_caching_for_step_with_context():
    """Tests that caching can be explicitly enabled for a step with a
    context."""

    @step(enable_cache=True)
    def some_step(context: StepContext):
        pass

    assert some_step().enable_cache is True


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
    with does_not_raise():
        step_with_config(config=StepConfig())

    # initializing as non-kwarg should work as well
    with does_not_raise():
        step_with_config(StepConfig())

    # initializing with multiple args or kwargs should fail
    with pytest.raises(StepInterfaceError):
        step_with_config(StepConfig(), config=StepConfig())

    with pytest.raises(StepInterfaceError):
        step_with_config(StepConfig(), StepConfig())

    with pytest.raises(StepInterfaceError):
        step_with_config(config=StepConfig(), config2=StepConfig())


def test_only_registered_output_artifact_types_are_allowed():
    """Tests that only artifact types which are registered for the output type
    are allowed as custom output artifact types."""

    class CustomType:
        pass

    class CustomTypeMaterializer(BaseMaterializer):
        ASSOCIATED_TYPES = (CustomType,)
        ASSOCIATED_ARTIFACT_TYPES = (DataArtifact,)

    @step(output_types={"output": DataArtifact})
    def some_step() -> CustomType:
        pass

    with does_not_raise():
        some_step()

    @step(output_types={"output": ModelArtifact})
    def some_other_step() -> CustomType:
        pass

    with pytest.raises(StepInterfaceError):
        some_other_step()


def test_pass_invalid_type_as_output_artifact_type():
    """Tests that passing a type that is not a `BaseArtifact` subclass as
    output artifact type fails.
    """

    @step(output_types={"output": int})
    def some_step() -> int:
        pass

    with pytest.raises(StepInterfaceError):
        some_step()


def test_unrecognized_output_in_output_artifact_types():
    """Tests that passing an output artifact type for an output that doesn't
    exist raises an exception."""

    @step(output_types={"non-existent": DataArtifact})
    def some_step():
        pass

    with pytest.raises(StepInterfaceError):
        some_step()


def test_enabling_a_custom_step_operator_for_a_step():
    """Tests that step operators are disabled by default and can be enabled
    using the step decorator."""

    @step
    def step_without_step_operator():
        pass

    @step(custom_step_operator="some_step_operator")
    def step_with_step_operator():
        pass

    assert step_without_step_operator().custom_step_operator is None
    assert (
        step_with_step_operator().custom_step_operator == "some_step_operator"
    )


def test_step_executor_operator():
    """Tests that the step returns the correct executor operator."""

    @step(custom_step_operator=None)
    def step_without_step_operator():
        pass

    @step(custom_step_operator="some_step_operator")
    def step_with_step_operator():
        pass

    assert (
        step_without_step_operator().executor_operator is PythonExecutorOperator
    )
    assert step_with_step_operator().executor_operator is StepExecutorOperator


def test_pipeline_parameter_name_is_empty_when_initializing_a_step():
    """Tests that the `pipeline_parameter_name` attribute is `None` when
    a step is initialized."""

    @step
    def some_step():
        pass

    assert some_step().pipeline_parameter_name is None


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

    with does_not_raise():
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

    materializers = {"some_output": "not_a_materializer_class"}
    with pytest.raises(StepInterfaceError):
        some_step().with_return_materializers(materializers)  # noqa


def test_setting_a_materializer_for_a_step_with_multiple_outputs():
    """Tests that setting a materializer for a step with multiple outputs
    sets the materializer for all the outputs."""

    @step
    def some_step() -> Output(some_output=int, some_other_output=str):
        pass

    step_instance = some_step().with_return_materializers(BaseMaterializer)
    assert step_instance.get_materializers()["some_output"] is BaseMaterializer
    assert (
        step_instance.get_materializers()["some_other_output"]
        is BaseMaterializer
    )


def test_overwriting_step_materializers():
    """Tests that calling `with_return_materializers` multiple times allows
    overwriting of the step materializers."""

    @step
    def some_step() -> Output(some_output=int, some_other_output=str):
        pass

    step_instance = some_step()
    assert not step_instance._explicit_materializers

    step_instance = step_instance.with_return_materializers(
        {"some_output": BaseMaterializer}
    )
    assert (
        step_instance._explicit_materializers["some_output"] is BaseMaterializer
    )
    assert "some_other_output" not in step_instance._explicit_materializers

    step_instance = step_instance.with_return_materializers(
        {"some_other_output": BuiltInMaterializer}
    )
    assert (
        step_instance._explicit_materializers["some_other_output"]
        is BuiltInMaterializer
    )
    assert (
        step_instance._explicit_materializers["some_output"] is BaseMaterializer
    )

    step_instance = step_instance.with_return_materializers(
        {"some_output": BuiltInMaterializer}
    )
    assert (
        step_instance._explicit_materializers["some_output"]
        is BuiltInMaterializer
    )

    step_instance.with_return_materializers(BaseMaterializer)
    assert (
        step_instance._explicit_materializers["some_output"] is BaseMaterializer
    )
    assert (
        step_instance._explicit_materializers["some_other_output"]
        is BaseMaterializer
    )


def test_step_with_disabled_cache_has_random_string_as_execution_property():
    """Tests that a step with disabled caching adds a random string as
    execution property to disable caching."""

    @step(enable_cache=False)
    def some_step():
        pass

    step_instance_1 = some_step()
    step_instance_2 = some_step()

    assert (
        step_instance_1._internal_execution_parameters["zenml-disable_cache"]
        != step_instance_2._internal_execution_parameters["zenml-disable_cache"]
    )


def test_step_source_execution_parameter_stays_the_same_if_step_is_not_modified():
    """Tests that the step source execution parameter remains constant when
    creating multiple steps from the same source code."""

    @step
    def some_step():
        pass

    step_1 = some_step()
    step_2 = some_step()

    assert (
        step_1._internal_execution_parameters["zenml-step_source"]
        == step_2._internal_execution_parameters["zenml-step_source"]
    )


def test_step_source_execution_parameter_changes_when_signature_changes():
    """Tests that modifying the input arguments or outputs of a step
    function changes the step source execution parameter."""

    @step
    def some_step(some_argument: int) -> int:
        pass

    step_1 = some_step()

    @step
    def some_step(some_argument_with_new_name: int) -> int:
        pass

    step_2 = some_step()

    assert (
        step_1._internal_execution_parameters["zenml-step_source"]
        != step_2._internal_execution_parameters["zenml-step_source"]
    )

    @step
    def some_step(some_argument: int) -> str:
        pass

    step_3 = some_step()

    assert (
        step_1._internal_execution_parameters["zenml-step_source"]
        != step_3._internal_execution_parameters["zenml-step_source"]
    )


def test_step_source_execution_parameter_changes_when_function_body_changes():
    """Tests that modifying the step function code changes the step
    source execution parameter."""

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
        step_1._internal_execution_parameters["zenml-step_source"]
        != step_2._internal_execution_parameters["zenml-step_source"]
    )


def test_materializer_source_execution_parameter_changes_when_materializer_changes():
    """Tests that changing the step materializer changes the materializer
    source execution parameter."""

    @step
    def some_step() -> int:
        return 1

    class MyCustomMaterializer(BuiltInMaterializer):
        pass

    step_1 = some_step().with_return_materializers(BuiltInMaterializer)
    step_2 = some_step().with_return_materializers(MyCustomMaterializer)

    key = "zenml-output_materializer_source"
    assert (
        step_1._internal_execution_parameters[key]
        != step_2._internal_execution_parameters[key]
    )


def test_call_step_with_args(int_step_output, step_with_two_int_inputs):
    """Test that a step can be called with args."""
    with does_not_raise():
        step_with_two_int_inputs()(int_step_output, int_step_output)


def test_call_step_with_kwargs(int_step_output, step_with_two_int_inputs):
    """Test that a step can be called with kwargs."""
    with does_not_raise():
        step_with_two_int_inputs()(
            input_1=int_step_output, input_2=int_step_output
        )


def test_call_step_with_args_and_kwargs(
    int_step_output, step_with_two_int_inputs
):
    """Test that a step can be called with a mix of args and kwargs."""
    with does_not_raise():
        step_with_two_int_inputs()(int_step_output, input_2=int_step_output)


def test_call_step_with_too_many_args(
    int_step_output, step_with_two_int_inputs
):
    """Test that calling a step fails when too many args
    are passed."""
    with pytest.raises(StepInterfaceError):
        step_with_two_int_inputs()(
            int_step_output, int_step_output, int_step_output
        )


def test_call_step_with_too_many_args_and_kwargs(
    int_step_output, step_with_two_int_inputs
):
    """Test that calling a step fails when too many args
    and kwargs are passed."""
    with pytest.raises(StepInterfaceError):
        step_with_two_int_inputs()(
            int_step_output, input_1=int_step_output, input_2=int_step_output
        )


def test_call_step_with_missing_key(int_step_output, step_with_two_int_inputs):
    """Test that calling a step fails when an argument
    is missing."""
    with pytest.raises(StepInterfaceError):
        step_with_two_int_inputs()(input_1=int_step_output)


def test_call_step_with_unexpected_key(
    int_step_output, step_with_two_int_inputs
):
    """Test that calling a step fails when an argument
    has an unexpected key."""
    with pytest.raises(StepInterfaceError):
        step_with_two_int_inputs()(
            input_1=int_step_output,
            input_2=int_step_output,
            input_3=int_step_output,
        )


def test_call_step_with_wrong_arg_type(
    int_step_output, step_with_two_int_inputs
):
    """Test that calling a step fails when an arg has a wrong type."""
    with pytest.raises(StepInterfaceError):
        step_with_two_int_inputs()(1, int_step_output)


def test_call_step_with_wrong_kwarg_type(
    int_step_output, step_with_two_int_inputs
):
    """Test that calling a step fails when a kwarg has a wrong type."""
    with pytest.raises(StepInterfaceError):
        step_with_two_int_inputs()(input_1=1, input_2=int_step_output)


def test_call_step_with_missing_materializer_for_type():
    """Tests that calling a step with an output without registered
    materializer raises a StepInterfaceError."""

    class MyTypeWithoutMaterializer:
        pass

    @step
    def some_step() -> MyTypeWithoutMaterializer:
        return MyTypeWithoutMaterializer()

    with pytest.raises(StepInterfaceError):
        some_step()()


def test_call_step_with_default_materializer_registered():
    """Tests that calling a step with a registered default materializer for the
    output works."""

    class MyType:
        pass

    class MyTypeMaterializer(BaseMaterializer):
        ASSOCIATED_TYPES = (MyType,)

    @step
    def some_step() -> MyType:
        return MyType()

    with does_not_raise():
        some_step()()


def test_step_uses_config_class_default_values_if_no_config_is_passed():
    """Tests that a step falls back to the config class default values if
    no config object is passed at initialization."""

    class ConfigWithDefaultValues(BaseStepConfig):
        some_parameter: int = 1

    @step
    def some_step(config: ConfigWithDefaultValues):
        pass

    # don't pass the config when initializing the step
    step_instance = some_step()
    step_instance._update_and_verify_parameter_spec()

    assert step_instance.PARAM_SPEC["some_parameter"] == 1


def test_step_fails_if_config_parameter_value_is_missing():
    """Tests that a step fails if no config object is passed at
    initialization and the config class misses some default values."""

    class ConfigWithoutDefaultValues(BaseStepConfig):
        some_parameter: int

    @step
    def some_step(config: ConfigWithoutDefaultValues):
        pass

    # don't pass the config when initializing the step
    step_instance = some_step()

    with pytest.raises(MissingStepParameterError):
        step_instance._update_and_verify_parameter_spec()


def test_step_config_allows_none_as_default_value():
    """Tests that `None` is allowed as a default value for a
    step config field."""

    class ConfigWithNoneDefaultValue(BaseStepConfig):
        some_parameter: Optional[int] = None

    @step
    def some_step(config: ConfigWithNoneDefaultValue):
        pass

    # don't pass the config when initializing the step
    step_instance = some_step()

    with does_not_raise():
        step_instance._update_and_verify_parameter_spec()


def test_calling_a_step_twice_raises_an_exception():
    """Tests that calling once step instance twice raises an exception."""

    @step
    def my_step():
        pass

    step_instance = my_step()

    # calling once works
    step_instance()

    with pytest.raises(StepInterfaceError):
        step_instance()


def test_step_sets_global_execution_status_on_environment(one_step_pipeline):
    """Tests that the `Environment.step_is_running` value is set to
    True during step execution."""

    @step
    def my_step():
        assert Environment().step_is_running is True

    assert Environment().step_is_running is False
    one_step_pipeline(my_step()).run()
    assert Environment().step_is_running is False


def test_step_resets_global_execution_status_even_if_the_step_crashes(
    one_step_pipeline,
):
    """Tests that the `Environment.step_is_running` value is set to
    False after step execution even if the step crashes."""

    @step
    def my_step():
        raise RuntimeError()

    assert Environment().step_is_running is False
    with pytest.raises(RuntimeError):
        one_step_pipeline(my_step()).run()
    assert Environment().step_is_running is False


def test_returning_an_object_of_the_wrong_type_raises_an_error(
    one_step_pipeline,
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


def test_returning_wrong_amount_of_objects_raises_an_error(one_step_pipeline):
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

    steps = [
        some_step_1,
        some_step_2,
        some_step_3,
        some_step_4,
        some_step_5,
        some_step_6,
        some_step_7,
    ]

    for step_function in steps:
        pipeline_ = one_step_pipeline(step_function())

        with pytest.raises(StepInterfaceError):
            pipeline_.run()


def test_step_can_output_generic_types(one_step_pipeline):
    """Tests that a step can output generic typing classes."""

    @step
    def some_step_1() -> Dict:
        return {}

    @step
    def some_step_2() -> List:
        return []

    for step_function in [some_step_1, some_step_2]:
        pipeline_ = one_step_pipeline(step_function())

        with does_not_raise():
            pipeline_.run()


def test_step_can_have_generic_input_types():
    """Tests that a step can have generic typing classes as input."""

    @step
    def step_1() -> Output(dict_output=Dict, list_output=List):
        return {}, []

    @step
    def step_2(dict_input: Dict, list_input: List) -> None:
        pass

    @pipeline
    def p(s1, s2):
        s2(*s1())

    with does_not_raise():
        p(step_1(), step_2()).run()


def test_step_can_have_raw_artifacts(clean_repo):
    """Check that you can bypass materialization with raw artifacts."""

    @step
    def step_1() -> Output(dict_=Dict, list_=List):
        return {"some": "data"}, []

    @step
    def step_2() -> Output(dict_=Dict, list_=List):
        return {"some": "data"}, []

    @step
    def step_3(dict_: DataArtifact, list_: ModelArtifact) -> None:
        assert hasattr(dict_, "uri")
        assert hasattr(list_, "uri")

    @step
    def step_4(dict_: Dict, list_: List) -> None:
        assert type(dict_) is dict
        assert type(list_) is list

    @pipeline
    def p(s1, s2, s3, s4):
        s3(*s1())
        s4(*s2())

    with does_not_raise():
        p(step_1(), step_2(), step_3(), step_4()).run()
