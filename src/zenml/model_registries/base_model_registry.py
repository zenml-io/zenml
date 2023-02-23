#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Base class for all ZenML model registries."""

import datetime
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Type, cast

from pydantic import BaseModel, Field, root_validator

from zenml.enums import StackComponentType
from zenml.stack import Flavor, StackComponent
from zenml.stack.stack_component import StackComponentConfig


class ModelVersionStage(Enum):
    """Enum of the possible stages of a registered model."""

    NONE = "None"
    STAGING = "Staging"
    PRODUCTION = "Production"
    ARCHIVED = "Archived"


class RegisteredModel(BaseModel):
    """Base class for all ZenML registered models.

    Model Registration are the top-level entities in the model registry.
    They serve as a container for all the versions of a model.

    Attributes:
        name: Name of the registered model.
        description: Description of the registered model.
        tags: Tags associated with the registered model.
    """

    name: str
    description: Optional[str]
    tags: Optional[Dict[str, str]] = None


class ModelRegistryModelMetadata(BaseModel):
    """Base class for all ZenML model registry model metadata.

    The `ModelRegistryModelMetadata` class represents metadata associated with
    a registered model version, including information such as the associated
    pipeline name, pipeline run ID, step name, ZenML version, and custom
    attributes. It serves as a blueprint for creating concrete model metadata
    implementations in a registry, and provides a record of the history of a
    model and its development process.
    """

    zenml_version: Optional[str] = None
    zenml_pipeline_run_id: Optional[str] = None
    zenml_pipeline_name: Optional[str] = None
    zenml_pipeline_uuid: Optional[str] = None
    zenml_pipeline_run_uuid: Optional[str] = None
    zenml_step_name: Optional[str] = None
    zenml_workspace: Optional[str] = None

    @property
    def custom_attributes(self) -> Dict[str, str]:
        """Returns a dictionary of custom attributes.

        Returns:
            A dictionary of custom attributes.
        """
        # Return all attributes that are not explicitly defined as Pydantic
        # fields in this class
        return {
            k: str(v)
            for k, v in self.__dict__.items()
            if k not in self.__fields__.keys()
        }

    class Config:
        """Pydantic configuration class."""

        # Allow extra attributes to be set in the metadata
        extra = "allow"


