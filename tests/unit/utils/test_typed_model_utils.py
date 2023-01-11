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

from typing import Union

from pydantic import Field

from zenml.utils.typed_model import BaseTypedModel


def test_basetypedmodel_works():
    """Ensure that the type literal attribute is added to the model."""

    class BluePill(BaseTypedModel):
        a: int = 3

    class RedPill(BaseTypedModel):
        b: int = 2

    class TheMatrix(BaseTypedModel):
        choice: Union[BluePill, RedPill] = Field(..., discriminator="type")

    matrix = TheMatrix(choice=RedPill())
    d = matrix.dict()
    new_matrix = TheMatrix.parse_obj(d)
    assert isinstance(new_matrix.choice, RedPill)
    assert new_matrix.choice.type
    assert new_matrix.choice.type.endswith("RedPill")
