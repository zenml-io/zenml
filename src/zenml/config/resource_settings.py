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
"""Resource settings class used to specify resources for a step."""

from enum import Enum
from typing import Optional, Union

from pydantic import Field, NonNegativeInt, PositiveFloat
from pydantic_settings import SettingsConfigDict

from zenml.config.base_settings import BaseSettings


class ByteUnit(Enum):
    """Enum for byte units."""

    KB = "KB"
    KIB = "KiB"
    MB = "MB"
    MIB = "MiB"
    GB = "GB"
    GIB = "GiB"
    TB = "TB"
    TIB = "TiB"
    PB = "PB"
    PIB = "PiB"

    @property
    def byte_value(self) -> int:
        """Returns the amount of bytes that this unit represents.

        Returns:
            The byte value of this unit.
        """
        return {
            ByteUnit.KB: 10**3,
            ByteUnit.KIB: 1 << 10,
            ByteUnit.MB: 10**6,
            ByteUnit.MIB: 1 << 20,
            ByteUnit.GB: 10**9,
            ByteUnit.GIB: 1 << 30,
            ByteUnit.TB: 10**12,
            ByteUnit.TIB: 1 << 40,
            ByteUnit.PB: 10**15,
            ByteUnit.PIB: 1 << 50,
        }[self]


MEMORY_REGEX = r"^[0-9]+(" + "|".join(unit.value for unit in ByteUnit) + r")$"


class ResourceSettings(BaseSettings):
    """Hardware resource settings.

    Attributes:
        cpu_count: The amount of CPU cores that should be configured.
        gpu_count: The amount of GPUs that should be configured.
        memory: The amount of memory that should be configured.
    """

    cpu_count: Optional[PositiveFloat] = None
    gpu_count: Optional[NonNegativeInt] = None
    memory: Optional[str] = Field(pattern=MEMORY_REGEX, default=None)

    @property
    def empty(self) -> bool:
        """Returns if this object is "empty" (=no values configured) or not.

        Returns:
            `True` if no values were configured, `False` otherwise.
        """
        # To detect whether this config is empty (= no values specified), we
        # check if there are any attributes which are explicitly set to any
        # value other than `None`.
        return len(self.model_dump(exclude_unset=True, exclude_none=True)) == 0

    def get_memory(
        self, unit: Union[str, ByteUnit] = ByteUnit.GB
    ) -> Optional[float]:
        """Gets the memory configuration in a specific unit.

        Args:
            unit: The unit to which the memory should be converted.

        Raises:
            ValueError: If the memory string is invalid.

        Returns:
            The memory configuration converted to the requested unit, or None
            if no memory was configured.
        """
        if not self.memory:
            return None

        if isinstance(unit, str):
            unit = ByteUnit(unit)

        memory = self.memory
        for memory_unit in ByteUnit:
            if memory.endswith(memory_unit.value):
                memory_value = int(memory[: -len(memory_unit.value)])
                return memory_value * memory_unit.byte_value / unit.byte_value
        else:
            # Should never happen due to the regex validation
            raise ValueError(f"Unable to parse memory unit from '{memory}'.")

    model_config = SettingsConfigDict(
        # public attributes are immutable
        frozen=True,
        # prevent extra attributes during model initialization
        extra="forbid",
    )
