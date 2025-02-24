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

from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel

from zenml.enums import ColorVariants

if TYPE_CHECKING:
    from zenml.models import TagRequest


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
