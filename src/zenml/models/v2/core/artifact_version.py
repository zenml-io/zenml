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
"""Models representing artifact versions."""

from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Union,
)
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from zenml.config.source import Source, SourceWithValidator
from zenml.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.enums import ArtifactType, GenericFilterOps
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType
from zenml.models.v2.base.filter import StrFilter
from zenml.models.v2.base.scoped import (
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
    WorkspaceScopedResponseResources,
    WorkspaceScopedTaggableFilter,
)
from zenml.models.v2.core.artifact import ArtifactResponse
from zenml.models.v2.core.tag import TagResponse

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement

    from zenml.models.v2.core.artifact_visualization import (
        ArtifactVisualizationRequest,
        ArtifactVisualizationResponse,
    )
    from zenml.models.v2.core.pipeline_run import PipelineRunResponse
    from zenml.models.v2.core.run_metadata import (
        RunMetadataResponse,
    )
    from zenml.models.v2.core.step_run import StepRunResponse

logger = get_logger(__name__)

# ------------------ Request Model ------------------


class ArtifactVersionRequest(WorkspaceScopedRequest):
    """Request model for artifact versions."""

    artifact_id: Optional[UUID] = Field(
        default=None,
        title="ID of the artifact to which this version belongs.",
    )
    artifact_name: Optional[str] = Field(
        default=None,
        title="Name of the artifact to which this version belongs.",
    )
    version: Optional[Union[int, str]] = Field(
        default=None, title="Version of the artifact."
    )
    has_custom_name: bool = Field(
        title="Whether the name is custom (True) or auto-generated (False).",
        default=False,
    )
    type: ArtifactType = Field(title="Type of the artifact.")
    artifact_store_id: Optional[UUID] = Field(
        title="ID of the artifact store in which this artifact is stored.",
        default=None,
    )
    uri: str = Field(
        title="URI of the artifact.", max_length=TEXT_FIELD_MAX_LENGTH
    )
    materializer: SourceWithValidator = Field(
        title="Materializer class to use for this artifact.",
    )
    data_type: SourceWithValidator = Field(
        title="Data type of the artifact.",
    )
    tags: Optional[List[str]] = Field(
        title="Tags of the artifact.",
        description="Should be a list of plain strings, e.g., ['tag1', 'tag2']",
        default=None,
    )
    visualizations: Optional[List["ArtifactVisualizationRequest"]] = Field(
        default=None, title="Visualizations of the artifact."
    )
    metadata: Optional[Dict[str, MetadataType]] = Field(
        default=None, title="Metadata of the artifact version."
    )

    @field_validator("version")
    @classmethod
    def str_field_max_length_check(cls, value: Any) -> Any:
        """Checks if the length of the value exceeds the maximum str length.

        Args:
            value: the value set in the field

        Returns:
            the value itself.

        Raises:
            AssertionError: if the length of the field is longer than the
                maximum threshold.
        """
        assert len(str(value)) < STR_FIELD_MAX_LENGTH, (
            "The length of the value for this field can not "
            f"exceed {STR_FIELD_MAX_LENGTH}"
        )
        return value

    @model_validator(mode="after")
    def _validate_request(self) -> "ArtifactVersionRequest":
        """Validate the request values.

        Raises:
            ValueError: If the request is invalid.

        Returns:
            The validated request.
        """
        if self.artifact_id and self.artifact_name:
            raise ValueError(
                "Only one of artifact_name and artifact_id can be set."
            )

        if not (self.artifact_id or self.artifact_name):
            raise ValueError(
                "Either artifact_name or artifact_id must be set."
            )

        return self


# ------------------ Update Model ------------------


class ArtifactVersionUpdate(BaseModel):
    """Artifact version update model."""

    name: Optional[str] = None
    add_tags: Optional[List[str]] = None
    remove_tags: Optional[List[str]] = None


# ------------------ Response Model ------------------


