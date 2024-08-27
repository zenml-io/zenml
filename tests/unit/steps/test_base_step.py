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
from pydantic import BaseModel

from zenml.environment import Environment
from zenml.exceptions import MissingStepParameterError, StepInterfaceError
from zenml.materializers import BuiltInMaterializer
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.models import ArtifactVersionResponse
from zenml.pipelines import pipeline
from zenml.steps import BaseParameters, Output, StepContext, step


def test_step_decorator_creates_class_in_same_module_as_decorated_function():
    """Tests that the `BaseStep` subclass created by our step decorator creates the class in the same module as the decorated function."""

    @step
    def some_step() -> None:
        pass

    assert some_step.__module__ == __name__


def test_define_step_with_shared_input_and_output_name():
    """Tests that defining a step with a shared input and output name does not raise a StepInterfaceError."""
    with does_not_raise():

        @step
        def some_step(shared_name: int) -> Output(shared_name=int):
            return shared_name


def test_define_step_with_multiple_parameter_classes():
    """Tests that defining a step with multiple parameter classes raises a StepInterfaceError."""
    with pytest.raises(StepInterfaceError):

        @step
        def some_step(
            first_params: BaseParameters, second_params: BaseParameters
        ) -> None:
            pass


def test_define_step_with_multiple_contexts():
    """Tests that defining a step with multiple contexts raises a StepInterfaceError."""
    with pytest.raises(StepInterfaceError):

        @step
        def some_step(
            first_context: StepContext, second_context: StepContext
        ) -> None:
            pass


def test_step_has_no_enable_cache_by_default():
    """Tests that a step has `enable_cache=None` by default."""

    @step
    def some_step() -> None:
        pass

    assert some_step().enable_cache is None


def test_enable_caching_for_step():
    """Tests that caching can be explicitly enabled for a step."""

    @step(enable_cache=True)
    def some_step() -> None:
        pass

    assert some_step().enable_cache is True


def test_disable_caching_for_step():
    """Tests that caching can be explicitly disabled for a step."""

    @step(enable_cache=False)
    def some_step() -> None:
        pass

    assert some_step().enable_cache is False


def test_step_with_context_has_caching_disabled_by_default():
    """Tests that defining a step with a context disables caching by default."""

    @step
    def some_step(context: StepContext) -> None:
        pass

    assert some_step().enable_cache is False


def test_enable_caching_for_step_with_context():
    """Tests that caching can be explicitly enabled for a step with a context."""

    @step(enable_cache=True)
    def some_step(context: StepContext) -> None:
        pass

    assert some_step().enable_cache is True


def test_define_step_without_input_annotation():
    """Tests that defining a step with a missing input annotation raises a StepInterfaceError."""
    with does_not_raise():

        @step
        def some_step(some_argument, some_other_argument: int) -> None:
            pass


def test_define_step_without_return_annotation():
    """Tests that defining a step with a missing return annotation does not
    raise a StepInterfaceError."""
    with does_not_raise():

        @step
        def some_step(some_argument: int, some_other_argument: int):
            pass


def test_define_step_with_variable_args():
    """Tests that defining a step with variable arguments raises a StepInterfaceError."""
    with pytest.raises(StepInterfaceError):

        @step
        def some_step(*args: int) -> None:
            pass


def test_define_step_with_variable_kwargs():
    """Tests that defining a step with variable keyword arguments raises a StepInterfaceError."""
    with pytest.raises(StepInterfaceError):

        @step
        def some_step(**kwargs: int) -> None:
            pass


def test_define_step_with_keyword_only_arguments():
    """Tests that keyword-only arguments get included in the input signature or a step."""

    @step
    def some_step(some_argument: int, *, keyword_only_argument: int) -> None:
        pass

    assert "keyword_only_argument" in some_step().entrypoint_definition.inputs


def test_initialize_step_with_unexpected_config():
    """Tests that passing a config to a step that was defined without config raises an Exception."""

    @step
    def step_without_params() -> None:
        pass

    with pytest.raises(StepInterfaceError):
        step_without_params(params=BaseParameters())


