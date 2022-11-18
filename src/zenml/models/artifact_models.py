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

from pydantic import BaseModel

from zenml.enums import ArtifactType
from zenml.models.base_models import BaseRequestModel, BaseResponseModel, update

# ---- #
# BASE #
# ---- #


class ArtifactBaseModel(BaseModel):
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


# -------- #
# RESPONSE #
# -------- #


class ArtifactResponseModel(ArtifactBaseModel, BaseResponseModel):
    """Domain Model representing an artifact."""


# ------- #
# REQUEST #
# ------- #


class ArtifactRequestModel(ArtifactBaseModel, BaseRequestModel):
    """Domain Model representing an artifact."""


# ------ #
# UPDATE #
# ------ #


@update
class ArtifactUpdateModel(ArtifactRequestModel):
    """"""
