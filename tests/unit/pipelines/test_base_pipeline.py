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
import os
from contextlib import ExitStack as does_not_raise

import pytest

from zenml.exceptions import (
    PipelineConfigurationError,
    PipelineInterfaceError,
    StackValidationError,
)
from zenml.pipelines import pipeline
from zenml.repository import Repository
from zenml.steps import BaseStepConfig, step
from zenml.utils.yaml_utils import write_yaml


def create_pipeline_with_config_value(config_value: int):
    """Creates pipeline instance with a step named 'step' which has a
    parameter named 'value'."""

    class Config(BaseStepConfig):
        value: int

    @step
    def step_with_config(config: Config):
        pass

    @pipeline
    def some_pipeline(step_):
        step_()

    pipeline_instance = some_pipeline(
        step_=step_with_config(config=Config(value=config_value))
    )
    return pipeline_instance


def test_initialize_pipeline_with_args(
    unconnected_two_step_pipeline, generate_empty_steps
):
    """Test that a pipeline can be initialized with args."""
    with does_not_raise():
        empty_step_1, empty_step_2 = generate_empty_steps(2)
        unconnected_two_step_pipeline(empty_step_1(), empty_step_2())


def test_initialize_pipeline_with_kwargs(
    unconnected_two_step_pipeline, generate_empty_steps
):
    """Test that a pipeline can be initialized with kwargs."""
    with does_not_raise():
        empty_step_1, empty_step_2 = generate_empty_steps(2)
        unconnected_two_step_pipeline(
            step_1=empty_step_1(), step_2=empty_step_2()
        )


def test_initialize_pipeline_with_args_and_kwargs(
    unconnected_two_step_pipeline, generate_empty_steps
):
    """Test that a pipeline can be initialized with a mix of args and kwargs."""
    with does_not_raise():
        empty_step_1, empty_step_2 = generate_empty_steps(2)
        unconnected_two_step_pipeline(empty_step_1(), step_2=empty_step_2())


def test_initialize_pipeline_with_too_many_args(
    unconnected_two_step_pipeline, generate_empty_steps
):
    """Test that pipeline initialization fails when too many args
    are passed."""
    with pytest.raises(PipelineInterfaceError):
        empty_step_1, empty_step_2, empty_step_3 = generate_empty_steps(3)
        unconnected_two_step_pipeline(
            empty_step_1(), empty_step_2(), empty_step_3()
        )


def test_initialize_pipeline_with_too_many_args_and_kwargs(
    unconnected_two_step_pipeline, generate_empty_steps
):
    """Test that pipeline initialization fails when too many args
    and kwargs are passed."""
    with pytest.raises(PipelineInterfaceError):
        empty_step_1, empty_step_2, empty_step_3 = generate_empty_steps(3)
        unconnected_two_step_pipeline(
            empty_step_3(), step_1=empty_step_1(), step_2=empty_step_2()
        )


def test_initialize_pipeline_with_missing_key(
    unconnected_two_step_pipeline, empty_step
):
    """Test that pipeline initialization fails when an argument
    is missing."""
    with pytest.raises(PipelineInterfaceError):
        unconnected_two_step_pipeline(step_1=empty_step())


def test_initialize_pipeline_with_unexpected_key(
    unconnected_two_step_pipeline, generate_empty_steps
):
    """Test that pipeline initialization fails when an argument
    has an unexpected key."""
    with pytest.raises(PipelineInterfaceError):
        empty_step_1, empty_step_2, empty_step_3 = generate_empty_steps(3)
        unconnected_two_step_pipeline(
            step_1=empty_step_1(), step_2=empty_step_2(), step_3=empty_step_3()
        )


def test_initialize_pipeline_with_repeated_args(
    unconnected_two_step_pipeline, empty_step
):
    """Test that pipeline initialization fails when same step
    object is used"""
    with pytest.raises(PipelineInterfaceError):
        unconnected_two_step_pipeline(empty_step(), empty_step())


def test_initialize_pipeline_with_repeated_kwargs(
    unconnected_two_step_pipeline, empty_step
):
    """Test that pipeline initialization fails when same step
    object is used"""
    with pytest.raises(PipelineInterfaceError):
        unconnected_two_step_pipeline(step_1=empty_step(), step_2=empty_step())


def test_initialize_pipeline_with_repeated_args_and_kwargs(
    unconnected_two_step_pipeline, empty_step
):
    """Test that pipeline initialization fails when same step
    object is used"""
    with pytest.raises(PipelineInterfaceError):
        unconnected_two_step_pipeline(empty_step(), step_2=empty_step())


def test_initialize_pipeline_with_wrong_arg_type(
    unconnected_two_step_pipeline, empty_step
):
    """Test that pipeline initialization fails when an arg has a wrong type."""
    with pytest.raises(PipelineInterfaceError):
        unconnected_two_step_pipeline(1, empty_step())


def test_initialize_pipeline_with_wrong_kwarg_type(
    unconnected_two_step_pipeline, empty_step
):
    """Test that pipeline initialization fails when a kwarg has a wrong type."""
    with pytest.raises(PipelineInterfaceError):
        unconnected_two_step_pipeline(step_1=1, step_2=empty_step())


