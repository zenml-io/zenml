#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Integration tests for step run post-execution functionality."""

import inspect
import random
import string

from tests.integration.functional.zen_stores.utils import (
    constant_int_output_test_step,
    int_plus_one_test_step,
)
from zenml.post_execution import get_pipeline


def test_step_run_has_source_code(clean_client, connected_two_step_pipeline):
    """Test that the step run has correct source code."""
    pipeline_instance = connected_two_step_pipeline(
        step_1=constant_int_output_test_step(),
        step_2=int_plus_one_test_step(),
    )
    pipeline_instance.run()
    pipeline_run = get_pipeline("connected_two_step_pipeline").runs[0]
    step_1 = pipeline_run.steps[0]
    step_2 = pipeline_run.steps[1]
    assert step_1.source_code == inspect.getsource(
        constant_int_output_test_step.entrypoint
    )
    assert step_2.source_code == inspect.getsource(
        int_plus_one_test_step.entrypoint
    )


def test_step_run_with_too_long_source_code_is_truncated(
    clean_client, connected_two_step_pipeline, mocker
):
    """Test that the step source code gets truncated if it is too long."""

    random_source = "".join(random.choices(string.ascii_uppercase, k=1000000))
    mocker.patch("zenml.steps.base_step.BaseStep.source_code", random_source)
    pipeline_instance = connected_two_step_pipeline(
        step_1=constant_int_output_test_step(),
        step_2=int_plus_one_test_step(),
    )
    pipeline_instance.run()
    pipeline_run = get_pipeline("connected_two_step_pipeline").runs[0]
    step_1 = pipeline_run.steps[0]
    step_2 = pipeline_run.steps[1]
    assert step_1.source_code == random_source[:1000] + "..."
    assert step_2.source_code == random_source[:1000] + "..."


def test_step_run_has_docstring(clean_client, connected_two_step_pipeline):
    """Test that the step run has correct docstring."""
    pipeline_instance = connected_two_step_pipeline(
        step_1=constant_int_output_test_step(),
        step_2=int_plus_one_test_step(),
    )
    pipeline_instance.run()
    pipeline_run = get_pipeline("connected_two_step_pipeline").runs[0]
    step_1 = pipeline_run.steps[0]
    step_2 = pipeline_run.steps[1]
    assert step_1.docstring == constant_int_output_test_step.entrypoint.__doc__
    assert step_2.docstring == int_plus_one_test_step.entrypoint.__doc__


def test_step_run_with_too_long_docstring_is_truncated(
    clean_client, connected_two_step_pipeline, mocker
):
    """Test that the step docstring gets truncated if it is too long."""
    random_docstring = "".join(
        random.choices(string.ascii_uppercase, k=1000000)
    )
    mocker.patch("zenml.steps.base_step.BaseStep.docstring", random_docstring)
    pipeline_instance = connected_two_step_pipeline(
        step_1=constant_int_output_test_step(),
        step_2=int_plus_one_test_step(),
    )
    pipeline_instance.run()
    pipeline_run = get_pipeline("connected_two_step_pipeline").runs[0]
    step_1 = pipeline_run.steps[0]
    step_2 = pipeline_run.steps[1]
    assert step_1.docstring == random_docstring[:1000] + "..."
    assert step_2.docstring == random_docstring[:1000] + "..."
