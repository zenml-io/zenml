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
from zenml.new_models.base import (
    WorkspaceScopedFilter,
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
    hydrated_property,
    update_model,
)

# ------------------ Request Model ------------------


class SecretRequest(WorkspaceScopedRequest):
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
class SecretUpdate(SecretRequest):
    """Update model for secrets."""


# ------------------ Response Model ------------------
class SecretResponseBody(WorkspaceScopedResponseBody):
    """Response body for secrets."""


class SecretResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata for secrets."""

    scope: SecretScope = Field(
        SecretScope.WORKSPACE, title="The scope of the secret."
    )
    values: Dict[str, Optional[SecretStr]] = Field(
        default_factory=dict, title="The values stored in this secret."
    )


class SecretResponse(WorkspaceScopedResponse):
    """Response model for secrets."""

    name: str = Field(
        title="The name of the secret.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    # Analytics
    ANALYTICS_FIELDS: ClassVar[List[str]] = ["scope"]

    # Body and metadata pair
    body: "SecretResponseBody"
    metadata: Optional["SecretResponseMetadata"]

    def get_hydrated_version(self) -> "SecretResponse":
        """Get the hydrated version of this secret."""
        from zenml.client import Client

        return Client().get_secret(self.id)

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

    # Body and metadata properties
    @hydrated_property
    def scope(self):
        """The `scope` property."""
        return self.metadata.scope

    @hydrated_property
    def values(self):
        """The `values` property."""
        return self.metadata.values


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
    )

    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Workspace of the Secret"
    )

    user_id: Optional[Union[UUID, str]] = Field(
        default=None, description="User that created the Secret"
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

    def secret_matches(self, secret: "SecretResponse") -> bool:
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
        self, secrets: List["SecretResponse"]
    ) -> List["SecretResponse"]:
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