class ArtifactVersionResponseBody(WorkspaceScopedResponseBody):
    """Response body for artifact versions."""

    artifact: ArtifactResponse = Field(
        title="Artifact to which this version belongs."
    )
    version: str = Field(title="Version of the artifact.")
    uri: str = Field(
        title="URI of the artifact.", max_length=TEXT_FIELD_MAX_LENGTH
    )
    type: ArtifactType = Field(title="Type of the artifact.")
    materializer: SourceWithValidator = Field(
        title="Materializer class to use for this artifact.",
    )
    data_type: SourceWithValidator = Field(
        title="Data type of the artifact.",
    )
    tags: List[TagResponse] = Field(
        title="Tags associated with the model",
    )
    producer_pipeline_run_id: Optional[UUID] = Field(
        title="The ID of the pipeline run that generated this artifact version.",
        default=None,
    )

    @field_validator("version")
    @classmethod
    def str_field_max_length_check(cls, value: Any) -> Any:
        """Checks if the length of the value exceeds the maximum str length.

        Args:
            value: the value set in the field

        Returns:
            the value itself.

        Raises:
            AssertionError: if the length of the field is longer than the
                maximum threshold.
        """
        assert len(str(value)) < STR_FIELD_MAX_LENGTH, (
            "The length of the value for this field can not "
            f"exceed {STR_FIELD_MAX_LENGTH}"
        )
        return value


class ArtifactVersionResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata for artifact versions."""

    artifact_store_id: Optional[UUID] = Field(
        title="ID of the artifact store in which this artifact is stored.",
        default=None,
    )
    producer_step_run_id: Optional[UUID] = Field(
        title="ID of the step run that produced this artifact.",
        default=None,
    )
    visualizations: Optional[List["ArtifactVisualizationResponse"]] = Field(
        default=None, title="Visualizations of the artifact."
    )
    run_metadata: Dict[str, "RunMetadataResponse"] = Field(
        default={}, title="Metadata of the artifact."
    )


class ArtifactVersionResponseResources(WorkspaceScopedResponseResources):
    """Class for all resource models associated with the artifact version entity."""


class ArtifactVersionResponse(
    WorkspaceScopedResponse[
        ArtifactVersionResponseBody,
        ArtifactVersionResponseMetadata,
        ArtifactVersionResponseResources,
    ]
):
    """Response model for artifact versions."""

    def get_hydrated_version(self) -> "ArtifactVersionResponse":
        """Get the hydrated version of this artifact version.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_artifact_version(self.id)

    # Body and metadata properties
    @property
    def artifact(self) -> "ArtifactResponse":
        """The `artifact` property.

        Returns:
            the value of the property.
        """
        return self.get_body().artifact

    @property
    def version(self) -> Union[str, int]:
        """The `version` property.

        Returns:
            the value of the property.
        """
        return self.get_body().version

    @property
    def uri(self) -> str:
        """The `uri` property.

        Returns:
            the value of the property.
        """
        return self.get_body().uri

    @property
    def type(self) -> ArtifactType:
        """The `type` property.

        Returns:
            the value of the property.
        """
        return self.get_body().type

    @property
    def tags(self) -> List[TagResponse]:
        """The `tags` property.

        Returns:
            the value of the property.
        """
        return self.get_body().tags

    @property
    def producer_pipeline_run_id(self) -> Optional[UUID]:
        """The `producer_pipeline_run_id` property.

        Returns:
            the value of the property.
        """
        return self.get_body().producer_pipeline_run_id

    @property
    def artifact_store_id(self) -> Optional[UUID]:
        """The `artifact_store_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().artifact_store_id

    @property
    def producer_step_run_id(self) -> Optional[UUID]:
        """The `producer_step_run_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().producer_step_run_id

    @property
    def visualizations(
        self,
    ) -> Optional[List["ArtifactVisualizationResponse"]]:
        """The `visualizations` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().visualizations

    @property
    def run_metadata(self) -> Dict[str, "RunMetadataResponse"]:
        """The `metadata` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().run_metadata

    @property
    def materializer(self) -> Source:
        """The `materializer` property.

        Returns:
            the value of the property.
        """
        return self.get_body().materializer

    @property
    def data_type(self) -> Source:
        """The `data_type` property.

        Returns:
            the value of the property.
        """
        return self.get_body().data_type

    # Helper methods
    @property
    def name(self) -> str:
        """The `name` property.

        Returns:
            the value of the property.
        """
        return self.artifact.name

    @property
    def step(self) -> "StepRunResponse":
        """Get the step that produced this artifact.

        Returns:
            The step that produced this artifact.
        """
        from zenml.artifacts.utils import get_producer_step_of_artifact

        return get_producer_step_of_artifact(self)

    @property
    def run(self) -> "PipelineRunResponse":
        """Get the pipeline run that produced this artifact.

        Returns:
            The pipeline run that produced this artifact.
        """
        from zenml.client import Client

        return Client().get_pipeline_run(self.step.pipeline_run_id)

    def load(self) -> Any:
        """Materializes (loads) the data stored in this artifact.

        Returns:
            The materialized data.
        """
        from zenml.artifacts.utils import load_artifact_from_response

        return load_artifact_from_response(self)

    def download_files(self, path: str, overwrite: bool = False) -> None:
        """Downloads data for an artifact with no materializing.

        Any artifacts will be saved as a zip file to the given path.

        Args:
            path: The path to save the binary data to.
            overwrite: Whether to overwrite the file if it already exists.

        Raises:
            ValueError: If the path does not end with '.zip'.
        """
        if not path.endswith(".zip"):
            raise ValueError(
                "The path should end with '.zip' to save the binary data."
            )
        from zenml.artifacts.utils import (
            download_artifact_files_from_response,
        )

        download_artifact_files_from_response(
            self,
            path=path,
            overwrite=overwrite,
        )

    def visualize(self, title: Optional[str] = None) -> None:
        """Visualize the artifact in notebook environments.

        Args:
            title: Optional title to show before the visualizations.
        """
        from zenml.utils.visualization_utils import visualize_artifact

        visualize_artifact(self, title=title)


# ------------------ Filter Model ------------------


class ArtifactVersionFilter(WorkspaceScopedTaggableFilter):
    """Model to enable advanced filtering of artifact versions."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *WorkspaceScopedTaggableFilter.FILTER_EXCLUDE_FIELDS,
        "name",
        "only_unused",
        "has_custom_name",
        "user",
        "model",
        "pipeline_run",
    ]
    artifact_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="ID of the artifact to which this version belongs.",
        union_mode="left_to_right",
    )
    name: Optional[str] = Field(
        default=None,
        description="Name of the artifact to which this version belongs.",
    )
    version: Optional[str] = Field(
        default=None,
        description="Version of the artifact",
    )
    version_number: Optional[Union[int, str]] = Field(
        default=None,
        description="Version of the artifact if it is an integer",
        union_mode="left_to_right",
    )
    uri: Optional[str] = Field(
        default=None,
        description="Uri of the artifact",
    )
    materializer: Optional[str] = Field(
        default=None,
        description="Materializer used to produce the artifact",
    )
    type: Optional[str] = Field(
        default=None,
        description="Type of the artifact",
    )
    data_type: Optional[str] = Field(
        default=None,
        description="Datatype of the artifact",
    )
    artifact_store_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Artifact store for this artifact",
        union_mode="left_to_right",
    )
    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Workspace for this artifact",
        union_mode="left_to_right",
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="User that produced this artifact",
        union_mode="left_to_right",
    )
    only_unused: Optional[bool] = Field(
        default=False, description="Filter only for unused artifacts"
    )
    has_custom_name: Optional[bool] = Field(
        default=None,
        description="Filter only artifacts with/without custom names.",
    )
    user: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Name/ID of the user that created the artifact version.",
    )
    model: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Name/ID of the model that is associated with this "
        "artifact version.",
    )
    pipeline_run: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Name/ID of a pipeline run that is associated with this "
        "artifact version.",
    )

    model_config = ConfigDict(protected_namespaces=())

    def get_custom_filters(self) -> List[Union["ColumnElement[bool]"]]:
        """Get custom filters.

        Returns:
            A list of custom filters.
        """
        custom_filters = super().get_custom_filters()

        from sqlmodel import and_, or_, select

        from zenml.zen_stores.schemas import (
            ArtifactSchema,
            ArtifactVersionSchema,
            ModelSchema,
            ModelVersionArtifactSchema,
            PipelineRunSchema,
            StepRunInputArtifactSchema,
            StepRunOutputArtifactSchema,
            StepRunSchema,
            UserSchema,
        )

        if self.name:
            value, filter_operator = self._resolve_operator(self.name)
            filter_ = StrFilter(
                operation=GenericFilterOps(filter_operator),
                column="name",
                value=value,
            )
            artifact_name_filter = and_(
                ArtifactVersionSchema.artifact_id == ArtifactSchema.id,
                filter_.generate_query_conditions(ArtifactSchema),
            )
            custom_filters.append(artifact_name_filter)

        if self.only_unused:
            unused_filter = and_(
                ArtifactVersionSchema.id.notin_(  # type: ignore[attr-defined]
                    select(StepRunOutputArtifactSchema.artifact_id)
                ),
                ArtifactVersionSchema.id.notin_(  # type: ignore[attr-defined]
                    select(StepRunInputArtifactSchema.artifact_id)
                ),
            )
            custom_filters.append(unused_filter)

        if self.has_custom_name is not None:
            custom_name_filter = and_(
                ArtifactVersionSchema.artifact_id == ArtifactSchema.id,
                ArtifactSchema.has_custom_name == self.has_custom_name,
            )
            custom_filters.append(custom_name_filter)

        if self.user:
            user_filter = and_(
                ArtifactVersionSchema.user_id == UserSchema.id,
                self.generate_name_or_id_query_conditions(
                    value=self.user, table=UserSchema
                ),
            )
            custom_filters.append(user_filter)

        if self.model:
            model_filter = and_(
                ArtifactVersionSchema.id
                == ModelVersionArtifactSchema.artifact_version_id,
                ModelVersionArtifactSchema.model_id == ModelSchema.id,
                self.generate_name_or_id_query_conditions(
                    value=self.model, table=ModelSchema
                ),
            )
            custom_filters.append(model_filter)

        if self.pipeline_run:
            pipeline_run_filter = and_(
                or_(
                    and_(
                        ArtifactVersionSchema.id
                        == StepRunOutputArtifactSchema.artifact_id,
                        StepRunOutputArtifactSchema.step_id
                        == StepRunSchema.id,
                    ),
                    and_(
                        ArtifactVersionSchema.id
                        == StepRunInputArtifactSchema.artifact_id,
                        StepRunInputArtifactSchema.step_id == StepRunSchema.id,
                    ),
                ),
                StepRunSchema.pipeline_run_id == PipelineRunSchema.id,
                self.generate_name_or_id_query_conditions(
                    value=self.pipeline_run, table=PipelineRunSchema
                ),
            )
            custom_filters.append(pipeline_run_filter)

        return custom_filters


# -------------------- Lazy Loader --------------------


class LazyArtifactVersionResponse(ArtifactVersionResponse):
    """Lazy artifact version response.

    Used if the artifact version is accessed from the model in
    a pipeline context available only during pipeline compilation.
    """

    id: Optional[UUID] = None  # type: ignore[assignment]
    lazy_load_name: Optional[str] = None
    lazy_load_version: Optional[str] = None
    lazy_load_model_name: str
    lazy_load_model_version: Optional[str] = None

    def get_body(self) -> None:  # type: ignore[override]
        """Protects from misuse of the lazy loader.

        Raises:
            RuntimeError: always
        """
        raise RuntimeError("Cannot access artifact body before pipeline runs.")

    def get_metadata(self) -> None:  # type: ignore[override]
        """Protects from misuse of the lazy loader.

        Raises:
            RuntimeError: always
        """
        raise RuntimeError(
            "Cannot access artifact metadata before pipeline runs."
        )

    @property
    def run_metadata(self) -> Dict[str, "RunMetadataResponse"]:
        """The `metadata` property in lazy loading mode.

        Returns:
            getter of lazy responses for internal use.
        """
        from zenml.metadata.lazy_load import RunMetadataLazyGetter

        return RunMetadataLazyGetter(  # type: ignore[return-value]
            self.lazy_load_model_name,
            self.lazy_load_model_version,
            self.lazy_load_name,
            self.lazy_load_version,
        )
