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

from zenml.artifacts import DataArtifact
from zenml.materializers.base_materializer import BaseMaterializer


class TestMaterializer(BaseMaterializer):
    ASSOCIATED_TYPES = (int,)


def test_materializer_raises_an_exception_when_asked_to_read_unfamiliar_type():
    """Tests that a materializer fails if it's asked to read the artifact to a
    non-associated type."""
    materializer = TestMaterializer(artifact=DataArtifact())

    with pytest.raises(TypeError):
        materializer.handle_input(data_type=str)


def test_materializer_raises_an_exception_when_asked_to_write_unfamiliar_type():
    """Tests that a materializer fails if it's asked to write data of a
    non-associated type."""
    materializer = TestMaterializer(artifact=DataArtifact())

    with pytest.raises(TypeError):
        materializer.handle_return(data="some_string")
