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
"""Base model definitions."""

from datetime import datetime
from typing import Any, Dict, Generic, Optional, TypeVar
from uuid import UUID

from pydantic import Extra, Field, SecretStr
from pydantic.generics import GenericModel

from zenml.analytics.models import AnalyticsTrackedModelMixin
from zenml.enums import ResponseUpdateStrategy
from zenml.exceptions import HydrationError, IllegalOperationError
from zenml.logger import get_logger
from zenml.utils.pydantic_utils import YAMLSerializationMixin

logger = get_logger(__name__)

# -------------------- Base Model --------------------


class BaseZenModel(YAMLSerializationMixin, AnalyticsTrackedModelMixin):
    """Base model class for all ZenML models.

    This class is used as a base class for all ZenML models. It provides
    functionality for tracking analytics events and proper encoding of
    SecretStr values.
    """

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
    """Base body model."""


class BaseResponseMetadata(BaseZenModel):
    """Base metadata model.

    Used as a base class for all metadata models associated with responses.
    """


class BaseResponseResources(BaseZenModel):
    """Base resources model.

    Used as a base class for all resource models associated with responses.
    """

    class Config:
        """Allows additional resources to be added."""

        extra = Extra.allow


AnyBody = TypeVar("AnyBody", bound=BaseResponseBody)
AnyMetadata = TypeVar("AnyMetadata", bound=BaseResponseMetadata)
AnyResources = TypeVar("AnyResources", bound=BaseResponseResources)


class BaseResponse(
    GenericModel, Generic[AnyBody, AnyMetadata, AnyResources], BaseZenModel
):
    """Base domain model for all responses."""

    # Body and metadata pair
    body: Optional["AnyBody"] = Field(
        default=None, title="The body of the resource."
    )
    metadata: Optional["AnyMetadata"] = Field(
        default=None, title="The metadata related to this resource."
    )
    resources: Optional["AnyResources"] = Field(
        default=None, title="The resources related to this resource."
    )

    _response_update_strategy: ResponseUpdateStrategy = (
        ResponseUpdateStrategy.ALLOW
    )
    _warn_on_response_updates: bool = True

    def _validate_hydrated_version(
        self,
        hydrated_model: "BaseResponse[AnyBody, AnyMetadata, AnyResources]",
    ) -> None:
        """Helper method to validate the values within the hydrated version.

        Args:
            hydrated_model: the hydrated version of the model.

        Raises:
            HydrationError: if the hydrated version has different values set
                for either the name of the body fields and the
                _method_body_mutation is set to ResponseBodyUpdate.DENY.
        """
        # Check whether the metadata exists in the hydrated version
        if hydrated_model.metadata is None:
            raise HydrationError(
                "The hydrated model does not have a metadata field."
            )

        # Check if the name has changed
        if "name" in self.__fields__:
            original_name = getattr(self, "name")
            hydrated_name = getattr(hydrated_model, "name")

            if original_name != hydrated_name:
                if (
                    self._response_update_strategy
                    == ResponseUpdateStrategy.ALLOW
                ):
                    setattr(self, "name", hydrated_name)

                    if self._warn_on_response_updates:
                        logger.warning(
                            f"The name of the entity has changed from "
                            f"`{original_name}` to `{hydrated_name}`."
                        )

                elif (
                    self._response_update_strategy
                    == ResponseUpdateStrategy.IGNORE
                ):
                    if self._warn_on_response_updates:
                        logger.warning(
                            f"Ignoring the name change in the hydrated version "
                            f"of the response: `{original_name}` to "
                            f"`{hydrated_name}`."
                        )
                elif (
                    self._response_update_strategy
                    == ResponseUpdateStrategy.DENY
                ):
                    raise HydrationError(
                        f"Failing the hydration, because there is a change in "
                        f"the name of the entity: `{original_name}` to "
                        f"`{hydrated_name}`."
                    )

        # Check all the fields in the body
        for field in self.get_body().__fields__:
            original_value = getattr(self.get_body(), field)
            hydrated_value = getattr(hydrated_model.get_body(), field)

            if original_value != hydrated_value:
                if (
                    self._response_update_strategy
                    == ResponseUpdateStrategy.ALLOW
                ):
                    setattr(self.get_body(), field, hydrated_value)

                    if self._warn_on_response_updates:
                        logger.warning(
                            f"The field `{field}` in the body of the response "
                            f"has changed from `{original_value}` to "
                            f"`{hydrated_value}`."
                        )

                elif (
                    self._response_update_strategy
                    == ResponseUpdateStrategy.IGNORE
                ):
                    if self._warn_on_response_updates:
                        logger.warning(
                            f"Ignoring the change in the hydrated version of "
                            f"the field `{field}`: `{original_value}` -> "
                            f"`{hydrated_value}`."
                        )
                elif (
                    self._response_update_strategy
                    == ResponseUpdateStrategy.DENY
                ):
                    raise HydrationError(
                        f"Failing the hydration, because there is a change in "
                        f"the field `{field}`: `{original_value}` -> "
                        f"`{hydrated_value}`"
                    )

    def get_hydrated_version(
        self,
    ) -> "BaseResponse[AnyBody, AnyMetadata, AnyResources]":
        """Abstract method to fetch the hydrated version of the model.

        Raises:
            NotImplementedError: in case the method is not implemented.
        """
        raise NotImplementedError(
            "Please implement a `get_hydrated_version` method before "
            "using/hydrating the model."
        )

    def get_body(self) -> "AnyBody":
        """Fetch the body of the entity.

        Returns:
            The body field of the response.

        Raises:
            RuntimeError: If the body was not included in the response.
        """
        if not self.body:
            raise RuntimeError(
                f"Missing response body for {type(self).__name__}."
            )

        return self.body

    def get_metadata(self) -> "AnyMetadata":
        """Fetch the metadata of the entity.

        Returns:
            The metadata field of the response.
        """
        if self.metadata is None:
            # If the metadata is not there, check the class first.
            metadata_type = self.__fields__["metadata"].type_

            if len(metadata_type.__fields__):
                # If the metadata class defines any fields, fetch the metadata
                # through the hydrated version.
                hydrated_version = self.get_hydrated_version()
                self._validate_hydrated_version(hydrated_version)
                self.metadata = hydrated_version.metadata
            else:
                # Otherwise, use the metadata class to create an empty metadata
                # object.
                self.metadata = metadata_type()

        assert self.metadata is not None

        return self.metadata

    def get_resources(self) -> "AnyResources":
        """Fetch the resources related to this entity.

        Returns:
            The resources field of the response.

        Raises:
            RuntimeError: If the resources field was not included in the response.
        """
        if self.resources is None:
            # If the resources are not there, check the class first.
            resources_type = self.__fields__["resources"].type_

            if len(resources_type.__fields__):
                # If the resources class defines any fields, fetch the resources
                # through the hydrated version.
                hydrated_version = self.get_hydrated_version()
                self._validate_hydrated_version(hydrated_version)
                self.resources = hydrated_version.resources
            else:
                # Otherwise, use the resources class to create an empty
                # resources object.
                self.metadata = resources_type()

        if self.resources is None:
            raise RuntimeError(
                f"Missing response resources for {type(self).__name__}."
            )

        return self.resources