def test_initialize_step_with_params():
    """Tests that a step can only be initialized with it's defined parameter class."""

    class StepParams(BaseParameters):
        pass

    class DifferentParams(BaseParameters):
        pass

    @step
    def step_with_params(params: StepParams) -> None:
        pass

    # initialize with wrong param classes
    with pytest.raises(StepInterfaceError):
        step_with_params(params=BaseParameters())  # noqa

    with pytest.raises(StepInterfaceError):
        step_with_params(params=DifferentParams())  # noqa

    # initialize with wrong key
    with pytest.raises(StepInterfaceError):
        step_with_params(wrong_params_key=StepParams())  # noqa

    # initializing with correct key should work
    with does_not_raise():
        step_with_params(params=StepParams())

    # initializing as non-kwarg should work as well
    with does_not_raise():
        step_with_params(StepParams())

    # initializing with multiple args or kwargs should fail
    with pytest.raises(StepInterfaceError):
        step_with_params(StepParams(), params=StepParams())

    with pytest.raises(StepInterfaceError):
        step_with_params(StepParams(), StepParams())

    with pytest.raises(StepInterfaceError):
        step_with_params(params=StepParams(), params2=StepParams())


def test_enabling_a_custom_step_operator_for_a_step():
    """Tests that step operators are disabled by default and can be enabled using the step decorator."""

    @step
    def step_without_step_operator() -> None:
        pass

    @step(step_operator="some_step_operator")
    def step_with_step_operator() -> None:
        pass

    assert step_without_step_operator().configuration.step_operator is None
    assert (
        step_with_step_operator().configuration.step_operator
        == "some_step_operator"
    )


def test_call_step_with_args(step_with_two_int_inputs):
    """Test that a step can be called with args."""
    with does_not_raise():
        step_with_two_int_inputs().call_entrypoint(1, 2)


def test_call_step_with_kwargs(step_with_two_int_inputs):
    """Test that a step can be called with kwargs."""
    with does_not_raise():
        step_with_two_int_inputs().call_entrypoint(input_1=1, input_2=2)


def test_call_step_with_args_and_kwargs(step_with_two_int_inputs):
    """Test that a step can be called with a mix of args and kwargs."""
    with does_not_raise():
        step_with_two_int_inputs().call_entrypoint(1, input_2=2)


def test_call_step_with_too_many_args(step_with_two_int_inputs):
    """Test that calling a step fails when too many args are passed."""
    with pytest.raises(StepInterfaceError):
        step_with_two_int_inputs().call_entrypoint(1, 2, 3)


def test_call_step_with_too_many_args_and_kwargs(step_with_two_int_inputs):
    """Test that calling a step fails when too many args and kwargs are passed."""
    with pytest.raises(StepInterfaceError):
        step_with_two_int_inputs().call_entrypoint(1, input_1=2, input_2=3)


def test_call_step_with_missing_key(step_with_two_int_inputs):
    """Test that calling a step fails when an argument is missing."""
    with pytest.raises(StepInterfaceError):
        step_with_two_int_inputs()(input_1=1)


def test_call_step_with_unexpected_key(step_with_two_int_inputs):
    """Test that calling a step fails when an argument has an unexpected key."""
    with pytest.raises(StepInterfaceError):
        step_with_two_int_inputs()(
            input_1=1,
            input_2=2,
            input_3=3,
        )


def test_call_step_with_wrong_arg_type(step_with_two_int_inputs):
    """Test that calling a step fails when an arg has a wrong type."""
    with pytest.raises(StepInterfaceError):
        step_with_two_int_inputs().call_entrypoint(1, "not_an_int")


def test_call_step_with_wrong_kwarg_type(step_with_two_int_inputs):
    """Test that calling a step fails when a kwarg has a wrong type."""
    with pytest.raises(StepInterfaceError):
        step_with_two_int_inputs().call_entrypoint(
            input_1=1, input_2="not_an_int"
        )


class MyType:
    pass


class MyTypeMaterializer(BaseMaterializer):
    ASSOCIATED_TYPES = (MyType,)


