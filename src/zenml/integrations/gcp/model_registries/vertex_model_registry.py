from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, cast

from google.cloud import aiplatform
from google.cloud.aiplatform import Model, ModelRegistry, ModelVersion
from google.cloud.aiplatform.exceptions import NotFound

from zenml.enums import StackComponentType
from zenml.stack import Flavor, StackComponent
from zenml.stack.stack_component import StackComponentConfig
from zenml.model_registries.base_model_registry import (
    BaseModelRegistry,
    ModelRegistryModelMetadata,
    ModelVersionStage,
    RegisteredModel,
    RegistryModelVersion,
)
from zenml.stack.stack_validator import StackValidator
from zenml.logger import get_logger

logger = get_logger(__name__)

class VertexAIModelRegistry(BaseModelRegistry):
    """Register models using Vertex AI."""

    def __init__(self):
        super().__init__()
        aiplatform.init()  # Initialize the Vertex AI SDK

    @property
    def config(self) -> StackComponentConfig:
        """Returns the config of the model registries."""
        return cast(StackComponentConfig, self._config)

    def register_model(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> RegisteredModel:
        """Register a model to the Vertex AI model registry."""
        try:
            model = Model(
                display_name=name,
                description=description,
                labels=metadata
            )
            model.upload()
            return RegisteredModel(name=name, description=description, metadata=metadata)
        except Exception as e:
            raise RuntimeError(f"Failed to register model: {str(e)}")

    def delete_model(
        self,
        name: str,
    ) -> None:
        """Delete a model from the Vertex AI model registry."""
        try:
            model = Model(model_name=name)
            model.delete()
        except NotFound:
            raise KeyError(f"Model with name {name} does not exist.")
        except Exception as e:
            raise RuntimeError(f"Failed to delete model: {str(e)}")

    def update_model(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        remove_metadata: Optional[List[str]] = None,
    ) -> RegisteredModel:
        """Update a model in the Vertex AI model registry."""
        try:
            model = Model(model_name=name)
            if description:
                model.update(description=description)
            if metadata:
                for key, value in metadata.items():
                    model.labels[key] = value
            if remove_metadata:
                for key in remove_metadata:
                    if key in model.labels:
                        del model.labels[key]
            model.update()
            return self.get_model(name)
        except NotFound:
            raise KeyError(f"Model with name {name} does not exist.")
        except Exception as e:
            raise RuntimeError(f"Failed to update model: {str(e)}")

    def get_model(self, name: str) -> RegisteredModel:
        """Get a model from the Vertex AI model registry."""
        try:
            model = Model(model_name=name)
            model_resource = model.gca_resource
            return RegisteredModel(
                name=model_resource.display_name,
                description=model_resource.description,
                metadata=model_resource.labels
            )
        except NotFound:
            raise KeyError(f"Model with name {name} does not exist.")
        except Exception as e:
            raise RuntimeError(f"Failed to get model: {str(e)}")

    def list_models(
        self,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> List[RegisteredModel]:
        """List models in the Vertex AI model registry."""
        filter_expression = ""
        if name:
            filter_expression += f"display_name={name}"
        if metadata:
            for key, value in metadata.items():
                filter_expression += f"labels.{key}={value} "
        try:
            models = Model.list(filter=filter_expression)
            return [
                RegisteredModel(
                    name=model.display_name,
                    description=model.description,
                    metadata=model.labels
                )
                for model in models
            ]
        except Exception as e:
            raise RuntimeError(f"Failed to list models: {str(e)}")

    def register_model_version(
        self,
        name: str,
        version: Optional[str] = None,
        model_source_uri: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[ModelRegistryModelMetadata] = None,
        **kwargs: Any,
    ) -> RegistryModelVersion:
        """Register a model version to the Vertex AI model registry."""
        try:
            model = Model(model_name=name)
            version_info = model.upload_version(
                display_name=version,
                description=description,
                artifact_uri=model_source_uri,
                labels=metadata.dict() if metadata else None
            )
            return RegistryModelVersion(
                version=version_info.version_id,
                model_source_uri=model_source_uri,
                model_format="Custom",
                registered_model=self.get_model(name),
                description=description,
                created_at=version_info.create_time,
                last_updated_at=version_info.update_time,
                stage=ModelVersionStage.NONE,
                metadata=metadata
            )
        except NotFound:
            raise KeyError(f"Model with name {name} does not exist.")
        except Exception as e:
            raise RuntimeError(f"Failed to register model version: {str(e)}")

    def delete_model_version(
        self,
        name: str,
        version: str,
    ) -> None:
        """Delete a model version from the Vertex AI model registry."""
        try:
            model = Model(model_name=name)
            version_info = ModelVersion(model_name=f"{name}@{version}")
            version_info.delete()
        except NotFound:
            raise KeyError(f"Model version {version} of model {name} does not exist.")
        except Exception as e:
            raise RuntimeError(f"Failed to delete model version: {str(e)}")

    def update_model_version(
        self,
        name: str,
        version: str,
        description: Optional[str] = None,
        metadata: Optional[ModelRegistryModelMetadata] = None,
        remove_metadata: Optional[List[str]] = None,
        stage: Optional[ModelVersionStage] = None,
    ) -> RegistryModelVersion:
        """Update a model version in the Vertex AI model registry."""
        try:
            model_version = ModelVersion(model_name=f"{name}@{version}")
            if description:
                model_version.update(description=description)
            if metadata:
                for key, value in metadata.dict().items():
                    model_version.labels[key] = value
            if remove_metadata:
                for key in remove_metadata:
                    if key in model_version.labels:
                        del model_version.labels[key]
            model_version.update()
            if stage:
                # Handle stage update if needed
                pass
            return self.get_model_version(name, version)
        except NotFound:
            raise KeyError(f"Model version {version} of model {name} does not exist.")
        except Exception as e:
            raise RuntimeError(f"Failed to update model version: {str(e)}")

    def get_model_version(
        self, name: str, version: str
    ) -> RegistryModelVersion:
        """Get a model version from the Vertex AI model registry."""
        try:
            model_version = ModelVersion(model_name=f"{name}@{version}")
            return RegistryModelVersion(
                version=model_version.version_id,
                model_source_uri=model_version.gca_resource.artifact_uri,
                model_format="Custom",
                registered_model=self.get_model(name),
                description=model_version.description,
                created_at=model_version.create_time,
                last_updated_at=model_version.update_time,
                stage=ModelVersionStage.NONE,
                metadata=ModelRegistryModelMetadata(**model_version.labels)
            )
        except NotFound:
            raise KeyError(f"Model version {version} of model {name} does not exist.")
        except Exception as e:
            raise RuntimeError(f"Failed to get model version: {str(e)}")

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
    ) -> List[RegistryModelVersion]:
        """List model versions from the Vertex AI model registry."""
        filter_expression = ""
        if name:
            filter_expression += f"display_name={name}"
        if metadata:
            for key, value in metadata.dict().items():
                filter_expression += f"labels.{key}={value} "
        try:
            model = Model(model_name=name)
            versions = model.list_versions(filter=filter_expression)
            return [
                RegistryModelVersion(
                    version=v.version_id,
                    model_source_uri=v.artifact_uri,
                    model_format="Custom",
                    registered_model=self.get_model(name),
                    description=v.description,
                    created_at=v.create_time,


                    last_updated_at=v.update_time,
                    stage=ModelVersionStage.NONE,
                    metadata=ModelRegistryModelMetadata(**v.labels)
                )
                for v in versions
            ]
        except Exception as e:
            raise RuntimeError(f"Failed to list model versions: {str(e)}")

    def load_model_version(
        self,
        name: str,
        version: str,
        **kwargs: Any,
    ) -> Any:
        """Load a model version from the Vertex AI model registry."""
        try:
            model_version = ModelVersion(model_name=f"{name}@{version}")
            return model_version
        except NotFound:
            raise KeyError(f"Model version {version} of model {name} does not exist.")
        except Exception as e:
            raise RuntimeError(f"Failed to load model version: {str(e)}")

    def get_model_uri_artifact_store(
        self,
        model_version: RegistryModelVersion,
    ) -> str:
        """Get the model URI artifact store."""
        return model_version.model_source_uri


class VertexAIModelRegistryFlavor(Flavor):
    """Base class for all ZenML model registry flavors."""

    @property
    def type(self) -> StackComponentType:
        """Type of the flavor."""
        return StackComponentType.MODEL_REGISTRY

    @property
    def config_class(self) -> Type[StackComponentConfig]:
        """Config class for this flavor."""
        return StackComponentConfig

    @property
    def implementation_class(self) -> Type[StackComponent]:
        """Returns the implementation class for this flavor."""
        return VertexAIModelRegistry
