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

import pytest

from zenml.post_execution import PipelineRunView, StepView
from zenml.steps import BaseStep, step


@pytest.fixture(scope="function")
def sample_step() -> "BaseStep":
    """Return sample step for testing purposes"""

    @step
    def some_step() -> None:
        pass

    return some_step


@pytest.fixture(scope="function")
def sample_stepview(sample_step: "BaseStep") -> StepView:
    """Return sample step view for testing purposes"""
    return StepView(
        id_=1,
        name=sample_step.__name__,
        parents_step_ids=[0],
        entrypoint_name="sample_entrypoint",
        parameters={},
        metadata_store=None,
    )


@pytest.fixture(scope="function")
def sample_pipeline_run_view(sample_stepview: StepView) -> PipelineRunView:
    """Return sample pipeline run view for testing purposes"""
    sample_pipeline_run_view = PipelineRunView(
        id_=1, name="sample_run_name", executions=None, metadata_store=None
    )
    setattr(sample_pipeline_run_view, "_steps", {"some_step": sample_stepview})
    return sample_pipeline_run_view


def test_get_step_returns_stepview(
    sample_step: "BaseStep",
    sample_stepview: StepView,
    sample_pipeline_run_view: PipelineRunView,
):
    """Test that the `get_step` method returns the correct step_view"""

    returned_sv = sample_pipeline_run_view.get_step(step="some_step")
    assert sample_stepview._id == returned_sv._id
    assert sample_stepview._name == returned_sv._name


def test_get_step_raises_key_error(
    sample_pipeline_run_view: PipelineRunView,
):
    """Test that `get_step()` raises a key error for wrong step names."""

    class NonStep:
        pass

    input_args = [
        {"step": NonStep},  # calling with a class
        {"step": NonStep()},  # calling with a class instance
        {"step": 1234},  # calling kwarg with wrong data type
    ]

    for input_arg in input_args:
        with pytest.raises(KeyError):
            sample_pipeline_run_view.get_step(**input_arg)


def test_get_step_raises_runtime_error(
    sample_pipeline_run_view: PipelineRunView,
):
    """Test that `get_step()` raises a runtime error for invalid kwargs."""
    with pytest.raises(RuntimeError):
        sample_pipeline_run_view.get_step(useless_kwarg="some_pipeline")


def test_get_step_raises_keyerror_exception(
    sample_pipeline_run_view: PipelineRunView,
):
    """Test that the `get_step` method raises runtime error with wrong step."""

    class NonStep:
        pass

    input_args = [
        {"step": "blupusthecat"},  # calling step with wrong step name
        {"name": "blupusthecat"},  # calling kwarg with wrong step name
    ]

    for input_arg in input_args:
        with pytest.raises(KeyError):
            sample_pipeline_run_view.get_step(**input_arg)
