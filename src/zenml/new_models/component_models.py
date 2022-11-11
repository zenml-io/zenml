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

from typing import Any, Dict

from pydantic import BaseModel, Field

from zenml.enums import StackComponentType
from zenml.models.constants import MODEL_NAME_FIELD_MAX_LENGTH
from zenml.new_models.base_models import (
    ShareableRequestModel,
    ShareableResponseModel,
    update,
)

# TODO: Add example schemas and analytics fields


# ---- #
# BASE #
# ---- #
class ComponentBaseModel(BaseModel):
    name: str = Field(
        title="The name of the stack component.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )
    type: StackComponentType = Field(
        title="The type of the stack component.",
    )

    flavor: str = Field(
        title="The flavor of the stack component.",
    )

    configuration: Dict[str, Any] = Field(
        title="The stack component configuration.",
    )


# -------- #
# RESPONSE #
# -------- #


class ComponentResponseModel(ComponentBaseModel, ShareableResponseModel):
    """Model describing the Component."""


# ------- #
# REQUEST #
# ------- #


class ComponentRequestModel(ComponentBaseModel, ShareableRequestModel):
    """ """


# ------ #
# UPDATE #
# ------ #


@update
class ComponentUpdateModel(ComponentRequestModel):
    """"""
