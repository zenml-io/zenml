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
"""Integration tests for pipeline post-execution functionality."""

from uuid import uuid4

import pytest

from tests.integration.functional.conftest import (
    constant_int_output_test_step,
    int_plus_one_test_step,
    int_plus_two_test_step,
)
from zenml.pipelines.base_pipeline import BasePipeline
from zenml.post_execution.pipeline import (
    PipelineClassView,
    PipelineView,
    get_pipeline,
    get_pipelines,
)


def test_get_pipelines(clean_client, connected_two_step_pipeline):
    """Integration test for the `get_pipelines` function."""
    pipeline_instance = connected_two_step_pipeline(
        step_1=constant_int_output_test_step(),
        step_2=int_plus_one_test_step(),
    )
    assert len(get_pipelines()) == 0
    pipeline_instance.run()
    pipelines = get_pipelines()
    assert len(pipelines) == 1
    assert pipelines[0].name == "connected_two_step_pipeline"


def test_get_pipeline(clean_client, connected_two_step_pipeline):
    """Integration test for the `get_pipeline` function."""
    pipeline_instance = connected_two_step_pipeline(
        step_1=constant_int_output_test_step(),
        step_2=int_plus_one_test_step(),
    )

    # Test getting non-existent pipeline returns None
    assert get_pipeline("connected_two_step_pipeline") is None
    assert get_pipeline(connected_two_step_pipeline) is None
    assert get_pipeline(pipeline_instance) is None

    pipeline_instance.run()

    # Test getting existing pipeline by name
    pipeline1 = get_pipeline("connected_two_step_pipeline")
    assert isinstance(pipeline1, PipelineClassView)
    assert pipeline1.name == "connected_two_step_pipeline"

    # Test getting existing pipeline by class
    pipeline2 = get_pipeline(connected_two_step_pipeline)
    assert pipeline2 == pipeline1

    # Test getting existing pipeline by instance
    pipeline3 = get_pipeline(pipeline_instance)
    assert isinstance(pipeline3, PipelineView)
    assert pipeline3.name == "connected_two_step_pipeline"


class NotAPipeline:
    """This is not a pipeline and cannot be used as arg of `get_pipeline()`."""


@pytest.mark.parametrize(
    "wrong_pipeline_type",
    [
        3,
        True,
        3.14,
        ["list_of_pipelines"],
        {"dict_of_pipelines": "yes"},
        NotAPipeline,
        NotAPipeline(),
    ],
)
def test_get_pipeline_fails_for_wrong_type(clean_client, wrong_pipeline_type):
    """Test that `get_pipeline` fails for wrong input types."""
    with pytest.raises(RuntimeError):
        get_pipeline(wrong_pipeline_type)


def test_get_runs(clean_client, connected_two_step_pipeline):
    """Unit test for `pipeline.get_runs()`.

    Tests that:
    - `pipeline_class.get_runs()` returns all runs of this pipeline name/class
        and `runs[0]` is the most recent run of any version of this pipeline
    - `pipeline_instance.get_runs()` returns all runs of this pipeline instance
        and `runs[0]` is the most recent run of this pipeline instance

    When calling `pipeline_instance.get_runs()`, only the runs for this
    pipeline instance should be included. However, when calling
    `get_pipeline(...).runs`, all runs of all versions should be included.

    To test this, we create two different pipeline versions, A and B. We then
    run them in the following order: A -> A -> B -> B -> A -> B.
    """

    with pytest.raises(RuntimeError):
        connected_two_step_pipeline.get_runs()

    pipeline_instance_a: BasePipeline = connected_two_step_pipeline(
        step_1=constant_int_output_test_step(),
        step_2=int_plus_one_test_step(),
    )
    with pytest.raises(RuntimeError):
        pipeline_instance_a.get_runs()

    pipeline_instance_b: BasePipeline = connected_two_step_pipeline(
        step_1=constant_int_output_test_step(),
        step_2=int_plus_two_test_step(),
    )
    with pytest.raises(RuntimeError):
        pipeline_instance_b.get_runs()

    # A
    run_name_a = str(uuid4())
    pipeline_instance_a.run(run_name=run_name_a)
    assert len(connected_two_step_pipeline.get_runs()) == 1
    assert len(pipeline_instance_a.get_runs()) == 1
    assert connected_two_step_pipeline.get_runs()[0].name == run_name_a
    assert pipeline_instance_a.get_runs()[0].name == run_name_a
    with pytest.raises(RuntimeError):
        pipeline_instance_b.get_runs()

    # A -> A
    run_name_a = str(uuid4())
    pipeline_instance_a.run(run_name=run_name_a)
    assert len(connected_two_step_pipeline.get_runs()) == 2
    assert len(pipeline_instance_a.get_runs()) == 2
    assert connected_two_step_pipeline.get_runs()[0].name == run_name_a
    assert pipeline_instance_a.get_runs()[0].name == run_name_a
    with pytest.raises(RuntimeError):
        pipeline_instance_b.get_runs()

    # A -> A -> B
    run_name_b = str(uuid4())
    pipeline_instance_b.run(run_name=run_name_b)
    assert len(connected_two_step_pipeline.get_runs()) == 3
    assert len(pipeline_instance_a.get_runs()) == 2
    assert len(pipeline_instance_b.get_runs()) == 1
    assert connected_two_step_pipeline.get_runs()[0].name == run_name_b
    assert pipeline_instance_a.get_runs()[0].name == run_name_a
    assert pipeline_instance_b.get_runs()[0].name == run_name_b

    # A -> A -> B -> B
    run_name_b = str(uuid4())
    pipeline_instance_b.run(run_name=run_name_b)
    assert len(connected_two_step_pipeline.get_runs()) == 4
    assert len(pipeline_instance_a.get_runs()) == 2
    assert len(pipeline_instance_b.get_runs()) == 2
    assert connected_two_step_pipeline.get_runs()[0].name == run_name_b
    assert pipeline_instance_a.get_runs()[0].name == run_name_a
    assert pipeline_instance_b.get_runs()[0].name == run_name_b

    # A -> A -> B -> B -> A
    run_name_a = str(uuid4())
    pipeline_instance_a.run(run_name=run_name_a)
    assert len(connected_two_step_pipeline.get_runs()) == 5
    assert len(pipeline_instance_a.get_runs()) == 3
    assert len(pipeline_instance_b.get_runs()) == 2
    assert connected_two_step_pipeline.get_runs()[0].name == run_name_a
    assert pipeline_instance_a.get_runs()[0].name == run_name_a
    assert pipeline_instance_b.get_runs()[0].name == run_name_b

    # A -> A -> B -> B -> A -> B
    run_name_b = str(uuid4())
    pipeline_instance_b.run(run_name=run_name_b)
    assert len(connected_two_step_pipeline.get_runs()) == 6
    assert len(pipeline_instance_a.get_runs()) == 3
    assert len(pipeline_instance_b.get_runs()) == 3
    assert connected_two_step_pipeline.get_runs()[0].name == run_name_b
    assert pipeline_instance_a.get_runs()[0].name == run_name_a
    assert pipeline_instance_b.get_runs()[0].name == run_name_b
