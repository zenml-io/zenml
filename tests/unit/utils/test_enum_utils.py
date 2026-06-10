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
from zenml.enums import PLATFORM_EVENT_REGISTRY
from zenml.utils.enum_utils import DescribedValuesEnum, StrEnum


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


# Dummy enum for testing
class DummyEnum(DescribedValuesEnum):
    A = "a"
    B = "b"
    C = "c"

    @classmethod
    def value_description_index(cls) -> dict[str, str | None]:
        return {
            cls.A: "Value A description",
            cls.B: "Value B description",
            # C is intentionally missing
        }


def test_described_values_returns_all_values():  # instance doesn't matter
    described = DummyEnum.described_values()
    values = {item["value"] for item in described}

    assert values == {"a", "b", "c"}


def test_missing_descriptions_are_none():
    enum_instance = DummyEnum.A

    described = enum_instance.described_values()
    described_dict = {item["value"]: item["description"] for item in described}

    assert described_dict["a"] == "Value A description"
    assert described_dict["b"] == "Value B description"
    assert described_dict["c"] is None  # Not in index → should be None


def test_pipeline_event_descriptions_cover_all_values():
    for target_enum in PLATFORM_EVENT_REGISTRY.values():
        assert len(target_enum.described_values()) > 1

        for value in target_enum.values():
            target_enum(value)