def test_call_step_with_default_materializer_registered():
    """Tests that calling a step with a registered default materializer for the output works."""

    @step
    def some_step() -> MyType:
        return MyType()

    with does_not_raise():
        some_step().call_entrypoint()


def test_step_uses_config_class_default_values_if_no_config_is_passed():
    """Tests that a step falls back to the param class default values if no params object is passed at initialization."""

    class ParamsWithDefaultValues(BaseParameters):
        some_parameter: int = 1

    @step
    def some_step(params: ParamsWithDefaultValues) -> None:
        pass

    # don't pass the config when initializing the step
    step_instance = some_step()
    step_instance._finalize_configuration({}, {}, {}, {})

    assert (
        step_instance.configuration.parameters["params"]["some_parameter"] == 1
    )


def test_step_fails_if_config_parameter_value_is_missing():
    """Tests that a step fails if no config object is passed at initialization and the config class misses some default values."""

    class ParamsWithoutDefaultValues(BaseParameters):
        some_parameter: int

    @step
    def some_step(params: ParamsWithoutDefaultValues) -> None:
        pass

    # don't pass the config when initializing the step
    step_instance = some_step()

    with pytest.raises(MissingStepParameterError):
        step_instance._finalize_parameters()


def test_step_config_allows_none_as_default_value():
    """Tests that `None` is allowed as a default value for a step config field."""

    class ParamsWithNoneDefaultValue(BaseParameters):
        some_parameter: Optional[int] = None

    @step
    def some_step(params: ParamsWithNoneDefaultValue) -> None:
        pass

    # don't pass the config when initializing the step
    step_instance = some_step()

    with does_not_raise():
        step_instance._finalize_parameters()


def test_calling_a_step_works():
    """Tests that calling once step instance works."""

    @step
    def my_step() -> None:
        pass

    step_instance = my_step()

    with does_not_raise():
        step_instance.call_entrypoint()
        step_instance.call_entrypoint()


@step
def environment_test_step_1() -> None:
    assert Environment().step_is_running is True


def test_step_sets_global_execution_status_on_environment(one_step_pipeline):
    """Tests that the `Environment.step_is_running` value is set to True during step execution."""
    assert Environment().step_is_running is False
    one_step_pipeline(environment_test_step_1()).run(unlisted=True)
    assert Environment().step_is_running is False


@step
def environment_test_step_2() -> None:
    raise RuntimeError()


def test_step_resets_global_execution_status_even_if_the_step_crashes(
    one_step_pipeline,
):
    """Tests that the `Environment.step_is_running` value is set to False after step execution even if the step crashes."""
    assert Environment().step_is_running is False
    with pytest.raises(RuntimeError):
        one_step_pipeline(environment_test_step_2()).run(unlisted=True)
    assert Environment().step_is_running is False


@step
def wrong_int_output_step_1() -> int:
    return "not_an_int"


@step
def wrong_int_output_step_2() -> Output(some_output_name=int):
    return "not_an_int"


@step
def wrong_int_output_step_3() -> Output(out1=int, out2=int):
    return 1, "not_an_int"


@pytest.mark.parametrize(
    "step_class",
    [
        wrong_int_output_step_1,
        wrong_int_output_step_2,
        wrong_int_output_step_3,
    ],
)
def test_returning_an_object_of_the_wrong_type_raises_an_error(
    step_class,
    one_step_pipeline,
):
    """Tests that returning an object of a type that wasn't specified (either directly or as part of the `Output` tuple annotation) raises an error."""
    pipeline_ = one_step_pipeline(step_class())

    with pytest.raises(StepInterfaceError):
        pipeline_.run(unlisted=True)


@step
def wrong_num_outputs_step_1() -> int:
    return 1, 2


@step
def wrong_num_outputs_step_2() -> Output(some_output_name=int):
    return 1, 2


@step
def wrong_num_outputs_step_3() -> Output(out1=list):
    return 1, 2, 3


@step
def wrong_num_outputs_step_4() -> Output(out1=int, out2=int):
    return 1, 2, 3


@step
def wrong_num_outputs_step_5() -> Output(out1=int, out2=int, out3=int):
    return 1, 2


