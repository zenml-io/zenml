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


from uuid import UUID

import pytest
from pydantic import ValidationError

from zenml.constants import TEXT_FIELD_MAX_LENGTH
from zenml.enums import ExecutionStatus
from zenml.models.step_run_models import StepRunBaseModel

UUID_BASE_STRING = "00000000-0000-0000-0000-000000000000"


def test_step_run_base_model_fails_with_long_docstring():
    """Test that the step run base model fails with long docstrings."""
    long_docstring_name = "a" * (TEXT_FIELD_MAX_LENGTH + 1)
    with pytest.raises(ValidationError):
        StepRunBaseModel(
            name="abc",
            pipeline_run_id=UUID(UUID_BASE_STRING),
            parent_step_ids=[],
            input_artifacts={},
            status=ExecutionStatus.COMPLETED,
            entrypoint_name="abc",
            parameters={},
            step_configuration={},
            docstring=long_docstring_name,
            mlmd_parent_step_ids=[],
        )
