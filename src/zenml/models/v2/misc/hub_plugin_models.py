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
"""Models representing ZenML Hub plugins."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from zenml.utils.enum_utils import StrEnum


class PluginStatus(StrEnum):
    """Enum that represents the status of a plugin.

    - PENDING: Plugin is being built
    - FAILED: Plugin build failed
    - AVAILABLE: Plugin is available for installation
    - YANKED: Plugin was yanked and is no longer available
    """

    PENDING = "pending"
    FAILED = "failed"
    AVAILABLE = "available"
    YANKED = "yanked"


class HubUserResponseModel(BaseModel):
    """Model for a ZenML Hub user."""

    id: UUID
    email: str
    username: Optional[str] = None


class HubPluginBaseModel(BaseModel):
    """Base model for a ZenML Hub plugin."""

    name: str
    description: Optional[str] = None
    version: Optional[str] = None
    release_notes: Optional[str] = None
    repository_url: str
    repository_subdirectory: Optional[str] = None
    repository_branch: Optional[str] = None
    repository_commit: Optional[str] = None
    tags: Optional[List[str]] = None
    logo_url: Optional[str] = None


class HubPluginRequestModel(HubPluginBaseModel):
    """Request model for a ZenML Hub plugin."""


class HubPluginResponseModel(HubPluginBaseModel):
    """Response model for a ZenML Hub plugin."""

    id: UUID
    status: PluginStatus
    author: str
    version: str
    index_url: Optional[str] = None
    package_name: Optional[str] = None
    requirements: Optional[List[str]] = None
    build_logs: Optional[str] = None
    created: datetime
    updated: datetime
