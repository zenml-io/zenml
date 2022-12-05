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
from hypothesis import given
from hypothesis.strategies import text
from pydantic import ValidationError

from zenml.enums import ArtifactType
from zenml.models.artifact_models import ArtifactBaseModel
from zenml.models.constants import (
    MODEL_METADATA_FIELD_MAX_LENGTH,
    MODEL_NAME_FIELD_MAX_LENGTH,
    MODEL_URI_FIELD_MAX_LENGTH,
)

UUID_BASE_STRING = "00000000-0000-0000-0000-000000000000"


@given(text(min_size=MODEL_NAME_FIELD_MAX_LENGTH + 1))
def test_artifact_base_model_fails_with_long_name(artifact_name):
    """Test that the artifact base model fails with long strings."""
    with pytest.raises(ValidationError):
        ArtifactBaseModel(
            name=artifact_name,
            parent_step_id=UUID(UUID_BASE_STRING),
            producer_step_id=UUID(UUID_BASE_STRING),
            type=ArtifactType.DATA,
            uri="abc",
            materializer="abc",
            data_type="abc",
            is_cached=False,
        )


@given(text(min_size=MODEL_URI_FIELD_MAX_LENGTH + 1))
def test_artifact_base_model_fails_with_long_uri(uri_string):
    """Test that the artifact base model fails with long URIs."""
    with pytest.raises(ValidationError):
        ArtifactBaseModel(
            name="abc",
            parent_step_id=UUID(UUID_BASE_STRING),
            producer_step_id=UUID(UUID_BASE_STRING),
            type=ArtifactType.DATA,
            uri=uri_string,
            materializer="abc",
            data_type="abc",
            is_cached=False,
        )


@given(text(min_size=MODEL_METADATA_FIELD_MAX_LENGTH + 1))
def test_artifact_base_model_fails_with_long_materializer(materializer_string):
    """Test that the artifact base model fails with long materializer strings."""
    with pytest.raises(ValidationError):
        ArtifactBaseModel(
            name="abc",
            parent_step_id=UUID(UUID_BASE_STRING),
            producer_step_id=UUID(UUID_BASE_STRING),
            type=ArtifactType.DATA,
            uri="abc",
            materializer=materializer_string,
            data_type="abc",
            is_cached=False,
        )


@given(text(min_size=MODEL_METADATA_FIELD_MAX_LENGTH + 1))
def test_artifact_base_model_fails_with_long_data_type(data_type):
    """Test that the artifact base model fails with long data type strings."""
    with pytest.raises(ValidationError):
        ArtifactBaseModel(
            name="abc",
            parent_step_id=UUID(UUID_BASE_STRING),
            producer_step_id=UUID(UUID_BASE_STRING),
            type=ArtifactType.DATA,
            uri="abc",
            materializer="abc",
            data_type=data_type,
            is_cached=False,
        )
