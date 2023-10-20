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

from zenml.enums import StackComponentType
from zenml.constants import TEXT_FIELD_MAX_LENGTH, STR_FIELD_MAX_LENGTH
from zenml.models.flavor_models import FlavorBaseModel


def test_flavor_base_model_fails_with_long_name():
    """Test that the flavor base model fails with long names."""
    long_name = "a" * (STR_FIELD_MAX_LENGTH + 1)
    with pytest.raises(ValidationError):
        FlavorBaseModel(
            name=long_name,
            type=StackComponentType.ANNOTATOR,
            config_schema="",
            source="",
            integration="",
        )


def test_flavor_base_model_fails_with_long_config_schema():
    """Test that the flavor base model fails with long types."""
    with pytest.raises(ValidationError):
        long_schema = "a" * (TEXT_FIELD_MAX_LENGTH + 1)
        FlavorBaseModel(
            name="abc",
            type=StackComponentType.ANNOTATOR,
            config_schema=long_schema,
            source="",
            integration="",
        )


def test_flavor_base_model_fails_with_long_source():
    """Test that the flavor base model fails with long source strings."""
    with pytest.raises(ValidationError):
        long_source = "a" * (STR_FIELD_MAX_LENGTH + 1)
        FlavorBaseModel(
            name="abc",
            type=StackComponentType.ANNOTATOR,
            config_schema="",
            source=long_source,
            integration="",
        )


def test_flavor_base_model_fails_with_long_integration():
    """Test that the flavor base model fails with long integration strings."""
    with pytest.raises(ValidationError):
        long_integration = "a" * (STR_FIELD_MAX_LENGTH + 1)
        FlavorBaseModel(
            name="abc",
            type=StackComponentType.ANNOTATOR,
            config_schema="",
            source="",
            integration=long_integration,
        )
