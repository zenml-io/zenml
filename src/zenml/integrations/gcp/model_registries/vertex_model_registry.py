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

import base64
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, cast

from google.api_core import exceptions
from google.cloud import aiplatform

from zenml.client import Client
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

# Constants for Vertex AI limitations
MAX_LABEL_COUNT = 64
MAX_LABEL_KEY_LENGTH = 63
MAX_LABEL_VALUE_LENGTH = 63
MAX_DISPLAY_NAME_LENGTH = 128


class VertexAIModelRegistry(BaseModelRegistry, GoogleCredentialsMixin):
    """Register models using Vertex AI."""

    @property
    def config(self) -> VertexAIModelRegistryConfig:
        """Returns the config of the model registry.

        Returns:
            The configuration.
        """
        return cast(VertexAIModelRegistryConfig, self._config)

    def _sanitize_label(self, value: str) -> str:
        """Sanitize a label value to comply with Vertex AI requirements.

        Args:
            value: The label value to sanitize

        Returns:
            Sanitized label value
        """
        if not value:
            return ""
        # Convert to lowercase and replace invalid chars
        value = value.lower()
        value = "".join(
            c if c.isalnum() or c in ["-", "_"] else "-" for c in value
        )
        # Ensure starts with letter/number
        if not value[0].isalnum():
            value = f"x{value}"
        return value[:MAX_LABEL_KEY_LENGTH]

    def _get_tenant_id(self) -> str:
        """Get the current ZenML server/tenant ID for multi-tenancy support.

        Returns:
            The tenant ID string
        """
        client = Client()
        return str(client.active_stack_model.id)

    def _encode_name_version(self, name: str, version: str) -> str:
        """Encode model name and version into a Vertex AI compatible format.

        Args:
            name: Model name
            version: Model version

        Returns:
            Encoded string suitable for Vertex AI
        """
        # Base64 encode to handle special characters while preserving uniqueness
        encoded = base64.b64encode(f"{name}:{version}".encode()).decode()
        # Make it URL and label safe
        encoded = encoded.replace("+", "-").replace("/", "_").replace("=", "")
        return encoded[:MAX_DISPLAY_NAME_LENGTH]

    def _decode_name_version(self, encoded: str) -> Tuple[str, str]:
        """Decode model name and version from encoded format.

        Args:
            encoded: The encoded string

        Returns:
            Tuple of (name, version)
        """
        # Add back padding
        padding = 4 - (len(encoded) % 4)
        if padding != 4:
            encoded += "=" * padding
        # Restore special chars
        encoded = encoded.replace("-", "+").replace("_", "/")
        try:
            decoded = base64.b64decode(encoded).decode()
            name, version = decoded.split(":", 1)
            return name, version
        except Exception as e:
            logger.warning(
                f"Failed to decode name/version from {encoded}: {e}"
            )
            return encoded, "unknown"

    def _prepare_labels(
        self,
        metadata: Optional[Dict[str, str]] = None,
        stage: Optional[ModelVersionStage] = None,
    ) -> Dict[str, str]:
        """Prepare labels for Vertex AI, including internal ZenML metadata."""
        labels = {}

        # Add internal ZenML labels
        labels["managed_by"] = "zenml"
        tenant_id = self._sanitize_label(self._get_tenant_id())
        labels["tenant_id"] = tenant_id

        if stage:
            labels["stage"] = stage.value.lower()

        # Merge user metadata with sanitization
        if metadata:
            remaining_slots = MAX_LABEL_COUNT - len(labels)
            for i, (key, value) in enumerate(metadata.items()):
                if i >= remaining_slots:
                    logger.warning(
                        f"Exceeded maximum label count ({MAX_LABEL_COUNT}), "
                        f"dropping remaining metadata"
                    )
                    break
                safe_key = self._sanitize_label(str(key))
                safe_value = self._sanitize_label(str(value))
                labels[safe_key] = safe_value

        return labels

    def _get_model_id(self, name: str) -> str:
        """Get the full Vertex AI model ID.

        Args:
            name: Model name

        Returns:
            Full model ID in format: projects/{project}/locations/{location}/models/{model}
        """
        _, project_id = self._get_authentication()
        return f"projects/{project_id}/locations/{self.config.location}/models/{name}"

    def _get_model_version_id(self, model_id: str, version: str) -> str:
        """Get the full Vertex AI model version ID.

        Args:
            model_id: Full model ID
            version: Version string

        Returns:
            Full model version ID in format: {model_id}/versions/{version}
        """
        return f"{model_id}/versions/{version}"

    def _init_vertex_model(
        self,
        name: Optional[str] = None,
        version: Optional[str] = None,
        credentials: Optional[Any] = None,
    ) -> aiplatform.Model:
        """Initialize a Vertex AI model with proper credentials.

        Args:
            name: Optional model name
            version: Optional version
            credentials: Optional credentials

        Returns:
            Vertex AI Model instance
        """
        if not credentials:
            credentials, _ = self._get_authentication()

        kwargs = {
            "location": self.config.location,
            "credentials": credentials,
        }

        if name:
            model_id = self._get_model_id(name)
            if version:
                model_id = self._get_model_version_id(model_id, version)
            kwargs["name"] = model_id

        return aiplatform.Model(**kwargs)

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
        """Delete a model and all of its versions from the Vertex AI model registry."""
        try:
            model = self._init_vertex_model(name=name)
            # List and delete all model versions first
            versions = model.list_versions()
            for version in versions:
                version.delete()
            # Then delete the parent model
            model.delete()
            logger.info(f"Deleted model '{name}' and all its versions.")
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
        """Get a model from the Vertex AI model registry by name without needing a version."""
        try:
            # Fetch by display_name, and use unique labels to ensure multi-tenancy
            model = aiplatform.Model(display_name=name)
            return RegisteredModel(
                name=model.display_name,
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
        _ = self._init_vertex_model(name=name)
        # Always filter with ZenML-specific labels (including tenant id for multi-tenancy)
        tenant_label = self._sanitize_label(self._get_tenant_id())
        filter_expr = (
            f"labels.managed_by='zenml' AND labels.tenant_id='{tenant_label}'"
        )

        if name:
            filter_expr += f" AND display_name='{name}'"
        if metadata:
            for key, value in metadata.items():
                filter_expr += f" AND labels.{key}='{value}'"
        try:
            all_models = aiplatform.Model.list(filter=filter_expr)
            # Deduplicate by display_name so only one entry per "logical" model is returned.
            unique_models = {model.display_name: model for model in all_models}
            return [
                RegisteredModel(
                    name=parent_model.display_name,
                    description=parent_model.description,
                    metadata=parent_model.labels,
                )
                for parent_model in unique_models.values()
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
        """Register a model version to the Vertex AI model registry.

        Args:
            name: Model name
            version: Model version
            model_source_uri: URI to model artifacts
            description: Model description
            metadata: Model metadata
            **kwargs: Additional arguments

        Returns:
            RegistryModelVersion instance
        """
        credentials, _ = self._get_authentication()

        # Prepare labels with internal ZenML metadata, ensuring they are sanitized
        metadata_dict = metadata.model_dump() if metadata else {}
        labels = self._prepare_labels(metadata_dict)
        if version:
            labels["user_version"] = self._sanitize_label(version)

        # Get container image from config if available, otherwise from metadata with a default
        if (
            hasattr(self.config, "container")
            and self.config.container
            and self.config.container.image_uri
        ):
            serving_container_image_uri = self.config.container.image_uri
        else:
            serving_container_image_uri = metadata_dict.get(
                "serving_container_image_uri",
                "europe-docker.pkg.dev/vertex-ai/prediction/sklearn-cpu.1-3:latest",
            )

        # Optionally add additional parameters from the config resources
        if hasattr(self.config, "resources") and self.config.resources:
            if self.config.resources.machine_type:
                metadata_dict.setdefault(
                    "machine_type", self.config.resources.machine_type
                )
            if self.config.resources.min_replica_count is not None:
                metadata_dict.setdefault(
                    "min_replica_count",
                    str(self.config.resources.min_replica_count),
                )
            if self.config.resources.max_replica_count is not None:
                metadata_dict.setdefault(
                    "max_replica_count",
                    str(self.config.resources.max_replica_count),
                )

        # Use a consistently sanitized display name instead of flat "name_version"
        model_display_name = self._sanitize_model_display_name(name)

        try:
            # Attempt to get the parent model (by name only)
            parent_model = self._init_vertex_model(name=name)
            logger.info(f"Found existing model: {name}")
        except exceptions.NotFound:
            # Create the parent model if it doesn"t exist
            parent_model = aiplatform.Model.upload(
                display_name=model_display_name,
                artifact_uri=model_source_uri,
                serving_container_image_uri=serving_container_image_uri,
                description=description,
                labels=labels,
                credentials=credentials,
                location=self.config.location,
            )
            logger.info(f"Created new model: {name}")

        # Create a new version for the model. Note that we keep the display name intact.
        model_version = parent_model.create_version(
            artifact_uri=model_source_uri,
            serving_container_image_uri=serving_container_image_uri,
            description=description,
            labels=labels,
        )
        logger.info(f"Created new version with labels: {model_version.labels}")

        return self._vertex_model_to_registry_version(model_version)

    def delete_model_version(
        self,
        name: str,
        version: str,
    ) -> None:
        """Delete a model version from the Vertex AI model registry.

        Args:
            name: Model name
            version: Version string
        """
        try:
            model = self._init_vertex_model(name=name, version=version)
            model.delete()
            logger.info(f"Deleted model version: {name} version {version}")
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
            parent_model = self._init_vertex_model(name=name)
            sanitized_version = self._sanitize_label(version)
            target_version = None
            for v in parent_model.list_versions():
                if v.labels.get("user_version") == sanitized_version:
                    target_version = v
                    break
            if target_version is None:
                raise RuntimeError(
                    f"Model version '{version}' for '{name}' not found."
                )
            labels = target_version.labels or {}
            if metadata:
                metadata_dict = metadata.model_dump()
                for key, value in metadata_dict.items():
                    labels[self._sanitize_label(key)] = self._sanitize_label(
                        str(value)
                    )
            if remove_metadata:
                for key in remove_metadata:
                    labels.pop(self._sanitize_label(key), None)
            if stage:
                labels["stage"] = stage.value.lower()
            target_version.update(description=description, labels=labels)
            return self.get_model_version(name, version)
        except Exception as e:
            raise RuntimeError(f"Failed to update model version: {str(e)}")

    def get_model_version(
        self, name: str, version: str
    ) -> RegistryModelVersion:
        """Get a model version from the Vertex AI model registry using the version label."""
        try:
            parent_model = self._init_vertex_model(name=name)
            sanitized_version = self._sanitize_label(version)
            for v in parent_model.list_versions():
                if v.labels.get("user_version") == sanitized_version:
                    return self._vertex_model_to_registry_version(v)
            raise RuntimeError(
                f"Model '{name}' with version '{version}' not found."
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
        filter_expr = []
        if name:
            filter_expr.append(
                f"display_name={self._sanitize_model_display_name(name)}"
            )
        if metadata:
            for key, value in metadata.dict().items():
                filter_expr.append(
                    f"labels.{self._sanitize_label(key)}={self._sanitize_label(str(value))}"
                )
        if created_after:
            filter_expr.append(f"create_time>{created_after.isoformat()}")
        if created_before:
            filter_expr.append(f"create_time<{created_before.isoformat()}")

        filter_str = " AND ".join(filter_expr) if filter_expr else None

        try:
            parent_model = self._init_vertex_model(name=name)
            versions = parent_model.list_versions(filter=filter_str)
            results = [
                self._vertex_model_to_registry_version(v) for v in versions
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
        """Load a model version from the Vertex AI model registry using label-based lookup."""
        try:
            parent_model = self._init_vertex_model(name=name)
            sanitized_version = self._sanitize_label(version)
            for v in parent_model.list_versions():
                if v.labels.get("user_version") == sanitized_version:
                    return v
            raise RuntimeError(
                f"Model version '{version}' for '{name}' not found."
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load model version: {str(e)}")

    def get_model_uri_artifact_store(
        self,
        model_version: RegistryModelVersion,
    ) -> str:
        """Get the model URI artifact store."""
        return model_version.model_source_uri

    def _vertex_model_to_registry_version(
        self, model: aiplatform.Model
    ) -> RegistryModelVersion:
        """Convert Vertex AI model to ZenML RegistryModelVersion.

        Args:
            model: Vertex AI Model instance

        Returns:
            RegistryModelVersion instance
        """
        # Extract stage from labels if present
        stage = ModelVersionStage.NONE
        if model.labels and "stage" in model.labels:
            try:
                stage = ModelVersionStage(model.labels["stage"].upper())
            except ValueError:
                pass

        # Get parent model for registered_model field
        parent_model = None
        try:
            model_id = model.resource_name.split("/versions/")[0]
            parent_model = self._init_vertex_model(name=model_id)
            registered_model = RegisteredModel(
                name=parent_model.display_name,
                description=parent_model.description,
                metadata=parent_model.labels,
            )
        except Exception:
            logger.warning(
                f"Failed to get parent model for version: {model.resource_name}"
            )
            registered_model = None

        return RegistryModelVersion(
            registered_model=registered_model,
            version=model.version_id,
            model_source_uri=model.artifact_uri,
            model_format="Custom",  # Vertex AI doesn't provide format info
            description=model.description,
            metadata=model.labels,
            created_at=model.create_time,
            last_updated_at=model.update_time,
            stage=stage,
        )

    def _sanitize_model_display_name(self, name: str) -> str:
        """Sanitize the model display name to conform to Vertex AI limits."""
        # Use our existing sanitizer (which converts to lowercase, replaces invalid characters, etc.)
        name = self._sanitize_label(name)
        if len(name) > MAX_DISPLAY_NAME_LENGTH:
            logger.warning(
                f"Model name '{name}' exceeds {MAX_DISPLAY_NAME_LENGTH} characters; truncating."
            )
            name = name[:MAX_DISPLAY_NAME_LENGTH]
        return name
