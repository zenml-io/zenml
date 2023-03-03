#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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

from pydantic import BaseModel

from tests.unit.test_general import _test_materializer
from zenml.materializers.pydantic_materializer import PydanticMaterializer


def test_pydantic_materializer():
    """Test the pydantic materializer."""

    class MyModel(BaseModel):
        a: int = 1
        b: int = 2

    model = MyModel(a=2, b=3)

    result = _test_materializer(
        step_output_type=MyModel,
        materializer_class=PydanticMaterializer,
        step_output=model,
    )
    assert result.a == 2
    assert result.b == 3
