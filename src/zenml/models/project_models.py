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
"""Project model implementation."""

from datetime import datetime
from typing import ClassVar, List, Optional
from uuid import UUID


from zenml.utils.analytics_utils import AnalyticsTrackedModelMixin


class ProjectModel(AnalyticsTrackedModelMixin):
    """Pydantic object representing a project.

    Attributes:
        id: Id of the project.
        created_at: Date when the project was created.
        name: Name of the project.
        description: Optional project description.
    """

    ANALYTICS_FIELDS: ClassVar[List[str]] = [
        "id",
    ]

    id: Optional[UUID] = None
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
