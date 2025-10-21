#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Utility classes for modeling run metadata."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.enums import MetadataResourceTypes
from zenml.metadata.metadata_types import MetadataType


class RunMetadataResource(BaseModel):
    """Utility class to help identify resources to tag metadata to."""

    id: UUID = Field(title="The ID of the resource.")
    type: MetadataResourceTypes = Field(title="The type of the resource.")

    def __eq__(self, other: Any) -> bool:
        """Overrides equality operator.

        Args:
            other: The object to compare.

        Returns:
            True if the object is equal to the given object. Will always return False if compared to a different type.

        """
        if not isinstance(other, RunMetadataResource):
            return False

        return hash(other) == hash(self)

    def __hash__(self) -> int:
        """Overrides hash operator.

        Returns:
            The hash value of the object.
        """
        return hash(f"{str(self.id)}_{self.type.value}")


class RunMetadataEntry(BaseModel):
    """Utility class to sort/list run metadata entries."""

    value: MetadataType = Field(title="The value for the run metadata entry")
    created: datetime = Field(
        title="The timestamp when this resource was created."
    )
