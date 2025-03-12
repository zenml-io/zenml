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
"""Models representing API keys."""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, ClassVar, List, Optional, Type, Union
from uuid import UUID

from passlib.context import CryptContext
from pydantic import BaseModel, Field

from zenml.constants import (
    STR_FIELD_MAX_LENGTH,
    TEXT_FIELD_MAX_LENGTH,
    ZENML_API_KEY_PREFIX,
)
from zenml.models.v2.base.base import (
    BaseDatedResponseBody,
    BaseIdentifiedResponse,
    BaseRequest,
    BaseResponseMetadata,
    BaseResponseResources,
    BaseUpdate,
)
from zenml.models.v2.base.filter import AnyQuery, BaseFilter
from zenml.utils.string_utils import b64_decode, b64_encode
from zenml.utils.time_utils import utc_now

if TYPE_CHECKING:
    from zenml.models.v2.base.filter import AnySchema
    from zenml.models.v2.core.service_account import ServiceAccountResponse


class APIKey(BaseModel):
    """Encoded model for API keys."""

    id: UUID
    key: str

    @classmethod
    def decode_api_key(cls, encoded_key: str) -> "APIKey":
        """Decodes an API key from a base64 string.

        Args:
            encoded_key: The encoded API key.

        Returns:
            The decoded API key.

        Raises:
            ValueError: If the key is not valid.
        """
        if encoded_key.startswith(ZENML_API_KEY_PREFIX):
            encoded_key = encoded_key[len(ZENML_API_KEY_PREFIX) :]
        try:
            json_key = b64_decode(encoded_key)
            return cls.model_validate_json(json_key)
        except Exception:
            raise ValueError("Invalid API key.")

    def encode(self) -> str:
        """Encodes the API key in a base64 string that includes the key ID and prefix.

        Returns:
            The encoded API key.
        """
        encoded_key = b64_encode(self.model_dump_json())
        return f"{ZENML_API_KEY_PREFIX}{encoded_key}"


# ------------------ Request Model ------------------


class APIKeyRequest(BaseRequest):
    """Request model for API keys."""

    name: str = Field(
        title="The name of the API Key.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    description: Optional[str] = Field(
        default=None,
        title="The description of the API Key.",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )


class APIKeyRotateRequest(BaseRequest):
    """Request model for API key rotation."""

    retain_period_minutes: int = Field(
        default=0,
        title="Number of minutes for which the previous key is still valid "
        "after it has been rotated.",
    )


# ------------------ Update Model ------------------


