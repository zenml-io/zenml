#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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

from zenml.utils.enum_utils import StrEnum


def test_enum_utils():
    """Test that `StrEnum` works as expected."""

    class TestEnum(StrEnum):
        """Test enum."""

        A = "aria"
        B = "b"

    assert TestEnum.A.name == "A"
    assert TestEnum.A.value == "aria"
    assert TestEnum.A == "aria"
    assert TestEnum.A == TestEnum.A
    assert TestEnum.A != TestEnum.B
    assert TestEnum.names() == ["A", "B"]
    assert TestEnum.values() == ["aria", "b"]
    assert isinstance(TestEnum.A, TestEnum)
    assert str(TestEnum.A) == "aria"
