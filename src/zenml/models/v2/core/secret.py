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

from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional, Union
from uuid import UUID

from pydantic import Field, SecretStr

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import (
    GenericFilterOps,
    LogicalOperators,
    SecretScope,
    SorterOps,
)
from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.scoped import (
    WorkspaceScopedFilter,
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
    WorkspaceScopedResponseResources,
)
from zenml.utils.secret_utils import PlainSerializedSecretStr

# ------------------ Request Model ------------------


class SecretRequest(WorkspaceScopedRequest):
    """Request models for secrets."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = ["scope"]

    name: str = Field(
        title="The name of the secret.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    scope: SecretScope = Field(
        SecretScope.WORKSPACE, title="The scope of the secret."
    )
    values: Dict[str, Optional[PlainSerializedSecretStr]] = Field(
        default_factory=dict, title="The values stored in this secret."
    )

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


class SecretUpdate(BaseUpdate):
    """Secret update model."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = ["scope"]

    name: Optional[str] = Field(
        title="The name of the secret.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    scope: Optional[SecretScope] = Field(
        default=None, title="The scope of the secret."
    )
    values: Optional[Dict[str, Optional[PlainSerializedSecretStr]]] = Field(
        title="The values stored in this secret.",
        default=None,
    )

    def get_secret_values_update(self) -> Dict[str, Optional[str]]:
        """Returns a dictionary with the secret values to update.

        Returns:
            A dictionary with the secret values to update.
        """
        if self.values is not None:
            return {
                k: v.get_secret_value() if v is not None else None
                for k, v in self.values.items()
            }

        return {}


# ------------------ Response Model ------------------


class SecretResponseBody(WorkspaceScopedResponseBody):
    """Response body for secrets."""

    scope: SecretScope = Field(
        SecretScope.WORKSPACE, title="The scope of the secret."
    )
    values: Dict[str, Optional[PlainSerializedSecretStr]] = Field(
        default_factory=dict, title="The values stored in this secret."
    )


class SecretResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata for secrets."""


class SecretResponseResources(WorkspaceScopedResponseResources):
    """Class for all resource models associated with the secret entity."""


class SecretResponse(
    WorkspaceScopedResponse[
        SecretResponseBody, SecretResponseMetadata, SecretResponseResources
    ]
):
    """Response model for secrets."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = ["scope"]

    name: str = Field(
        title="The name of the secret.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    def get_hydrated_version(self) -> "SecretResponse":
        """Get the hydrated version of this workspace.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_secret(self.id)

    # Body and metadata properties

    @property
    def scope(self) -> SecretScope:
        """The `scope` property.

        Returns:
            the value of the property.
        """
        return self.get_body().scope

    @property
    def values(self) -> Dict[str, Optional[SecretStr]]:
        """The `values` property.

        Returns:
            the value of the property.
        """
        return self.get_body().values

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

    def add_secret(self, key: str, value: str) -> None:
        """Adds a secret value to the secret.

        Args:
            key: The key of the secret value.
            value: The secret value.
        """
        self.get_body().values[key] = SecretStr(value)

    def remove_secret(self, key: str) -> None:
        """Removes a secret value from the secret.

        Args:
            key: The key of the secret value.
        """
        del self.get_body().values[key]

    def remove_secrets(self) -> None:
        """Removes all secret values from the secret but keep the keys."""
        self.get_body().values = {k: None for k in self.values.keys()}

    def set_secrets(self, values: Dict[str, str]) -> None:
        """Sets the secret values of the secret.

        Args:
            values: The secret values to set.
        """
        self.get_body().values = {k: SecretStr(v) for k, v in values.items()}


# ------------------ Filter Model ------------------


class SecretFilter(WorkspaceScopedFilter):
    """Model to enable advanced filtering of all Secrets."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *WorkspaceScopedFilter.FILTER_EXCLUDE_FIELDS,
        "values",
    ]

    name: Optional[str] = Field(
        default=None,
        description="Name of the secret",
    )

    scope: Optional[Union[SecretScope, str]] = Field(
        default=None,
        description="Scope in which to filter secrets",
        union_mode="left_to_right",
    )

    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Workspace of the Secret",
        union_mode="left_to_right",
    )

    user_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="User that created the Secret",
        union_mode="left_to_right",
    )

    @staticmethod
    def _get_filtering_value(value: Optional[Any]) -> str:
        """Convert the value to a string that can be used for lexicographical filtering and sorting.

        Args:
            value: The value to convert.

        Returns:
            The value converted to string format that can be used for
            lexicographical sorting and filtering.
        """
        if value is None:
            return ""
        str_value = str(value)
        if isinstance(value, datetime):
            str_value = value.strftime("%Y-%m-%d %H:%M:%S")
        return str_value

    def secret_matches(self, secret: SecretResponse) -> bool:
        """Checks if a secret matches the filter criteria.

        Args:
            secret: The secret to check.

        Returns:
            True if the secret matches the filter criteria, False otherwise.
        """
        for filter in self.list_of_filters:
            column_value: Optional[Any] = None
            if filter.column == "workspace_id":
                column_value = secret.workspace.id
            elif filter.column == "user_id":
                column_value = secret.user.id if secret.user else None
            else:
                column_value = getattr(secret, filter.column)

            # Convert the values to strings for lexicographical comparison.
            str_column_value = self._get_filtering_value(column_value)
            str_filter_value = self._get_filtering_value(filter.value)

            # Compare the lexicographical values according to the operation.
            if filter.operation == GenericFilterOps.EQUALS:
                result = str_column_value == str_filter_value
            elif filter.operation == GenericFilterOps.CONTAINS:
                result = str_filter_value in str_column_value
            elif filter.operation == GenericFilterOps.STARTSWITH:
                result = str_column_value.startswith(str_filter_value)
            elif filter.operation == GenericFilterOps.ENDSWITH:
                result = str_column_value.endswith(str_filter_value)
            elif filter.operation == GenericFilterOps.GT:
                result = str_column_value > str_filter_value
            elif filter.operation == GenericFilterOps.GTE:
                result = str_column_value >= str_filter_value
            elif filter.operation == GenericFilterOps.LT:
                result = str_column_value < str_filter_value
            elif filter.operation == GenericFilterOps.LTE:
                result = str_column_value <= str_filter_value

            # Exit early if the result is False for AND, and True for OR
            if self.logical_operator == LogicalOperators.AND:
                if not result:
                    return False
            else:
                if result:
                    return True

        # If we get here, all filters have been checked and the result is
        # True for AND, and False for OR
        if self.logical_operator == LogicalOperators.AND:
            return True
        else:
            return False

    def sort_secrets(
        self, secrets: List[SecretResponse]
    ) -> List[SecretResponse]:
        """Sorts a list of secrets according to the filter criteria.

        Args:
            secrets: The list of secrets to sort.

        Returns:
            The sorted list of secrets.
        """
        column, sort_op = self.sorting_params
        sorted_secrets = sorted(
            secrets,
            key=lambda secret: self._get_filtering_value(
                getattr(secret, column)
            ),
            reverse=sort_op == SorterOps.DESCENDING,
        )

        return sorted_secrets
