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
"""Project Models for the API endpoint definitions."""
from typing import ClassVar, Dict, Optional, Type

from pydantic import BaseModel, Field

from zenml.models import PipelineModel
from zenml.models.constants import MODEL_NAME_FIELD_MAX_LENGTH
from zenml.zen_server.models.base_models import (
    ProjectScopedCreateRequest,
    UpdateRequest,
)


class CreatePipelineRequest(ProjectScopedCreateRequest):
    """Pipeline model for create requests."""

    DOMAIN_MODEL: ClassVar[Type[BaseModel]] = PipelineModel

    name: str = Field(
        title="The name of the pipeline.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )

    docstring: Optional[str]
    configuration: Dict[str, str]


class UpdatePipelineRequest(UpdateRequest):
    """Pipeline model for update requests."""

    DOMAIN_MODEL: ClassVar[Type[BaseModel]] = PipelineModel

    name: Optional[str] = Field(
        title="The name of the pipeline.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )

    docstring: Optional[str]
    # TODO: [server] have another look at this to figure out if adding a
    #  single k:v pair overwrites the existing k:v pairs
    configuration: Optional[Dict[str, str]]
