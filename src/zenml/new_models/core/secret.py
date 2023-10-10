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
from typing import Dict, Optional, ClassVar, List

from pydantic import Field, SecretStr
from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import SecretScope
from zenml.new_models.base import (
    WorkspaceScopedRequestModel,
    WorkspaceScopedResponseMetadataModel,
    WorkspaceScopedResponseModel,
    update_model,
    hydrated_property,
)


# ------------------ Request Model ------------------


class SecretRequestModel(WorkspaceScopedRequestModel):
    """Request model for secrets."""

    name: str = Field(
        title="The name of the secret.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    scope: SecretScope = Field(
        SecretScope.WORKSPACE, title="The scope of the secret."
    )
    values: Dict[str, Optional[SecretStr]] = Field(
        default_factory=dict, title="The values stored in this secret."
    )

    # Analytics
    ANALYTICS_FIELDS: ClassVar[List[str]] = ["scope"]

    # Helper methods
    @property
    def secret_values(self) -> Dict[str, str]:
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


# ------------------ Update Model ------------------


@update_model
class SecretUpdateModel(SecretRequestModel):
    """Update model for secrets."""


# ------------------ Response Model ------------------


class SecretResponseMetadataModel(WorkspaceScopedResponseMetadataModel):
    """Response metadata model for secrets."""
    scope: SecretScope = Field(
        SecretScope.WORKSPACE, title="The scope of the secret."
    )
    values: Dict[str, Optional[SecretStr]] = Field(
        default_factory=dict, title="The values stored in this secret."
    )


class SecretResponseModel(WorkspaceScopedResponseModel):
    """Response model for secrets."""

    # Entity fields
    name: str = Field(
        title="The name of the secret.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    # Analytics
    ANALYTICS_FIELDS: ClassVar[List[str]] = ["scope"]

    # Metadata related field, method and properties
    metadata: Optional["SecretResponseMetadataModel"]

    def get_hydrated_version(self) -> "SecretResponseModel":
        # TODO: Implement it with the parameterized calls
        from zenml.client import Client

        return Client().get_secret(self.id, hydrate=True)

    @hydrated_property
    def scope(self):
        """The scope property."""
        return self.metadata.scope

    @hydrated_property
    def values(self):
        """The values property."""
        return self.metadata.values

    # Helper methods
    @property
    def secret_values(self) -> Dict[str, str]:
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

    @property
    def has_missing_values(self) -> bool:
        """Returns True if the secret has missing values (i.e. None).

        Values can be missing from a secret for example if the user retrieves a
        secret but does not have the permission to view the secret values.

        Returns:
            True if the secret has any values set to None.
        """
        return any(v is None for v in self.values.values())

    def remove_secrets(self) -> None:
        """Removes all secret values from the secret but keep the keys."""
        self.values = {k: None for k in self.values.keys()}
