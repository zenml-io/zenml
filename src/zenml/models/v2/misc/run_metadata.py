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
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.enums import MetadataResourceTypes
from zenml.metadata.metadata_types import MetadataType


class RunMetadataResource(BaseModel):
    """Utility class to help identify resources to tag metadata to."""

    id: UUID = Field(title="The ID of the resource.")
    type: MetadataResourceTypes = Field(title="The type of the resource.")


class RunMetadataEntry(BaseModel):
    """Utility class to sort/list run metadata entries."""

    value: MetadataType = Field(title="The value for the run metadata entry")
    created: datetime = Field(
        title="The timestamp when this resource was created."
    )
