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
"""Base domain model definitions."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DomainModel(BaseModel):
    """Base domain model.

    Used as a base class for all domain models that have the following common
    characteristics:

      * are uniquely identified by an UUID
      * have a creation timestamp and a last modified timestamp
    """

    def __hash__(self) -> int:
        """Implementation of hash magic method.

        Returns:
            Hash of the UUID.
        """
        return hash((type(self),) + tuple([self.id]))

    def __eq__(self, other: Any) -> bool:
        """Implementation of equality magic method.

        Args:
            other: The other object to compare to.

        Returns:
            True if the other object is of the same type and has the same UUID.
        """
        return self.id == other.id if isinstance(other, DomainModel) else False

    id: UUID = Field(default_factory=uuid4, title="The unique resource id.")
    created: datetime = Field(
        default_factory=datetime.now,
        title="Time when this resource was created.",
    )
    updated: datetime = Field(
        default_factory=datetime.now,
        title="Time when this resource was last updated.",
    )


class UserOwnedDomainModel(DomainModel):
    """Base user-owned domain model.

    Used as a base class for all domain models that are "owned" by a user.
    """

    user: UUID = Field(
        title="The id of the user that created this resource.",
    )


class ProjectScopedDomainModel(UserOwnedDomainModel):
    """Base project-scoped domain model.

    Used as a base class for all domain models that are project-scoped.
    """

    project: UUID = Field(title="The project to which this resource belongs.")


class ShareableProjectScopedDomainModel(ProjectScopedDomainModel):
    """Base shareable project-scoped domain model.

    Used as a base class for all domain models that are project-scoped and are
    shareable.
    """

    is_shared: bool = Field(
        default=False,
        title=(
            "Flag describing if this resource is shared with other users in "
            "the same project."
        ),
    )
