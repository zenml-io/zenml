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
"""ZenML Server API Models.

These models are only used as REST API representations of the domain models
in the context of different operations, where different fields can be omitted
or even renamed depending on the REST endpoint where they are used. These are
separate from the domain models and should provide conversion logic where
needed.

This separation allows the domain models and REST API to evolve independently
of each other.
"""

from zenml.zen_server.models.pipeline_models import (
    CreatePipelineRequest,
    UpdatePipelineRequest,
)
from zenml.zen_server.models.projects_models import (
    CreateProjectRequest,
    UpdateProjectRequest,
)
from zenml.zen_server.models.stack_models import (
    CreateStackRequest,
    UpdateStackRequest,
)

__all__ = [
    "CreateStackRequest",
    "UpdateStackRequest",
    "CreateProjectRequest",
    "UpdateProjectRequest",
    "CreatePipelineRequest",
    "UpdatePipelineRequest",
]
