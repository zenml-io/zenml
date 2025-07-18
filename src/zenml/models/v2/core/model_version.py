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
"""Models representing model versions."""

import json
from typing import (
    TYPE_CHECKING,
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator

from zenml.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.enums import ArtifactType, ModelStages
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType
from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.page import Page
from zenml.models.v2.base.scoped import (
    ProjectScopedFilter,
    ProjectScopedRequest,
    ProjectScopedResponse,
    ProjectScopedResponseBody,
    ProjectScopedResponseMetadata,
    ProjectScopedResponseResources,
    RunMetadataFilterMixin,
    TaggableFilter,
)
from zenml.models.v2.core.service import ServiceResponse
from zenml.models.v2.core.tag import TagResponse
from zenml.utils import pagination_utils

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement

    from zenml.model.model import Model
    from zenml.models.v2.core.artifact_version import ArtifactVersionResponse
    from zenml.models.v2.core.model import ModelResponse
    from zenml.models.v2.core.pipeline_run import PipelineRunResponse
    from zenml.zen_stores.schemas import (
        BaseSchema,
    )

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)


logger = get_logger(__name__)

# ------------------ Request Model ------------------


class ModelVersionRequest(ProjectScopedRequest):
    """Request model for model versions."""

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

    model: UUID = Field(
        description="The ID of the model containing version",
    )
    tags: Optional[List[str]] = Field(
        title="Tags associated with the model version",
        default=None,
    )


# ------------------ Update Model ------------------


class ModelVersionUpdate(BaseUpdate):
    """Update model for model versions."""

    stage: Optional[Union[str, ModelStages]] = Field(
        description="Target model version stage to be set",
        default=None,
        union_mode="left_to_right",
    )
    force: bool = Field(
        description="Whether existing model version in target stage should be "
        "silently archived or an error should be raised.",
        default=False,
    )
    name: Optional[str] = Field(
        description="Target model version name to be set",
        default=None,
    )
    description: Optional[str] = Field(
        description="Target model version description to be set",
        default=None,
    )
    add_tags: Optional[List[str]] = Field(
        description="Tags to be added to the model version",
        default=None,
    )
    remove_tags: Optional[List[str]] = Field(
        description="Tags to be removed from the model version",
        default=None,
    )

    @field_validator("stage")
    @classmethod
    def _validate_stage(cls, stage: str) -> str:
        stage = getattr(stage, "value", stage)
        if stage is not None and stage not in [
            stage.value for stage in ModelStages
        ]:
            raise ValueError(f"`{stage}` is not a valid model stage.")
        return stage


# ------------------ Response Model ------------------


