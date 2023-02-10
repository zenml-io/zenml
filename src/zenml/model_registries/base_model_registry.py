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

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, cast

from pydantic import BaseModel, Field

from zenml.enums import StackComponentType
from zenml.stack import Flavor, StackComponent
from zenml.stack.stack_component import StackComponentConfig
from zenml.utils.enum_utils import StrEnum


class ModelVersionStageEnum(StrEnum):
    """String Enum of the possible stages of a registered model."""

    NONE = "none"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


class ModelRegistration(BaseModel):
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


class ZenMLModelMetadata(BaseModel):
    """Base class for all ZenML model metadata.

    The `ZenMLModelMetadata` class represents the metadata associated with a
    model version. It includes information about the ZenML version, pipeline run
    ID, pipeline run name, and pipeline step.

    Attributes:
        zenml_version: The ZenML version associated with this model version.
        pipeline_run_id: The pipeline run ID associated with this model version.
        pipeline_run_name: The pipeline run name associated with this model version.
        pipeline_step: The pipeline step associated with this model version.
    """

    zenml_version: Optional[str] = None
    pipeline_run_id: Optional[str] = None
    pipeline_run_name: Optional[str] = None
    pipeline_step: Optional[str] = None


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
        current_stage: The current stage of this model version
        tags: Tags associated with this model version
        model_registry_metadata: The metadata associated with this model version
    """

    model_registration: ModelRegistration
    model_source_uri: str
    description: Optional[str] = None
    version: Optional[str] = None
    created_at: Optional[str] = None
    last_updated_at: Optional[str] = None
    current_stage: Optional[ModelVersionStageEnum] = None
    tags: Dict[str, str] = Field(default_factory=dict)
    model_registry_metadata: Dict[str, str] = Field(default_factory=dict)


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

    @abstractmethod
    def register_model(self, registered_model: ModelRegistration) -> None:
        """Registers a model in the model registry.

        Args:
            registered_model: The model to register.
        """

    @abstractmethod
    def delete_model(self, registered_model: ModelRegistration) -> None:
        """Deletes a registered model from the model registry.

        Args:
            registered_model: The registered model to delete.
        """

    @abstractmethod
    def update_model(self, registered_model: ModelRegistration) -> None:
        """Updates a registered model in the model registry.

        Args:
            registered_model: The registered model to update.
        """

    @abstractmethod
    def list_models(
        self,
        name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> List[ModelRegistration]:
        """Lists all registered models in the model registry.

        Args:
            name: The name of the registered model.
            tags: The tags associated with the registered model.

        Returns:
            A list of registered models.
        """

    @abstractmethod
    def register_model_version(
        self,
        model_version: ModelVersion,
        **kwargs: Any,
    ) -> ModelVersion:
        """Registers a model version in the model registry.

        Args:
            model_version: The model version to register.
            kwargs: Additional keyword arguments.

        Returns:
            The registered model version.
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
        """

    @abstractmethod
    def update_model_version(
        self,
        name: str,
        version: str,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        stage: Optional[ModelVersionStageEnum] = None,
    ) -> ModelVersion:
        """Updates a model version in the model registry.

        Args:
            name: The name of the registered model.
            version: The version of the model version to update.
            description: The description of the model version.
            tags: The tags associated with the model version.
            stage: The stage of the model version.

        Returns:
            The updated model version.
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
        """

    @abstractmethod
    def load_model_version(
        self,
        name: str,
        version: str,
        **kwargs: Any,
    ) -> Any:
        """Loads a model version for a registered model.

        Args:
            name: The name of the registered model.
            version: The version of the model version to load.
            kwargs: Additional keyword arguments.

        Returns:
            The loaded model version.
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
