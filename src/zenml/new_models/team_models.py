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

from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.models.constants import MODEL_NAME_FIELD_MAX_LENGTH
from zenml.new_models.base_models import BaseRequestModel, BaseResponseModel

if TYPE_CHECKING:
    from zenml.new_models import UserModel

# ---- #
# BASE #
# ---- #


class TeamBaseModel(BaseModel):
    """"""

    name: str = Field(
        title="The unique name of the team.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )


# -------- #
# RESPONSE #
# -------- #


class TeamResponseModel(TeamBaseModel, BaseResponseModel):
    """"""

    users: Optional[List["UserModel"]] = Field(
        title="The list of users within this team."
    )


# ------- #
# REQUEST #
# ------- #


class TeamRequestModel(TeamBaseModel, BaseRequestModel):
    """"""

    users: Optional[List[UUID]] = Field(
        title="The list of users within this team."
    )
