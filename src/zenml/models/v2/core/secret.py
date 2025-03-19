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

from typing import (
    TYPE_CHECKING,
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
)

from pydantic import Field, SecretStr

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.filter import AnyQuery
from zenml.models.v2.base.scoped import (
    UserScopedFilter,
    UserScopedRequest,
    UserScopedResponse,
    UserScopedResponseBody,
    UserScopedResponseMetadata,
    UserScopedResponseResources,
)
from zenml.utils.secret_utils import PlainSerializedSecretStr

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.base_schemas import BaseSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)

# ------------------ Request Model ------------------


class SecretRequest(UserScopedRequest):
    """Request model for secrets."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = ["private"]

    name: str = Field(
        title="The name of the secret.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    private: bool = Field(
        False,
        title="Whether the secret is private. A private secret is only "
        "accessible to the user who created it.",
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
    """Update model for secrets."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = ["private"]

    name: Optional[str] = Field(
        title="The name of the secret.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    private: Optional[bool] = Field(
        default=None,
        title="Whether the secret is private. A private secret is only "
        "accessible to the user who created it.",
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


class SecretResponseBody(UserScopedResponseBody):
    """Response body for secrets."""

    private: bool = Field(
        False,
        title="Whether the secret is private. A private secret is only "
        "accessible to the user who created it.",
    )
    values: Dict[str, Optional[PlainSerializedSecretStr]] = Field(
        default_factory=dict, title="The values stored in this secret."
    )


class SecretResponseMetadata(UserScopedResponseMetadata):
    """Response metadata for secrets."""


class SecretResponseResources(UserScopedResponseResources):
    """Response resources for secrets."""


class SecretResponse(
    UserScopedResponse[
        SecretResponseBody,
        SecretResponseMetadata,
        SecretResponseResources,
    ]
):
    """Response model for secrets."""

    ANALYTICS_FIELDS: ClassVar[List[str]] = ["private"]

    name: str = Field(
        title="The name of the secret.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    def get_hydrated_version(self) -> "SecretResponse":
        """Get the hydrated version of this secret.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_secret(self.id)

    # Body and metadata properties

    @property
    def private(self) -> bool:
        """The `private` property.

        Returns:
            the value of the property.
        """
        return self.get_body().private

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


class SecretFilter(UserScopedFilter):
    """Model to enable advanced secret filtering."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *UserScopedFilter.FILTER_EXCLUDE_FIELDS,
        "values",
    ]

    name: Optional[str] = Field(
        default=None,
        description="Name of the secret",
    )
    private: Optional[bool] = Field(
        default=None,
        description="Whether to filter secrets by private status",
    )

    def apply_filter(
        self,
        query: AnyQuery,
        table: Type["AnySchema"],
    ) -> AnyQuery:
        """Applies the filter to a query.

        Args:
            query: The query to which to apply the filter.
            table: The query table.

        Returns:
            The query with filter applied.
        """
        # The secret user scoping works a bit differently than the other
        # scoped filters. We have to filter out all private secrets that are
        # not owned by the current user.
        if not self.scope_user:
            return super().apply_filter(query=query, table=table)

        scope_user = self.scope_user

        # First we apply the inherited filters without the user scoping
        # applied.
        self.scope_user = None
        query = super().apply_filter(query=query, table=table)
        self.scope_user = scope_user

        # Then we apply the user scoping filter.
        if self.scope_user:
            from sqlmodel import and_, or_

            query = query.where(
                or_(
                    and_(
                        getattr(table, "user_id") == self.scope_user,
                        getattr(table, "private") == True,  # noqa: E712
                    ),
                    getattr(table, "private") == False,  # noqa: E712
                )
            )

        else:
            query = query.where(getattr(table, "private") == False)  # noqa: E712

        return query
