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
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional
from uuid import UUID

from pydantic import Field, SecretStr

from zenml.exceptions import HydrationError
from zenml.models.v2.base.utils import hydrated_property
from zenml.utils.pydantic_utils import YAMLSerializationMixin


# -------------------- Base Model --------------------


class BaseZenModel(YAMLSerializationMixin):
    """Base model class for all ZenML models.

    This class is used as a base class for all ZenML models. It provides
    functionality for tracking analytics events and proper encoding of
    SecretStr values.
    """

    ANALYTICS_FIELDS: ClassVar[List[str]] = []

    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Get the analytics metadata for the model.

        Returns:
            Dict of analytics metadata.
        """
        metadata = {}
        for field_name in self.ANALYTICS_FIELDS:
            metadata[field_name] = getattr(self, field_name, None)
        return metadata

    class Config:
        """Pydantic configuration class."""

        # This is needed to allow the REST client and server to unpack SecretStr
        # values correctly.
        json_encoders = {
            SecretStr: lambda v: v.get_secret_value()
            if v is not None
            else None
        }

        # Allow extras on all models to support forwards and backwards
        # compatibility (e.g. new fields in newer versions of ZenML servers
        # are allowed to be present in older versions of ZenML clients and
        # vice versa).
        extra = "allow"


# -------------------- Request Model --------------------


class BaseRequest(BaseZenModel):
    """Base request model.

    Used as a base class for all request models.
    """


# -------------------- Response Model --------------------


class BaseResponseBody(BaseZenModel):
    """Base body model.

    Used as a base class for all body models associated with responses.
    Features a creation and update timestamp.
    """
    created: Optional[datetime] = Field(
        title="The timestamp when this resource was created.",
        default=None,
    )
    updated: Optional[datetime] = Field(
        title="The timestamp when this resource was last updated.",
        default=None,
    )


class BaseResponseMetadata(BaseZenModel):
    """Base metadata model.

    Used as a base class for all metadata models associated with responses.
    """


class BaseResponse(BaseZenModel):
    """Base domain model."""

    id: UUID = Field(title="The unique resource id.")

    # Body and metadata pair
    body: "BaseResponseBody" = Field(title="The body of the resource.")
    metadata: Optional["BaseResponseMetadata"] = Field(
        title="The metadata related to this resource."
    )

    def get_hydrated_version(self) -> "BaseResponse":
        """Abstract method to fetch the hydrated version of the model.

        Raises:
            NotImplementedError, in case the method is not overriden.
        """
        raise NotImplementedError(
            'Please implement a `get_hydrated_version` method before '
            'using/hydrating the model.'
        )

    # Helper functions
    def __hash__(self) -> int:
        """Implementation of hash magic method.

        Returns:
            Hash of the UUID.
        """
        return hash((type(self),) + tuple([self.id]))

    def __eq__(self, other: Any) -> bool:
        """Implementation of equality magic method.

        Args:
            other: The other object to compare to.

        Returns:
            True if the other object is of the same type and has the same UUID.
        """
        if isinstance(other, BaseResponse):
            return self.id == other.id
        else:
            return False

    def _validate_hydrated_version(
            self, hydrated_model: "BaseResponse"
    ) -> None:
        """Helper method to validate the values within the hydrated version.

        Args:
            hydrated_model: the hydrated version of the model.

        Raises:
            HydrationError: if the hydrated version has different values set
                for the main fields.
        """
        # Check the values of each field except the metadata field
        # TODO: Now that the method is not abstract add more validation
        fields = set(self.__fields__.keys())
        fields.remove("metadata")

        for field in fields:
            original_value = getattr(self, field)
            hydrated_value = getattr(hydrated_model, field)
            if original_value != hydrated_value:
                raise HydrationError(
                    f"The field {field} in the hydrated version of the "
                    f"response model has a different value '{hydrated_value}'"
                    f"than the original value '{original_value}'"
                )

        # Assert that metadata exists in the hydrated version
        if hydrated_model.metadata is None:
            raise HydrationError(
                "The hydrated model does not have a metadata field."
            )

    def hydrate(self) -> None:
        """Generalized method to hydrate a non-hydrated instance of a model.

        Gets only executed if the model has not been hydrated before.
        """
        if self.metadata is None:
            hydrated_version = self.get_hydrated_version()
            self._validate_hydrated_version(hydrated_version)
            self.metadata = hydrated_version.metadata

    # Analytics
    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Fetches the analytics metadata for base response models.

        Returns:
            The analytics metadata.
        """
        metadata = super().get_analytics_metadata()
        metadata["entity_id"] = self.id
        return metadata

    # Body and metadata properties
    @property
    def created(self):
        """The`created` property"""
        return self.body.created

    @property
    def updated(self):
        """The `updated` property."""
        return self.body.updated
