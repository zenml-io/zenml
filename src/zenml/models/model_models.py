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
"""Model implementation to support Model Control Plane feature."""

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

from pydantic import BaseModel, Field, PrivateAttr, validator

from zenml.constants import (
    STR_FIELD_MAX_LENGTH,
    TEXT_FIELD_MAX_LENGTH,
)
from zenml.enums import ModelStages
from zenml.logger import get_logger
from zenml.models.base_models import (
    WorkspaceScopedRequestModel,
    WorkspaceScopedResponseModel,
)
from zenml.models.model_base_model import ModelBaseModel
from zenml.models.tag_models import TagResponseModel
from zenml.models.v2.base.filter import AnyQuery
from zenml.models.v2.base.scoped import WorkspaceScopedFilter
from zenml.models.v2.core.artifact import ArtifactResponse
from zenml.models.v2.core.pipeline_run import PipelineRunResponse

if TYPE_CHECKING:
    from zenml.model.model_version import ModelVersion
    from zenml.zen_stores.schemas import BaseSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)

logger = get_logger(__name__)


class ModelVersionBaseModel(BaseModel):
    """Model Version base model."""

    name: Optional[str] = Field(
        description="The name of the model version",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    description: Optional[str] = Field(
        description="The description of the model version",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    stage: Optional[str] = Field(
        description="The stage of the model version",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )


class ModelScopedFilterModel(WorkspaceScopedFilter):
    """Base filter model inside Model Scope."""

    _model_id: UUID = PrivateAttr(None)

    def set_scope_model(self, model_name_or_id: Union[str, UUID]) -> None:
        """Set the model to scope this response.

        Args:
            model_name_or_id: The model to scope this response to.
        """
        try:
            model_id = UUID(str(model_name_or_id))
        except ValueError:
            from zenml.client import Client

            model_id = Client().get_model(model_name_or_id).id

        self._model_id = model_id

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
        query = super().apply_filter(query=query, table=table)

        if self._model_id:
            query = query.where(getattr(table, "model_id") == self._model_id)

        return query


class ModelVersionRequestModel(
    ModelVersionBaseModel,
    WorkspaceScopedRequestModel,
):
    """Model Version request model."""

    number: Optional[int] = Field(
        description="The number of the model version",
    )
    model: UUID = Field(
        description="The ID of the model containing version",
    )


class ModelVersionResponseModel(
    ModelVersionBaseModel,
    WorkspaceScopedResponseModel,
):
    """Model Version response model."""

    number: int = Field(
        description="The number of the model version",
    )
    model: "ModelResponseModel" = Field(
        description="The model containing version",
    )
    model_artifact_ids: Dict[str, Dict[str, UUID]] = Field(
        description="Model artifacts linked to the model version",
        default={},
    )
    data_artifact_ids: Dict[str, Dict[str, UUID]] = Field(
        description="Data artifacts linked to the model version",
        default={},
    )
    endpoint_artifact_ids: Dict[str, Dict[str, UUID]] = Field(
        description="Endpoint artifacts linked to the model version",
        default={},
    )
    pipeline_run_ids: Dict[str, UUID] = Field(
        description="Pipeline runs linked to the model version",
        default={},
    )

    def to_model_version(
        self,
        was_created_in_this_run: bool = False,
        suppress_class_validation_warnings: bool = False,
    ) -> "ModelVersion":
        """Convert response model to ModelVersion object.

        Args:
            was_created_in_this_run: Whether model version was created during current run.
            suppress_class_validation_warnings: internally used to suppress repeated warnings.

        Returns:
            ModelVersion object
        """
        from zenml.model.model_version import ModelVersion

        mv = ModelVersion(
            name=self.model.name,
            license=self.model.license,
            description=self.description,
            audience=self.model.audience,
            use_cases=self.model.use_cases,
            limitations=self.model.limitations,
            trade_offs=self.model.trade_offs,
            ethics=self.model.ethics,
            tags=[t.name for t in self.model.tags],
            version=self.name,
            was_created_in_this_run=was_created_in_this_run,
            suppress_class_validation_warnings=suppress_class_validation_warnings,
        )
        mv._id = self.id

        return mv

    @property
    def model_artifacts(self) -> Dict[str, Dict[str, "ArtifactResponse"]]:
        """Get all model artifacts linked to this model version.

        Returns:
            Dictionary of model artifacts with versions as Dict[str, Dict[str, ArtifactResponse]]
        """
        from zenml.client import Client

        return {
            name: {
                version: Client().get_artifact(a)
                for version, a in self.model_artifact_ids[name].items()
            }
            for name in self.model_artifact_ids
        }

    @property
    def data_artifacts(self) -> Dict[str, Dict[str, "ArtifactResponse"]]:
        """Get all data artifacts linked to this model version.

        Returns:
            Dictionary of data artifacts with versions as Dict[str, Dict[str, ArtifactResponse]]
        """
        from zenml.client import Client

        return {
            name: {
                version: Client().get_artifact(a)
                for version, a in self.data_artifact_ids[name].items()
            }
            for name in self.data_artifact_ids
        }

    @property
    def endpoint_artifacts(
        self,
    ) -> Dict[str, Dict[str, "ArtifactResponse"]]:
        """Get all endpoint artifacts linked to this model version.

        Returns:
            Dictionary of endpoint artifacts with versions as Dict[str, Dict[str, ArtifactResponse]]
        """
        from zenml.client import Client

        return {
            name: {
                version: Client().get_artifact(a)
                for version, a in self.endpoint_artifact_ids[name].items()
            }
            for name in self.endpoint_artifact_ids
        }

    @property
    def pipeline_runs(self) -> Dict[str, "PipelineRunResponse"]:
        """Get all pipeline runs linked to this version.

        Returns:
            Dictionary of Pipeline Runs as PipelineRunResponseModel
        """
        from zenml.client import Client

        return {
            name: Client().get_pipeline_run(pr)
            for name, pr in self.pipeline_run_ids.items()
        }

    def _get_linked_object(
        self,
        collection: Dict[str, Dict[str, UUID]],
        name: str,
        version: Optional[str] = None,
    ) -> Optional["ArtifactResponse"]:
        """Get the artifact linked to this model version given type.

        Args:
            collection: The collection to search in (one of self.model_artifact_ids, self.data_artifact_ids, self.endpoint_artifact_ids)
            name: The name of the artifact to retrieve.
            version: The version of the artifact to retrieve (None for latest/non-versioned)

        Returns:
            Specific version of an artifact from collection or None
        """
        from zenml.client import Client

        client = Client()

        if name not in collection:
            return None
        if version is None:
            version = max(collection[name].keys())
        return client.get_artifact(collection[name][version])

    def get_artifact(
        self,
        name: str,
        version: Optional[str] = None,
    ) -> Optional["ArtifactResponse"]:
        """Get the artifact linked to this model version.

        Args:
            name: The name of the artifact to retrieve.
            version: The version of the artifact to retrieve (None for latest/non-versioned)

        Returns:
            Specific version of an artifact or None
        """
        all_artifact_ids = {
            **self.model_artifact_ids,
            **self.data_artifact_ids,
            **self.endpoint_artifact_ids,
        }
        return self._get_linked_object(all_artifact_ids, name, version)

    def get_model_artifact(
        self,
        name: str,
        version: Optional[str] = None,
    ) -> Optional["ArtifactResponse"]:
        """Get the model artifact linked to this model version.

        Args:
            name: The name of the model artifact to retrieve.
            version: The version of the model artifact to retrieve (None for latest/non-versioned)

        Returns:
            Specific version of the model artifact or None
        """
        return self._get_linked_object(self.model_artifact_ids, name, version)

    def get_data_artifact(
        self,
        name: str,
        version: Optional[str] = None,
    ) -> Optional["ArtifactResponse"]:
        """Get the data artifact linked to this model version.

        Args:
            name: The name of the data artifact to retrieve.
            version: The version of the data artifact to retrieve (None for latest/non-versioned)

        Returns:
            Specific version of the data artifact or None
        """
        return self._get_linked_object(
            self.data_artifact_ids,
            name,
            version,
        )

    def get_endpoint_artifact(
        self,
        name: str,
        version: Optional[str] = None,
    ) -> Optional["ArtifactResponse"]:
        """Get the endpoint artifact linked to this model version.

        Args:
            name: The name of the endpoint artifact to retrieve.
            version: The version of the endpoint artifact to retrieve (None for latest/non-versioned)

        Returns:
            Specific version of the endpoint artifact or None
        """
        return self._get_linked_object(
            self.endpoint_artifact_ids,
            name,
            version,
        )

    def get_pipeline_run(self, name: str) -> "PipelineRunResponse":
        """Get pipeline run linked to this version.

        Args:
            name: The name of the pipeline run to retrieve.

        Returns:
            PipelineRun as PipelineRunResponseModel
        """
        from zenml.client import Client

        return Client().get_pipeline_run(self.pipeline_run_ids[name])

    def set_stage(
        self, stage: Union[str, ModelStages], force: bool = False
    ) -> None:
        """Sets this Model Version to a desired stage.

        Args:
            stage: the target stage for model version.
            force: whether to force archiving of current model version in
                target stage or raise.

        Raises:
            ValueError: if model_stage is not valid.
        """
        from zenml.client import Client

        stage = getattr(stage, "value", stage)
        if stage not in [stage.value for stage in ModelStages]:
            raise ValueError(f"`{stage}` is not a valid model stage.")

        Client().update_model_version(
            model_name_or_id=self.model.id,
            version_name_or_id=self.id,
            stage=stage,
            force=force,
        )

    # TODO in https://zenml.atlassian.net/browse/OSS-2433
    # def generate_model_card(self, template_name: str) -> str:
    #     """Return HTML/PDF based on input template"""


class ModelVersionFilterModel(ModelScopedFilterModel):
    """Filter Model for Model Version."""

    name: Optional[str] = Field(
        default=None,
        description="The name of the Model Version",
    )
    number: Optional[int] = Field(
        default=None,
        description="The number of the Model Version",
    )
    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None, description="The workspace of the Model Version"
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None, description="The user of the Model Version"
    )
    stage: Optional[Union[str, ModelStages]] = Field(
        description="The model version stage", default=None
    )


class ModelVersionUpdateModel(BaseModel):
    """Update Model for Model Version."""

    model: UUID = Field(
        description="The ID of the model containing version",
    )
    stage: Optional[Union[str, ModelStages]] = Field(
        description="Target model version stage to be set", default=None
    )
    force: bool = Field(
        description="Whether existing model version in target stage should be "
        "silently archived or an error should be raised.",
        default=False,
    )
    name: Optional[str] = Field(
        description="Target model version name to be set", default=None
    )

    @validator("stage")
    def _validate_stage(cls, stage: str) -> str:
        stage = getattr(stage, "value", stage)
        if stage is not None and stage not in [
            stage.value for stage in ModelStages
        ]:
            raise ValueError(f"`{stage}` is not a valid model stage.")
        return stage


class ModelVersionArtifactBaseModel(BaseModel):
    """Model version links with artifact base model."""

    model: UUID
    model_version: UUID
    is_model_artifact: bool = False
    is_endpoint_artifact: bool = False

    @validator("is_endpoint_artifact")
    def _validate_is_endpoint_artifact(
        cls, is_endpoint_artifact: bool, values: Dict[str, Any]
    ) -> bool:
        is_model_artifact = values.get("is_model_artifact", False)
        if is_model_artifact and is_endpoint_artifact:
            raise ValueError(
                "Artifact cannot be a model artifact and endpoint artifact at the same time."
            )
        return is_endpoint_artifact


class ModelVersionArtifactRequestModel(
    ModelVersionArtifactBaseModel, WorkspaceScopedRequestModel
):
    """Model version link with artifact request model."""

    artifact: UUID


class ModelVersionArtifactResponseModel(
    ModelVersionArtifactBaseModel, WorkspaceScopedResponseModel
):
    """Model version link with artifact response model."""

    artifact: ArtifactResponse


class ModelVersionArtifactFilterModel(WorkspaceScopedFilter):
    """Model version pipeline run links filter model."""

    # Artifact name and type are not DB fields and need to be handled separately
    FILTER_EXCLUDE_FIELDS = [
        *WorkspaceScopedFilter.FILTER_EXCLUDE_FIELDS,
        "artifact_name",
        "only_data_artifacts",
        "only_model_artifacts",
        "only_endpoint_artifacts",
    ]

    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None, description="The workspace of the Model Version"
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None, description="The user of the Model Version"
    )
    model_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Filter by model ID"
    )
    model_version_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Filter by model version ID"
    )
    artifact_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Filter by artifact ID"
    )
    artifact_name: Optional[str] = Field(
        default=None,
        description="Name of the artifact",
    )
    only_data_artifacts: Optional[bool] = False
    only_model_artifacts: Optional[bool] = False
    only_endpoint_artifacts: Optional[bool] = False

    CLI_EXCLUDE_FIELDS = [
        *WorkspaceScopedFilter.CLI_EXCLUDE_FIELDS,
        "only_data_artifacts",
        "only_model_artifacts",
        "only_endpoint_artifacts",
        "model_id",
        "model_version_id",
        "user_id",
        "workspace_id",
        "updated",
        "id",
    ]


