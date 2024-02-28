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
"""Models representing the link between tags and resources."""

from uuid import UUID

from zenml.enums import TaggableResourceTypes
from zenml.models.v2.base.base import (
    BaseDatedResponseBody,
    BaseIdentifiedResponse,
    BaseRequest,
    BaseResponseMetadata,
    BaseResponseResources,
)

# ------------------ Request Model ------------------


class TagResourceRequest(BaseRequest):
    """Request model for links between tags and resources."""

    tag_id: UUID
    resource_id: UUID
    resource_type: TaggableResourceTypes


# ------------------ Update Model ------------------

# There is no update model for links between tags and resources.

# ------------------ Response Model ------------------


class TagResourceResponseBody(BaseDatedResponseBody):
    """Response body for the links between tags and resources."""

    tag_id: UUID
    resource_id: UUID
    resource_type: TaggableResourceTypes


class TagResourceResponseResources(BaseResponseResources):
    """Class for all resource models associated with the tag resource entity."""


class TagResourceResponse(
    BaseIdentifiedResponse[
        TagResourceResponseBody,
        BaseResponseMetadata,
        TagResourceResponseResources,
    ]
):
    """Response model for the links between tags and resources."""

    @property
    def tag_id(self) -> UUID:
        """The `tag_id` property.

        Returns:
            the value of the property.
        """
        return self.get_body().tag_id

    @property
    def resource_id(self) -> UUID:
        """The `resource_id` property.

        Returns:
            the value of the property.
        """
        return self.get_body().resource_id

    @property
    def resource_type(self) -> TaggableResourceTypes:
        """The `resource_type` property.

        Returns:
            the value of the property.
        """
        return self.get_body().resource_type


# ------------------ Filter Model ------------------

# There is no filter model for links between tags and resources.
