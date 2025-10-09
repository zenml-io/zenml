#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Models describing curated visualization resources."""

from uuid import UUID

from pydantic import BaseModel, Field

from zenml.enums import VisualizationResourceTypes


class CuratedVisualizationResource(BaseModel):
    """Resource reference associated with a curated visualization."""

    id: UUID = Field(
        title="The ID of the resource.",
        description="Identifier of the resource associated with the visualization.",
    )
    type: VisualizationResourceTypes = Field(
        title="The type of the resource.",
        description="Classification of the resource associated with the visualization.",
    )