class APIKeyUpdate(BaseUpdate):
    """Update model for API keys."""

    name: Optional[str] = Field(
        title="The name of the API Key.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    description: Optional[str] = Field(
        title="The description of the API Key.",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    active: Optional[bool] = Field(
        title="Whether the API key is active.",
        default=None,
    )


class APIKeyInternalUpdate(APIKeyUpdate):
    """Update model for API keys used internally."""

    update_last_login: bool = Field(
        default=False,
        title="Whether to update the last login timestamp.",
    )


# ------------------ Response Model ------------------


class APIKeyResponseBody(BaseDatedResponseBody):
    """Response body for API keys."""

    key: Optional[str] = Field(
        default=None,
        title="The API key. Only set immediately after creation or rotation.",
    )
    active: bool = Field(
        default=True,
        title="Whether the API key is active.",
    )
    service_account: "ServiceAccountResponse" = Field(
        title="The service account associated with this API key."
    )


class APIKeyResponseMetadata(BaseResponseMetadata):
    """Response metadata for API keys."""

    description: str = Field(
        default="",
        title="The description of the API Key.",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    retain_period_minutes: int = Field(
        title="Number of minutes for which the previous key is still valid "
        "after it has been rotated.",
    )
    last_login: Optional[datetime] = Field(
        default=None, title="Time when the API key was last used to log in."
    )
    last_rotated: Optional[datetime] = Field(
        default=None, title="Time when the API key was last rotated."
    )


class APIKeyResponseResources(BaseResponseResources):
    """Class for all resource models associated with the APIKey entity."""


class APIKeyResponse(
    BaseIdentifiedResponse[
        APIKeyResponseBody, APIKeyResponseMetadata, APIKeyResponseResources
    ]
):
    """Response model for API keys."""

    name: str = Field(
        title="The name of the API Key.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    _warn_on_response_updates = False

    def get_hydrated_version(self) -> "APIKeyResponse":
        """Get the hydrated version of this API key.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_api_key(
            service_account_id=self.service_account.id,
            api_key_name_or_id=self.id,
        )

    # Helper functions
    def set_key(self, key: str) -> None:
        """Sets the API key and encodes it.

        Args:
            key: The API key value to be set.
        """
        self.get_body().key = APIKey(id=self.id, key=key).encode()

    # Body and metadata properties
    @property
    def key(self) -> Optional[str]:
        """The `key` property.

        Returns:
            the value of the property.
        """
        return self.get_body().key

    @property
    def active(self) -> bool:
        """The `active` property.

        Returns:
            the value of the property.
        """
        return self.get_body().active

    @property
    def service_account(self) -> "ServiceAccountResponse":
        """The `service_account` property.

        Returns:
            the value of the property.
        """
        return self.get_body().service_account

    @property
    def description(self) -> str:
        """The `description` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().description

    @property
    def retain_period_minutes(self) -> int:
        """The `retain_period_minutes` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().retain_period_minutes

    @property
    def last_login(self) -> Optional[datetime]:
        """The `last_login` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().last_login

    @property
    def last_rotated(self) -> Optional[datetime]:
        """The `last_rotated` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().last_rotated


class APIKeyInternalResponse(APIKeyResponse):
    """Response model for API keys used internally."""

    previous_key: Optional[str] = Field(
        default=None,
        title="The previous API key. Only set if the key was rotated.",
    )

    def verify_key(
        self,
        key: str,
    ) -> bool:
        """Verifies a given key against the stored (hashed) key(s).

        Args:
            key: Input key to be verified.

        Returns:
            True if the keys match.
        """
        # even when the hashed key is not set, we still want to execute
        # the hash verification to protect against response discrepancy
        # attacks (https://cwe.mitre.org/data/definitions/204.html)
        key_hash: Optional[str] = None
        context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        if self.key is not None and self.active:
            key_hash = self.key
        result = context.verify(key, key_hash)

        # same for the previous key, if set and if it's still valid
        key_hash = None
        if (
            self.previous_key is not None
            and self.last_rotated is not None
            and self.active
            and self.retain_period_minutes > 0
        ):
            # check if the previous key is still valid
            if utc_now(
                tz_aware=self.last_rotated
            ) - self.last_rotated < timedelta(
                minutes=self.retain_period_minutes
            ):
                key_hash = self.previous_key
        previous_result = context.verify(key, key_hash)

        return result or previous_result


# ------------------ Filter Model ------------------


class APIKeyFilter(BaseFilter):
    """Filter model for API keys."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *BaseFilter.FILTER_EXCLUDE_FIELDS,
        "service_account",
    ]
    CLI_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *BaseFilter.CLI_EXCLUDE_FIELDS,
        "service_account",
    ]

    service_account: Optional[UUID] = Field(
        default=None,
        description="The service account to scope this query to.",
    )
    name: Optional[str] = Field(
        default=None,
        description="Name of the API key",
    )
    description: Optional[str] = Field(
        default=None,
        title="Filter by the API key description.",
    )
    active: Optional[Union[bool, str]] = Field(
        default=None,
        title="Whether the API key is active.",
        union_mode="left_to_right",
    )
    last_login: Optional[Union[datetime, str]] = Field(
        default=None,
        title="Time when the API key was last used to log in.",
        union_mode="left_to_right",
    )
    last_rotated: Optional[Union[datetime, str]] = Field(
        default=None,
        title="Time when the API key was last rotated.",
        union_mode="left_to_right",
    )

    def set_service_account(self, service_account_id: UUID) -> None:
        """Set the service account by which to scope this query.

        Args:
            service_account_id: The service account ID.
        """
        self.service_account = service_account_id

    def apply_filter(
        self,
        query: AnyQuery,
        table: Type["AnySchema"],
    ) -> AnyQuery:
        """Override to apply the service account scope as an additional filter.

        Args:
            query: The query to which to apply the filter.
            table: The query table.

        Returns:
            The query with filter applied.
        """
        query = super().apply_filter(query=query, table=table)

        if self.service_account:
            scope_filter = (
                getattr(table, "service_account_id") == self.service_account
            )
            query = query.where(scope_filter)

        return query
