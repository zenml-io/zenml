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
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)
from uuid import UUID

from pydantic import ConfigDict, Field
from sqlalchemy.sql.elements import ColumnElement

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import ServiceState
from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.scoped import (
    ProjectScopedFilter,
    ProjectScopedRequest,
    ProjectScopedResponse,
    ProjectScopedResponseBody,
    ProjectScopedResponseMetadata,
    ProjectScopedResponseResources,
)
from zenml.models.v2.misc.service import ServiceType

if TYPE_CHECKING:
    from zenml.models.v2.core.model_version import ModelVersionResponse
    from zenml.models.v2.core.pipeline_run import PipelineRunResponse
    from zenml.zen_stores.schemas import BaseSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)

# ------------------ Request Model ------------------


class ServiceRequest(ProjectScopedRequest):
    """Request model for services."""

    name: str = Field(
        title="The name of the service.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    service_type: ServiceType = Field(
        title="The type of the service.",
    )
    service_source: Optional[str] = Field(
        title="The class of the service.",
        description="The fully qualified class name of the service "
        "implementation.",
        default=None,
    )
    admin_state: Optional[ServiceState] = Field(
        title="The admin state of the service.",
        description="The administrative state of the service, e.g., ACTIVE, "
        "INACTIVE.",
        default=None,
    )
    config: Dict[str, Any] = Field(
        title="The service config.",
        description="A dictionary containing configuration parameters for the "
        "service.",
    )
    labels: Optional[Dict[str, str]] = Field(
        default=None,
        title="The service labels.",
    )
    status: Optional[Dict[str, Any]] = Field(
        default=None,
        title="The status of the service.",
    )
    endpoint: Optional[Dict[str, Any]] = Field(
        default=None,
        title="The service endpoint.",
    )
    prediction_url: Optional[str] = Field(
        default=None,
        title="The service endpoint URL.",
    )
    health_check_url: Optional[str] = Field(
        default=None,
        title="The service health check URL.",
    )
    model_version_id: Optional[UUID] = Field(
        default=None,
        title="The model version id linked to the service.",
    )
    pipeline_run_id: Optional[UUID] = Field(
        default=None,
        title="The pipeline run id linked to the service.",
    )

    # TODO: In Pydantic v2, the `model_` is a protected namespaces for all
    #  fields defined under base models. If not handled, this raises a warning.
    #  It is possible to suppress this warning message with the following
    #  configuration, however the ultimate solution is to rename these fields.
    #  Even though they do not cause any problems right now, if we are not
    #  careful we might overwrite some fields protected by pydantic.
    model_config = ConfigDict(protected_namespaces=())


# ------------------ Update Model ------------------


class ServiceUpdate(BaseUpdate):
    """Update model for stack components."""

    name: Optional[str] = Field(
        None,
        title="The name of the service.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    admin_state: Optional[ServiceState] = Field(
        None,
        title="The admin state of the service.",
        description="The administrative state of the service, e.g., ACTIVE, "
        "INACTIVE.",
    )
    service_source: Optional[str] = Field(
        None,
        title="The class of the service.",
        description="The fully qualified class name of the service "
        "implementation.",
    )
    status: Optional[Dict[str, Any]] = Field(
        None,
        title="The status of the service.",
    )
    endpoint: Optional[Dict[str, Any]] = Field(
        None,
        title="The service endpoint.",
    )
    prediction_url: Optional[str] = Field(
        None,
        title="The service endpoint URL.",
    )
    health_check_url: Optional[str] = Field(
        None,
        title="The service health check URL.",
    )
    labels: Optional[Dict[str, str]] = Field(
        default=None,
        title="The service labels.",
    )
    model_version_id: Optional[UUID] = Field(
        default=None,
        title="The model version id linked to the service.",
    )

    # TODO: In Pydantic v2, the `model_` is a protected namespaces for all
    #  fields defined under base models. If not handled, this raises a warning.
    #  It is possible to suppress this warning message with the following
    #  configuration, however the ultimate solution is to rename these fields.
    #  Even though they do not cause any problems right now, if we are not
    #  careful we might overwrite some fields protected by pydantic.
    model_config = ConfigDict(protected_namespaces=())


# ------------------ Response Model ------------------


