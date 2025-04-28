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

from google.cloud import aiplatform

from zenml.integrations.gcp.flavors.vertex_base_config import (
    VertexAIModelConfig,
)
from zenml.integrations.gcp.flavors.vertex_model_registry_flavor import (
    VertexAIModelRegistryConfig,
)
from zenml.integrations.gcp.google_credentials_mixin import (
    GoogleCredentialsMixin,
)
from zenml.integrations.gcp.utils import sanitize_vertex_label
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


# Helper function to safely get values from metadata dict
def _get_metadata_value(
    metadata: Dict[str, Any], key: str, default: Any = None
) -> Any:
    """Safely retrieves a value from a dictionary."""
    return metadata.get(key, default)


class VertexAIModelRegistry(BaseModelRegistry, GoogleCredentialsMixin):
    """Register models using Vertex AI."""

    @property
    def config(self) -> VertexAIModelRegistryConfig:
        """Returns the config of the model registry.

        Returns:
            The configuration.
        """
        return cast(VertexAIModelRegistryConfig, self._config)

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
        """Prepare labels for Vertex AI model.

        Args:
            metadata: Optional metadata to include as labels
            stage: Optional model version stage

        Returns:
            Dictionary of sanitized labels
        """
        labels = {}

        # Add base labels
        labels["managed_by"] = "zenml"
        # Add stage if provided
        if stage:
            labels["stage"] = sanitize_vertex_label(stage.value)

        # Process metadata if provided
        if metadata:
            for key, value in metadata.items():
                # Sanitize both key and value
                sanitized_key = sanitize_vertex_label(str(key))
                sanitized_value = sanitize_vertex_label(str(value))
                # Only add if both key and value are valid
                if sanitized_key and sanitized_value:
                    labels[sanitized_key] = sanitized_value

        # Ensure we don't exceed 64 labels
        if len(labels) > 64:
            # Keep essential labels and truncate the rest
            essential_labels = {
                k: labels[k] for k in ["managed_by", "stage"] if k in labels
            }
            # Add remaining labels up to limit
            remaining_slots = 64 - len(essential_labels)
            other_labels = {
                k: v
                for i, (k, v) in enumerate(labels.items())
                if k not in essential_labels and i < remaining_slots
            }
            labels = {**essential_labels, **other_labels}

        return labels

    def _get_model_id(self, name: str) -> str:
        """Get the full Vertex AI model ID.

        Args:
            name: Model name

        Returns:
            str: Full model ID in format: projects/{project}/locations/{location}/models/{model}
        """
        _, project_id = self._get_authentication()
        model_id = f"projects/{project_id}/locations/{self.config.location}/models/{name}"
        return model_id

    def _get_model_version_id(self, model_id: str, version: str) -> str:
        """Get the full Vertex AI model version ID.

        Args:
            model_id: Full model ID
            version: Version string

        Returns:
            str: Full model version ID in format: {model_id}/versions/{version}
        """
        model_version_id = f"{model_id}/versions/{version}"
        return model_version_id

    def _init_vertex_model(
        self, name: str, version: Optional[str] = None
    ) -> Optional[aiplatform.Model]:
        """Initialize a single Vertex AI model with proper credentials.

        This method returns one Vertex AI model based on the given name (and optional version).

        Args:
            name: The model name.
            version: The model version (optional).

        Returns:
            A single Vertex AI model instance or None if initialization fails.
        """
        credentials, project_id = self._get_authentication()
        location = self.config.location
        kwargs = {
            "location": location,
            "project": project_id,
            "credentials": credentials,
        }

        if name.startswith("projects/"):
            kwargs["model_name"] = name
        else:
            # Attempt to find an existing model by display_name
            existing_models = aiplatform.Model.list(
                filter=f"display_name={name}",
                project=self.config.project or project_id,
                location=location,
            )
            if existing_models:
                kwargs["model_name"] = existing_models[0].resource_name
            else:
                model_id = self._get_model_id(name)
                if version:
                    model_id = self._get_model_version_id(model_id, version)
                kwargs["model_name"] = model_id
        try:
            return aiplatform.Model(**kwargs)
        except Exception as e:
            logger.warning(f"Failed to initialize model: {e}")
            return None

    def register_model(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> RegisteredModel:
        """Register a model to the Vertex AI model registry.

        Args:
            name: The name of the model.
            description: The description of the model.
            metadata: The metadata of the model.

        Raises:
            NotImplementedError: Vertex AI does not support registering models, you can only register model versions, skipping model registration...

        """
        raise NotImplementedError(
            "Vertex AI does not support registering models, you can only register model versions, skipping model registration..."
        )

    def delete_model(
        self,
        name: str,
    ) -> None:
        """Delete a model and all of its versions from the Vertex AI model registry.

        Args:
            name: The name of the model.

        Raises:
            RuntimeError: if model deletion fails
        """
        try:
            model = self._init_vertex_model(name=name)
            if isinstance(model, aiplatform.Model):
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
        """Update a model in the Vertex AI model registry.

        Args:
            name: The name of the model.
            description: The description of the model.
            metadata: The metadata of the model.
            remove_metadata: The metadata to remove from the model.

        Raises:
            NotImplementedError: Vertex AI does not support updating models, you can only update model versions, skipping model registration...
        """
        raise NotImplementedError(
            "Vertex AI does not support updating models, you can only update model versions, skipping model registration..."
        )

    def get_model(self, name: str) -> RegisteredModel:
        """Get a model from the Vertex AI model registry by name without needing a version.

        Args:
            name: The name of the model.

        Returns:
            The registered model.

        Raises:
            RuntimeError: if model retrieval fails
        """
        try:
            # Fetch by display_name, and use unique labels to ensure multi-tenancy
            model = aiplatform.Model(display_name=name)
        except Exception as e:
            raise RuntimeError(f"Failed to get model: {str(e)}")
        return RegisteredModel(
            name=model.display_name,
            description=model.description,
            metadata=model.labels,
        )

    def list_models(
        self,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> List[RegisteredModel]:
        """List models in the Vertex AI model registry.

        Args:
            name: The name of the model.
            metadata: The metadata of the model.

        Returns:
            The registered models.

        Raises:
            RuntimeError: If the models are not found
        """
        credentials, project_id = self._get_authentication()
        location = self.config.location
        # Always filter with ZenML-specific labels (including deployer id for multi-tenancy)
        filter_expr = "labels.managed_by=zenml"

        if name:
            filter_expr += f" AND display_name={name}"
        if metadata:
            for key, value in metadata.items():
                filter_expr += f" AND labels.{key}={value}"
        try:
            all_models = aiplatform.Model.list(
                project=project_id,
                location=location,
                filter=filter_expr,
                credentials=credentials,
            )
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

    def _extract_vertex_config_from_metadata(
        self, metadata: Dict[str, Any]
    ) -> "VertexAIModelConfig":
        """Extracts Vertex AI specific configuration from metadata dictionary.

        Args:
            metadata: The metadata dictionary potentially containing config overrides.

        Returns:
            A VertexAIModelConfig instance populated from metadata.
        """
        # Use the module-level helper function
        container_config_dict = _get_metadata_value(metadata, "container", {})
        container_config = None
        if isinstance(container_config_dict, dict) and container_config_dict:
            from zenml.integrations.gcp.flavors.vertex_base_config import (
                VertexAIContainerSpec,
            )

            container_config = VertexAIContainerSpec(**container_config_dict)

        explanation_config_dict = _get_metadata_value(
            metadata, "explanation", {}
        )
        explanation_config = None
        if (
            isinstance(explanation_config_dict, dict)
            and explanation_config_dict
        ):
            from zenml.integrations.gcp.flavors.vertex_base_config import (
                VertexAIExplanationSpec,
            )

            explanation_config = VertexAIExplanationSpec(
                **explanation_config_dict
            )

        # Use the module-level helper function and correct instantiation
        return VertexAIModelConfig(
            # Model metadata overrides
            display_name=_get_metadata_value(metadata, "display_name"),
            description=_get_metadata_value(metadata, "description"),
            version_description=_get_metadata_value(
                metadata, "version_description"
            ),
            version_aliases=_get_metadata_value(metadata, "version_aliases"),
            # Model artifacts overrides
            artifact_uri=_get_metadata_value(metadata, "artifact_uri"),
            # Model versioning overrides
            is_default_version=_get_metadata_value(
                metadata, "is_default_version"
            ),
            # Model formats overrides (less likely used here, but for completeness)
            supported_deployment_resources_types=_get_metadata_value(
                metadata, "supported_deployment_resources_types"
            ),
            supported_input_storage_formats=_get_metadata_value(
                metadata, "supported_input_storage_formats"
            ),
            supported_output_storage_formats=_get_metadata_value(
                metadata, "supported_output_storage_formats"
            ),
            # Container and Explanation config (parsed above)
            container=container_config,
            explanation=explanation_config,
            # GCP Base config (from component config)
            encryption_spec_key_name=_get_metadata_value(
                metadata, "encryption_spec_key_name"
            ),
        )

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
            model_source_uri: URI to model artifacts (overrides metadata if provided)
            description: Model description (overrides metadata if provided)
            metadata: Model metadata (expected to be a ModelRegistryModelMetadata or
                      equivalent serializable dict). Can contain overrides for
                      Vertex AI model parameters like 'display_name', 'artifact_uri',
                      'version_description', 'container', 'explanation', etc.
            config: Vertex AI model configuration overrides.
            **kwargs: Additional arguments

        Returns:
            RegistryModelVersion instance
        """
        # Prepare labels with internal ZenML metadata, ensuring they are sanitized
        metadata_dict = metadata.model_dump() if metadata else {}
        labels = self._prepare_labels(metadata_dict)
        if version:
            labels["user_version"] = sanitize_vertex_label(version)

        # Extract Vertex AI specific config overrides from metadata
        vertex_config = self._extract_vertex_config_from_metadata(
            metadata_dict
        )

        # Use a consistently sanitized display name. Prioritize metadata, then name arg.
        model_display_name_override = vertex_config.display_name
        model_display_name = (
            model_display_name_override
            or self._sanitize_model_display_name(name)
        )

        # Determine serving container image URI: prioritize metadata container config,
        # then metadata direct key, then default.
        serving_container_image_uri = "europe-docker.pkg.dev/vertex-ai/prediction/sklearn-cpu.1-3:latest"  # Default
        if "serving_container_image_uri" in metadata_dict:
            serving_container_image_uri = metadata_dict[
                "serving_container_image_uri"
            ]
        if vertex_config.container and vertex_config.container.image_uri:
            serving_container_image_uri = vertex_config.container.image_uri

        # Determine artifact URI: prioritize direct argument, then metadata, then log warning.
        final_artifact_uri = model_source_uri or vertex_config.artifact_uri
        if not final_artifact_uri:
            logger.warning(
                "No 'artifact_uri' provided in function arguments or metadata. "
                "Model registration might fail or use an unexpected artifact source."
            )

        # Determine description: prioritize direct argument, then metadata.
        final_description = description or vertex_config.description

        # Build extended upload arguments for vertex.Model.upload,
        # leveraging extracted config from metadata and component config for core details.
        upload_arguments = {
            # Core GCP config from component
            "project": self.config.project_id or self.config.project,
            "location": self.config.location or vertex_config.location,
            # Model identification and artifacts
            "display_name": model_display_name,
            "artifact_uri": final_artifact_uri,
            # Description and Versioning - prioritize metadata
            "description": final_description,
            "version_description": vertex_config.version_description,
            "version_aliases": vertex_config.version_aliases,
            "is_default_version": vertex_config.is_default_version
            if vertex_config.is_default_version is not None
            else True,
            # Container configuration from metadata
            "serving_container_image_uri": serving_container_image_uri,
            "serving_container_predict_route": vertex_config.container.predict_route
            if vertex_config.container
            else None,
            "serving_container_health_route": vertex_config.container.health_route
            if vertex_config.container
            else None,
            "serving_container_command": vertex_config.container.command
            if vertex_config.container
            else None,
            "serving_container_args": vertex_config.container.args
            if vertex_config.container
            else None,
            "serving_container_environment_variables": vertex_config.container.env
            if vertex_config.container
            else None,
            "serving_container_ports": vertex_config.container.ports
            if vertex_config.container
            else None,
            # Labels and Encryption
            "labels": labels,
            "encryption_spec_key_name": vertex_config.encryption_spec_key_name,
        }

        # Include explanation settings if provided in metadata config.
        if vertex_config.explanation:
            upload_arguments["explanation_metadata"] = (
                vertex_config.explanation.metadata
            )
            upload_arguments["explanation_parameters"] = (
                vertex_config.explanation.parameters
            )

        # Remove any parameters that are None to avoid passing them to upload.
        upload_arguments = {
            k: v for k, v in upload_arguments.items() if v is not None
        }

        # Try to get existing parent model, but don't fail if it doesn't exist
        # Use the actual model name `name` for lookup, not the potentially overridden display name
        parent_model = self._init_vertex_model(name=name, version=version)

        # If parent model exists and has same URI, return existing version
        # Check against final_artifact_uri used for upload
        if parent_model and parent_model.uri == final_artifact_uri:
            logger.info(
                f"Model version {version} targeting artifact URI "
                f"'{final_artifact_uri}' already exists, skipping upload..."
            )
            return self._vertex_model_to_registry_version(parent_model)

        # Set parent model resource name if it exists
        if parent_model:
            # Ensure the display_name matches the parent model if it exists,
            # otherwise upload might create a *new* model instead of a version.
            # Use the parent model's display name for the upload.
            upload_arguments["display_name"] = parent_model.display_name
            upload_arguments["parent_model"] = parent_model.resource_name
            logger.info(
                f"Found existing parent model '{parent_model.display_name}' "
                f"({parent_model.resource_name}). Uploading as a new version."
            )
        else:
            logger.info(
                f"No existing parent model found for name '{name}'. "
                f"A new model named '{upload_arguments['display_name']}' will be created."
            )

        # Upload the model
        try:
            logger.info(
                f"Uploading model to Vertex AI with arguments: { {k: v for k, v in upload_arguments.items() if k != 'labels'} }"
            )  # Don't log potentially large labels dict
            model = aiplatform.Model.upload(**upload_arguments)
            logger.info(
                f"Uploaded new model version with labels: {model.labels}"
            )
        except Exception as e:
            logger.error(f"Failed to upload model to Vertex AI: {e}")
            # Log the arguments again on failure for easier debugging
            logger.error(f"Failed upload arguments: {upload_arguments}")
            raise

        return self._vertex_model_to_registry_version(model)

    def delete_model_version(
        self,
        name: str,
        version: str,
    ) -> None:
        """Delete a model version from the Vertex AI model registry.

        Args:
            name: Model name
            version: Version string

        Raises:
            RuntimeError: If the model version is not found
        """
        try:
            model = self._init_vertex_model(name=name, version=version)
            if model is None:
                raise RuntimeError(
                    f"Model version '{version}' for '{name}' not found."
                )
            model.versioning_registry.delete_version(version)
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
        """Update a model version in the Vertex AI model registry.

        Args:
            name: The name of the model.
            version: The version of the model.
            description: The description of the model.
            metadata: The metadata of the model.
            remove_metadata: The metadata to remove from the model.
            stage: The stage of the model.

        Returns:
            The updated model version.

        Raises:
            RuntimeError: If the model version is not found
        """
        try:
            parent_model = self._init_vertex_model(name=name, version=version)
            sanitized_version = sanitize_vertex_label(version)
            target_version = None
            for v in parent_model.list():
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
                    labels[sanitize_vertex_label(key)] = sanitize_vertex_label(
                        str(value)
                    )
            if remove_metadata:
                for key in remove_metadata:
                    labels.pop(sanitize_vertex_label(key), None)
            if stage:
                labels["stage"] = stage.value.lower()
            target_version.update(description=description, labels=labels)
        except Exception as e:
            raise RuntimeError(f"Failed to update model version: {str(e)}")
        return self.get_model_version(name, version)

    def get_model_version(
        self, name: str, version: str
    ) -> RegistryModelVersion:
        """Get a model version from the Vertex AI model registry using the version label.

        Args:
            name: The name of the model.
            version: The version of the model.

        Returns:
            The registered model version.

        Raises:
            RuntimeError: If the model version is not found
        """
        try:
            parent_model = self._init_vertex_model(name=name, version=version)
            if parent_model is None:
                raise RuntimeError(
                    f"Model version '{version}' for '{name}' not found."
                )
            return self._vertex_model_to_registry_version(parent_model)
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
        """List model versions from the Vertex AI model registry.

        Args:
            name: The name of the model.
            model_source_uri: The URI of the model source.
            metadata: The metadata of the model.
            stage: The stage of the model.
            count: The number of model versions to return.
            created_after: The date after which the model versions were created.
            created_before: The date before which the model versions were created.
            order_by_date: The date to order the model versions by.
            **kwargs: Additional arguments

        Returns:
            The registered model versions.

        Raises:
            RuntimeError: If the model versions are not found
        """
        credentials, project_id = self._get_authentication()
        location = self.config.location
        filter_expr = []
        if name:
            filter_expr.append(
                f"display_name={self._sanitize_model_display_name(name)}"
            )
        if metadata:
            for key, value in metadata.dict().items():
                filter_expr.append(
                    f"labels.{sanitize_vertex_label(key)}={sanitize_vertex_label(str(value))}"
                )
        if created_after:
            filter_expr.append(f"create_time>{created_after.isoformat()}")
        if created_before:
            filter_expr.append(f"create_time<{created_before.isoformat()}")

        filter_str = " AND ".join(filter_expr) if filter_expr else None

        try:
            model = aiplatform.Model(
                project=project_id,
                location=location,
                filter=filter_str,
                credentials=credentials,
            )
            versions = model.versioning_registry.list_versions()
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
        """Load a model version from the Vertex AI model registry using label-based lookup.

        Args:
            name: The name of the model.
            version: The version of the model.
            **kwargs: Additional arguments

        Returns:
            The loaded model version.

        Raises:
            RuntimeError: If the model version is not found
        """
        try:
            parent_model = self._init_vertex_model(name=name, version=version)
            assert isinstance(parent_model, aiplatform.Model)
            return parent_model
        except Exception as e:
            raise RuntimeError(f"Failed to load model version: {str(e)}")

    def get_model_uri_artifact_store(
        self,
        model_version: RegistryModelVersion,
    ) -> str:
        """Get the model URI artifact store.

        Args:
            model_version: The model version.

        Returns:
            The model URI artifact store.
        """
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
        try:
            registered_model = RegisteredModel(
                name=model.display_name,
                description=model.description,
                metadata=model.labels,
            )
        except Exception as e:
            logger.warning(
                f"Failed to get parent model for version: {model.resource_name}: {e}"
            )
            registered_model = RegisteredModel(
                name=model.display_name if model.display_name else "unknown",
                description=model.description if model.description else "",
                metadata=model.labels if model.labels else {},
            )

        model_version_metadata = model.labels
        model_version_metadata["resource_name"] = model.resource_name
        return RegistryModelVersion(
            registered_model=registered_model,
            version=model.version_id,
            model_source_uri=model.uri,
            model_format="Custom",  # Vertex AI doesn't provide format info
            description=model.description,
            metadata=model_version_metadata,
            created_at=model.create_time,
            last_updated_at=model.update_time,
            stage=stage,
        )

    def _sanitize_model_display_name(self, name: str) -> str:
        """Sanitize the model display name to conform to Vertex AI limits.

        Args:
            name: The name of the model.

        Returns:
            The sanitized model name.
        """
        name = sanitize_vertex_label(name)
        if len(name) > MAX_DISPLAY_NAME_LENGTH:
            logger.warning(
                f"Model name '{name}' exceeds {MAX_DISPLAY_NAME_LENGTH} characters; truncating."
            )
            name = name[:MAX_DISPLAY_NAME_LENGTH]
        return name