class ModelVersionPipelineRunBaseModel(BaseModel):
    """Model version links with pipeline run base model."""

    model: UUID
    model_version: UUID


class ModelVersionPipelineRunRequestModel(
    ModelVersionPipelineRunBaseModel, WorkspaceScopedRequestModel
):
    """Model version link with pipeline run request model."""

    pipeline_run: UUID


class ModelVersionPipelineRunResponseModel(
    ModelVersionPipelineRunBaseModel, WorkspaceScopedResponseModel
):
    """Model version link with pipeline run response model."""

    pipeline_run: PipelineRunResponse


class ModelVersionPipelineRunFilterModel(WorkspaceScopedFilter):
    """Model version pipeline run links filter model."""

    # Pipeline run name is not a DB field and needs to be handled separately
    FILTER_EXCLUDE_FIELDS = [
        *WorkspaceScopedFilter.FILTER_EXCLUDE_FIELDS,
        "pipeline_run_name",
    ]

    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None, description="The workspace of the Model Version"
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None, description="The user of the Model Version"
    )
    model_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Filter by model ID"
    )
    model_version_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Filter by model version ID"
    )
    pipeline_run_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Filter by pipeline run ID"
    )
    pipeline_run_name: Optional[str] = Field(
        default=None,
        description="Name of the pipeline run",
    )

    CLI_EXCLUDE_FIELDS = [
        *WorkspaceScopedFilter.CLI_EXCLUDE_FIELDS,
        "model_id",
        "model_version_id",
        "user_id",
        "workspace_id",
        "updated",
        "id",
    ]