class ModelVersionResponseBody(ProjectScopedResponseBody):
    """Response body for model versions."""

    stage: Optional[str] = Field(
        description="The stage of the model version",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    number: int = Field(
        description="The number of the model version",
    )
    model: "ModelResponse" = Field(
        description="The model containing version",
    )

    # TODO: In Pydantic v2, the `model_` is a protected namespaces for all
    #  fields defined under base models. If not handled, this raises a warning.
    #  It is possible to suppress this warning message with the following
    #  configuration, however the ultimate solution is to rename these fields.
    #  Even though they do not cause any problems right now, if we are not
    #  careful we might overwrite some fields protected by pydantic.
    model_config = ConfigDict(protected_namespaces=())


class ModelVersionResponseMetadata(ProjectScopedResponseMetadata):
    """Response metadata for model versions."""

    description: Optional[str] = Field(
        description="The description of the model version",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    run_metadata: Dict[str, MetadataType] = Field(
        description="Metadata linked to the model version",
        default={},
    )


class ModelVersionResponseResources(ProjectScopedResponseResources):
    """Class for all resource models associated with the model version entity."""

    services: Page[ServiceResponse] = Field(
        description="Services linked to the model version",
    )
    tags: List[TagResponse] = Field(
        title="Tags associated with the model version", default=[]
    )


class ModelVersionResponse(
    ProjectScopedResponse[
        ModelVersionResponseBody,
        ModelVersionResponseMetadata,
        ModelVersionResponseResources,
    ]
):
    """Response model for model versions."""

    name: Optional[str] = Field(
        description="The name of the model version",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )

    @property
    def stage(self) -> Optional[str]:
        """The `stage` property.

        Returns:
            the value of the property.
        """
        return self.get_body().stage

    @property
    def number(self) -> int:
        """The `number` property.

        Returns:
            the value of the property.
        """
        return self.get_body().number

    @property
    def model(self) -> "ModelResponse":
        """The `model` property.

        Returns:
            the value of the property.
        """
        return self.get_body().model

    @property
    def tags(self) -> List[TagResponse]:
        """The `tags` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().tags

    @property
    def description(self) -> Optional[str]:
        """The `description` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().description

    @property
    def run_metadata(self) -> Dict[str, MetadataType]:
        """The `run_metadata` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().run_metadata

    def get_hydrated_version(self) -> "ModelVersionResponse":
        """Get the hydrated version of this model version.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_model_version(self.id)

    # Helper functions
    def to_model_class(
        self,
        suppress_class_validation_warnings: bool = True,
    ) -> "Model":
        """Convert response model to Model object.

        Args:
            suppress_class_validation_warnings: internally used to suppress
                repeated warnings.

        Returns:
            Model object
        """
        from zenml.model.model import Model

        mv = Model(
            name=self.model.name,
            license=self.model.license,
            description=self.description,
            audience=self.model.audience,
            use_cases=self.model.use_cases,
            limitations=self.model.limitations,
            trade_offs=self.model.trade_offs,
            ethics=self.model.ethics,
            tags=[t.name for t in self.tags],
            version=self.name,
            suppress_class_validation_warnings=suppress_class_validation_warnings,
            model_version_id=self.id,
        )

        return mv

    @property
    def model_artifacts(
        self,
    ) -> Dict[str, Dict[str, "ArtifactVersionResponse"]]:
        """Get all model artifacts linked to this model version.

        Returns:
            Dictionary of model artifacts with versions as
            Dict[str, Dict[str, ArtifactResponse]]
        """
        logger.warning(
            "ModelVersionResponse.model_artifacts is deprecated and will be "
            "removed in a future release."
        )
        from zenml.client import Client

        artifact_versions = pagination_utils.depaginate(
            Client().list_artifact_versions,
            model_version_id=self.id,
            type=ArtifactType.MODEL,
            project=self.project_id,
        )

        result: Dict[str, Dict[str, "ArtifactVersionResponse"]] = {}
        for artifact_version in artifact_versions:
            result.setdefault(artifact_version.name, {})
            result[artifact_version.name][artifact_version.version] = (
                artifact_version
            )

        return result

    @property
    def data_artifact_ids(self) -> Dict[str, Dict[str, UUID]]:
        """Data artifacts linked to this model version.

        Returns:
            Data artifacts linked to this model version.
        """
        logger.warning(
            "ModelVersionResponse.data_artifact_ids is deprecated and will "
            "be removed in a future release."
        )

        return {
            artifact_name: {
                version_name: version_response.id
                for version_name, version_response in artifact_versions.items()
            }
            for artifact_name, artifact_versions in self.data_artifacts.items()
        }

    @property
    def model_artifact_ids(self) -> Dict[str, Dict[str, UUID]]:
        """Model artifacts linked to this model version.

        Returns:
            Model artifacts linked to this model version.
        """
        logger.warning(
            "ModelVersionResponse.model_artifact_ids is deprecated and will "
            "be removed in a future release."
        )

        return {
            artifact_name: {
                version_name: version_response.id
                for version_name, version_response in artifact_versions.items()
            }
            for artifact_name, artifact_versions in self.model_artifacts.items()
        }

    @property
    def deployment_artifact_ids(self) -> Dict[str, Dict[str, UUID]]:
        """Deployment artifacts linked to this model version.

        Returns:
            Deployment artifacts linked to this model version.
        """
        logger.warning(
            "ModelVersionResponse.deployment_artifact_ids is deprecated and "
            "will be removed in a future release."
        )

        return {
            artifact_name: {
                version_name: version_response.id
                for version_name, version_response in artifact_versions.items()
            }
            for artifact_name, artifact_versions in self.deployment_artifacts.items()
        }

    @property
    def data_artifacts(
        self,
    ) -> Dict[str, Dict[str, "ArtifactVersionResponse"]]:
        """Get all data artifacts linked to this model version.

        Returns:
            Dictionary of data artifacts with versions as
            Dict[str, Dict[str, ArtifactResponse]]
        """
        logger.warning(
            "ModelVersionResponse.data_artifacts is deprecated and will be "
            "removed in a future release."
        )

        from zenml.client import Client

        data_artifact_types = [
            value
            for value in ArtifactType.values()
            if value
            not in [ArtifactType.MODEL.value, ArtifactType.SERVICE.value]
        ]

        artifact_versions = pagination_utils.depaginate(
            Client().list_artifact_versions,
            model_version_id=self.id,
            type="oneof:" + json.dumps(data_artifact_types),
            project=self.project_id,
        )

        result: Dict[str, Dict[str, "ArtifactVersionResponse"]] = {}
        for artifact_version in artifact_versions:
            result.setdefault(artifact_version.name, {})
            result[artifact_version.name][artifact_version.version] = (
                artifact_version
            )

        return result

    @property
    def deployment_artifacts(
        self,
    ) -> Dict[str, Dict[str, "ArtifactVersionResponse"]]:
        """Get all deployment artifacts linked to this model version.

        Returns:
            Dictionary of deployment artifacts with versions as
            Dict[str, Dict[str, ArtifactResponse]]
        """
        logger.warning(
            "ModelVersionResponse.deployment_artifacts is deprecated and will "
            "be removed in a future release."
        )

        from zenml.client import Client

        artifact_versions = pagination_utils.depaginate(
            Client().list_artifact_versions,
            model_version_id=self.id,
            type=ArtifactType.SERVICE,
            project=self.project_id,
        )

        result: Dict[str, Dict[str, "ArtifactVersionResponse"]] = {}
        for artifact_version in artifact_versions:
            result.setdefault(artifact_version.name, {})
            result[artifact_version.name][artifact_version.version] = (
                artifact_version
            )

        return result

    @property
    def pipeline_run_ids(self) -> Dict[str, UUID]:
        """Pipeline runs linked to this model version.

        Returns:
            Pipeline runs linked to this model version.
        """
        logger.warning(
            "ModelVersionResponse.pipeline_run_ids is deprecated and will be "
            "removed in a future release."
        )

        from zenml.client import Client

        return {
            link.pipeline_run.name: link.pipeline_run.id
            for link in pagination_utils.depaginate(
                Client().list_model_version_pipeline_run_links,
                model_version_id=self.id,
            )
        }

    @property
    def pipeline_runs(self) -> Dict[str, "PipelineRunResponse"]:
        """Get all pipeline runs linked to this version.

        Returns:
            Dictionary of Pipeline Runs as PipelineRunResponseModel
        """
        logger.warning(
            "ModelVersionResponse.pipeline_runs is deprecated and will be "
            "removed in a future release."
        )

        from zenml.client import Client

        return {
            link.pipeline_run.name: link.pipeline_run
            for link in pagination_utils.depaginate(
                Client().list_model_version_pipeline_run_links,
                model_version_id=self.id,
            )
        }

    def _get_linked_object(
        self,
        name: str,
        version: Optional[str] = None,
        type: Optional[ArtifactType] = None,
    ) -> Optional["ArtifactVersionResponse"]:
        """Get the artifact linked to this model version given type.

        Args:
            name: The name of the artifact to retrieve.
            version: The version of the artifact to retrieve (None for
                latest/non-versioned)
            type: The type of the artifact to filter by.

        Returns:
            Specific version of an artifact from collection or None
        """
        from zenml.client import Client

        artifact_versions = Client().list_artifact_versions(
            sort_by="desc:created",
            size=1,
            artifact=name,
            version=version,
            model_version_id=self.id,
            type=type,
            project=self.project_id,
            hydrate=True,
        )

        if not artifact_versions.items:
            return None
        return artifact_versions.items[0]

    def get_artifact(
        self,
        name: str,
        version: Optional[str] = None,
    ) -> Optional["ArtifactVersionResponse"]:
        """Get the artifact linked to this model version.

        Args:
            name: The name of the artifact to retrieve.
            version: The version of the artifact to retrieve (None for
                latest/non-versioned)

        Returns:
            Specific version of an artifact or None
        """
        return self._get_linked_object(name, version)

    def get_model_artifact(
        self,
        name: str,
        version: Optional[str] = None,
    ) -> Optional["ArtifactVersionResponse"]:
        """Get the model artifact linked to this model version.

        Args:
            name: The name of the model artifact to retrieve.
            version: The version of the model artifact to retrieve (None for
                latest/non-versioned)

        Returns:
            Specific version of the model artifact or None
        """
        return self._get_linked_object(name, version, ArtifactType.MODEL)

    def get_data_artifact(
        self,
        name: str,
        version: Optional[str] = None,
    ) -> Optional["ArtifactVersionResponse"]:
        """Get the data artifact linked to this model version.

        Args:
            name: The name of the data artifact to retrieve.
            version: The version of the data artifact to retrieve (None for
                latest/non-versioned)

        Returns:
            Specific version of the data artifact or None
        """
        return self._get_linked_object(name, version, ArtifactType.DATA)

    def get_deployment_artifact(
        self,
        name: str,
        version: Optional[str] = None,
    ) -> Optional["ArtifactVersionResponse"]:
        """Get the deployment artifact linked to this model version.

        Args:
            name: The name of the deployment artifact to retrieve.
            version: The version of the deployment artifact to retrieve (None for
                latest/non-versioned)

        Returns:
            Specific version of the deployment artifact or None
        """
        return self._get_linked_object(name, version, ArtifactType.SERVICE)

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


# ------------------ Filter Model ------------------


class ModelVersionFilter(
    ProjectScopedFilter, TaggableFilter, RunMetadataFilterMixin
):
    """Filter model for model versions."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *ProjectScopedFilter.FILTER_EXCLUDE_FIELDS,
        *TaggableFilter.FILTER_EXCLUDE_FIELDS,
        *RunMetadataFilterMixin.FILTER_EXCLUDE_FIELDS,
        "model",
    ]
    CUSTOM_SORTING_OPTIONS: ClassVar[List[str]] = [
        *ProjectScopedFilter.CUSTOM_SORTING_OPTIONS,
        *TaggableFilter.CUSTOM_SORTING_OPTIONS,
        *RunMetadataFilterMixin.CUSTOM_SORTING_OPTIONS,
    ]
    CLI_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *ProjectScopedFilter.CLI_EXCLUDE_FIELDS,
        *TaggableFilter.CLI_EXCLUDE_FIELDS,
        *RunMetadataFilterMixin.CLI_EXCLUDE_FIELDS,
    ]
    API_MULTI_INPUT_PARAMS: ClassVar[List[str]] = [
        *ProjectScopedFilter.API_MULTI_INPUT_PARAMS,
        *TaggableFilter.API_MULTI_INPUT_PARAMS,
        *RunMetadataFilterMixin.API_MULTI_INPUT_PARAMS,
    ]

    name: Optional[str] = Field(
        default=None,
        description="The name of the Model Version",
    )
    number: Optional[int] = Field(
        default=None,
        description="The number of the Model Version",
    )
    stage: Optional[Union[str, ModelStages]] = Field(
        description="The model version stage",
        default=None,
        union_mode="left_to_right",
    )
    model: Optional[Union[str, UUID]] = Field(
        default=None,
        description="The name or ID of the model which the search is scoped "
        "to. This field must always be set and is always applied in addition "
        "to the other filters, regardless of the value of the "
        "logical_operator field.",
        union_mode="left_to_right",
    )

    def get_custom_filters(
        self, table: Type["AnySchema"]
    ) -> List[Union["ColumnElement[bool]"]]:
        """Get custom filters.

        Args:
            table: The query table.

        Returns:
            A list of custom filters.
        """
        from sqlalchemy import and_

        from zenml.zen_stores.schemas import (
            ModelSchema,
            ModelVersionSchema,
        )

        custom_filters = super().get_custom_filters(table)

        if self.model:
            model_filter = and_(
                ModelVersionSchema.model_id == ModelSchema.id,  # type: ignore[arg-type]
                self.generate_name_or_id_query_conditions(
                    value=self.model, table=ModelSchema
                ),
            )
            custom_filters.append(model_filter)

        return custom_filters
