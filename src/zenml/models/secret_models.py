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

from typing import ClassVar, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr

from zenml.enums import SecretScope
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

    scope: SecretScope = Field(
        SecretScope.WORKSPACE, title="The scope of the secret."
    )

    values: Dict[str, Optional[SecretStr]] = Field(
        title="The values stored in this secret."
    )

    @property
    def get_clear_values(self) -> Dict[str, str]:
        """A dictionary with all un-obfuscated values stored in this secret.

        The values are returned as strings, not SecretStr. If a value is
        None, it is not included in the returned dictionary. This is to enable
        the use of None values in the update model to indicate that a secret
        value should be deleted.

        Returns:
            A dictionary containing the secret's values.
        """
        return {
            k: v.get_secret_value()
            for k, v in self.values.items()
            if v is not None
        }

    def remove_secrets(self) -> None:
        """Removes all secret values from the secret but keep the keys."""
        self.values = {k: None for k in self.values.keys()}


# -------- #
# RESPONSE #
# -------- #


class SecretResponseModel(SecretBaseModel, WorkspaceScopedResponseModel):
    """Secret response model with user and workspace hydrated."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = ["scope"]


# ------ #
# FILTER #
# ------ #


class SecretFilterModel(WorkspaceScopedFilterModel):
    """Model to enable advanced filtering of all Secrets."""

    name: Optional[str] = Field(
        default=None,
        description="Name of the secret",
    )

    scope: Optional[Union[SecretScope, str]] = Field(
        default=None,
        description="Scope in which to filter secrets",
    )

    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Workspace of the Secret"
    )

    user_id: Optional[Union[UUID, str]] = Field(
        None, description="User that created the Secret"
    )


# ------- #
# REQUEST #
# ------- #


class SecretRequestModel(SecretBaseModel, WorkspaceScopedRequestModel):
    """Secret request model."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = ["scope"]


# ------ #
# UPDATE #
# ------ #


@update_model
class SecretUpdateModel(SecretRequestModel):
    """Secret update model."""