class ServiceResponseBody(ProjectScopedResponseBody):
    """Response body for services."""

    service_type: ServiceType = Field(
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
    state: Optional[ServiceState] = Field(
        default=None,
        title="The current state of the service.",
    )


class ServiceResponseMetadata(ProjectScopedResponseMetadata):
    """Response metadata for services."""

    service_source: Optional[str] = Field(
        title="The class of the service.",
    )
    admin_state: Optional[ServiceState] = Field(
        title="The admin state of the service.",
    )
    config: Dict[str, Any] = Field(
        title="The service config.",
    )
    status: Optional[Dict[str, Any]] = Field(
        title="The status of the service.",
    )
    endpoint: Optional[Dict[str, Any]] = Field(
        default=None,
        title="The service endpoint.",
    )
    prediction_url: Optional[str] = Field(
        default=None,
        title="The service endpoint URL.",
    )
    health_check_url: Optional[str] = Field(
        default=None,
        title="The service health check URL.",
    )


class ServiceResponseResources(ProjectScopedResponseResources):
    """Class for all resource models associated with the service entity."""

    pipeline_run: Optional["PipelineRunResponse"] = Field(
        default=None,
        title="The pipeline run associated with the service.",
    )
    model_version: Optional["ModelVersionResponse"] = Field(
        default=None,
        title="The model version associated with the service.",
    )

    # TODO: In Pydantic v2, the `model_` is a protected namespaces for all
    #  fields defined under base models. If not handled, this raises a warning.
    #  It is possible to suppress this warning message with the following
    #  configuration, however the ultimate solution is to rename these fields.
    #  Even though they do not cause any problems right now, if we are not
    #  careful we might overwrite some fields protected by pydantic.
    model_config = ConfigDict(protected_namespaces=())


class ServiceResponse(
    ProjectScopedResponse[
        ServiceResponseBody, ServiceResponseMetadata, ServiceResponseResources
    ]
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
    def service_type(self) -> ServiceType:
        """The `service_type` property.

        Returns:
            the value of the property.
        """
        return self.get_body().service_type

    @property
    def labels(self) -> Optional[Dict[str, str]]:
        """The `labels` property.

        Returns:
            the value of the property.
        """
        return self.get_body().labels

    @property
    def service_source(self) -> Optional[str]:
        """The `service_source` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().service_source

    @property
    def config(self) -> Dict[str, Any]:
        """The `config` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().config

    @property
    def status(self) -> Optional[Dict[str, Any]]:
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
    def admin_state(self) -> Optional[ServiceState]:
        """The `admin_state` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().admin_state

    @property
    def prediction_url(self) -> Optional[str]:
        """The `prediction_url` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().prediction_url

    @property
    def health_check_url(self) -> Optional[str]:
        """The `health_check_url` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().health_check_url

    @property
    def state(self) -> Optional[ServiceState]:
        """The `state` property.

        Returns:
            the value of the property.
        """
        return self.get_body().state

    @property
    def pipeline_run(self) -> Optional["PipelineRunResponse"]:
        """The `pipeline_run` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().pipeline_run

    @property
    def model_version(self) -> Optional["ModelVersionResponse"]:
        """The `model_version` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().model_version


# ------------------ Filter Model ------------------


class ServiceFilter(ProjectScopedFilter):
    """Model to enable advanced filtering of services."""

    name: Optional[str] = Field(
        default=None,
        description="Name of the service. Use this to filter services by "
        "their name.",
    )
    type: Optional[str] = Field(
        default=None,
        description="Type of the service. Filter services by their type.",
    )
    flavor: Optional[str] = Field(
        default=None,
        description="Flavor of the service. Use this to filter services by "
        "their flavor.",
    )
    config: Optional[bytes] = Field(
        default=None,
        description="Config of the service. Use this to filter services by "
        "their config.",
    )
    pipeline_name: Optional[str] = Field(
        default=None,
        description="Pipeline name responsible for deploying the service",
    )
    pipeline_step_name: Optional[str] = Field(
        default=None,
        description="Pipeline step name responsible for deploying the service",
    )
    running: Optional[bool] = Field(
        default=None, description="Whether the service is running"
    )
    model_version_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="By the model version this service is attached to.",
        union_mode="left_to_right",
    )
    pipeline_run_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="By the pipeline run this service is attached to.",
        union_mode="left_to_right",
    )

    # TODO: In Pydantic v2, the `model_` is a protected namespaces for all
    #  fields defined under base models. If not handled, this raises a warning.
    #  It is possible to suppress this warning message with the following
    #  configuration, however the ultimate solution is to rename these fields.
    #  Even though they do not cause any problems right now, if we are not
    #  careful we might overwrite some fields protected by pydantic.
    model_config = ConfigDict(protected_namespaces=())

    def set_type(self, type: str) -> None:
        """Set the type of the service.

        Args:
            type: The type of the service.
        """
        self.type = type

    def set_flavor(self, flavor: str) -> None:
        """Set the flavor of the service.

        Args:
            flavor: The flavor of the service.
        """
        self.flavor = flavor

    # Artifact name and type are not DB fields and need to be handled separately
    FILTER_EXCLUDE_FIELDS = [
        *ProjectScopedFilter.FILTER_EXCLUDE_FIELDS,
        "flavor",
        "type",
        "pipeline_step_name",
        "running",
        "pipeline_name",
        "config",
    ]
    CLI_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *ProjectScopedFilter.CLI_EXCLUDE_FIELDS,
        "flavor",
        "type",
        "pipeline_step_name",
        "running",
        "pipeline_name",
    ]

    def generate_filter(
        self, table: Type["AnySchema"]
    ) -> Union["ColumnElement[bool]"]:
        """Generate the filter for the query.

        Services can be scoped by type to narrow the search.

        Args:
            table: The Table that is being queried from.

        Returns:
            The filter expression for the query.
        """
        from sqlmodel import and_

        base_filter = super().generate_filter(table)

        if self.type:
            type_filter = getattr(table, "type") == self.type
            base_filter = and_(base_filter, type_filter)

        if self.flavor:
            flavor_filter = getattr(table, "flavor") == self.flavor
            base_filter = and_(base_filter, flavor_filter)

        if self.pipeline_name:
            pipeline_name_filter = (
                getattr(table, "pipeline_name") == self.pipeline_name
            )
            base_filter = and_(base_filter, pipeline_name_filter)

        if self.pipeline_step_name:
            pipeline_step_name_filter = (
                getattr(table, "pipeline_step_name") == self.pipeline_step_name
            )
            base_filter = and_(base_filter, pipeline_step_name_filter)

        return base_filter
