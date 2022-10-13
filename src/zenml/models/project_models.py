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
"""Model definitions for code projects."""

from typing import ClassVar, List

from pydantic import Field

from zenml.models.base_models import DomainModel
from zenml.models.constants import (
    MODEL_DESCRIPTIVE_FIELD_MAX_LENGTH,
    MODEL_NAME_FIELD_MAX_LENGTH,
)
from zenml.utils.analytics_utils import AnalyticsTrackedModelMixin


class ProjectModel(DomainModel, AnalyticsTrackedModelMixin):
    """Domain model for projects."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = [
        "id",
    ]

    name: str = Field(
        title="The unique name of the project.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )
    description: str = Field(
        default="",
        title="The description of the project.",
        max_length=MODEL_DESCRIPTIVE_FIELD_MAX_LENGTH,
    )
