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

from pydantic import BaseModel, Field, SecretStr

from zenml.new_models.base.utils import generate_property

# TODO: We can now remove the additional analytics model from the module
# -------------------- Base Model --------------------


class BaseZenModel(BaseModel):
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


class BaseRequestModel(BaseZenModel):
    """Base request model.

    Used as a base class for all request models.
    """


# -------------------- Response Model --------------------


class BaseResponseModelMetadata(BaseModel):
    """Base metadata model.

    Used as a base class for all metadata models associated with domain models.
    Features a creation and update timestamp.
    """

    created: Optional[datetime] = Field(
        title="The timestamp when this resource was created."
    )
    updated: Optional[datetime] = Field(
        title="The timestamp when this resource was last updated."
    )


class BaseResponseModel(BaseZenModel):
    """Base domain model.

    Used as a base class for all domain models that have the following common
    characteristics:

      * are uniquely identified by a UUID
      * have a dedicated metadata class which features a creation timestamp
            and a last modified timestamp
    """

    id: UUID = Field(title="The unique resource id.")

    metadata: Optional[BaseResponseModelMetadata] = Field(
        title="The metadata related to this resource."
    )

    def get_metadata(self) -> "BaseResponseModelMetadata":
        """Abstract method that needs to be implemented to hydrate the instance.

        Each response model has a metadata field. The purpose of this
        is to populate this field by making an additional call to the API.
        """
        return BaseResponseModelMetadata()

    def __new__(cls, *args, **kwargs) -> "BaseResponseModel":
        """A modified version of the __new__ function.

        It automatically looks at the given metadata model and generates
        properties for the class.
        """
        metadata_model = cls.__fields__["metadata"].type_

        for name in metadata_model.__fields__:
            setattr(cls, name, generate_property(name))

        return super().__new__(cls)

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
        if isinstance(other, BaseResponseModel):
            return self.id == other.id
        else:
            return False

    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Fetches the analytics metadata for base response models.

        Returns:
            The analytics metadata.
        """
        metadata = super().get_analytics_metadata()
        metadata["entity_id"] = self.id
        return metadata
