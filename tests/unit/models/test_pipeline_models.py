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
from hypothesis import given
from hypothesis.strategies import text
from pydantic import ValidationError

from zenml.config.pipeline_configurations import PipelineSpec
from zenml.models.constants import (
    MODEL_DOCSTRING_FIELD_MAX_LENGTH,
    MODEL_NAME_FIELD_MAX_LENGTH,
)
from zenml.models.pipeline_models import PipelineBaseModel


@given(text(min_size=MODEL_NAME_FIELD_MAX_LENGTH + 1))
def test_pipeline_base_model_fails_with_long_name(generated_name):
    """Test that the pipeline base model fails with long names."""
    with pytest.raises(ValidationError):
        PipelineBaseModel(
            name=generated_name,
            docstring="",
            spec=PipelineSpec(steps=[]),
        )


def test_pipeline_base_model_fails_with_long_docstring():
    """Test that the pipeline base model fails with long docstrings."""
    long_docstring = "a" * (MODEL_DOCSTRING_FIELD_MAX_LENGTH + 1)
    with pytest.raises(ValidationError):
        PipelineBaseModel(
            name="abc",
            docstring=long_docstring,
            spec=PipelineSpec(steps=[]),
        )
