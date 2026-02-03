# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Base classes for Trigger implementations."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, Field

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import TriggerFlavor, TriggerType
from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.scoped import (
    ProjectScopedFilter,
    ProjectScopedRequest,
    ProjectScopedResponseBody,
    ProjectScopedResponseMetadata,
    ProjectScopedResponseResources,
)

if TYPE_CHECKING:
    from zenml.models import PipelineSnapshotResponse, UserResponse


class TriggerBase(BaseModel, ABC):
    """Base class for triggers."""

    name: str = Field(
        max_length=STR_FIELD_MAX_LENGTH,
        description="The name of the trigger.",
    )
    active: bool
    type: TriggerType


class TriggerRequest(ProjectScopedRequest, TriggerBase, ABC):
    """Base class for trigger requests."""

    flavor: TriggerFlavor

    @abstractmethod
    def get_config(self) -> str:
        """Calculates a serialized JSON object for the type-specific fields of the trigger.

        Returns:
            A JSON string representing the trigger-type configuration.
        """
        pass

    @abstractmethod
    def get_extra_fields(self) -> dict[str, Any]:
        """Calculates extra, type-specific fields needed for the trigger.

        Returns:
            A dictionary of extra fields (e.g. {"next_occurrence': "..."}
        """
        pass


class TriggerUpdate(TriggerBase, BaseUpdate, ABC):
    """Base trigger update class."""

    @abstractmethod
    def get_config(self) -> str:
        """Calculates a serialized JSON object for the type-specific fields of the trigger.

        Returns:
            A JSON string representing the trigger-type configuration.
        """
        pass

    @abstractmethod
    def get_extra_fields(self) -> dict[str, Any]:
        """Calculates extra, type-specific fields needed for the trigger.

        Returns:
            A dictionary of extra fields (e.g. {"next_occurrence': "..."}) to be stored in the database.
            IMPORTANT: These fields must match the attributes defined in the `TriggerSchema` ORM class.
        """
        pass


class TriggerResponseBody(ProjectScopedResponseBody, TriggerBase, ABC):
    """Response body for triggers."""

    is_archived: bool
    flavor: TriggerFlavor

    @abstractmethod
    def get_extra_fields(self) -> list[str]:
        """Specify the extra fields needed for the trigger.

        Returns:
            A list of extra fields (e.g. ["next_occurrence"]).
        """
        pass


class TriggerResponseMetadata(ProjectScopedResponseMetadata):
    """Response metadata for triggers."""

    pass


class TriggerResponseResources(ProjectScopedResponseResources):
    """Class for all resource models associated with the schedule entity."""

    snapshots: Optional[list["PipelineSnapshotResponse"]] = None
    user: Optional["UserResponse"] = None


class TriggerFilter(ProjectScopedFilter):
    """Base class for filtering triggers."""

    name: str
    active: bool
    is_archived: bool
    flavor: TriggerFlavor
    type: TriggerType
