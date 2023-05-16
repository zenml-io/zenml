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

import pytest

from zenml.enums import ArtifactType
from zenml.exceptions import MaterializerInterfaceError
from zenml.materializers.base_materializer import BaseMaterializer


class TestMaterializer(BaseMaterializer):
    __test__ = False
    ASSOCIATED_TYPES = (int,)


def test_materializer_raises_an_exception_if_associated_types_are_no_classes():
    """Tests that a materializer can only define classes as associated types."""
    with does_not_raise():

        class ValidMaterializer(BaseMaterializer):
            ASSOCIATED_TYPES = (int,)

    with pytest.raises(MaterializerInterfaceError):

        class InvalidMaterializer(BaseMaterializer):
            ASSOCIATED_TYPES = ("not_a_class",)


def test_materializer_raises_an_exception_if_associated_artifact_type_wrong():
    """Tests that a materializer can only define classes as associated types."""
    with does_not_raise():

        class ValidMaterializer(BaseMaterializer):
            ASSOCIATED_TYPES = (int,)
            ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA

    with pytest.raises(MaterializerInterfaceError):

        class InvalidMaterializer(BaseMaterializer):
            ASSOCIATED_TYPES = (int,)
            ASSOCIATED_ARTIFACT_TYPE = "not_an_artifact_type"


def test_validate_type_compatibility():
    """Unit test for `BaseMaterializer.validate_type_compatibility`."""
    materializer = TestMaterializer(uri="")

    with pytest.raises(TypeError):
        materializer.validate_type_compatibility(data_type=str)