def test_setting_step_parameter_with_config_object():
    """Test whether step parameters can be set using a config object."""
    config_value = 0
    pipeline_instance = create_pipeline_with_config_value(config_value)
    step_instance = pipeline_instance.steps["step_"]

    assert step_instance.PARAM_SPEC["value"] == config_value


def test_overwrite_step_parameter_with_config_yaml(tmp_path):
    """Test whether step parameters can be overwritten using a config yaml."""
    config_value = 0
    pipeline_instance = create_pipeline_with_config_value(config_value)

    yaml_path = os.path.join(tmp_path, "config.yaml")
    yaml_config_value = 1
    write_yaml(
        yaml_path,
        {"steps": {"step_": {"parameters": {"value": yaml_config_value}}}},
    )
    pipeline_instance = pipeline_instance.with_config(
        yaml_path, overwrite_step_parameters=True
    )
    step_instance = pipeline_instance.steps["step_"]
    assert step_instance.PARAM_SPEC["value"] == yaml_config_value


def test_dont_overwrite_step_parameter_with_config_yaml(tmp_path):
    """Test that step parameters don't get overwritten by yaml file
    if not forced."""
    config_value = 0
    pipeline_instance = create_pipeline_with_config_value(config_value)

    yaml_path = os.path.join(tmp_path, "config.yaml")
    yaml_config_value = 1
    write_yaml(
        yaml_path,
        {"steps": {"step_": {"parameters": {"value": yaml_config_value}}}},
    )
    pipeline_instance = pipeline_instance.with_config(yaml_path)
    step_instance = pipeline_instance.steps["step_"]
    assert step_instance.PARAM_SPEC["value"] == config_value


def test_yaml_configuration_with_invalid_step_name(tmp_path):
    """Test that a config yaml with an invalid step name raises an exception"""
    pipeline_instance = create_pipeline_with_config_value(0)

    yaml_path = os.path.join(tmp_path, "config.yaml")
    write_yaml(
        yaml_path,
        {"steps": {"WRONG_STEP_NAME": {"parameters": {"value": 0}}}},
    )
    with pytest.raises(PipelineConfigurationError):
        _ = pipeline_instance.with_config(yaml_path)


def test_yaml_configuration_with_invalid_parameter_name(tmp_path):
    """Test that a config yaml with an invalid parameter
    name raises an exception"""
    pipeline_instance = create_pipeline_with_config_value(0)

    yaml_path = os.path.join(tmp_path, "config.yaml")
    write_yaml(
        yaml_path,
        {"steps": {"step_": {"parameters": {"WRONG_PARAMETER_NAME": 0}}}},
    )
    with pytest.raises(PipelineConfigurationError):
        _ = pipeline_instance.with_config(yaml_path)


def test_setting_pipeline_parameter_name_when_initializing_pipeline(
    one_step_pipeline, empty_step
):
    """Tests that initializing a pipeline with a step sets the attribute
    `pipeline_parameter_name` of the step."""
    step_instance = empty_step()
    assert step_instance.pipeline_parameter_name is None
    one_step_pipeline(step_instance)
    assert step_instance.pipeline_parameter_name == "step_"


def test_calling_a_pipeline_twice_raises_no_exception(
    one_step_pipeline, empty_step
):
    """Tests that calling one pipeline instance twice does not raise
    any exception."""

    pipeline_instance = one_step_pipeline(empty_step())

    with does_not_raise():
        pipeline_instance.run()
        pipeline_instance.run()


def test_pipeline_requirements(tmp_path):
    """Tests that the pipeline requirements are a combination of the
    requirements of integrations and requirements of the specified
    requirements file."""
    from zenml.integrations.sklearn import SklearnIntegration

    requirements_file = tmp_path / "requirements.txt"
    requirements_file.write_text("any_requirement")

    @pipeline(required_integrations=[SklearnIntegration.NAME])
    def my_pipeline():
        pass

    assert my_pipeline().requirements == set(SklearnIntegration.REQUIREMENTS)

    @pipeline(requirements_file=str(requirements_file))
    def my_pipeline():
        pass

    assert my_pipeline().requirements == {"any_requirement"}

    @pipeline(
        required_integrations=[SklearnIntegration.NAME],
        requirements_file=str(requirements_file),
    )
    def my_pipeline():
        pass

    assert my_pipeline().requirements == {
        "any_requirement",
        *SklearnIntegration.REQUIREMENTS,
    }


def test_pipeline_run_fails_when_required_step_operator_is_missing(
    one_step_pipeline,
):
    """Tests that running a pipeline with a step that requires a custom step
    operator fails if the active stack does not contain this step operator."""

    @step(custom_step_operator="azureml")
    def step_that_requires_step_operator():
        pass

    assert not Repository().active_stack.step_operator
    with pytest.raises(StackValidationError):
        one_step_pipeline(step_that_requires_step_operator()).run()
