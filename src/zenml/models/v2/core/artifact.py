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
"""Models representing artifacts."""

from typing import TYPE_CHECKING, Dict, List, Optional

from pydantic import BaseModel, Field

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.models.tag_models import TagResponseModel
from zenml.models.v2.base.base import (
    BaseRequest,
    BaseResponse,
    BaseResponseBody,
    BaseResponseMetadata,
)
from zenml.models.v2.base.filter import BaseFilter

if TYPE_CHECKING:
    from zenml.models.v2.core.artifact_version import ArtifactVersionResponse

# ------------------ Request Model ------------------


class ArtifactRequest(BaseRequest):
    """Artifact request model."""

    name: str = Field(
        title="Name of the artifact.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    has_custom_name: bool = Field(
        title="Whether the name is custom (True) or auto-generated (False).",
        default=False,
    )


# ------------------ Update Model ------------------


class ArtifactUpdate(BaseModel):
    """Artifact update model."""

    name: Optional[str] = None
    add_tags: Optional[List[str]] = None
    remove_tags: Optional[List[str]] = None


# ------------------ Response Model ------------------


class ArtifactResponseBody(BaseResponseBody):
    """Response body for artifacts."""

    tags: List[TagResponseModel] = Field(
        title="Tags associated with the model",
    )


class ArtifactResponseMetadata(BaseResponseMetadata):
    """Response metadata for artifacts."""

    has_custom_name: bool = Field(
        title="Whether the name is custom (True) or auto-generated (False).",
        default=False,
    )


class ArtifactResponse(
    BaseResponse[ArtifactResponseBody, ArtifactResponseMetadata]
):
    """Artifact response model."""

    def get_hydrated_version(self) -> "ArtifactResponse":
        """Get the hydrated version of this artifact.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_artifact(self.id)

    name: str = Field(
        title="Name of the output in the parent step.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    # Body and metadata properties
    @property
    def tags(self) -> List[TagResponseModel]:
        """The `tags` property.

        Returns:
            the value of the property.
        """
        return self.get_body().tags

    @property
    def has_custom_name(self) -> bool:
        """The `has_custom_name` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().has_custom_name

    # Helper methods
    @property
    def versions(self) -> Dict[str, "ArtifactVersionResponse"]:
        """Get a list of all versions of this artifact.

        Returns:
            A list of all versions of this artifact.
        """
        from zenml.client import Client

        responses = Client().list_artifact_versions(name=self.name)
        return {str(response.version): response for response in responses}


# ------------------ Filter Model ------------------


class ArtifactFilter(BaseFilter):
    """Model to enable advanced filtering of artifacts."""

    name: Optional[str]