@step
def wrong_num_outputs_step_6() -> Output(out1=tuple, out2=tuple):
    return (1, 2), (3, 4), (5, 6)


@step
def wrong_num_outputs_step_7() -> Output(a=list, b=int):
    return [2, 1]


@pytest.mark.parametrize(
    "step_class",
    [
        wrong_num_outputs_step_1,
        wrong_num_outputs_step_2,
        wrong_num_outputs_step_3,
        wrong_num_outputs_step_4,
        wrong_num_outputs_step_5,
        wrong_num_outputs_step_6,
        wrong_num_outputs_step_7,
    ],
)
def test_returning_wrong_amount_of_objects_raises_an_error(
    step_class, one_step_pipeline
):
    """Tests that returning a different amount of objects than defined (either directly or as part of the `Output` tuple annotation) raises an error."""
    pipeline_ = one_step_pipeline(step_class())

    with pytest.raises(StepInterfaceError):
        pipeline_.run(unlisted=True)


@step
def dict_output_step() -> Dict:
    return {}


@step
def list_output_step() -> List:
    return []


@pytest.mark.parametrize(
    "step_class",
    [
        dict_output_step,
        list_output_step,
    ],
)
def test_step_can_output_generic_types(step_class, one_step_pipeline):
    """Tests that a step can output generic typing classes."""
    pipeline_ = one_step_pipeline(step_class())

    with does_not_raise():
        pipeline_.run(unlisted=True)


@step
def list_of_str_output_step() -> List[str]:
    return []


@step
def dict_of_str_output_step() -> (
    Output(str_output=str, dict_output=Dict[str, int])
):
    return "", {}


@pytest.mark.parametrize(
    "step_class",
    [
        list_of_str_output_step,
        dict_of_str_output_step,
    ],
)
def test_step_can_output_subscripted_generic_types(
    step_class, one_step_pipeline
):
    """Tests that a step can output subscripted generic types."""
    pipeline_ = one_step_pipeline(step_class())

    with does_not_raise():
        pipeline_.run(unlisted=True)


@step
def list_dict_output_step() -> Output(dict_output=Dict, list_output=List):
    return {}, []


@step
def dict_list_input_step(dict_input: Dict, list_input: List) -> None:
    pass


def test_step_can_have_generic_input_types():
    """Tests that a step can have generic typing classes as input."""

    @pipeline
    def p(s1, s2):
        s2(*s1())

    with does_not_raise():
        p(list_dict_output_step(), dict_list_input_step()).run(unlisted=True)


@step
def subscripted_generic_output_step() -> (
    Output(dict_output=Dict[str, int], list_output=List[str])
):
    return {}, []


@step
def subscripted_generic_input_step(
    dict_input: Dict[str, int], list_input: List[str]
) -> None:
    pass


def test_step_can_have_subscripted_generic_input_types():
    """Tests that a step can have subscripted generic input types."""

    @pipeline
    def p(s1, s2):
        s2(*s1())

    with does_not_raise():
        p(
            subscripted_generic_output_step(), subscripted_generic_input_step()
        ).run(unlisted=True)


@step
def raw_artifact_test_step_1() -> Output(dict_=Dict, list_=List):
    return {"some": "data"}, []


@step
def raw_artifact_test_step_2() -> Output(dict_=Dict, list_=List):
    return {"some": "data"}, []


@step
def raw_artifact_test_step_3(
    dict_: ArtifactVersionResponse, list_: ArtifactVersionResponse
) -> None:
    assert hasattr(dict_, "uri")
    assert hasattr(list_, "uri")


@step
def raw_artifact_test_step_4(dict_: Dict, list_: List) -> None:
    assert isinstance(dict_, dict)
    assert isinstance(list_, list)


def test_step_can_have_raw_artifacts(clean_client):
    """Check that you can bypass materialization with raw artifacts."""

    @pipeline
    def p(s1, s2, s3, s4):
        s3(*s1())
        s4(*s2())

    with does_not_raise():
        p(
            raw_artifact_test_step_1(),
            raw_artifact_test_step_2(),
            raw_artifact_test_step_3(),
            raw_artifact_test_step_4(),
        )


