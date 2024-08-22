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
"""Integration tests for step run models."""

import inspect
import random
import string
from typing import TYPE_CHECKING

from tests.integration.functional.conftest import step_with_logs
from tests.integration.functional.zen_stores.utils import (
    constant_int_output_test_step,
    int_plus_one_test_step,
)
from zenml.constants import TEXT_FIELD_MAX_LENGTH
from zenml.enums import ExecutionStatus

if TYPE_CHECKING:
    from zenml.client import Client
    from zenml.models import StepRunResponse


def test_step_run_linkage(clean_client: "Client", one_step_pipeline):
    """Integration test for `step.run` property."""
    pipe = one_step_pipeline(constant_int_output_test_step)
    pipe()

    # Non-cached run
    pipeline_run = pipe.model.last_run
    step_run = pipeline_run.steps["constant_int_output_test_step"]

    run = clean_client.get_pipeline_run(step_run.pipeline_run_id)

    assert run == pipeline_run

    # Cached run
    pipe()
    pipeline_run_2 = pipe.model.last_run
    step_run_2 = pipeline_run_2.steps["constant_int_output_test_step"]
    assert step_run_2.status == ExecutionStatus.CACHED


def test_step_run_parent_steps_linkage(
    clean_client: "Client", connected_two_step_pipeline
):
    """Integration test for `step.parent_steps` property."""
    pipeline_instance = connected_two_step_pipeline(
        step_1=constant_int_output_test_step,
        step_2=int_plus_one_test_step,
    )
    pipeline_instance()
    pipeline_run = pipeline_instance.model.last_run
    step_1 = pipeline_run.steps["constant_int_output_test_step"]
    step_2 = pipeline_run.steps["int_plus_one_test_step"]

    parent_steps = [
        clean_client.get_run_step(step_id)
        for step_id in step_1.parent_step_ids
    ]
    assert parent_steps == []

    parent_steps = [
        clean_client.get_run_step(step_id)
        for step_id in step_2.parent_step_ids
    ]
    assert parent_steps == [step_1]


def test_step_run_has_source_code(clean_client, connected_two_step_pipeline):
    """Test that the step run has correct source code."""
    pipeline_instance = connected_two_step_pipeline(
        step_1=constant_int_output_test_step,
        step_2=int_plus_one_test_step,
    )
    pipeline_instance()
    pipeline_run = clean_client.get_pipeline(
        "connected_two_step_pipeline"
    ).runs[0]
    step_1 = pipeline_run.steps["constant_int_output_test_step"]
    step_2 = pipeline_run.steps["int_plus_one_test_step"]
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
        step_1=constant_int_output_test_step,
        step_2=int_plus_one_test_step,
    )
    pipeline_instance()
    pipeline_run = clean_client.get_pipeline(
        "connected_two_step_pipeline"
    ).runs[0]
    step_1 = pipeline_run.steps["constant_int_output_test_step"]
    step_2 = pipeline_run.steps["int_plus_one_test_step"]
    assert len(step_1.source_code) == TEXT_FIELD_MAX_LENGTH
    assert len(step_2.source_code) == TEXT_FIELD_MAX_LENGTH
    assert (
        step_1.source_code
        == random_source[: (TEXT_FIELD_MAX_LENGTH - 3)] + "..."
    )
    assert (
        step_2.source_code
        == random_source[: (TEXT_FIELD_MAX_LENGTH - 3)] + "..."
    )


def test_step_run_has_docstring(clean_client, connected_two_step_pipeline):
    """Test that the step run has correct docstring."""
    pipeline_instance = connected_two_step_pipeline(
        step_1=constant_int_output_test_step,
        step_2=int_plus_one_test_step,
    )
    pipeline_instance()
    pipeline_run = clean_client.get_pipeline(
        "connected_two_step_pipeline"
    ).runs[0]
    step_1 = pipeline_run.steps["constant_int_output_test_step"]
    step_2 = pipeline_run.steps["int_plus_one_test_step"]
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
        step_1=constant_int_output_test_step,
        step_2=int_plus_one_test_step,
    )
    pipeline_instance()
    pipeline_run = clean_client.get_pipeline(
        "connected_two_step_pipeline"
    ).runs[0]
    step_1 = pipeline_run.steps["constant_int_output_test_step"]
    step_2 = pipeline_run.steps["int_plus_one_test_step"]
    assert len(step_1.docstring) == TEXT_FIELD_MAX_LENGTH
    assert len(step_2.docstring) == TEXT_FIELD_MAX_LENGTH
    assert (
        step_1.docstring
        == random_docstring[: (TEXT_FIELD_MAX_LENGTH - 3)] + "..."
    )
    assert (
        step_2.docstring
        == random_docstring[: (TEXT_FIELD_MAX_LENGTH - 3)] + "..."
    )


def test_disabling_step_logs(clean_client: "Client", one_step_pipeline):
    """Test that disabling step logs works."""

    # By default, step logs should be enabled
    step_ = step_with_logs.copy()
    pipe = one_step_pipeline(step_)
    pipe.configure(enable_cache=False)
    pipe()
    _assert_step_logs_enabled(pipe)

    # Test disabling step logs on pipeline level
    pipe.configure(enable_step_logs=False)
    pipe()
    _assert_step_logs_disabled(pipe)

    pipe.configure(enable_step_logs=True)
    pipe()
    _assert_step_logs_enabled(pipe)

    # Test disabling step logs on step level
    # This should override the pipeline level setting
    step_.configure(enable_step_logs=False)
    pipe()
    _assert_step_logs_disabled(pipe)

    step_.configure(enable_step_logs=True)
    pipe()
    _assert_step_logs_enabled(pipe)

    # Test disabling step logs on run level
    # This should override both the pipeline and step level setting
    pipe.with_options(enable_step_logs=False)()
    _assert_step_logs_disabled(pipe)

    pipe.configure(enable_step_logs=False)
    step_.configure(enable_step_logs=False)
    pipe.with_options(enable_step_logs=True)()
    _assert_step_logs_enabled(pipe)


def _assert_step_logs_enabled(pipe, step_name="step_with_logs"):
    """Assert that step logs were enabled in the last run."""
    assert _get_first_step_of_last_run(pipe, step_name=step_name).logs


def _assert_step_logs_disabled(pipe, step_name="step_with_logs"):
    """Assert that step logs were disabled in the last run."""
    assert not _get_first_step_of_last_run(pipe, step_name=step_name).logs


def _get_first_step_of_last_run(pipe, step_name) -> "StepRunResponse":
    """Get the output of the last run."""
    return pipe.model.last_run.steps[step_name]
