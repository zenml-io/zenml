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
"""Model user facing interface to pass into pipeline or step."""

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Union,
)
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

from zenml.enums import MetadataResourceTypes, ModelStages
from zenml.exceptions import EntityExistsError
from zenml.logger import get_logger
from zenml.pipelines.pipeline_context import get_pipeline_context
from zenml.utils.pydantic_utils import before_validator_handler
from zenml.utils.string_utils import format_name_template

if TYPE_CHECKING:
    from zenml.metadata.metadata_types import MetadataType
    from zenml.models import (
        ArtifactVersionResponse,
        ModelResponse,
        ModelVersionResponse,
        PipelineRunResponse,
    )

logger = get_logger(__name__)


class Model(BaseModel):
    """Model class to pass into pipeline or step to set it into a model context.

    name: The name of the model.
    license: The license under which the model is created.
    description: The description of the model.
    audience: The target audience of the model.
    use_cases: The use cases of the model.
    limitations: The known limitations of the model.
    trade_offs: The tradeoffs of the model.
    ethics: The ethical implications of the model.
    tags: Tags associated with the model.
    version: The version name, version number or stage is optional and points model context
        to a specific version/stage. If skipped new version will be created. `version`
        also supports placeholders: standard `{date}` and `{time}` and any custom placeholders
        that are passed as substitutions in the pipeline or step decorators.
    save_models_to_registry: Whether to save all ModelArtifacts to Model Registry,
        if available in active stack.
    """

    name: str
    license: Optional[str] = None
    description: Optional[str] = None
    audience: Optional[str] = None
    use_cases: Optional[str] = None
    limitations: Optional[str] = None
    trade_offs: Optional[str] = None
    ethics: Optional[str] = None
    tags: Optional[List[str]] = None
    version: Optional[Union[ModelStages, int, str]] = Field(
        default=None, union_mode="smart"
    )
    save_models_to_registry: bool = True

    # technical attributes
    model_version_id: Optional[UUID] = None
    suppress_class_validation_warnings: bool = False
    _model_id: UUID = PrivateAttr(None)
    _number: Optional[int] = PrivateAttr(None)
    _created_model_version: bool = PrivateAttr(False)

    # TODO: In Pydantic v2, the `model_` is a protected namespaces for all
    #  fields defined under base models. If not handled, this raises a warning.
    #  It is possible to suppress this warning message with the following
    #  configuration, however the ultimate solution is to rename these fields.
    #  Even though they do not cause any problems right now, if we are not
    #  careful we might overwrite some fields protected by pydantic.
    model_config = ConfigDict(protected_namespaces=())

    #########################
    #    Public methods     #
    #########################
    @property
    def id(self) -> UUID:
        """Get version id from the Model Control Plane.

        Returns:
            ID of the model version or None, if model version
                doesn't exist and can only be read given current
                config (you used stage name or number as
                a version name).

        Raises:
            RuntimeError: if model version doesn't exist and
                cannot be fetched from the Model Control Plane.
        """
        if self.model_version_id is None:
            try:
                mv = self._get_or_create_model_version()
                self.model_version_id = mv.id
            except RuntimeError as e:
                raise RuntimeError(
                    f"Version `{self.version}` of `{self.name}` model doesn't "
                    "exist and cannot be fetched from the Model Control Plane."
                ) from e
        return self.model_version_id

    @property
    def model_id(self) -> UUID:
        """Get model id from the Model Control Plane.

        Returns:
            The UUID of the model containing this model version.
        """
        if self._model_id is None:
            self._get_or_create_model()
        return self._model_id

    @property
    def number(self) -> int:
        """Get version number from  the Model Control Plane.

        Returns:
            Number of the model version or None, if model version
                doesn't exist and can only be read given current
                config (you used stage name or number as
                a version name).

        Raises:
            KeyError: if model version doesn't exist and
                cannot be fetched from the Model Control Plane.
        """
        if self._number is None:
            try:
                mv = self._get_or_create_model_version()
                self._number = mv.number
            except RuntimeError as e:
                raise KeyError(
                    f"Version `{self.version}` of `{self.name}` model doesn't "
                    "exist and cannot be fetched from the Model Control Plane."
                ) from e
        return self._number

    @property
    def stage(self) -> Optional[ModelStages]:
        """Get version stage from  the Model Control Plane.

        Returns:
            Stage of the model version or None, if model version
                doesn't exist and can only be read given current
                config (you used stage name or number as
                a version name).
        """
        try:
            stage = self._get_or_create_model_version().stage
            if stage:
                return ModelStages(stage)
        except RuntimeError:
            logger.info(
                f"Version `{self.version}` of `{self.name}` model doesn't "
                "exist and cannot be fetched from the Model Control Plane."
            )
        return None

    def load_artifact(self, name: str, version: Optional[str] = None) -> Any:
        """Load artifact from the Model Control Plane.

        Args:
            name: Name of the artifact to load.
            version: Version of the artifact to load.

        Returns:
            The loaded artifact.

        Raises:
            ValueError: if the model version is not linked to any artifact with
                the given name and version.
        """
        from zenml.artifacts.utils import load_artifact
        from zenml.models import ArtifactVersionResponse

        artifact = self.get_artifact(name=name, version=version)

        if not isinstance(artifact, ArtifactVersionResponse):
            raise ValueError(
                f"Version {self.version} of model {self.name} does not have "
                f"an artifact with name {name} and version {version}."
            )

        return load_artifact(artifact.id, str(artifact.version))

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
            Specific version of the artifact or placeholder in the design time
                of the pipeline.
        """
        if lazy := self._lazy_artifact_get(name, version):
            return lazy

        return self._get_or_create_model_version().get_artifact(
            name=name,
            version=version,
        )

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
            Specific version of the model artifact or placeholder in the design
                time of the pipeline.
        """
        if lazy := self._lazy_artifact_get(name, version):
            return lazy

        return self._get_or_create_model_version().get_model_artifact(
            name=name,
            version=version,
        )

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
            Specific version of the data artifact or placeholder in the design
            time of the pipeline.
        """
        if lazy := self._lazy_artifact_get(name, version):
            return lazy

        return self._get_or_create_model_version().get_data_artifact(
            name=name,
            version=version,
        )

    def get_deployment_artifact(
        self,
        name: str,
        version: Optional[str] = None,
    ) -> Optional["ArtifactVersionResponse"]:
        """Get the deployment artifact linked to this model version.

        Args:
            name: The name of the deployment artifact to retrieve.
            version: The version of the deployment artifact to retrieve (None
                for latest/non-versioned)

        Returns:
            Specific version of the deployment artifact or placeholder in the
            design time of the pipeline.
        """
        if lazy := self._lazy_artifact_get(name, version):
            return lazy

        return self._get_or_create_model_version().get_deployment_artifact(
            name=name,
            version=version,
        )

    def get_pipeline_run(self, name: str) -> "PipelineRunResponse":
        """Get pipeline run linked to this version.

        Args:
            name: The name of the pipeline run to retrieve.

        Returns:
            PipelineRun as PipelineRunResponse
        """
        return self._get_or_create_model_version().get_pipeline_run(name=name)

    def set_stage(
        self, stage: Union[str, ModelStages], force: bool = False
    ) -> None:
        """Sets this Model to a desired stage.

        Args:
            stage: the target stage for model version.
            force: whether to force archiving of current model version in
                target stage or raise.
        """
        self._get_or_create_model_version().set_stage(stage=stage, force=force)

    def log_metadata(
        self,
        metadata: Dict[str, "MetadataType"],
    ) -> None:
        """Log model version metadata.

        This function can be used to log metadata for current model version.

        Args:
            metadata: The metadata to log.
        """
        from zenml.client import Client
        from zenml.models import RunMetadataResource

        response = self._get_or_create_model_version()
        Client().create_run_metadata(
            metadata=metadata,
            resources=[
                RunMetadataResource(
                    id=response.id, type=MetadataResourceTypes.MODEL_VERSION
                )
            ],
        )

    @property
    def run_metadata(self) -> Dict[str, "MetadataType"]:
        """Get model version run metadata.

        Returns:
            The model version run metadata.

        Raises:
            RuntimeError: If the model version run metadata cannot be fetched.
        """
        from zenml.metadata.lazy_load import RunMetadataLazyGetter

        try:
            get_pipeline_context()
            # avoid exposing too much of internal details by keeping the return type
            return RunMetadataLazyGetter(  # type: ignore[return-value]
                self.name,
                self._lazy_version,
            )
        except RuntimeError:
            pass

        response = self._get_or_create_model_version(hydrate=True)
        if response.run_metadata is None:
            raise RuntimeError(
                "Failed to fetch metadata of this model version."
            )
        return response.run_metadata

    def delete_artifact(
        self,
        name: str,
        version: Optional[str] = None,
        only_link: bool = True,
        delete_metadata: bool = True,
        delete_from_artifact_store: bool = False,
    ) -> None:
        """Delete the artifact linked to this model version.

        Args:
            name: The name of the artifact to delete.
            version: The version of the artifact to delete (None for
                latest/non-versioned)
            only_link: Whether to only delete the link to the artifact.
            delete_metadata: Whether to delete the metadata of the artifact.
            delete_from_artifact_store: Whether to delete the artifact from the
                artifact store.
        """
        from zenml.client import Client
        from zenml.models import ArtifactVersionResponse

        artifact_version = self.get_artifact(name, version)
        if isinstance(artifact_version, ArtifactVersionResponse):
            client = Client()
            client.delete_model_version_artifact_link(
                model_version_id=self.id,
                artifact_version_id=artifact_version.id,
            )
            if not only_link:
                client.delete_artifact_version(
                    name_id_or_prefix=artifact_version.id,
                    delete_metadata=delete_metadata,
                    delete_from_artifact_store=delete_from_artifact_store,
                )

    def delete_all_artifacts(
        self,
        only_link: bool = True,
        delete_from_artifact_store: bool = False,
    ) -> None:
        """Delete all artifacts linked to this model version.

        Args:
            only_link: Whether to only delete the link to the artifact.
            delete_from_artifact_store: Whether to delete the artifact from
                the artifact store.
        """
        from zenml.client import Client

        client = Client()

        if not only_link and delete_from_artifact_store:
            mv = self._get_model_version()
            artifact_responses = mv.data_artifacts
            artifact_responses.update(mv.model_artifacts)
            artifact_responses.update(mv.deployment_artifacts)

            for artifact_ in artifact_responses.values():
                for artifact_response_ in artifact_.values():
                    client._delete_artifact_from_artifact_store(
                        artifact_version=artifact_response_
                    )

        client.delete_all_model_version_artifact_links(self.id, only_link)

    def _lazy_artifact_get(
        self,
        name: str,
        version: Optional[str] = None,
    ) -> Optional["ArtifactVersionResponse"]:
        from zenml.models.v2.core.artifact_version import (
            LazyArtifactVersionResponse,
        )

        try:
            get_pipeline_context()
            return LazyArtifactVersionResponse(
                lazy_load_name=name,
                lazy_load_version=version,
                lazy_load_model_name=self.name,
                lazy_load_model_version=self._lazy_version,
            )
        except RuntimeError:
            pass

        return None

    def __eq__(self, other: object) -> bool:
        """Check two Models for equality.

        Args:
            other: object to compare with

        Returns:
            True, if equal, False otherwise.
        """
        if not isinstance(other, Model):
            return NotImplemented
        if self.name != other.name:
            return False
        if self.name == other.name and self.version == other.version:
            return True
        self_mv = self._get_or_create_model_version()
        other_mv = other._get_or_create_model_version()
        return self_mv.id == other_mv.id

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def _root_validator(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate all in one.

        Args:
            data: Dict of values.

        Returns:
            Dict of validated values.

        Raises:
            ValueError: If the model version id, but call is not internal.
        """
        suppress_class_validation_warnings = data.get(
            "suppress_class_validation_warnings",
            False,
        )
        if not suppress_class_validation_warnings and data.get(
            "model_version_id", None
        ):
            raise ValueError(
                "`model_version_id` field is for internal use only"
            )

        version = data.get("version", None)

        if (
            version in [stage.value for stage in ModelStages]
            and not suppress_class_validation_warnings
        ):
            logger.info(
                f"Version `{version}` matches one of the possible "
                "`ModelStages` and will be fetched using stage."
            )
        if str(version).isnumeric() and not suppress_class_validation_warnings:
            logger.info(
                f"`version` `{version}` is numeric and will be fetched "
                "using version number."
            )
        data["suppress_class_validation_warnings"] = True
        return data

    def _get_or_create_model(self) -> "ModelResponse":
        """This method should get or create a model from Model Control Plane.

        New model is created implicitly, if missing, otherwise fetched.

        Returns:
            The model based on configuration.
        """
        from zenml.client import Client
        from zenml.models import ModelRequest

        zenml_client = Client()
        # backup logic, if the Model class is used directly from the code
        self.name = format_name_template(self.name, substitutions={})
        if self.model_version_id:
            mv = zenml_client.get_model_version(
                model_version_name_or_number_or_id=self.model_version_id,
            )
            model = mv.model
        else:
            try:
                model = zenml_client.zen_store.get_model(
                    model_name_or_id=self.name
                )
            except KeyError:
                model_request = ModelRequest(
                    name=self.name,
                    license=self.license,
                    description=self.description,
                    audience=self.audience,
                    use_cases=self.use_cases,
                    limitations=self.limitations,
                    trade_offs=self.trade_offs,
                    ethics=self.ethics,
                    user=zenml_client.active_user.id,
                    workspace=zenml_client.active_workspace.id,
                    save_models_to_registry=self.save_models_to_registry,
                )
                model_request = ModelRequest.model_validate(model_request)
                try:
                    model = zenml_client.zen_store.create_model(
                        model=model_request
                    )
                    logger.info(
                        f"New model `{self.name}` was created implicitly."
                    )
                except EntityExistsError:
                    model = zenml_client.zen_store.get_model(
                        model_name_or_id=self.name
                    )

        self._model_id = model.id
        return model

    def _get_model_version(
        self, hydrate: bool = True
    ) -> "ModelVersionResponse":
        """This method gets a model version from Model Control Plane.

        Args:
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The model version based on configuration.
        """
        from zenml.client import Client

        zenml_client = Client()
        if self.model_version_id:
            mv = zenml_client.get_model_version(
                model_version_name_or_number_or_id=self.model_version_id,
                hydrate=hydrate,
            )
        else:
            mv = zenml_client.get_model_version(
                model_name_or_id=self.name,
                model_version_name_or_number_or_id=self.version,
                hydrate=hydrate,
            )
            self.model_version_id = mv.id

        difference: Dict[str, Any] = {}
        if mv.metadata:
            if self.description and mv.description != self.description:
                difference["description"] = {
                    "config": self.description,
                    "db": mv.description,
                }
        if self.tags:
            configured_tags = set(self.tags)
            db_tags = {t.name for t in mv.tags}
            if db_tags != configured_tags:
                difference["tags added"] = list(configured_tags - db_tags)
                difference["tags removed"] = list(db_tags - configured_tags)
        if difference:
            logger.warning(
                "Provided model version configuration does not match existing model "
                f"version `{self.name}::{self.version}` with the following "
                f"changes: {difference}. If you want to update the model version "
                "configuration, please use the `zenml model version update` command."
            )

        return mv

    def _get_or_create_model_version(
        self, hydrate: bool = False
    ) -> "ModelVersionResponse":
        """This method should get or create a model and a model version from Model Control Plane.

        A new model is created implicitly if missing, otherwise existing model
        is fetched. Model name is controlled by the `name` parameter.

        Model Version returned by this method is resolved based on model version:
        - If `version` is None, a new model version is created, if not created
            by other steps in same run.
        - If `version` is not None a model version will be fetched based on the
            version:
            - If `version` is set to an integer or digit string, the model
                version with the matching number will be fetched.
            - If `version` is set to a string, the model version with the
                matching version will be fetched.
            - If `version` is set to a `ModelStage`, the model version with the
                matching stage will be fetched.

        Args:
            hydrate: Whether to return a hydrated version of the model version.

        Returns:
            The model version based on configuration.

        Raises:
            RuntimeError: if the model version needs to be created, but
                provided name is reserved.
            RuntimeError: if the model version cannot be created.
        """
        from zenml.client import Client
        from zenml.models import ModelVersionRequest

        model = self._get_or_create_model()

        # backup logic, if the Model class is used directly from the code
        if isinstance(self.version, str):
            self.version = format_name_template(self.version, substitutions={})

        try:
            if self.version or self.model_version_id:
                model_version = self._get_model_version()
            else:
                raise KeyError
        except KeyError:
            if (
                self.version
                and str(self.version).lower() in ModelStages.values()
            ):
                raise RuntimeError(
                    f"Cannot create a model version named {str(self.version)} as "
                    "it matches one of the possible model version stages. If you "
                    "are aiming to fetch model version by stage, check if the "
                    "model version in given stage exists. It might be missing, if "
                    "the pipeline promoting model version to this stage failed,"
                    " as an example. You can explore model versions using "
                    f"`zenml model version list -n {self.name}` CLI command."
                )
            if str(self.version).isnumeric():
                raise RuntimeError(
                    f"Cannot create a model version named {str(self.version)} as "
                    "numeric model version names are reserved. If you "
                    "are aiming to fetch model version by number, check if the "
                    "model version with given number exists. It might be missing, if "
                    "the pipeline creating model version failed,"
                    " as an example. You can explore model versions using "
                    f"`zenml model version list -n {self.name}` CLI command."
                )

            client = Client()
            model_version_request = ModelVersionRequest(
                user=client.active_user.id,
                workspace=client.active_workspace.id,
                name=str(self.version) if self.version else None,
                description=self.description,
                model=model.id,
                tags=self.tags,
            )
            model_version = client.zen_store.create_model_version(
                model_version=model_version_request
            )

            self._created_model_version = True

            logger.info(
                "Created new model version `%s` for model `%s`.",
                model_version.name,
                self.name,
            )

        self.version = model_version.name
        self.model_version_id = model_version.id
        self._model_id = model_version.model.id
        self._number = model_version.number
        return model_version

    def __hash__(self) -> int:
        """Get hash of the `Model`.

        Returns:
            Hash function results
        """
        return hash(
            "::".join(
                (
                    str(v)
                    for v in (
                        self.name,
                        self.version,
                    )
                )
            )
        )

    @property
    def _lazy_version(self) -> Optional[str]:
        """Get version name for lazy loader.

        This getter ensures that new model version
        creation is never triggered here.

        Returns:
            Version name or None if it was not set
        """
        if self._number is not None:
            return str(self._number)
        elif self.version is not None:
            if isinstance(self.version, ModelStages):
                return self.version.value
            return str(self.version)
        return None