class ModelRequestModel(
    WorkspaceScopedRequestModel,
    ModelBaseModel,
):
    """Model request model."""

    tags: Optional[List[str]] = Field(
        title="Tags associated with the model",
    )


class ModelResponseModel(
    WorkspaceScopedResponseModel,
    ModelBaseModel,
):
    """Model response model.

    latest_version: name of latest version, if any
    """

    tags: List[TagResponseModel] = Field(
        title="Tags associated with the model",
    )
    latest_version: Optional[str]

    @property
    def versions(self) -> List["ModelVersion"]:
        """List all versions of the model.

        Returns:
            The list of all model version.
        """
        from zenml.client import Client

        client = Client()
        model_versions = client.list_model_versions(
            model_name_or_id=self.id, page=1
        )
        ret = [
            mv.to_model_version(suppress_class_validation_warnings=True)
            for mv in model_versions.items
        ]
        for i in range(2, model_versions.total_pages + 1):
            ret += [
                mv.to_model_version(suppress_class_validation_warnings=True)
                for mv in model_versions.items
            ]

        return ret


class ModelFilterModel(WorkspaceScopedFilter):
    """Model to enable advanced filtering of all Workspaces."""

    name: Optional[str] = Field(
        default=None,
        description="Name of the Model",
    )
    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None, description="Workspace of the Model"
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None, description="User of the Model"
    )

    CLI_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *WorkspaceScopedFilter.CLI_EXCLUDE_FIELDS,
        "workspace_id",
        "user_id",
    ]


class ModelUpdateModel(BaseModel):
    """Model update model."""

    license: Optional[str] = None
    description: Optional[str] = None
    audience: Optional[str] = None
    use_cases: Optional[str] = None
    limitations: Optional[str] = None
    trade_offs: Optional[str] = None
    ethics: Optional[str] = None
    add_tags: Optional[List[str]] = None
    remove_tags: Optional[List[str]] = None
