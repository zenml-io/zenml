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
from typing import Annotated, Dict, List, Tuple, Union

import pytest
from pydantic import BaseModel

from zenml import pipeline, step
from zenml.exceptions import StepInterfaceError
from zenml.materializers import BuiltInMaterializer
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.models import ArtifactVersionResponse


def test_step_decorator_creates_class_in_same_module_as_decorated_function():
    """Tests that the `BaseStep` subclass created by our step decorator creates the class in the same module as the decorated function."""

    @step
    def some_step() -> None:
        pass

    assert some_step.__module__ == __name__


def test_step_has_no_enable_cache_by_default():
    """Tests that a step has `enable_cache=None` by default."""

    @step
    def some_step() -> None:
        pass

    assert some_step.enable_cache is None


def test_enable_caching_for_step():
    """Tests that caching can be explicitly enabled for a step."""

    @step(enable_cache=True)
    def some_step() -> None:
        pass

    assert some_step.enable_cache is True


def test_disable_caching_for_step():
    """Tests that caching can be explicitly disabled for a step."""

    @step(enable_cache=False)
    def some_step() -> None:
        pass

    assert some_step.enable_cache is False


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

    assert "keyword_only_argument" in some_step.entrypoint_definition.inputs


def test_enabling_a_custom_step_operator_for_a_step():
    """Tests that step operators are disabled by default and can be enabled using the step decorator."""

    @step
    def step_without_step_operator() -> None:
        pass

    @step(step_operator="some_step_operator")
    def step_with_step_operator() -> None:
        pass

    assert step_without_step_operator.configuration.step_operator is None
    assert (
        step_with_step_operator.configuration.step_operator
        == "some_step_operator"
    )


def test_call_step_with_args(step_with_two_int_inputs):
    """Test that a step can be called with args."""
    with does_not_raise():
        step_with_two_int_inputs.call_entrypoint(1, 2)


def test_call_step_with_kwargs(step_with_two_int_inputs):
    """Test that a step can be called with kwargs."""
    with does_not_raise():
        step_with_two_int_inputs.call_entrypoint(input_1=1, input_2=2)


def test_call_step_with_args_and_kwargs(step_with_two_int_inputs):
    """Test that a step can be called with a mix of args and kwargs."""
    with does_not_raise():
        step_with_two_int_inputs.call_entrypoint(1, input_2=2)


def test_call_step_with_too_many_args(step_with_two_int_inputs):
    """Test that calling a step fails when too many args are passed."""
    with pytest.raises(StepInterfaceError):
        step_with_two_int_inputs.call_entrypoint(1, 2, 3)


def test_call_step_with_too_many_args_and_kwargs(step_with_two_int_inputs):
    """Test that calling a step fails when too many args and kwargs are passed."""
    with pytest.raises(StepInterfaceError):
        step_with_two_int_inputs.call_entrypoint(1, input_1=2, input_2=3)


def test_call_step_with_missing_key(step_with_two_int_inputs):
    """Test that calling a step fails when an argument is missing."""
    with pytest.raises(StepInterfaceError):
        step_with_two_int_inputs(input_1=1)


def test_call_step_with_unexpected_key(step_with_two_int_inputs):
    """Test that calling a step fails when an argument has an unexpected key."""
    with pytest.raises(StepInterfaceError):
        step_with_two_int_inputs(
            input_1=1,
            input_2=2,
            input_3=3,
        )


def test_call_step_with_wrong_arg_type(step_with_two_int_inputs):
    """Test that calling a step fails when an arg has a wrong type."""
    with pytest.raises(StepInterfaceError):
        step_with_two_int_inputs.call_entrypoint(1, "not_an_int")


