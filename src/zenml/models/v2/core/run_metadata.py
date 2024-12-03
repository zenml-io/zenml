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
"""Models representing run metadata."""

from typing import Dict, List, Optional
from uuid import UUID

from pydantic import Field, model_validator

from zenml.metadata.metadata_types import MetadataType, MetadataTypeEnum
from zenml.models.v2.base.scoped import (
    WorkspaceScopedRequest,
)
from zenml.models.v2.misc.run_metadata import RunMetadataResource

# ------------------ Request Model ------------------


class RunMetadataRequest(WorkspaceScopedRequest):
    """Request model for run metadata."""

    resources: List[RunMetadataResource] = Field(
        title="The list of resources that this metadata belongs to."
    )
    stack_component_id: Optional[UUID] = Field(
        title="The ID of the stack component that this metadata belongs to.",
        default=None,
    )
    values: Dict[str, "MetadataType"] = Field(
        title="The metadata to be created.",
    )
    types: Dict[str, "MetadataTypeEnum"] = Field(
        title="The types of the metadata to be created.",
    )
    publisher_step_id: Optional[UUID] = Field(
        title="The ID of the step execution that published this metadata.",
        default=None,
    )

    @model_validator(mode="after")
    def validate_values_keys(self) -> "RunMetadataRequest":
        """Validates if the keys in the metadata are properly defined.

        Returns:
            self

        Raises:
            ValueError: if one of the key in the metadata contains `:`
        """
        invalid_keys = [key for key in self.values.keys() if ":" in key]
        if invalid_keys:
            raise ValueError(
                "You can not use colons (`:`) in the key names when you "
                "are creating metadata for your ZenML objects. Please change "
                f"the following keys: {invalid_keys}"
            )
        return self
