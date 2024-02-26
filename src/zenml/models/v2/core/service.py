#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Models representing Services."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.models.v2.base.scoped import (
    WorkspaceScopedFilter,
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
    WorkspaceScopedTaggableFilter,
)
from zenml.services.service_status import ServiceState
from zenml.services.service_type import ServiceType

if TYPE_CHECKING:
    pass


# ------------------ Request Model ------------------


class ServiceRequest(WorkspaceScopedRequest):
    """Request model for services."""

    name: str = Field(
        title="The name of the service.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    type: ServiceType = Field(
        title="The type of the service.",
    )

    admin_state: ServiceState = Field(
        title="The admin state of the service.",
    )

    configuration: Dict[str, Any] = Field(
        title="The service configuration.",
    )

    labels: Optional[Dict[str, str]] = Field(
        default=None,
        title="The service labels.",
    )

    status: Dict[str, Any] = Field(
        title="The status of the service.",
    )

    endpoint: Optional[Dict[str, Any]] = Field(
        default=None,
        title="The service endpoint.",
    )

    endpoint_url: Optional[str] = Field(
        default=None,
        title="The service endpoint URL.",
    )

    health_check_url: Optional[str] = Field(
        default=None,
        title="The service health check URL.",
    )


# ------------------ Update Model ------------------


class ServiceUpdate(BaseModel):
    """Service update model."""

    name: Optional[str] = None
    admin_state: Optional[ServiceState] = None
    configuration: Optional[Dict[str, Any]] = None
    labels: Optional[Dict[str, str]] = None
    status: Optional[Dict[str, Any]] = None
    endpoint: Optional[Dict[str, Any]] = None
    endpoint_url: Optional[str] = None
    health_check_url: Optional[str] = None


# ------------------ Response Model ------------------


class ServiceResponseBody(WorkspaceScopedResponseBody):
    """Response body for services."""

    type: ServiceType = Field(
        title="The type of the service.",
    )
    labels: Optional[Dict[str, str]] = Field(
        default=None,
        title="The service labels.",
    )
    created: datetime = Field(
        title="The timestamp when this component was created."
    )
    updated: datetime = Field(
        title="The timestamp when this component was last updated.",
    )


class ServiceResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata for services."""

    admin_state: ServiceState = Field(
        title="The admin state of the service.",
    )

    configuration: Dict[str, Any] = Field(
        title="The service configuration.",
    )
    status: Dict[str, Any] = Field(
        title="The status of the service.",
    )
    endpoint: Optional[Dict[str, Any]] = Field(
        default=None,
        title="The service endpoint.",
    )
    endpoint_url: Optional[str] = Field(
        default=None,
        title="The service endpoint URL.",
    )
    health_check_url: Optional[str] = Field(
        default=None,
        title="The service health check URL.",
    )


class ServiceResponse(
    WorkspaceScopedResponse[ServiceResponseBody, ServiceResponseMetadata]
):
    """Response model for services."""

    name: str = Field(
        title="The name of the service.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    def get_hydrated_version(self) -> "ServiceResponse":
        """Get the hydrated version of this artifact.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_service(self.id)

    # Body and metadata properties

    @property
    def type(self) -> ServiceType:
        """The `type` property.

        Returns:
            the value of the property.
        """
        return self.get_body().type

    @property
    def labels(self) -> Optional[Dict[str, str]]:
        """The `labels` property.

        Returns:
            the value of the property.
        """
        return self.get_body().labels

    @property
    def configuration(self) -> Dict[str, Any]:
        """The `configuration` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().configuration

    @property
    def status(self) -> Dict[str, Any]:
        """The `status` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().status

    @property
    def endpoint(self) -> Optional[Dict[str, Any]]:
        """The `endpoint` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().endpoint

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

    @property
    def admin_state(self) -> ServiceState:
        """The `admin_state` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().admin_state

    @property
    def endpoint_url(self) -> Optional[str]:
        """The `endpoint_url` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().endpoint_url

    @property
    def health_check_url(self) -> Optional[str]:
        """The `health_check_url` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().health_check_url


# ------------------ Filter Model ------------------


class ServiceFilter(WorkspaceScopedFilter):
    """Model to enable advanced filtering of services."""

    name: Optional[str] = Field(
        default=None,
        description="Name of the service",
    )
    type: Optional[ServiceType] = Field(
        default=None,
        description="Type of the service",
    )
    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Workspace of the service"
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None, description="User of the service"
    )

    CLI_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *WorkspaceScopedTaggableFilter.CLI_EXCLUDE_FIELDS,
        "workspace_id",
        "user_id",
    ]