def test_call_step_with_wrong_kwarg_type(step_with_two_int_inputs):
    """Test that calling a step fails when a kwarg has a wrong type."""
    with pytest.raises(StepInterfaceError):
        step_with_two_int_inputs.call_entrypoint(
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
        some_step.call_entrypoint()


def test_calling_a_step_works():
    """Tests that calling once step instance works."""

    @step
    def step_instance() -> None:
        pass

    with does_not_raise():
        step_instance.call_entrypoint()
        step_instance.call_entrypoint()


@step
def wrong_int_output_step_1() -> int:
    return "not_an_int"


@step
def wrong_int_output_step_2() -> Annotated[int, "output_name"]:
    return "not_an_int"


@step
def wrong_int_output_step_3() -> (
    Tuple[Annotated[int, "out_1"], Annotated[int, "out_2"]]
):
    return 1, "not_an_int"


@pytest.mark.parametrize(
    "step_instance",
    [
        wrong_int_output_step_1,
        wrong_int_output_step_2,
        wrong_int_output_step_3,
    ],
)
def test_returning_an_object_of_the_wrong_type_raises_an_error(
    step_instance,
    one_step_pipeline,
):
    """Tests that returning an object of a type that wasn't specified (either directly or as part of the `Output` tuple annotation) raises an error."""
    pipeline_ = one_step_pipeline(step_instance)

    with pytest.raises(StepInterfaceError):
        pipeline_.with_options(unlisted=True)()


@step
def wrong_num_outputs_step_1() -> int:
    return 1, 2


@step
def wrong_num_outputs_step_2() -> Annotated[int, "some_output_name"]:
    return 1, 2


@step
def wrong_num_outputs_step_3() -> Annotated[list, "out1"]:
    return 1, 2, 3


@step
def wrong_num_outputs_step_4() -> (
    Tuple[Annotated[int, "out_1"], Annotated[int, "out_2"]]
):
    return 1, 2, 3


@step
def wrong_num_outputs_step_5() -> (
    Tuple[
        Annotated[int, "out_1"],
        Annotated[int, "out_2"],
        Annotated[int, "out_3"],
    ]
):
    return 1, 2


@step
def wrong_num_outputs_step_6() -> (
    Tuple[Annotated[tuple, "out_1"], Annotated[tuple, "out_2"]]
):
    return (1, 2), (3, 4), (5, 6)


@step
def wrong_num_outputs_step_7() -> (
    Tuple[Annotated[list, "a"], Annotated[int, "b"]]
):
    return [2, 1]


@pytest.mark.parametrize(
    "step_instance",
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
    step_instance, one_step_pipeline
):
    """Tests that returning a different amount of objects than defined (either directly or as part of the `Output` tuple annotation) raises an error."""
    pipeline_ = one_step_pipeline(step_instance)

    with pytest.raises(StepInterfaceError):
        pipeline_.with_options(unlisted=True)()


@step
def dict_output_step() -> Dict:
    return {}


@step
def list_output_step() -> List:
    return []


@pytest.mark.parametrize(
    "step_instance",
    [
        dict_output_step,
        list_output_step,
    ],
)
def test_step_can_output_generic_types(step_instance, one_step_pipeline):
    """Tests that a step can output generic typing classes."""
    pipeline_ = one_step_pipeline(step_instance)

    with does_not_raise():
        pipeline_.with_options(unlisted=True)()


@step
def list_of_str_output_step() -> List[str]:
    return []


@step
def dict_of_str_output_step() -> (
    Tuple[
        Annotated[str, "str_output"], Annotated[Dict[str, int], "dict_output"]
    ]
):
    return "", {}


@pytest.mark.parametrize(
    "step_instance",
    [
        list_of_str_output_step,
        dict_of_str_output_step,
    ],
)
def test_step_can_output_subscripted_generic_types(
    step_instance, one_step_pipeline
):
    """Tests that a step can output subscripted generic types."""
    pipeline_ = one_step_pipeline(step_instance)

    with does_not_raise():
        pipeline_.with_options(unlisted=True)()


@step
def list_dict_output_step() -> (
    Tuple[Annotated[Dict, "dict_output"], Annotated[List, "list_output"]]
):
    return {}, []


@step
def dict_list_input_step(dict_input: Dict, list_input: List) -> None:
    pass


def test_step_can_have_generic_input_types():
    """Tests that a step can have generic typing classes as input."""

    @pipeline
    def p():
        dict_list_input_step(*list_dict_output_step())

    with does_not_raise():
        p.with_options(unlisted=True)()


@step
def subscripted_generic_output_step() -> (
    Tuple[
        Annotated[Dict[str, int], "dict_output"],
        Annotated[List[str], "list_output"],
    ]
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
    def p():
        subscripted_generic_input_step(*subscripted_generic_output_step())

    with does_not_raise():
        p.with_options(unlisted=True)()


@step
def raw_artifact_test_step_1() -> (
    Tuple[Annotated[Dict, "dict_"], Annotated[List, "list_"]]
):
    return {"some": "data"}, []


@step
def raw_artifact_test_step_2() -> (
    Tuple[Annotated[Dict, "dict_"], Annotated[List, "list_"]]
):
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

    with does_not_raise():

        @pipeline
        def p():
            raw_artifact_test_step_3(*raw_artifact_test_step_1())
            raw_artifact_test_step_4(*raw_artifact_test_step_2())


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
    def p():
        a = upstream_test_step_1(after="upstream_test_step_2")
        upstream_test_step_3(a, upstream_test_step_2())

    p.prepare()

    assert p._invocations["upstream_test_step_1"].upstream_steps == {
        "upstream_test_step_2"
    }
    assert not p._invocations["upstream_test_step_2"].upstream_steps
    assert p._invocations["upstream_test_step_3"].upstream_steps == {
        "upstream_test_step_1",
        "upstream_test_step_2",
    }


@step
def step_with_two_letter_string_output() -> (
    Tuple[Annotated[str, "a"], Annotated[str, "b"]]
):
    return "ab"


def test_string_outputs_do_not_get_split(one_step_pipeline):
    """Tests that a step which outputs a N-character string is not allowed if the output annotations require N string outputs."""
    pipeline_ = one_step_pipeline(step_with_two_letter_string_output)

    with pytest.raises(StepInterfaceError):
        pipeline_.with_options(unlisted=True)()


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
    def step_instance() -> None:
        pass

    assert step_instance.configuration.experiment_tracker == "e"
    assert step_instance.configuration.step_operator == "s"
    assert step_instance.configuration.extra == {"key": "value"}


def test_step_configuration(empty_step):
    """Tests the step configuration and overwriting/merging with existing
    configurations."""
    step_instance = empty_step
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
        empty_step.configure(settings={"invalid_settings_key": {}})


def test_configure_step_with_invalid_materializer_key_or_source():
    """Tests that configuring a step with an invalid materializer key or source
    raises an error."""

    @step
    def step_instance() -> int:
        return 0

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


def on_failure_with_exception(e: BaseException):
    global is_hook_called
    is_hook_called = True


def on_failure_with_wrong_params(a: int):
    global is_hook_called
    is_hook_called = True


def on_failure_with_not_annotated_params(a):
    global is_hook_called
    is_hook_called = True


def on_failure_with_no_params():
    global is_hook_called
    is_hook_called = True


@step
def exception_step() -> None:
    raise BaseException("A cat appeared!")


def test_configure_step_with_failure_hook(one_step_pipeline):
    """Tests that configuring a step with different failure
    hook configurations"""
    global is_hook_called

    # Test 1
    is_hook_called = False
    with pytest.raises(BaseException):
        one_step_pipeline(
            exception_step.configure(on_failure=on_failure_with_exception)
        ).with_options(unlisted=True)()
    assert is_hook_called

    # Test 2
    is_hook_called = False
    with pytest.raises(ValueError):
        one_step_pipeline(
            exception_step.configure(on_failure=on_failure_with_wrong_params)
        ).with_options(unlisted=True)()
    assert not is_hook_called

    # Test 3
    is_hook_called = False
    with pytest.raises(ValueError):
        one_step_pipeline(
            exception_step.configure(
                on_failure=on_failure_with_not_annotated_params
            )
        ).with_options(unlisted=True)()
    assert not is_hook_called

    # Test 4
    is_hook_called = False
    with pytest.raises(BaseException):
        one_step_pipeline(
            exception_step.configure(on_failure=on_failure_with_no_params)
        ).with_options(unlisted=True)()
    assert is_hook_called


def on_success_with_exception(e: BaseException):
    global is_hook_called
    is_hook_called = True


def on_success_with_wrong_params(a: int):
    global is_hook_called
    is_hook_called = True


def on_success_with_not_annotated_params(a):
    global is_hook_called
    is_hook_called = True


def on_success_with_no_params():
    global is_hook_called
    is_hook_called = True


@step(enable_cache=False)
def passing_step() -> None:
    pass


def test_configure_step_with_success_hook(one_step_pipeline):
    """Tests that configuring a step with different success
    hook configurations"""
    global is_hook_called

    # Test 1
    is_hook_called = False
    with pytest.raises(ValueError):
        one_step_pipeline(
            passing_step.configure(on_success=on_success_with_wrong_params)
        ).with_options(unlisted=True)()
    assert not is_hook_called

    # Test 2
    is_hook_called = False
    with pytest.raises(ValueError):
        one_step_pipeline(
            passing_step.configure(
                on_success=on_success_with_not_annotated_params
            )
        ).with_options(unlisted=True)()
    assert not is_hook_called

    # Test 3
    is_hook_called = False
    one_step_pipeline(
        passing_step.configure(on_success=on_success_with_no_params)
    ).with_options(unlisted=True)()
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
    p = one_step_pipeline(passing_step)
    p.configure(on_success=on_success).with_options(unlisted=True)()

    assert is_success_hook_called

    # Test 2
    is_failure_hook_called = False
    p = one_step_pipeline(
        exception_step,
    )
    with pytest.raises(BaseException):
        p.configure(on_failure=on_failure).with_options(unlisted=True)()
    assert is_failure_hook_called


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

    with pytest.raises(RuntimeError):
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


class MyStringMaterializer(BaseMaterializer):
    ASSOCIATED_TYPES = (str,)

    def load(self, data_type: Any) -> Any:
        return None

    def save(self, data: Any) -> None:
        return


def test_configure_step_with_wrong_materializers():
    """Tests that configuring a step with invalid materializers raises an
    error."""

    @step(output_materializers=MyStringMaterializer)
    def step_with_int_return() -> int:
        return 1

    with pytest.raises(StepInterfaceError):
        step_with_int_return._finalize_configuration({}, {}, {}, {})

    @step
    def step_with_int_and_string_return() -> Tuple[str, int]:
        return "", 1

    with pytest.raises(StepInterfaceError):
        step_with_int_and_string_return.with_options(
            output_materializers=MyStringMaterializer
        )._finalize_configuration({}, {}, {}, {})

    with does_not_raise():
        step_with_int_and_string_return.with_options(
            output_materializers={"output_0": MyStringMaterializer}
        )._finalize_configuration({}, {}, {}, {})

    @step(output_materializers=MyStringMaterializer)
    def step_with_str_union_return() -> Union[str, int]:
        return 1

    with does_not_raise():
        step_with_str_union_return._finalize_configuration({}, {}, {}, {})

    @step(output_materializers=MyStringMaterializer)
    def step_without_str_union_return() -> Union[int, float]:
        return 1

    with pytest.raises(StepInterfaceError):
        step_without_str_union_return._finalize_configuration({}, {}, {}, {})
