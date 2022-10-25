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

from uuid import UUID

from zenml.enums import ArtifactType
from zenml.new_models.base_models import BaseResponseModel

# -------- #
# RESPONSE #
# -------- #


class ArtifactRequestModel(BaseResponseModel):
    """Domain Model representing an artifact."""

    name: str  # Name of the output in the parent step

    parent_step_id: UUID
    producer_step_id: UUID

    type: ArtifactType
    uri: str
    materializer: str
    data_type: str
    is_cached: bool

    # IDs in MLMD - needed for some metadata store methods
    mlmd_id: int
    mlmd_parent_step_id: int
    mlmd_producer_step_id: int


# ------- #
# REQUEST #
# ------- #


class ArtifactResponseModel(BaseResponseModel):
    """Domain Model representing an artifact."""

    name: str  # Name of the output in the parent step

    parent_step_id: UUID
    producer_step_id: UUID

    type: ArtifactType
    uri: str
    materializer: str
    data_type: str
    is_cached: bool

    # IDs in MLMD - needed for some metadata store methods
    mlmd_id: int
    mlmd_parent_step_id: int
    mlmd_producer_step_id: int
