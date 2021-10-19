#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import pytest
from tfx.types.artifact import Property

from zenml.artifacts import data_artifact


@pytest.fixture()
def data_artifact_fixture():
    """Fixture for creating a model_artifact instance"""
    return data_artifact.DataArtifact()


def test_data_artifact_class_has_properties_dictionary_property(data_artifact_fixture):
    """Check two constants are defined on DataArtifact class"""
    assert data_artifact_fixture.TYPE_NAME == "data_artifact"
    assert isinstance(data_artifact_fixture.PROPERTIES, dict)


def test_properties_dict_has_a_split_names_property(data_artifact_fixture):
    """Check the properties dict has a split_names property"""
    assert "split_names" in data_artifact_fixture.PROPERTIES


def test_split_names_property_is_a_property_type(data_artifact_fixture):
    """Check the split_names property is a property type"""
    assert isinstance(
        data_artifact_fixture.PROPERTIES["split_names"], Property)
