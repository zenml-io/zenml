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
"""Utility functions for tags."""

from typing import TYPE_CHECKING, Any, Optional, Type, TypeVar

from pydantic import BaseModel

from zenml.enums import ColorVariants, TaggableResourceTypes

if TYPE_CHECKING:
    from zenml.models import TagRequest
    from zenml.zen_stores.schemas.base_schemas import BaseSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)


class Tag(BaseModel):
    """A tag is a label that can be applied to a pipeline run."""

    name: str
    color: Optional[ColorVariants] = None
    singleton: Optional[bool] = None
    hierarchical: Optional[bool] = None

    def to_request(self) -> "TagRequest":
        """Convert the tag to a TagRequest.

        Returns:
            The tag as a TagRequest.
        """
        from zenml.models import TagRequest

        request = TagRequest(name=self.name)
        if self.color is not None:
            request.color = self.color

        if self.singleton is not None:
            request.singleton = self.singleton
        return request


def get_schema_from_resource_type(
    resource_type: TaggableResourceTypes,
) -> Any:
    """Get the schema for a resource type.

    Args:
        resource_type: The type of the resource.

    Returns:
        The schema for the resource type.
    """
    from zenml.zen_stores.schemas import (
        ArtifactSchema,
        ArtifactVersionSchema,
        ModelSchema,
        ModelVersionSchema,
        PipelineRunSchema,
        PipelineSchema,
        RunTemplateSchema,
    )

    resource_type_to_schema_mapping = {
        TaggableResourceTypes.ARTIFACT: ArtifactSchema,
        TaggableResourceTypes.ARTIFACT_VERSION: ArtifactVersionSchema,
        TaggableResourceTypes.MODEL: ModelSchema,
        TaggableResourceTypes.MODEL_VERSION: ModelVersionSchema,
        TaggableResourceTypes.PIPELINE: PipelineSchema,
        TaggableResourceTypes.PIPELINE_RUN: PipelineRunSchema,
        TaggableResourceTypes.RUN_TEMPLATE: RunTemplateSchema,
    }

    return resource_type_to_schema_mapping[resource_type]


def get_resource_type_from_schema(
    schema: Type["AnySchema"],
) -> TaggableResourceTypes:
    """Get the resource type from a schema.

    Args:
        schema: The schema of the resource.

    Returns:
        The resource type for the schema.
    """
    from zenml.zen_stores.schemas import (
        ArtifactSchema,
        ArtifactVersionSchema,
        ModelSchema,
        ModelVersionSchema,
        PipelineRunSchema,
        PipelineSchema,
        RunTemplateSchema,
    )

    schema_to_resource_type_mapping = {
        ArtifactSchema: TaggableResourceTypes.ARTIFACT,
        ArtifactVersionSchema: TaggableResourceTypes.ARTIFACT_VERSION,
        ModelSchema: TaggableResourceTypes.MODEL,
        ModelVersionSchema: TaggableResourceTypes.MODEL_VERSION,
        PipelineSchema: TaggableResourceTypes.PIPELINE,
        PipelineRunSchema: TaggableResourceTypes.PIPELINE_RUN,
        RunTemplateSchema: TaggableResourceTypes.RUN_TEMPLATE,
    }
    return schema_to_resource_type_mapping[schema]
