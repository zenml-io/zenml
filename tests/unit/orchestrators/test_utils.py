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

import json

import pytest
from tfx.orchestration.portable.data_types import ExecutionInfo
from tfx.proto.orchestration.pipeline_pb2 import PipelineInfo

from zenml.orchestrators.utils import get_cache_status
from zenml.repository import Repository
from zenml.steps.utils import (
    INTERNAL_EXECUTION_PARAMETER_PREFIX,
    PARAM_PIPELINE_PARAMETER_NAME,
)


def test_get_cache_status_raises_no_error_when_none_passed():
    """Ensure get_cache_status raises no error when None is passed."""
    try:
        get_cache_status(None)
    except AttributeError:
        pytest.fail("`get_cache_status()` raised an `AttributeError`")


def test_get_cache_status_works_when_running_pipeline_twice():
    """Check that steps are cached when a pipeline is run twice successively."""
    from zenml.pipelines import pipeline
    from zenml.steps import step

    @step
    def step_one():
        return 1

    @pipeline
    def some_pipeline(
        step_one,
    ):
        step_one()

    pipeline = some_pipeline(
        step_one=step_one(),
    )

    pipeline.run()
    pipeline.run()

    pipeline = Repository().get_pipeline("some_pipeline")
    first_run = pipeline.runs[-2]
    second_run = pipeline.runs[-1]

    step_name_param = (
        INTERNAL_EXECUTION_PARAMETER_PREFIX + PARAM_PIPELINE_PARAMETER_NAME
    )
    properties_param = json.dumps("step_one")
    pipeline_id = pipeline.name
    first_run_id = first_run.name
    second_run_id = second_run.name
    first_run_execution_object = ExecutionInfo(
        exec_properties={step_name_param: properties_param},
        pipeline_info=PipelineInfo(id=pipeline_id),
        pipeline_run_id=first_run_id,
    )
    second_run_execution_object = ExecutionInfo(
        exec_properties={step_name_param: properties_param},
        pipeline_info=PipelineInfo(id=pipeline_id),
        pipeline_run_id=second_run_id,
    )

    assert get_cache_status(first_run_execution_object) is False
    assert get_cache_status(second_run_execution_object) is True
