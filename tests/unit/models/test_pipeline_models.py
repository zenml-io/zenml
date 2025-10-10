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


import pytest
from pydantic import ValidationError

from zenml.config.pipeline_spec import PipelineSpec
from zenml.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.models import PipelineFilter, PipelineRequest


def test_pipeline_request_model_fails_with_long_name():
    """Test that the pipeline base model fails with long names."""
    long_name = "a" * (STR_FIELD_MAX_LENGTH + 1)
    with pytest.raises(ValidationError):
        PipelineRequest(
            name=long_name,
            docstring="",
            spec=PipelineSpec(steps=[]),
        )


def test_pipeline_request_model_fails_with_long_docstring():
    """Test that the pipeline base model fails with long docstrings."""
    long_docstring = "a" * (TEXT_FIELD_MAX_LENGTH + 1)
    with pytest.raises(ValidationError):
        PipelineRequest(
            name="abc",
            docstring=long_docstring,
            spec=PipelineSpec(steps=[]),
        )


def test_pipeline_filter_by_latest_execution():
    f = PipelineFilter()

    assert not f.filter_by_latest_execution

    f = PipelineFilter(latest_run_status="completed")

    assert f.filter_by_latest_execution

    f = PipelineFilter(latest_run_user="test")

    assert f.filter_by_latest_execution

    # make sure latest pipeline run associated fields are not propagated to base table filters.

    latest_run_fields = [
        "latest_run_status",
        "latest_run_user",
    ]

    assert all(field in f.FILTER_EXCLUDE_FIELDS for field in latest_run_fields)
