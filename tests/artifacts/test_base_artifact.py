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

from zenml.artifacts import base_artifact
from zenml.materializers.materializer_factory import MaterializerFactory
from zenml.utils.exceptions import ArtifactInterfaceError


@pytest.fixture()
def artifact():
    """Fixture for a base_artifact"""
    return base_artifact.BaseArtifact()


def test_baseartifact_class_has_two_constants(artifact):
    """Check two constants are defined on BaseArtifact class"""
    assert artifact.TYPE_NAME == "BaseArtifact"
    assert isinstance(artifact.PROPERTIES, dict)


def test_reading_materializers_property_returns_a_materializer_factory(
    artifact,
):
    """Test a MaterializerFactor is returned when reading from base_artifact"""
    assert isinstance(artifact.materializers, MaterializerFactory)


def test_baseartifact_materializer_cannot_be_set(artifact):
    """Check that setting the materializer isn't possible"""
    with pytest.raises(ArtifactInterfaceError):
        artifact.materializers = None
