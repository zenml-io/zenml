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
"""ModelVersion user facing interface to pass into pipeline or step."""

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Union,
)
from uuid import UUID

from pydantic import BaseModel, PrivateAttr, root_validator

from zenml.enums import MetadataResourceTypes, ModelStages
from zenml.exceptions import EntityExistsError
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml import ExternalArtifact
    from zenml.metadata.metadata_types import MetadataType
    from zenml.models import (
        ArtifactVersionResponse,
        ModelResponse,
        ModelVersionResponse,
        PipelineRunResponse,
    )

logger = get_logger(__name__)


class ModelVersion(BaseModel):
    """ModelVersion class to pass into pipeline or step to set it into a model context.

    name: The name of the model.
    license: The license under which the model is created.
    description: The description of the model.
    audience: The target audience of the model.
    use_cases: The use cases of the model.
    limitations: The known limitations of the model.
    trade_offs: The tradeoffs of the model.
    ethics: The ethical implications of the model.
    tags: Tags associated with the model.
    version: The model version name, number or stage is optional and points model context
        to a specific version/stage. If skipped new model version will be created.
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
    version: Optional[Union[ModelStages, int, str]] = None
    save_models_to_registry: bool = True

    suppress_class_validation_warnings: bool = False
    was_created_in_this_run: bool = False

    _model_id: UUID = PrivateAttr(None)
    _id: UUID = PrivateAttr(None)
    _number: int = PrivateAttr(None)

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
        """
        if self._id is None:
            try:
                self._get_or_create_model_version()
            except RuntimeError:
                logger.info(
                    f"Model version `{self.version}` doesn't exist "
                    "and cannot be fetched from the Model Control Plane."
                )
        return self._id

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
        """
        if self._number is None:
            try:
                self._get_or_create_model_version()
            except RuntimeError:
                logger.info(
                    f"Model version `{self.version}` doesn't exist "
                    "and cannot be fetched from the Model Control Plane."
                )
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
                f"Model version `{self.version}` doesn't exist "
                "and cannot be fetched from the Model Control Plane."
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

    def _try_get_as_external_artifact(
        self,
        name: str,
        version: Optional[str] = None,
    ) -> Optional["ExternalArtifact"]:
        from zenml import ExternalArtifact, get_pipeline_context

        try:
            get_pipeline_context()
        except RuntimeError:
            return None

        ea = ExternalArtifact(name=name, version=version, model_version=self)
        return ea

    def get_artifact(
        self,
        name: str,
        version: Optional[str] = None,
    ) -> Optional[Union["ArtifactVersionResponse", "ExternalArtifact"]]:
        """Get the artifact linked to this model version.

        Args:
            name: The name of the artifact to retrieve.
            version: The version of the artifact to retrieve (None for latest/non-versioned)

        Returns:
            Inside pipeline context: ExternalArtifact object as a lazy loader
            Outside of pipeline context: Specific version of the artifact or None
        """
        if response := self._try_get_as_external_artifact(name, version):
            return response
        return self._get_or_create_model_version().get_artifact(
            name=name,
            version=version,
        )

    def get_model_artifact(
        self,
        name: str,
        version: Optional[str] = None,
    ) -> Optional[Union["ArtifactVersionResponse", "ExternalArtifact"]]:
        """Get the model artifact linked to this model version.

        Args:
            name: The name of the model artifact to retrieve.
            version: The version of the model artifact to retrieve (None for latest/non-versioned)

        Returns:
            Inside pipeline context: ExternalArtifact object as a lazy loader
            Outside of pipeline context: Specific version of the model artifact or None
        """
        if response := self._try_get_as_external_artifact(name, version):
            return response
        return self._get_or_create_model_version().get_model_artifact(
            name=name,
            version=version,
        )

    def get_data_artifact(
        self,
        name: str,
        version: Optional[str] = None,
    ) -> Optional[Union["ArtifactVersionResponse", "ExternalArtifact"]]:
        """Get the data artifact linked to this model version.

        Args:
            name: The name of the data artifact to retrieve.
            version: The version of the data artifact to retrieve (None for latest/non-versioned)

        Returns:
            Inside pipeline context: ExternalArtifact object as a lazy loader
            Outside of pipeline context: Specific version of the data artifact or None
        """
        if response := self._try_get_as_external_artifact(name, version):
            return response
        return self._get_or_create_model_version().get_data_artifact(
            name=name,
            version=version,
        )

    def get_deployment_artifact(
        self,
        name: str,
        version: Optional[str] = None,
    ) -> Optional[Union["ArtifactVersionResponse", "ExternalArtifact"]]:
        """Get the deployment artifact linked to this model version.

        Args:
            name: The name of the deployment artifact to retrieve.
            version: The version of the deployment artifact to retrieve (None for latest/non-versioned)

        Returns:
            Inside pipeline context: ExternalArtifact object as a lazy loader
            Outside of pipeline context: Specific version of the deployment artifact or None
        """
        if response := self._try_get_as_external_artifact(name, version):
            return response
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
        """Sets this Model Version to a desired stage.

        Args:
            stage: the target stage for model version.
            force: whether to force archiving of current model version in target stage or raise.
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

        response = self._get_or_create_model_version()
        Client().create_run_metadata(
            metadata=metadata,
            resource_id=response.id,
            resource_type=MetadataResourceTypes.MODEL_VERSION,
        )

    @property
    def metadata(self) -> Dict[str, "MetadataType"]:
        """Get model version metadata.

        Returns:
            The model version metadata.

        Raises:
            RuntimeError: If the model version metadata cannot be fetched.
        """
        response = self._get_or_create_model_version(hydrate=True)
        if response.run_metadata is None:
            raise RuntimeError(
                "Failed to fetch metadata of this model version."
            )
        return {
            name: response.value
            for name, response in response.run_metadata.items()
        }

    #########################
    #   Internal methods    #
    #########################

    class Config:
        """Config class."""

        smart_union = True

    def __eq__(self, other: object) -> bool:
        """Check two ModelVersions for equality.

        Args:
            other: object to compare with

        Returns:
            True, if equal, False otherwise.
        """
        if not isinstance(other, ModelVersion):
            return NotImplemented
        if self.name != other.name:
            return False
        if self.name == other.name and self.version == other.version:
            return True
        self_mv = self._get_or_create_model_version()
        other_mv = other._get_or_create_model_version()
        return self_mv.id == other_mv.id

    @root_validator(pre=True)
    def _root_validator(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate all in one.

        Args:
            values: Dict of values.

        Returns:
            Dict of validated values.
        """
        suppress_class_validation_warnings = values.get(
            "suppress_class_validation_warnings", False
        )
        version = values.get("version", None)

        if (
            version in [stage.value for stage in ModelStages]
            and not suppress_class_validation_warnings
        ):
            logger.info(
                f"`version` `{version}` matches one of the possible `ModelStages` and will be fetched using stage."
            )
        if str(version).isnumeric() and not suppress_class_validation_warnings:
            logger.info(
                f"`version` `{version}` is numeric and will be fetched using version number."
            )
        values["suppress_class_validation_warnings"] = True
        return values

    def _validate_config_in_runtime(self) -> None:
        """Validate that config doesn't conflict with runtime environment."""
        self._get_or_create_model_version()

    def _get_or_create_model(self) -> "ModelResponse":
        """This method should get or create a model from Model Control Plane.

        New model is created implicitly, if missing, otherwise fetched.

        Returns:
            The model based on configuration.
        """
        from zenml.client import Client
        from zenml.models import ModelRequest

        zenml_client = Client()
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
                tags=self.tags,
                user=zenml_client.active_user.id,
                workspace=zenml_client.active_workspace.id,
            )
            model_request = ModelRequest.parse_obj(model_request)
            try:
                model = zenml_client.zen_store.create_model(
                    model=model_request
                )
                logger.info(f"New model `{self.name}` was created implicitly.")
            except EntityExistsError:
                # this is backup logic, if model was created somehow in between get and create calls
                pass
            finally:
                model = zenml_client.zen_store.get_model(
                    model_name_or_id=self.name
                )
        self._model_id = model.id
        return model

    def _get_model_version(self) -> "ModelVersionResponse":
        """This method gets a model version from Model Control Plane.

        Returns:
            The model version based on configuration.
        """
        from zenml.client import Client

        zenml_client = Client()
        mv = zenml_client.get_model_version(
            model_name_or_id=self.name,
            model_version_name_or_number_or_id=self.version,
        )
        if not self._id:
            self._id = mv.id

        return mv

    def _get_or_create_model_version(
        self, hydrate: bool = False
    ) -> "ModelVersionResponse":
        """This method should get or create a model and a model version from Model Control Plane.

        A new model is created implicitly if missing, otherwise existing model is fetched. Model
        name is controlled by the `name` parameter.

        Model Version returned by this method is resolved based on model version:
        - If `version` is None, a new model version is created, if not created by other steps in same run.
        - If `version` is not None a model version will be fetched based on the version:
            - If `version` is set to an integer or digit string, the model version with the matching number will be fetched.
            - If `version` is set to a string, the model version with the matching version will be fetched.
            - If `version` is set to a `ModelStage`, the model version with the matching stage will be fetched.

        Args:
            hydrate: Whether to return a hydrated version of the model version.

        Returns:
            The model version based on configuration.

        Raises:
            RuntimeError: if the model version needs to be created, but provided name is reserved
        """
        from zenml.client import Client
        from zenml.models import ModelVersionRequest

        model = self._get_or_create_model()

        zenml_client = Client()
        model_version_request = ModelVersionRequest(
            user=zenml_client.active_user.id,
            workspace=zenml_client.active_workspace.id,
            name=self.version,
            description=self.description,
            model=model.id,
            tags=self.tags,
        )
        mv_request = ModelVersionRequest.parse_obj(model_version_request)
        try:
            if not self.version:
                try:
                    from zenml import get_step_context

                    context = get_step_context()
                except RuntimeError:
                    pass
                else:
                    # if inside a step context we loop over all
                    # model version configuration to find, if the
                    # model version for current model was already
                    # created in the current run, not to create
                    # new model versions
                    pipeline_mv = context.pipeline_run.config.model_version
                    if (
                        pipeline_mv
                        and pipeline_mv.was_created_in_this_run
                        and pipeline_mv.name == self.name
                        and pipeline_mv.version is not None
                    ):
                        self.version = pipeline_mv.version
                    else:
                        for step in context.pipeline_run.steps.values():
                            step_mv = step.config.model_version
                            if (
                                step_mv
                                and step_mv.was_created_in_this_run
                                and step_mv.name == self.name
                                and step_mv.version is not None
                            ):
                                self.version = step_mv.version
                                break
            if self.version:
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
                    f"`zenml model version list {self.name}` CLI command."
                )
            if str(self.version).isnumeric():
                raise RuntimeError(
                    f"Cannot create a model version named {str(self.version)} as "
                    "numeric model version names are reserved. If you "
                    "are aiming to fetch model version by number, check if the "
                    "model version with given number exists. It might be missing, if "
                    "the pipeline creating model version failed,"
                    " as an example. You can explore model versions using "
                    f"`zenml model version list {self.name}` CLI command."
                )
            model_version = zenml_client.zen_store.create_model_version(
                model_version=mv_request
            )
            self.version = model_version.name
            self.was_created_in_this_run = True
            logger.info(f"New model version `{self.version}` was created.")
        self._id = model_version.id
        self._model_id = model_version.model.id
        self._number = model_version.number
        return model_version

    def _merge(self, model_version: "ModelVersion") -> None:
        self.license = self.license or model_version.license
        self.description = self.description or model_version.description
        self.audience = self.audience or model_version.audience
        self.use_cases = self.use_cases or model_version.use_cases
        self.limitations = self.limitations or model_version.limitations
        self.trade_offs = self.trade_offs or model_version.trade_offs
        self.ethics = self.ethics or model_version.ethics
        if model_version.tags is not None:
            self.tags = list(
                {t for t in self.tags or []}.union(set(model_version.tags))
            )

    def __hash__(self) -> int:
        """Get hash of the `ModelVersion`.

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
