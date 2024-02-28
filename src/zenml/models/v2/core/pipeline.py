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
"""Models representing pipelines."""

from typing import TYPE_CHECKING, Any, List, Optional, Union
from uuid import UUID

from pydantic import Field

from zenml.config.pipeline_spec import PipelineSpec
from zenml.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.enums import ExecutionStatus
from zenml.models import (
    BaseFilter,
    BaseResponseMetadata,
    WorkspaceScopedFilter,
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
)
from zenml.models.v2.base.base import (
    BaseResponse,
    BaseResponseBody,
    BaseResponseResources,
)
from zenml.models.v2.base.scoped import WorkspaceScopedResponseResources
from zenml.models.v2.base.update import update_model

if TYPE_CHECKING:
    from zenml.models.v2.core.pipeline_run import (
        PipelineRunResponse,
    )


# ------------------ Request Model ------------------


class PipelineRequest(WorkspaceScopedRequest):
    """Request model for pipelines."""

    name: str = Field(
        title="The name of the pipeline.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    version: str = Field(
        title="The version of the pipeline.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    version_hash: str = Field(
        title="The version hash of the pipeline.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    docstring: Optional[str] = Field(
        title="The docstring of the pipeline.",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    spec: PipelineSpec = Field(title="The spec of the pipeline.")


# ------------------ Update Model ------------------


@update_model
class PipelineUpdate(PipelineRequest):
    """Update model for pipelines."""


# ------------------ Response Model ------------------


class PipelineResponseBody(WorkspaceScopedResponseBody):
    """Response body for pipelines."""

    status: Optional[List[ExecutionStatus]] = Field(
        default=None, title="The status of the last 3 Pipeline Runs."
    )
    version: str = Field(
        title="The version of the pipeline.",
        max_length=STR_FIELD_MAX_LENGTH,
    )


class PipelineResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata for pipelines."""

    version_hash: str = Field(
        title="The version hash of the pipeline.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    spec: PipelineSpec = Field(title="The spec of the pipeline.")
    docstring: Optional[str] = Field(
        title="The docstring of the pipeline.",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )


class PipelineResponseResources(WorkspaceScopedResponseResources):
    """Class for all resource models associated with the pipeline entity."""


class PipelineResponse(
    WorkspaceScopedResponse[
        PipelineResponseBody,
        PipelineResponseMetadata,
        PipelineResponseResources,
    ]
):
    """Response model for pipelines."""

    name: str = Field(
        title="The name of the pipeline.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    def get_hydrated_version(self) -> "PipelineResponse":
        """Get the hydrated version of this pipeline.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_pipeline(self.id)

    # Helper methods
    def get_runs(self, **kwargs: Any) -> List["PipelineRunResponse"]:
        """Get runs of this pipeline.

        Can be used to fetch runs other than `self.runs` and supports
        fine-grained filtering and pagination.

        Args:
            **kwargs: Further arguments for filtering or pagination that are
                passed to `client.list_pipeline_runs()`.

        Returns:
            List of runs of this pipeline.
        """
        from zenml.client import Client

        return Client().list_pipeline_runs(pipeline_id=self.id, **kwargs).items

    @property
    def runs(self) -> List["PipelineRunResponse"]:
        """Returns the 20 most recent runs of this pipeline in descending order.

        Returns:
            The 20 most recent runs of this pipeline in descending order.
        """
        return self.get_runs()

    @property
    def num_runs(self) -> int:
        """Returns the number of runs of this pipeline.

        Returns:
            The number of runs of this pipeline.
        """
        from zenml.client import Client

        return Client().list_pipeline_runs(pipeline_id=self.id, size=1).total

    @property
    def last_run(self) -> "PipelineRunResponse":
        """Returns the last run of this pipeline.

        Returns:
            The last run of this pipeline.

        Raises:
            RuntimeError: If no runs were found for this pipeline.
        """
        runs = self.get_runs(size=1)
        if not runs:
            raise RuntimeError(
                f"No runs found for pipeline '{self.name}' with id {self.id}."
            )
        return runs[0]

    @property
    def last_successful_run(self) -> "PipelineRunResponse":
        """Returns the last successful run of this pipeline.

        Returns:
            The last successful run of this pipeline.

        Raises:
            RuntimeError: If no successful runs were found for this pipeline.
        """
        runs = self.get_runs(status=ExecutionStatus.COMPLETED, size=1)
        if not runs:
            raise RuntimeError(
                f"No successful runs found for pipeline '{self.name}' with id "
                f"{self.id}."
            )
        return runs[0]

    # Body and metadata properties
    @property
    def status(self) -> Optional[List[ExecutionStatus]]:
        """The `status` property.

        Returns:
            the value of the property.
        """
        return self.get_body().status

    @property
    def version(self) -> str:
        """The `version` property.

        Returns:
            the value of the property.
        """
        return self.get_body().version

    @property
    def spec(self) -> PipelineSpec:
        """The `spec` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().spec

    @property
    def version_hash(self) -> str:
        """The `version_hash` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().version_hash

    @property
    def docstring(self) -> Optional[str]:
        """The `docstring` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().docstring


# ------------------ Filter Model ------------------


class PipelineFilter(WorkspaceScopedFilter):
    """Pipeline filter model."""

    name: Optional[str] = Field(
        default=None,
        description="Name of the Pipeline",
    )
    version: Optional[str] = Field(
        default=None,
        description="Version of the Pipeline",
    )
    version_hash: Optional[str] = Field(
        default=None,
        description="Version hash of the Pipeline",
    )
    docstring: Optional[str] = Field(
        default=None,
        description="Docstring of the Pipeline",
    )
    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Workspace of the Pipeline"
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None, description="User of the Pipeline"
    )


# ------------------ Pipeline Namespaces ------------------


class PipelineNamespaceResponseBody(BaseResponseBody):
    """Response body for pipeline namespaces."""

    latest_run_id: Optional[UUID] = Field(
        default=None,
        title="The ID of the latest run of the pipeline namespace.",
    )
    latest_run_status: Optional[ExecutionStatus] = Field(
        default=None,
        title="The status of the latest run of the pipeline namespace.",
    )


class PipelineNamespaceResponseMetadata(BaseResponseMetadata):
    """Response metadata for pipeline namespaces."""


class PipelineNamespaceResponseResources(BaseResponseResources):
    """Class for all resource models associated with the pipeline namespace entity."""


class PipelineNamespaceResponse(
    BaseResponse[
        PipelineNamespaceResponseBody,
        PipelineNamespaceResponseMetadata,
        PipelineNamespaceResponseResources,
    ]
):
    """Response model for pipeline namespaces."""

    name: str = Field(
        title="The name of the pipeline namespace.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    def get_hydrated_version(self) -> "PipelineNamespaceResponse":
        """Get the hydrated version of this pipeline namespace.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        return self


class PipelineNamespaceFilter(BaseFilter):
    """Pipeline namespace filter model."""

    name: Optional[str] = Field(
        default=None,
        description="Name of the pipeline namespace.",
    )
