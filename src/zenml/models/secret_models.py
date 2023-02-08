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
"""Models representing secrets."""

from typing import TYPE_CHECKING, Dict, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr

from zenml.models.base_models import (
    WorkspaceScopedRequestModel,
    WorkspaceScopedResponseModel,
    update_model,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH
from zenml.models.filter_models import WorkspaceScopedFilterModel


# ---- #
# BASE #
# ---- #


class SecretBaseModel(BaseModel):
    """Base model for secrets."""

    name: str = Field(
        title="The name of the secret.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    values: Dict[str, Optional[SecretStr]] = Field(
        title="The values stored in this secret."
    )

    @property
    def clear_values(self) -> Dict[str, str]:
        """A dictionary with all un-obfuscated values stored in this secret.

        Returns:
            A dictionary containing the secret's values.
        """
        return {
            k: v.get_secret_value() if v is not None else None
            for k, v in self.values.items()
        }


# -------- #
# RESPONSE #
# -------- #


class SecretResponseModel(SecretBaseModel, WorkspaceScopedResponseModel):
    """Secret response model with user and workspace hydrated."""


# ------ #
# FILTER #
# ------ #


class SecretFilterModel(WorkspaceScopedFilterModel):
    """Model to enable advanced filtering of all Secrets."""

    name: str = Field(
        default=None,
        description="Name of the secret",
    )

    workspace_id: Union[UUID, str] = Field(
        default=None, description="Workspace of the Secret"
    )

    user_id: Union[UUID, str] = Field(
        None, description="User that created the Secret"
    )


# ------- #
# REQUEST #
# ------- #


class SecretRequestModel(SecretBaseModel, WorkspaceScopedRequestModel):
    """Secret request model."""


# ------ #
# UPDATE #
# ------ #


@update_model
class SecretUpdateModel(SecretRequestModel):
    """Secret update model."""
