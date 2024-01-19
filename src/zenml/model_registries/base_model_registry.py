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
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type, cast

from pydantic import BaseModel

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
        metadata: metadata associated with the registered model.
    """

    name: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None


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
    zenml_run_name: Optional[str] = None
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

    def dict(
        self,
        *,
        exclude_unset: bool = False,
        exclude_none: bool = True,
        **kwargs: Any,
    ) -> Dict[str, str]:
        """Returns a dictionary representation of the metadata.

        This method overrides the default Pydantic `dict` method to allow
        for the exclusion of fields with a value of None.

        Args:
            exclude_unset: Whether to exclude unset attributes.
            exclude_none: Whether to exclude None attributes.
            **kwargs: Additional keyword arguments.

        Returns:
            A dictionary representation of the metadata.
        """
        if exclude_none:
            return {
                k: v
                for k, v in super()
                .dict(exclude_unset=exclude_unset, **kwargs)
                .items()
                if v is not None
            }
        else:
            return super().dict(exclude_unset=exclude_unset, **kwargs)

    class Config:
        """Pydantic configuration class."""

        # Allow extra attributes to be set in the metadata
        extra = "allow"


class RegistryModelVersion(BaseModel):
    """Base class for all ZenML model versions.

    The `RegistryModelVersion` class represents a version or snapshot of a registered
    model, including information such as the associated `ModelBundle`, version
    number, creation time, pipeline run information, and metadata. It serves as
    a blueprint for creating concrete model version implementations in a registry,
    and provides a record of the history of a model and its development process.

    All model registries must extend this class with their own specific fields.

    Attributes:
        registered_model: The registered model associated with this model
        model_source_uri: The URI of the model bundle associated with this model,
            The model source can not be changed after the model version is created.
            If the model source is changed, a new model version must be created.
        model_format: The format of the model bundle associated with this model,
            The model format is set automatically by the model registry integration
            and can not be changed after the model version is created.
        model_library: The library used to create the model bundle associated with
            this model, The model library refers to the library used to create the
            model source, e.g. TensorFlow, PyTorch, etc. For some model registries,
            the model library is set retrieved automatically by the model registry.
        version: The version number of this model version
        description: The description of this model version
        created_at: The creation time of this model version
        last_updated_at: The last updated time of this model version
        stage: The current stage of this model version
        metadata: Metadata associated with this model version
    """

    version: str
    model_source_uri: str
    model_format: str
    model_library: Optional[str] = None
    registered_model: RegisteredModel
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    last_updated_at: Optional[datetime] = None
    stage: ModelVersionStage = ModelVersionStage.NONE
    metadata: Optional[ModelRegistryModelMetadata] = None


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
        metadata: Optional[Dict[str, str]] = None,
    ) -> RegisteredModel:
        """Registers a model in the model registry.

        Args:
            name: The name of the registered model.
            description: The description of the registered model.
            metadata: The metadata associated with the registered model.

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
        metadata: Optional[Dict[str, str]] = None,
        remove_metadata: Optional[List[str]] = None,
    ) -> RegisteredModel:
        """Updates a registered model in the model registry.

        Args:
            name: The name of the registered model.
            description: The description of the registered model.
            metadata: The metadata associated with the registered model.
            remove_metadata: The metadata to remove from the registered model.

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
        metadata: Optional[Dict[str, str]] = None,
    ) -> List[RegisteredModel]:
        """Lists all registered models in the model registry.

        Args:
            name: The name of the registered model.
            metadata: The metadata associated with the registered model.

        Returns:
            A list of registered models.
        """

    # ---------
    # Model Version Methods
    # ---------

    @abstractmethod
    def register_model_version(
        self,
        name: str,
        version: Optional[str] = None,
        model_source_uri: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[ModelRegistryModelMetadata] = None,
        **kwargs: Any,
    ) -> RegistryModelVersion:
        """Registers a model version in the model registry.

        Args:
            name: The name of the registered model.
            model_source_uri: The source URI of the model.
            version: The version of the model version.
            description: The description of the model version.
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
        metadata: Optional[ModelRegistryModelMetadata] = None,
        remove_metadata: Optional[List[str]] = None,
        stage: Optional[ModelVersionStage] = None,
    ) -> RegistryModelVersion:
        """Updates a model version in the model registry.

        Args:
            name: The name of the registered model.
            version: The version of the model version to update.
            description: The description of the model version.
            metadata: Metadata associated with this model version.
            remove_metadata: The metadata to remove from the model version.
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
        metadata: Optional[ModelRegistryModelMetadata] = None,
        stage: Optional[ModelVersionStage] = None,
        count: Optional[int] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        order_by_date: Optional[str] = None,
        **kwargs: Any,
    ) -> Optional[List[RegistryModelVersion]]:
        """Lists all model versions for a registered model.

        Args:
            name: The name of the registered model.
            model_source_uri: The model source URI of the registered model.
            metadata: Metadata associated with this model version.
            stage: The stage of the model version.
            count: The number of model versions to return.
            created_after: The timestamp after which to list model versions.
            created_before: The timestamp before which to list model versions.
            order_by_date: Whether to sort by creation time, this can
                be "asc" or "desc".
            kwargs: Additional keyword arguments.

        Returns:
            A list of model versions.
        """

    def get_latest_model_version(
        self,
        name: str,
        stage: Optional[ModelVersionStage] = None,
    ) -> Optional[RegistryModelVersion]:
        """Gets the latest model version for a registered model.

        This method is used to get the latest model version for a registered
        model. If no stage is provided, the latest model version across all
        stages is returned. If a stage is provided, the latest model version
        for that stage is returned.

        Args:
            name: The name of the registered model.
            stage: The stage of the model version.

        Returns:
            The latest model version.
        """
        model_versions = self.list_model_versions(
            name=name, stage=stage, order_by_date="desc", count=1
        )
        if model_versions:
            return model_versions[0]
        return None

    @abstractmethod
    def get_model_version(
        self, name: str, version: str
    ) -> RegistryModelVersion:
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

    @abstractmethod
    def get_model_uri_artifact_store(
        self,
        model_version: RegistryModelVersion,
    ) -> str:
        """Gets the URI artifact store for a model version.

        This method retrieves the URI of the artifact store for a specific model
        version. Its purpose is to ensure that the URI is in the correct format
        for the specific artifact store being used. This is essential for the
        model serving component, which relies on the URI to serve the model
        version. In some cases, the URI may be stored in a different format by
        certain model registry integrations. This method allows us to obtain the
        URI in the correct format, regardless of the integration being used.

        Note: In some cases the URI artifact store may not be available to the
        user, the method should save the target model in one of the other
        artifact stores supported by ZenML and return the URI of that artifact
        store.

        Args:
            model_version: The model version for which to get the URI artifact
                store.

        Returns:
            The URI artifact store for the model version.
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
