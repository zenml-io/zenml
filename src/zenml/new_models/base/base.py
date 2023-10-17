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
from abc import abstractmethod
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr

from zenml.exceptions import HydrationError
from zenml.new_models.base.utils import hydrated_property
from zenml.utils.pydantic_utils import YAMLSerializationMixin

# -------------------- Base Model --------------------


class BaseZenModel(BaseModel, YAMLSerializationMixin):
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


class BaseResponseMetadata(BaseModel):
    """Base metadata model.

    Used as a base class for all metadata models associated with responses.
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


class BaseResponseBody(BaseModel):
    """Base body model.

    Used as a base class for all body models associated with responses.
    """


class BaseResponse(BaseZenModel):
    """Base domain model.

    Used as a base class for all domain models that have the following common
    characteristics:

      * are uniquely identified by a UUID
      * have a dedicated metadata class which features a creation timestamp
            and a last modified timestamp
    """

    # Entity fields
    id: UUID = Field(title="The unique resource id.")

    # Body related field
    body: "BaseResponseBody" = Field(title="The body of the resource.")

    # Metadata related field, method and properties
    metadata: Optional["BaseResponseMetadata"] = Field(
        title="The metadata related to this resource."
    )

    @abstractmethod
    def get_hydrated_version(self) -> "BaseResponse":
        """Abstract method to fetch the hydrated version of the model."""

    @hydrated_property
    def created(self):
        """The created property"""
        return self.metadata.created

    @hydrated_property
    def updated(self):
        """The updated property."""
        return self.metadata.updated

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
