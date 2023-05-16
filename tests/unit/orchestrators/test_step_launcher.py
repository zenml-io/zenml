#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
from uuid import uuid4

import pytest

from zenml.config.step_configurations import Step
from zenml.enums import StackComponentType
from zenml.models.pipeline_deployment_models import PipelineDeploymentBaseModel
from zenml.orchestrators.step_launcher import (
    _get_step_name_in_pipeline,
    _get_step_operator,
)
from zenml.stack import Stack


def test_pipeline_step_name_extraction():
    """Tests that the name of the step inside the pipeline gets extracted
    correctly."""
    step_1 = Step.parse_obj(
        {
            "spec": {
                "source": "module.step_class",
                "upstream_steps": [],
                "inputs": {},
            },
            "config": {
                "name": "step_1_name",
            },
        }
    )
    step_2 = Step.parse_obj(
        {
            "spec": {
                "source": "module.step_class",
                "upstream_steps": [],
                "inputs": {},
            },
            "config": {
                "name": "step_2_name",
            },
        }
    )

    deployment = PipelineDeploymentBaseModel.parse_obj(
        {
            "run_name_template": "run_name",
            "pipeline_configuration": {"name": "pipeline_name"},
            "step_configurations": {"step_1": step_1, "step_2": step_2},
        }
    )

    assert (
        _get_step_name_in_pipeline(step_1, deployment=deployment) == "step_1"
    )
    assert (
        _get_step_name_in_pipeline(step_2, deployment=deployment) == "step_2"
    )


def test_step_operator_validation(local_stack, sample_step_operator):
    """Tests that the step operator gets correctly extracted and validated
    from the stack."""

    with pytest.raises(RuntimeError):
        _get_step_operator(
            stack=local_stack, step_operator_name="step_operator"
        )

    components = local_stack.components
    components[StackComponentType.STEP_OPERATOR] = sample_step_operator
    stack_with_step_operator = Stack.from_components(
        id=uuid4(), name="", components=components
    )
    with pytest.raises(RuntimeError):
        _get_step_operator(
            stack=stack_with_step_operator,
            step_operator_name="not_the_step_operator_name",
        )

    with does_not_raise():
        _get_step_operator(
            stack=stack_with_step_operator,
            step_operator_name=sample_step_operator.name,
        )
