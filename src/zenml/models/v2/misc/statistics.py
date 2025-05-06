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
"""Models representing statistics."""

from pydantic import Field

from zenml.models.v2.base.base import (
    BaseZenModel,
)


class ProjectStatistics(BaseZenModel):
    """Project statistics."""

    pipelines: int = Field(
        title="The number of pipelines.",
    )
    runs: int = Field(
        title="The number of pipeline runs.",
    )


class ServerStatistics(BaseZenModel):
    """Server statistics."""

    stacks: int = Field(
        title="The number of stacks.",
    )
    components: int = Field(
        title="The number of components.",
    )
    projects: int = Field(
        title="The number of projects.",
    )