@step
def upstream_test_step_1() -> int:
    return 1


@step
def upstream_test_step_2() -> int:
    return 2


@step
def upstream_test_step_3(a: int, b: int) -> None:
    pass


def test_upstream_step_computation():
    """Tests that step upstream consider both data and manual dependencies."""

    @pipeline
    def p(s1, s2, s3):
        s3(s1(), s2())
        s1.after(s2)

    s1 = upstream_test_step_1()
    s2 = upstream_test_step_2()
    s3 = upstream_test_step_3()
    pipeline_instance = p(s1, s2, s3)
    pipeline_instance.connect(**pipeline_instance.steps)

    assert s1.upstream_steps == {s2}
    assert not s2.upstream_steps
    assert not s3.upstream_steps


class ParamTestBaseClass(BaseModel):
    key: str


class ParamTestSubClass(ParamTestBaseClass):
    key: str = "value"


class ParamTestClass(BaseParameters):
    attribute: ParamTestBaseClass = ParamTestSubClass()


@step
def parametrized_step(params: ParamTestClass) -> None:
    pass


def test_base_parameter_subclasses_as_attribute():
    """Tests that parameter class attributes which are unset.

    For example (for example due to being set on a subclass) still get
    serialized so the params can be reconstructed.
    """
    step_instance = parametrized_step(ParamTestClass())
    assert step_instance.configuration.parameters == {
        "attribute": {"key": "value"}
    }


@step
def step_with_two_letter_string_output() -> Output(a=str, b=str):
    return "ab"


def test_string_outputs_do_not_get_split(one_step_pipeline):
    """Tests that a step which outputs a N-character string is not allowed if the output annotations require N string outputs."""
    pipeline_ = one_step_pipeline(step_with_two_letter_string_output())

    with pytest.raises(StepInterfaceError):
        pipeline_.run(unlisted=True)


def test_step_decorator_configuration_gets_applied_during_initialization(
    mocker,
):
    """Tests that the configuration passed to the step decorator gets applied
    when creating an instance of the step."""
    config = {
        "experiment_tracker": "e",
        "step_operator": "s",
        "extra": {"key": "value"},
    }

    @step(**config)
    def s() -> None:
        pass

    step_instance = s()
    assert step_instance.configuration.experiment_tracker == "e"
    assert step_instance.configuration.step_operator == "s"
    assert step_instance.configuration.extra == {"key": "value"}


def test_step_configuration(empty_step):
    """Tests the step configuration and overwriting/merging with existing
    configurations."""
    step_instance = empty_step()
    step_instance.configure(
        enable_cache=False,
        experiment_tracker="experiment_tracker",
        step_operator="step_operator",
        extra={"key": "value"},
    )

    assert step_instance.configuration.enable_cache is False
    assert (
        step_instance.configuration.experiment_tracker == "experiment_tracker"
    )
    assert step_instance.configuration.step_operator == "step_operator"
    assert step_instance.configuration.extra == {"key": "value"}

    # No merging
    step_instance.configure(
        enable_cache=True,
        experiment_tracker="experiment_tracker2",
        step_operator="step_operator2",
        extra={"key2": "value2"},
        merge=False,
    )
    assert step_instance.configuration.enable_cache is True
    assert (
        step_instance.configuration.experiment_tracker == "experiment_tracker2"
    )
    assert step_instance.configuration.step_operator == "step_operator2"
    assert step_instance.configuration.extra == {"key2": "value2"}

    # With merging
    step_instance.configure(
        enable_cache=False,
        experiment_tracker="experiment_tracker3",
        step_operator="step_operator3",
        extra={"key3": "value3"},
        merge=True,
    )
    assert step_instance.configuration.enable_cache is False
    assert (
        step_instance.configuration.experiment_tracker == "experiment_tracker3"
    )
    assert step_instance.configuration.step_operator == "step_operator3"
    assert step_instance.configuration.extra == {
        "key2": "value2",
        "key3": "value3",
    }


