#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Vertex AI model registry integration for ZenML."""

from datetime import datetime
import re
from typing import Any, Dict, List, Optional, cast

from google.cloud import aiplatform

from zenml.integrations.gcp.flavors.vertex_model_registry_flavor import (
    VertexAIModelRegistryConfig,
)
from zenml.integrations.gcp.google_credentials_mixin import (
    GoogleCredentialsMixin,
)
from zenml.logger import get_logger
from zenml.model_registries.base_model_registry import (
    BaseModelRegistry,
    ModelRegistryModelMetadata,
    ModelVersionStage,
    RegisteredModel,
    RegistryModelVersion,
)

logger = get_logger(__name__)


class VertexAIModelRegistry(BaseModelRegistry, GoogleCredentialsMixin):
    """Register models using Vertex AI."""

    @property
    def config(self) -> VertexAIModelRegistryConfig:
        """Returns the config of the model registry.

        Returns:
            The configuration.
        """
        return cast(VertexAIModelRegistryConfig, self._config)

    def setup_aiplatform(self) -> None:
        """Setup the Vertex AI platform."""
        credentials, project_id = self._get_authentication()
        aiplatform.init(
            project=project_id,
            location=self.config.location,
            credentials=credentials,
        )

    def register_model(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> RegisteredModel:
        """Register a model to the Vertex AI model registry."""
        raise NotImplementedError(
            "Vertex AI does not support registering models, you can only register model versions, skipping model registration..."
        )

    def delete_model(
        self,
        name: str,
    ) -> None:
        """Delete a model from the Vertex AI model registry."""
        try:
            model = aiplatform.Model(model_name=name)
            model.delete()
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
        raise NotImplementedError(
            "Vertex AI does not support updating models, you can only update model versions, skipping model registration..."
        )

    def get_model(self, name: str) -> RegisteredModel:
        """Get a model from the Vertex AI model registry."""
        try:
            model = aiplatform.Model(model_name=name)
            return RegisteredModel(
                name=model.name,
                description=model.description,
                metadata=model.labels,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to get model: {str(e)}")

    def list_models(
        self,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> List[RegisteredModel]:
        """List models in the Vertex AI model registry."""
        self.setup_aiplatform()
        filter_expr = 'labels.managed_by="zenml"'
        if name:
            filter_expr = filter_expr + f' AND  display_name="{name}"'
        if metadata:
            for key, value in metadata.items():
                filter_expr = filter_expr + f' AND  labels.{key}="{value}"'
        try:
            models = aiplatform.Model.list(filter=filter_expr)
            return [
                RegisteredModel(
                    name=model.display_name,
                    description=model.description,
                    metadata=model.labels,
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
        self.setup_aiplatform()
        metadata_dict = metadata.model_dump() if metadata else {}
        # Truncate all label values to 63 characters
        metadata_dict = {
            key.lower(): value[:63].lower() for key, value in metadata_dict.items()
        }
        # In both keys and values, keep letters, numbers, dashes and
        # underscores, replace all other characters with dashes
        metadata_dict = {
            re.sub(r"[^a-z0-9-_]", "-", key): re.sub(r"[^a-z0-9-_]", "-", value)
            for key, value in metadata_dict.items()
        }

        serving_container_image_uri = metadata_dict.get(
            "serving_container_image_uri",
            None
            or "europe-docker.pkg.dev/vertex-ai/prediction/sklearn-cpu.1-3:latest",
        )
        is_default_version = metadata_dict.get("is_default_version", False)
        try:
            version_info = aiplatform.Model.upload(
                artifact_uri=model_source_uri,
                display_name=f"{name}_{version}",
                serving_container_image_uri=serving_container_image_uri,
                description=description,
                is_default_version=is_default_version,
                labels=metadata_dict,
            )
            return RegistryModelVersion(
                version=version_info.version_id,
                model_source_uri=version_info.resource_name,
                model_format="Custom",  # Vertex AI doesn't provide this info directly
                registered_model=self.get_model(version_info.name),
                description=description,
                created_at=version_info.create_time,
                last_updated_at=version_info.update_time,
                stage=ModelVersionStage.NONE,  # Vertex AI doesn't have built-in stages
                metadata=metadata,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to register model version: {str(e)}")

    def delete_model_version(
        self,
        name: str,
        version: str,
    ) -> None:
        """Delete a model version from the Vertex AI model registry."""
        self.setup_aiplatform()
        try:
            model_version = aiplatform.ModelVersion(
                model_name=f"{name}@{version}"
            )
            model_version.delete()
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
        self.setup_aiplatform()
        try:
            model_version = aiplatform.Model(model_name=f"{name}@{version}")
            labels = model_version.labels
            if metadata:
                metadata_dict = metadata.model_dump() if metadata else {}
                for key, value in metadata_dict.items():
                    labels[key] = value
            if remove_metadata:
                for key in remove_metadata:
                    labels.pop(key, None)
            model_version.update(description=description, labels=labels)
            return self.get_model_version(name, version)
        except Exception as e:
            raise RuntimeError(f"Failed to update model version: {str(e)}")

    def get_model_version(
        self, name: str, version: str
    ) -> RegistryModelVersion:
        """Get a model version from the Vertex AI model registry."""
        self.setup_aiplatform()
        try:
            model_version = aiplatform.Model(model_name=f"{name}@{version}")
            return RegistryModelVersion(
                version=model_version.version_id,
                model_source_uri=model_version.artifact_uri,
                model_format="Custom",  # Vertex AI doesn't provide this info directly
                registered_model=self.get_model(model_version.name),
                description=model_version.description,
                created_at=model_version.create_time,
                last_updated_at=model_version.update_time,
                stage=ModelVersionStage.NONE,  # Vertex AI doesn't have built-in stages
                metadata=ModelRegistryModelMetadata(**model_version.labels),
            )
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
        self.setup_aiplatform()
        filter_expr = []
        if name:
            filter_expr.append(f"display_name={name}")
        if metadata:
            for key, value in metadata.dict().items():
                filter_expr.append(f"labels.{key}={value}")
        if created_after:
            filter_expr.append(f"create_time>{created_after.isoformat()}")
        if created_before:
            filter_expr.append(f"create_time<{created_before.isoformat()}")

        filter_str = " AND ".join(filter_expr) if filter_expr else None

        try:
            model = aiplatform.Model(model_name=name)
            versions = model.list_versions(filter=filter_str)

            results = [
                RegistryModelVersion(
                    version=v.version_id,
                    model_source_uri=v.artifact_uri,
                    model_format="Custom",  # Vertex AI doesn't provide this info directly
                    registered_model=self.get_model(v.name),
                    description=v.description,
                    created_at=v.create_time,
                    last_updated_at=v.update_time,
                    stage=ModelVersionStage.NONE,  # Vertex AI doesn't have built-in stages
                    metadata=ModelRegistryModelMetadata(**v.labels),
                )
                for v in versions
            ]

            if count:
                results = results[:count]

            return results
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
            model_version = aiplatform.ModelVersion(
                model_name=f"{name}@{version}"
            )
            return model_version
        except Exception as e:
            raise RuntimeError(f"Failed to load model version: {str(e)}")

    def get_model_uri_artifact_store(
        self,
        model_version: RegistryModelVersion,
    ) -> str:
        """Get the model URI artifact store."""
        return model_version.model_source_uri