class BaseDatedResponseBody(BaseResponseBody):
    """Base body model for entities that track a creation and update timestamp.

    Used as a base class for all body models associated with responses.
    Features a creation and update timestamp.
    """

    created: datetime = Field(
        title="The timestamp when this resource was created."
    )
    updated: datetime = Field(
        title="The timestamp when this resource was last updated."
    )


AnyDatedBody = TypeVar("AnyDatedBody", bound=BaseDatedResponseBody)


class BaseIdentifiedResponse(
    BaseResponse[AnyDatedBody, AnyMetadata, AnyResources],
    Generic[AnyDatedBody, AnyMetadata, AnyResources],
):
    """Base domain model for resources with DB representation."""

    id: UUID = Field(title="The unique resource id.")
    body: Optional["AnyDatedBody"] = Field(
        title="The body of the resource, "
        "containing at the minimum "
        "creation and updated fields."
    )
    metadata: Optional["AnyMetadata"] = Field(
        title="The metadata related to this resource."
    )
    resources: Optional["AnyResources"] = Field(
        title="The resources related to this resource."
    )
    permission_denied: bool = False

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
        if isinstance(other, type(self)):
            return self.id == other.id
        else:
            return False

    def _validate_hydrated_version(
        self,
        hydrated_model: "BaseResponse[AnyDatedBody, AnyMetadata, AnyResources]",
    ) -> None:
        """Helper method to validate the values within the hydrated version.

        Args:
            hydrated_model: the hydrated version of the model.

        Raises:
            HydrationError: if the hydrated version has different values set
                for either the name of the body fields and the
                _method_body_mutation is set to ResponseBodyUpdate.DENY.
        """
        super()._validate_hydrated_version(hydrated_model)

        assert isinstance(hydrated_model, type(self))

        # Check if the ID is the same
        if self.id != hydrated_model.id:
            raise HydrationError(
                "The hydrated version of the model does not have the same id."
            )

    def get_hydrated_version(
        self,
    ) -> "BaseIdentifiedResponse[AnyDatedBody, AnyMetadata, AnyResources]":
        """Abstract method to fetch the hydrated version of the model.

        Raises:
            NotImplementedError: in case the method is not implemented.
        """
        raise NotImplementedError(
            "Please implement a `get_hydrated_version` method before "
            "using/hydrating the model."
        )

    def get_body(self) -> "AnyDatedBody":
        """Fetch the body of the entity.

        Returns:
            The body field of the response.

        Raises:
            IllegalOperationError: If the user lacks permission to access the
                entity represented by this response.
        """
        if self.permission_denied:
            raise IllegalOperationError(
                f"Missing permissions to access {type(self).__name__} with "
                f"ID {self.id}."
            )

        return super().get_body()

    def get_metadata(self) -> "AnyMetadata":
        """Fetch the metadata of the entity.

        Returns:
            The metadata field of the response.

        Raises:
            IllegalOperationError: If the user lacks permission to access this
                entity represented by this response.
        """
        if self.permission_denied:
            raise IllegalOperationError(
                f"Missing permissions to access {type(self).__name__} with "
                f"ID {self.id}."
            )

        return super().get_metadata()

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
    def created(self) -> datetime:
        """The `created` property.

        Returns:
            the value of the property.
        """
        return self.get_body().created

    @property
    def updated(self) -> datetime:
        """The `updated` property.

        Returns:
            the value of the property.
        """
        return self.get_body().updated