def test_configure_step_with_invalid_settings_key(empty_step):
    """Tests that configuring a step with an invalid settings key raises an
    error."""
    with pytest.raises(ValueError):
        empty_step().configure(settings={"invalid_settings_key": {}})


def test_configure_step_with_invalid_materializer_key_or_source():
    """Tests that configuring a step with an invalid materializer key or source
    raises an error."""

    @step
    def s() -> int:
        return 0

    step_instance = s()
    with pytest.raises(StepInterfaceError):
        step_instance.configure(
            output_materializers={"not_an_output_key": BuiltInMaterializer}
        )

    with pytest.raises(StepInterfaceError):
        step_instance.configure(
            output_materializers={
                "output": "non_existent_module.materializer_class"
            }
        )

    with does_not_raise():
        step_instance.configure(
            output_materializers={"output": BuiltInMaterializer}
        )
        step_instance.configure(
            output_materializers={
                "output": "zenml.materializers.built_in_materializer.BuiltInMaterializer"
            }
        )


def test_configure_step_with_invalid_parameters():
    """Tests that configuring a step with an invalid parameter key raises an
    error."""

    @step
    def step_without_parameters() -> None:
        pass

    with pytest.raises(StepInterfaceError):
        step_without_parameters().configure(parameters={"key": "value"})

    class StepParams(BaseParameters):
        key: int

    @step
    def step_with_parameters(params: StepParams) -> None:
        pass

    with does_not_raise():
        step_with_parameters().configure(parameters={"key": 1})

    # Missing key (only fail once step is called)
    step_instance = step_with_parameters().configure(
        parameters={"invalid_key": 1}
    )
    with pytest.raises(StepInterfaceError):
        step_instance()

    # Wrong type (only fail once step is called)
    step_instance = step_with_parameters().configure(
        parameters={"key": "not_an_int"}
    )
    with pytest.raises(StepInterfaceError):
        step_instance()


def on_failure_with_context(context: StepContext):
    global is_hook_called
    is_hook_called = True


def on_failure_with_params(params: BaseParameters):
    global is_hook_called
    is_hook_called = True


def on_failure_with_exception(e: BaseException):
    global is_hook_called
    is_hook_called = True


def on_failure_with_all(
    context: StepContext, params: BaseParameters, e: BaseException
):
    global is_hook_called
    is_hook_called = True


def on_failure_with_wrong_params(a: int):
    global is_hook_called
    is_hook_called = True


def on_failure_with_not_annotated_params(a):
    global is_hook_called
    is_hook_called = True


def on_failure_with_multiple_param_annotations(
    a: BaseParameters, b: BaseParameters
):
    global is_hook_called
    is_hook_called = True


def on_failure_with_no_params():
    global is_hook_called
    is_hook_called = True


@step
def exception_step(params: BaseParameters) -> None:
    raise BaseException("A cat appeared!")


def test_configure_step_with_failure_hook(one_step_pipeline):
    """Tests that configuring a step with different failure
    hook configurations"""
    global is_hook_called

    # Test 1
    is_hook_called = False
    with pytest.raises(BaseException):
        one_step_pipeline(
            exception_step().configure(on_failure=on_failure_with_context)
        ).run(unlisted=True)
    assert is_hook_called

    # Test 2
    is_hook_called = False
    with pytest.raises(BaseException):
        one_step_pipeline(
            exception_step().configure(on_failure=on_failure_with_params)
        ).run(unlisted=True)
    assert is_hook_called

    # Test 3
    is_hook_called = False
    with pytest.raises(BaseException):
        one_step_pipeline(
            exception_step().configure(on_failure=on_failure_with_exception)
        ).run(unlisted=True)
    assert is_hook_called

    # Test 4
    is_hook_called = False
    with pytest.raises(BaseException):
        one_step_pipeline(
            exception_step().configure(on_failure=on_failure_with_all)
        ).run(unlisted=True)
    assert is_hook_called

    # Test 5
    is_hook_called = False
    with pytest.raises(ValueError):
        one_step_pipeline(
            exception_step().configure(on_failure=on_failure_with_wrong_params)
        ).run(unlisted=True)
    assert not is_hook_called

    # Test 6
    is_hook_called = False
    with pytest.raises(ValueError):
        one_step_pipeline(
            exception_step().configure(
                on_failure=on_failure_with_not_annotated_params
            )
        ).run(unlisted=True)
    assert not is_hook_called

    # Test 7
    is_hook_called = False
    with pytest.raises(ValueError):
        one_step_pipeline(
            exception_step().configure(
                on_failure=on_failure_with_multiple_param_annotations
            )
        ).run(unlisted=True)
    assert not is_hook_called

    # Test 8
    is_hook_called = False
    with pytest.raises(BaseException):
        one_step_pipeline(
            exception_step().configure(on_failure=on_failure_with_no_params)
        ).run(unlisted=True)
    assert is_hook_called


