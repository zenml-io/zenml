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
from uuid import UUID

import pytest
from pydantic import ValidationError

from zenml.enums import ArtifactType
from zenml.models.artifact_models import ArtifactBaseModel
from zenml.models.constants import STR_FIELD_MAX_LENGTH

UUID_BASE_STRING = "00000000-0000-0000-0000-000000000000"


def test_artifact_base_model_fails_with_long_name():
    """Test that the artifact base model fails with long strings."""
    with pytest.raises(ValidationError):
        long_name = "a" * (STR_FIELD_MAX_LENGTH + 1)
        ArtifactBaseModel(
            name=long_name,
            version=1,
            parent_step_id=UUID(UUID_BASE_STRING),
            producer_step_id=UUID(UUID_BASE_STRING),
            type=ArtifactType.DATA,
            uri="abc",
            materializer="abc",
            data_type="abc",
            is_cached=False,
        )


def test_artifact_base_model_fails_with_long_uri():
    """Test that the artifact base model fails with long URIs."""
    long_uri = "a" * (STR_FIELD_MAX_LENGTH + 1)
    with pytest.raises(ValidationError):
        ArtifactBaseModel(
            name="abc",
            version=1,
            parent_step_id=UUID(UUID_BASE_STRING),
            producer_step_id=UUID(UUID_BASE_STRING),
            type=ArtifactType.DATA,
            uri=long_uri,
            materializer="abc",
            data_type="abc",
            is_cached=False,
        )


def test_artifact_base_model_works_with_long_materializer():
    """Test that the artifact base model works with long materializer strings."""
    with does_not_raise():
        long_materializer = "a" * (STR_FIELD_MAX_LENGTH + 1)
        ArtifactBaseModel(
            name="abc",
            version=1,
            parent_step_id=UUID(UUID_BASE_STRING),
            producer_step_id=UUID(UUID_BASE_STRING),
            type=ArtifactType.DATA,
            uri="abc",
            materializer=long_materializer,
            data_type="abc",
            is_cached=False,
        )


def test_artifact_base_model_works_with_long_data_type():
    """Test that the artifact base model works with long data type strings."""
    with does_not_raise():
        long_data_type = "a" * (STR_FIELD_MAX_LENGTH + 1)
        ArtifactBaseModel(
            name="abc",
            version=1,
            parent_step_id=UUID(UUID_BASE_STRING),
            producer_step_id=UUID(UUID_BASE_STRING),
            type=ArtifactType.DATA,
            uri="abc",
            materializer="abc",
            data_type=long_data_type,
            is_cached=False,
        )
