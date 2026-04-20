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
"""Util functions for enums."""

from abc import ABCMeta, abstractmethod
from enum import Enum, EnumMeta
from typing import List


class StrEnum(str, Enum):
    """Base enum type for string enum values."""

    def __str__(self) -> str:
        """Returns the enum string value.

        Returns:
            The enum string value.
        """
        return self.value  # type: ignore

    @classmethod
    def names(cls) -> List[str]:
        """Get all enum names as a list of strings.

        Returns:
            A list of all enum names.
        """
        return [c.name for c in cls]

    @classmethod
    def values(cls) -> List[str]:
        """Get all enum values as a list of strings.

        Returns:
            A list of all enum values.
        """
        return [c.value for c in cls]


class ABCEnumMeta(ABCMeta, EnumMeta):
    """Metaclass combining ABCMeta and EnumType."""


class DescribedValuesEnum(StrEnum, metaclass=ABCEnumMeta):
    """Enum abstraction displaying enum descriptions."""

    @classmethod
    @abstractmethod
    def value_description_index(cls) -> dict[str, str]:
        """Helper utility to describe enum values.

        Returns:
            An dictionary with descriptions for each enum value.
        """
        pass

    @classmethod
    def described_values(cls) -> list[dict[str, str | None]]:
        """Helper - returns a list of dictionaries describing the enum values.

        Returns:
            A list of dictionary objects with descriptions.
        """
        idx = cls.value_description_index()

        return [
            {"value": value, "description": idx.get(value)}
            for value in cls.values()
        ]
