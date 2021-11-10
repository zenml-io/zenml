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
import os

import pytest

from zenml.exceptions import PipelineConfigurationError, PipelineInterfaceError
from zenml.pipelines import pipeline
from zenml.steps import step
from zenml.steps.base_step_config import BaseStepConfig
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
    unconnected_two_step_pipeline, empty_step
):
    """Test that a pipeline can be initialized with args."""
    unconnected_two_step_pipeline(empty_step(), empty_step())


def test_initialize_pipeline_with_kwargs(
    unconnected_two_step_pipeline, empty_step
):
    """Test that a pipeline can be initialized with kwargs."""
    unconnected_two_step_pipeline(step_1=empty_step(), step_2=empty_step())


def test_initialize_pipeline_with_args_and_kwargs(
    unconnected_two_step_pipeline, empty_step
):
    """Test that a pipeline can be initialized with a mix of args and kwargs."""
    unconnected_two_step_pipeline(empty_step(), step_2=empty_step())


def test_initialize_pipeline_with_too_many_args(
    unconnected_two_step_pipeline, empty_step
):
    """Test that pipeline initialization fails when too many args
    are passed."""
    with pytest.raises(PipelineInterfaceError):
        unconnected_two_step_pipeline(empty_step(), empty_step(), empty_step())


def test_initialize_pipeline_with_too_many_args_and_kwargs(
    unconnected_two_step_pipeline, empty_step
):
    """Test that pipeline initialization fails when too many args
    and kwargs are passed."""
    with pytest.raises(PipelineInterfaceError):
        unconnected_two_step_pipeline(
            empty_step(), step_1=empty_step(), step_2=empty_step()
        )


def test_initialize_pipeline_with_missing_key(
    unconnected_two_step_pipeline, empty_step
):
    """Test that pipeline initialization fails when an argument
    is missing."""
    with pytest.raises(PipelineInterfaceError):
        unconnected_two_step_pipeline(step_1=empty_step())


def test_initialize_pipeline_with_unexpected_key(
    unconnected_two_step_pipeline, empty_step
):
    """Test that pipeline initialization fails when an argument
    has an unexpected key."""
    with pytest.raises(PipelineInterfaceError):
        unconnected_two_step_pipeline(
            step_1=empty_step(), step_2=empty_step(), step_3=empty_step()
        )


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