def on_success_with_context(context: StepContext):
    global is_hook_called
    is_hook_called = True


def on_success_with_params(params: BaseParameters):
    global is_hook_called
    is_hook_called = True


def on_success_with_exception(e: BaseException):
    global is_hook_called
    is_hook_called = True


def on_success_with_all(context: StepContext, params: BaseParameters):
    global is_hook_called
    is_hook_called = True


def on_success_with_wrong_params(a: int):
    global is_hook_called
    is_hook_called = True


def on_success_with_not_annotated_params(a):
    global is_hook_called
    is_hook_called = True


def on_success_with_multiple_param_annotations(
    a: BaseParameters, b: BaseParameters
):
    global is_hook_called
    is_hook_called = True


def on_success_with_no_params():
    global is_hook_called
    is_hook_called = True


@step(enable_cache=False)
def passing_step(params: BaseParameters) -> None:
    pass


def test_configure_step_with_success_hook(one_step_pipeline):
    """Tests that configuring a step with different success
    hook configurations"""
    global is_hook_called

    # Test 1
    is_hook_called = False
    one_step_pipeline(
        passing_step().configure(on_success=on_success_with_context)
    ).run(unlisted=True)
    assert is_hook_called

    # Test 2
    is_hook_called = False
    one_step_pipeline(
        passing_step().configure(on_success=on_success_with_params)
    ).run(unlisted=True)
    assert is_hook_called

    # Test 3
    is_hook_called = False
    one_step_pipeline(
        passing_step().configure(on_success=on_success_with_all)
    ).run(unlisted=True)
    assert is_hook_called

    # Test 4
    is_hook_called = False
    with pytest.raises(ValueError):
        one_step_pipeline(
            passing_step().configure(on_success=on_success_with_wrong_params)
        ).run(unlisted=True)
    assert not is_hook_called

    # Test 5
    is_hook_called = False
    with pytest.raises(ValueError):
        one_step_pipeline(
            passing_step().configure(
                on_success=on_success_with_not_annotated_params
            )
        ).run(unlisted=True)
    assert not is_hook_called

    # Test 6
    is_hook_called = False
    with pytest.raises(ValueError):
        one_step_pipeline(
            passing_step().configure(
                on_success=on_success_with_multiple_param_annotations
            )
        ).run(unlisted=True)
    assert not is_hook_called

    # Test 7
    is_hook_called = False
    one_step_pipeline(
        passing_step().configure(on_success=on_success_with_no_params)
    ).run(unlisted=True)
    assert is_hook_called


def on_success():
    global is_success_hook_called
    is_success_hook_called = True


def on_failure():
    global is_failure_hook_called
    is_failure_hook_called = True


def test_configure_pipeline_with_hooks(one_step_pipeline):
    """Tests that configuring a pipeline with hooks"""
    global is_success_hook_called
    global is_failure_hook_called

    # Test 1
    is_success_hook_called = False
    p = one_step_pipeline(
        passing_step(),
    )
    p.configure(on_success=on_success).run(unlisted=True)

    assert is_success_hook_called

    # Test 2
    is_failure_hook_called = False
    p = one_step_pipeline(
        exception_step(),
    )
    with pytest.raises(BaseException):
        p.configure(on_failure=on_failure).run(unlisted=True)
    assert is_failure_hook_called