class ModelVersion(BaseModel):
    """Base class for all ZenML model versions.

    The `ModelVersion` class represents a version or snapshot of a registered
    model, including information such as the associated `ModelBundle`, version
    number, creation time, pipeline run information, and metadata. It serves as
    a blueprint for creating concrete model version implementations in a registry,
    and provides a record of the history of a model and its development process.

    All model registries must extend this class with their own specific fields.

    Attributes:
        model_registration: The registered model associated with this model
        model_source_uri: The URI of the model bundle associated with this model
        version: The version number of this model version
        description: The description of this model version
        created_at: The creation time of this model version
        last_updated_at: The last updated time of this model version
        stage: The current stage of this model version
        tags: Tags associated with this model version
        metadata: Metadata associated with this model version
    """

    version: str
    model_source_uri: str
    model_registration: RegisteredModel
    description: Optional[str] = None
    created_at: Optional[datetime.datetime] = None
    last_updated_at: Optional[datetime.datetime] = None
    stage: ModelVersionStage = ModelVersionStage.NONE
    tags: Dict[str, str] = Field(default_factory=dict)
    metadata: ModelRegistryModelMetadata = Field(
        default_factory=ModelRegistryModelMetadata
    )

    @root_validator
    def fill_in_out_zenml_metadata(
        cls, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fills in ZenML metadata if not provided.

        Args:
            values: The values to validate.

        Returns:
            The validated values.
        """
        if values.get("metadata") is None:
            values["metadata"] = ModelRegistryModelMetadata()
        tags = values.get("tags")
        if tags:
            if "zenml_version" in tags.keys():
                values["metadata"].zenml_version = tags["zenml_version"]
                values["tags"].pop("zenml_version")
            if "zenml_pipeline_run_id" in tags.keys():
                values["metadata"].zenml_pipeline_run_id = tags[
                    "zenml_pipeline_run_id"
                ]
                values["tags"].pop("zenml_pipeline_run_id")
            if "zenml_pipeline_name" in tags.keys():
                values["metadata"].zenml_pipeline_name = tags[
                    "zenml_pipeline_name"
                ]
                values["tags"].pop("zenml_pipeline_name")
            if "zenml_step_name" in tags.keys():
                values["metadata"].zenml_step_name = tags["zenml_step_name"]
                values["tags"].pop("zenml_step_name")
            if "zenml_workspace" in tags.keys():
                values["metadata"].zenml_workspace = tags["zenml_workspace"]
                values["tags"].pop("zenml_workspace")
            if "zenml_pipeline_uuid" in tags.keys():
                values["metadata"].zenml_pipeline_uuid = tags[
                    "zenml_pipeline_uuid"
                ]
                values["tags"].pop("zenml_pipeline_uuid")
            if "zenml_pipeline_run_uuid" in tags.keys():
                values["metadata"].zenml_pipeline_run_uuid = tags[
                    "zenml_pipeline_run_uuid"
                ]
                values["tags"].pop("zenml_pipeline_run_uuid")
        return values


class BaseModelRegistryConfig(StackComponentConfig):
    """Base config for model registries."""


class BaseModelRegistry(StackComponent, ABC):
    """Base class for all ZenML model registries."""

    @property
    def config(self) -> BaseModelRegistryConfig:
        """Returns the config of the model registries.

        Returns:
            The config of the model registries.
        """
        return cast(BaseModelRegistryConfig, self._config)

    # ---------
    # Model Registration Methods
    # ---------

    @abstractmethod
    def register_model(
        self,
        name: str,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> RegisteredModel:
        """Registers a model in the model registry.

        Args:
            name: The name of the registered model.
            description: The description of the registered model.
            tags: The tags associated with the registered model.

        Returns:
            The registered model.

        Raises:
            zenml.exceptions.EntityExistsError: If a model with the same name already exists.
            RuntimeError: If registration fails.
        """

    @abstractmethod
    def delete_model(
        self,
        name: str,
    ) -> None:
        """Deletes a registered model from the model registry.

        Args:
            name: The name of the registered model.

        Raises:
            KeyError: If the model does not exist.
            RuntimeError: If deletion fails.
        """

    @abstractmethod
    def update_model(
        self,
        name: str,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        remove_tags: Optional[List[str]] = None,
    ) -> RegisteredModel:
        """Updates a registered model in the model registry.

        Args:
            name: The name of the registered model.
            description: The description of the registered model.
            tags: The tags associated with the registered model.
            remove_tags: The tags to remove from the registered model.

        Raises:
            KeyError: If the model does not exist.
            RuntimeError: If update fails.
        """

    @abstractmethod
    def get_model(self, name: str) -> RegisteredModel:
        """Gets a registered model from the model registry.

        Args:
            name: The name of the registered model.

        Returns:
            The registered model.

        Raises:
            zenml.exceptions.EntityExistsError: If the model does not exist.
            RuntimeError: If retrieval fails.
        """

    @abstractmethod
    def list_models(
        self,
        name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> List[RegisteredModel]:
        """Lists all registered models in the model registry.

        Args:
            name: The name of the registered model.
            tags: The tags associated with the registered model.

        Returns:
            A list of registered models.
        """

    @abstractmethod
    def check_model_exists(self, name: str) -> bool:
        """Checks if a model exists in the model registry.

        This method is used to check if a model exists before registering
        a new model, deleting a model, or updating a model.

        Args:
            name: The name of the registered model.

        Returns:
            True if the model exists, False otherwise.
        """

    # ---------
    # Model Version Methods
    # ---------

    @abstractmethod
    def register_model_version(
        self,
        name: str,
        version: str,
        model_source_uri: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        metadata: ModelRegistryModelMetadata = Field(
            default_factory=ModelRegistryModelMetadata
        ),
        **kwargs: Any,
    ) -> ModelVersion:
        """Registers a model version in the model registry.

        Args:
            name: The name of the registered model.
            model_source_uri: The source URI of the model.
            version: The version of the model version.
            description: The description of the model version.
            tags: The tags associated with the model version.
            metadata: The metadata associated with the model
                version.
            **kwargs: Additional keyword arguments.

        Returns:
            The registered model version.

        Raises:
            RuntimeError: If registration fails.
        """

    @abstractmethod
    def delete_model_version(
        self,
        name: str,
        version: str,
    ) -> None:
        """Deletes a model version from the model registry.

        Args:
            name: The name of the registered model.
            version: The version of the model version to delete.

        Raises:
            KeyError: If the model version does not exist.
            RuntimeError: If deletion fails.
        """

    @abstractmethod
    def update_model_version(
        self,
        name: str,
        version: str,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        remove_tags: Optional[List[str]] = None,
        stage: Optional[ModelVersionStage] = None,
    ) -> ModelVersion:
        """Updates a model version in the model registry.

        Args:
            name: The name of the registered model.
            version: The version of the model version to update.
            description: The description of the model version.
            tags: The tags associated with the model version.
            remove_tags: The tags to remove from the model version.
            stage: The stage of the model version.

        Returns:
            The updated model version.

        Raises:
            KeyError: If the model version does not exist.
            RuntimeError: If update fails.
        """

    @abstractmethod
    def list_model_versions(
        self,
        name: Optional[str] = None,
        model_source_uri: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> List[ModelVersion]:
        """Lists all model versions for a registered model.

        Args:
            name: The name of the registered model.
            model_source_uri: The model source URI of the registered model.
            tags: The tags associated with the registered model.
            kwargs: Additional keyword arguments.

        Returns:
            A list of model versions.
        """

    @abstractmethod
    def get_model_version(self, name: str, version: str) -> ModelVersion:
        """Gets a model version for a registered model.

        Args:
            name: The name of the registered model.
            version: The version of the model version to get.

        Returns:
            The model version.

        Raises:
            KeyError: If the model version does not exist.
            RuntimeError: If retrieval fails.
        """

    @abstractmethod
    def check_model_version_exists(
        self,
        name: str,
        version: str,
    ) -> bool:
        """Checks if a model version exists in the model registry.

        This method is used to check if a model version exists in the model
        registry before attempting to get it, load it, delete it, or update it.

        Args:
            name: The name of the registered model.
            version: The version of the model version to check.

        Returns:
            True if the model version exists, False otherwise.
        """

    @abstractmethod
    def load_model_version(
        self,
        name: str,
        version: str,
        **kwargs: Any,
    ) -> Any:
        """Loads a model version from the model registry.

        Args:
            name: The name of the registered model.
            version: The version of the model version to load.
            **kwargs: Additional keyword arguments.

        Returns:
            The loaded model version.

        Raises:
            KeyError: If the model version does not exist.
            RuntimeError: If loading fails.
        """


class BaseModelRegistryFlavor(Flavor):
    """Base class for all ZenML model registry flavors."""

    @property
    def type(self) -> StackComponentType:
        """Type of the flavor.

        Returns:
            StackComponentType: The type of the flavor.
        """
        return StackComponentType.MODEL_REGISTRY

    @property
    def config_class(self) -> Type[BaseModelRegistryConfig]:
        """Config class for this flavor.

        Returns:
            The config class for this flavor.
        """
        return BaseModelRegistryConfig

    @property
    @abstractmethod
    def implementation_class(self) -> Type[StackComponent]:
        """Returns the implementation class for this flavor.

        Returns:
            The implementation class for this flavor.
        """
        return BaseModelRegistry
