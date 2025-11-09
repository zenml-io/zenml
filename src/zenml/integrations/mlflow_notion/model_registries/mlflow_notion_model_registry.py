#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Implementation of the MLflow-Notion hybrid model registry for ZenML."""

from datetime import datetime
from typing import Any, Dict, List, Optional, cast

import mlflow
from mlflow import MlflowClient
from mlflow.entities.model_registry import ModelVersion as MLflowModelVersion
from mlflow.exceptions import MlflowException
from notion_client import Client as NotionClient
from notion_client.errors import APIResponseError

from zenml import log_metadata
from zenml.client import Client
from zenml.enums import ModelStages
from zenml.integrations.mlflow_notion.flavors.mlflow_notion_model_registry_flavor import (
    MLFlowNotionModelRegistryConfig,
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

# Tag to identify models managed by this integration
MLFLOW_NOTION_TAG = "zenml.mlflow_notion_managed"
MLFLOW_NOTION_TAG_VALUE = "true"


class MLFlowNotionModelRegistry(BaseModelRegistry):
    """Hybrid model registry combining MLflow and Notion."""

    _mlflow_client: Optional[MlflowClient] = None
    _notion_client: Optional[NotionClient] = None

    @property
    def config(self) -> MLFlowNotionModelRegistryConfig:
        """Returns the `MLFlowNotionModelRegistryConfig` config.

        Returns:
            The configuration.
        """
        return cast(MLFlowNotionModelRegistryConfig, self._config)

    @property
    def mlflow_client(self) -> MlflowClient:
        """Get the MLflow client.

        Returns:
            The MLflow client.
        """
        if not self._mlflow_client:
            if self.config.tracking_uri:
                mlflow.set_tracking_uri(self.config.tracking_uri)

            if self.config.registry_uri:
                mlflow.set_registry_uri(self.config.registry_uri)

            self._mlflow_client = MlflowClient()
        return self._mlflow_client

    @property
    def notion_client(self) -> NotionClient:
        """Get the Notion client.

        Returns:
            The Notion client.
        """
        if not self._notion_client:
            self._notion_client = NotionClient(
                auth=self.config.notion_api_token,
                notion_version="2025-09-03",
            )
        return self._notion_client

    # ---------
    # Notion Helper Methods
    # ---------

    def _get_data_source_id(self) -> str:
        """Get the data source ID for the configured Notion database.

        Returns:
            The data source ID.

        Raises:
            RuntimeError: If the database has no data sources.
        """
        try:
            response = self.notion_client.databases.retrieve(
                database_id=self.config.database_id
            )
            data_sources = response.get("data_sources", [])  # type: ignore[union-attr]

            if not data_sources:
                raise RuntimeError(
                    f"Database {self.config.database_id} has no data sources. "
                    "This may indicate the database was deleted or the integration "
                    "doesn't have access to it."
                )

            data_source_id: str = data_sources[0]["id"]
            return data_source_id

        except APIResponseError as e:
            raise RuntimeError(
                f"Failed to retrieve data sources for database "
                f"{self.config.database_id}: {str(e)}"
            )

    def _notion_properties_from_mlflow(
        self,
        mlflow_version: MLflowModelVersion,
        description: Optional[str] = None,
        zenml_model_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Convert MLflow model version to Notion property format.

        Args:
            mlflow_version: MLflow model version object
            description: Optional description override
            zenml_model_url: Optional ZenML Model URL for dashboard link

        Returns:
            Notion properties dictionary.
        """
        properties: Dict[str, Any] = {
            "Model Name": {
                "title": [{"text": {"content": mlflow_version.name}}]
            },
            "Version": {
                "rich_text": [
                    {"text": {"content": str(mlflow_version.version)}}
                ]
            },
            "Model Source URI": {"url": mlflow_version.source},
            "Created At": {
                "date": {
                    "start": datetime.fromtimestamp(
                        mlflow_version.creation_timestamp / 1000
                    ).isoformat()
                }
            },
            "Stage": {"select": {"name": mlflow_version.current_stage}},
        }

        if description or mlflow_version.description:
            desc_text = description or mlflow_version.description
            properties["Description"] = {
                "rich_text": [{"text": {"content": desc_text}}]
            }

        # Add ZenML Model URL if provided
        if zenml_model_url:
            properties["ZenML Model URL"] = {"url": zenml_model_url}

        if mlflow_version.tags:
            zenml_fields = {
                "zenml_version": "ZenML Version",
                "zenml_pipeline_name": "ZenML Pipeline Name",
                "zenml_run_name": "ZenML Run Name",
                "zenml_pipeline_run_uuid": "ZenML Run UUID",
                "zenml_step_name": "ZenML Step Name",
            }

            for tag_key, prop_name in zenml_fields.items():
                if (
                    tag_key in mlflow_version.tags
                    and tag_key != MLFLOW_NOTION_TAG
                ):
                    properties[prop_name] = {
                        "rich_text": [
                            {"text": {"content": mlflow_version.tags[tag_key]}}
                        ]
                    }

        return properties

    def _find_notion_version(
        self, model_name: str, version: str
    ) -> Optional[Dict[str, Any]]:
        """Find a model version in the Notion database.

        Args:
            model_name: Name of the model
            version: Version number

        Returns:
            Notion page data if found, None otherwise.
        """
        try:
            data_source_id = self._get_data_source_id()
            response = self.notion_client.request(
                method="post",
                path=f"data_sources/{data_source_id}/query",
                body={
                    "filter": {
                        "and": [
                            {
                                "property": "Model Name",
                                "title": {
                                    "equals": model_name,
                                },
                            },
                            {
                                "property": "Version",
                                "rich_text": {
                                    "equals": version,
                                },
                            },
                        ]
                    },
                },
            )

            if response.get("results"):
                return response["results"][0]
            return None

        except APIResponseError as e:
            logger.warning(
                f"Error finding Notion version {model_name}:{version}: {e}"
            )
            return None

    def _create_in_notion(
        self,
        mlflow_version: MLflowModelVersion,
        description: Optional[str] = None,
        zenml_model_url: Optional[str] = None,
    ) -> None:
        """Create a model version entry in Notion database.

        Args:
            mlflow_version: MLflow model version to create in Notion
            description: Optional description
            zenml_model_url: Optional ZenML Model URL for dashboard link
        """
        properties = self._notion_properties_from_mlflow(
            mlflow_version, description, zenml_model_url
        )

        data_source_id = self._get_data_source_id()
        response = self.notion_client.pages.create(
            parent={
                "type": "data_source_id",
                "data_source_id": data_source_id,
            },
            properties=properties,
        )

        page_id: str = response["id"]  # type: ignore[index]
        logger.info(
            f"Created Notion page for {mlflow_version.name}:{mlflow_version.version} "
            f"(page ID: {page_id})"
        )

    def _update_notion_stage(self, page_id: str, stage: str) -> None:
        """Update the stage of a model version in Notion.

        Args:
            page_id: Notion page ID
            stage: New stage value
        """
        self.notion_client.pages.update(
            page_id=page_id,
            properties={"Stage": {"select": {"name": stage}}},
        )
        logger.debug(f"Updated Notion page {page_id} stage to {stage}")

    def _sync_version_to_notion(
        self,
        mlflow_version: MLflowModelVersion,
        description: Optional[str] = None,
        zenml_model_url: Optional[str] = None,
    ) -> None:
        """Sync a single model version from MLflow to Notion.

        This is used for auto-sync on write operations. It creates the version
        in Notion if it doesn't exist, or updates the stage if it changed.

        Args:
            mlflow_version: MLflow model version to sync.
            description: Optional description override.
            zenml_model_url: Optional ZenML Model URL for dashboard link.
        """
        notion_version = self._find_notion_version(
            mlflow_version.name, str(mlflow_version.version)
        )

        if not notion_version:
            self._create_in_notion(
                mlflow_version, description, zenml_model_url
            )
        else:
            properties = notion_version.get("properties", {})
            stage_prop = properties.get("Stage", {})
            current_stage = (
                stage_prop.get("select", {}).get("name", "None")
                if stage_prop.get("select")
                else "None"
            )

            if current_stage != mlflow_version.current_stage:
                self._update_notion_stage(
                    notion_version["id"], mlflow_version.current_stage
                )

    # ---------
    # Model Registration Methods
    # ---------

    def register_model(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> RegisteredModel:
        """Register a model in MLflow with management tag.

        Args:
            name: The name of the model.
            description: The description of the model.
            metadata: The metadata of the model.

        Returns:
            The registered model.

        Raises:
            RuntimeError: If registration fails.
        """
        try:
            tags = metadata or {}
            tags[MLFLOW_NOTION_TAG] = MLFLOW_NOTION_TAG_VALUE

            self.mlflow_client.create_registered_model(
                name=name,
                tags=tags,
                description=description,
            )

            logger.info(f"Registered model '{name}' in MLflow")

            return RegisteredModel(
                name=name,
                description=description,
                metadata=metadata,
            )

        except MlflowException as e:
            raise RuntimeError(
                f"Failed to register model '{name}' in MLflow: {str(e)}"
            )

    def delete_model(
        self,
        name: str,
    ) -> None:
        """Delete a model from MLflow.

        Note: This does not automatically clean up Notion entries. Use the
        sync operation with cleanup_orphans=True to remove orphaned entries.

        Args:
            name: The name of the model.

        Raises:
            RuntimeError: If deletion fails.
        """
        try:
            self.mlflow_client.delete_registered_model(name=name)
            logger.info(f"Deleted model '{name}' from MLflow")

        except MlflowException as e:
            raise RuntimeError(
                f"Failed to delete model '{name}' from MLflow: {str(e)}"
            )

    def update_model(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        remove_metadata: Optional[List[str]] = None,
    ) -> RegisteredModel:
        """Update a model in MLflow.

        Args:
            name: The name of the model.
            description: The description of the model.
            metadata: The metadata of the model.
            remove_metadata: The metadata to remove from the model.

        Returns:
            The updated model.

        Raises:
            RuntimeError: If update fails.
        """
        try:
            if description:
                self.mlflow_client.update_registered_model(
                    name=name,
                    description=description,
                )

            if metadata:
                for key, value in metadata.items():
                    self.mlflow_client.set_registered_model_tag(
                        name=name, key=key, value=value
                    )

            if remove_metadata:
                for key in remove_metadata:
                    self.mlflow_client.delete_registered_model_tag(
                        name=name, key=key
                    )

            logger.info(f"Updated model '{name}' in MLflow")

            return RegisteredModel(
                name=name,
                description=description,
                metadata=metadata,
            )

        except MlflowException as e:
            raise RuntimeError(
                f"Failed to update model '{name}' in MLflow: {str(e)}"
            )

    def get_model(self, name: str) -> RegisteredModel:
        """Get a model from MLflow.

        Args:
            name: The name of the model.

        Returns:
            The model.

        Raises:
            KeyError: If the model does not exist.
        """
        try:
            model = self.mlflow_client.get_registered_model(name=name)
            return RegisteredModel(
                name=model.name,
                description=model.description,
                metadata=model.tags,
            )

        except MlflowException as e:
            raise KeyError(
                f"Model '{name}' not found in MLflow registry: {str(e)}"
            )

    def list_models(
        self,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> List[RegisteredModel]:
        """List models from MLflow.

        Only lists models tagged with the management tag unless filtering by
        specific name.

        Args:
            name: A name to filter the models by.
            metadata: The metadata to filter the models by.

        Returns:
            A list of models.
        """
        try:
            filters = []
            if name:
                filters.append(f"name='{name}'")
            else:
                filters.append(
                    f"tags.`{MLFLOW_NOTION_TAG}`='{MLFLOW_NOTION_TAG_VALUE}'"
                )

            if metadata:
                for key, value in metadata.items():
                    filters.append(f"tags.`{key}`='{value}'")

            filter_string = " AND ".join(filters) if filters else None

            models = self.mlflow_client.search_registered_models(
                filter_string=filter_string
            )

            return [
                RegisteredModel(
                    name=model.name,
                    description=model.description,
                    metadata=model.tags,
                )
                for model in models
            ]

        except MlflowException as e:
            logger.error(f"Failed to list models from MLflow: {str(e)}")
            return []

    # ---------
    # Model Version Methods
    # ---------

    def register_model_version(
        self,
        name: str,
        version: Optional[str] = None,
        model_source_uri: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[ModelRegistryModelMetadata] = None,
        **kwargs: Any,
    ) -> RegistryModelVersion:
        """Register a model version to MLflow and optionally sync to Notion.

        Args:
            name: The name of the model.
            version: The version of the model (ignored, MLflow auto-generates).
            model_source_uri: The source URI of the model.
            description: The description of the model version.
            metadata: The registry metadata of the model version.
            **kwargs: Additional keyword arguments.

        Returns:
            The registered model version.

        Raises:
            ValueError: If no model source URI was provided.
            RuntimeError: If registration fails.
        """
        if not model_source_uri:
            raise ValueError(
                "Unable to register model version without model source URI."
            )

        try:
            try:
                model = self.mlflow_client.get_registered_model(name)
                if (
                    not model.tags
                    or model.tags.get(MLFLOW_NOTION_TAG)
                    != MLFLOW_NOTION_TAG_VALUE
                ):
                    self.mlflow_client.set_registered_model_tag(
                        name, MLFLOW_NOTION_TAG, MLFLOW_NOTION_TAG_VALUE
                    )
            except MlflowException:
                self.mlflow_client.create_registered_model(
                    name=name,
                    tags={MLFLOW_NOTION_TAG: MLFLOW_NOTION_TAG_VALUE},
                )

            tags = {MLFLOW_NOTION_TAG: MLFLOW_NOTION_TAG_VALUE}
            if metadata:
                metadata_dict = metadata.model_dump()
                tags.update({k: str(v) for k, v in metadata_dict.items() if v})

            mlflow_version = self.mlflow_client.create_model_version(
                name=name,
                source=model_source_uri,
                description=description,
                tags=tags,
            )

            logger.info(
                f"Registered model version {name}:{mlflow_version.version} in MLflow"
            )

            if self.config.sync_on_write:
                # Extract ZenML Model URL from kwargs if provided
                zenml_model_url = kwargs.get("zenml_model_url", None)

                try:
                    self._sync_version_to_notion(
                        mlflow_version, description, zenml_model_url
                    )
                    logger.info(
                        f"Synced {name}:{mlflow_version.version} to Notion"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to sync {name}:{mlflow_version.version} to Notion: {e}"
                    )
                    try:
                        log_metadata({"notion_sync_error": str(e)})
                    except Exception:
                        pass

            return self._mlflow_to_zenml_version(mlflow_version)

        except MlflowException as e:
            raise RuntimeError(
                f"Failed to register model version for '{name}': {str(e)}"
            )

    def delete_model_version(
        self,
        name: str,
        version: str,
    ) -> None:
        """Delete a model version from MLflow.

        Note: This does not automatically clean up Notion entries. Use the
        sync operation with cleanup_orphans=True to remove orphaned entries.

        Args:
            name: The name of the model.
            version: The version of the model.

        Raises:
            RuntimeError: If deletion fails.
        """
        try:
            self.mlflow_client.delete_model_version(name=name, version=version)
            logger.info(f"Deleted model version {name}:{version} from MLflow")

        except MlflowException as e:
            raise RuntimeError(
                f"Failed to delete model version {name}:{version}: {str(e)}"
            )

    def update_model_version(
        self,
        name: str,
        version: str,
        description: Optional[str] = None,
        metadata: Optional[ModelRegistryModelMetadata] = None,
        remove_metadata: Optional[List[str]] = None,
        stage: Optional[ModelVersionStage] = None,
    ) -> RegistryModelVersion:
        """Update a model version in MLflow and optionally sync to Notion.

        Args:
            name: The name of the model.
            version: The version of the model.
            description: The description of the model version.
            metadata: The metadata of the model version.
            remove_metadata: The metadata to remove from the model version.
            stage: The stage of the model version.

        Returns:
            The updated model version.

        Raises:
            RuntimeError: If update fails.
        """
        try:
            if description:
                self.mlflow_client.update_model_version(
                    name=name, version=version, description=description
                )

            if stage:
                self.mlflow_client.transition_model_version_stage(
                    name=name,
                    version=version,
                    stage=stage.value,
                    archive_existing_versions=False,
                )

            if metadata:
                metadata_dict = metadata.model_dump() if metadata else {}
                for key, value in metadata_dict.items():
                    if value:
                        self.mlflow_client.set_model_version_tag(
                            name=name,
                            version=version,
                            key=key,
                            value=str(value),
                        )

            if remove_metadata:
                for key in remove_metadata:
                    self.mlflow_client.delete_model_version_tag(
                        name=name, version=version, key=key
                    )

            logger.info(f"Updated model version {name}:{version} in MLflow")

            mlflow_version = self.mlflow_client.get_model_version(
                name=name, version=version
            )

            if self.config.sync_on_write:
                try:
                    self._sync_version_to_notion(mlflow_version, description)
                    logger.info(f"Synced {name}:{version} update to Notion")
                except Exception as e:
                    logger.warning(
                        f"Failed to sync {name}:{version} to Notion: {e}"
                    )

            return self._mlflow_to_zenml_version(mlflow_version)

        except MlflowException as e:
            raise RuntimeError(
                f"Failed to update model version {name}:{version}: {str(e)}"
            )

    def get_model_version(
        self,
        name: str,
        version: str,
    ) -> RegistryModelVersion:
        """Get a model version from MLflow.

        Args:
            name: The name of the model.
            version: The version of the model.

        Returns:
            The model version.

        Raises:
            KeyError: If the model version does not exist.
        """
        try:
            mlflow_version = self.mlflow_client.get_model_version(
                name=name, version=version
            )
            return self._mlflow_to_zenml_version(mlflow_version)

        except MlflowException as e:
            raise KeyError(
                f"Model version {name}:{version} not found: {str(e)}"
            )

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
        """List model versions from MLflow.

        Args:
            name: The name of the model.
            model_source_uri: The model source URI (not supported by MLflow search).
            metadata: The metadata to filter by (not fully supported).
            stage: The stage of the model version.
            count: The maximum number of model versions to return.
            created_after: The minimum creation time (not supported by MLflow search).
            created_before: The maximum creation time (not supported by MLflow search).
            order_by_date: The order of the model versions by creation time.
            **kwargs: Additional keyword arguments.

        Returns:
            The model versions.
        """
        try:
            filters = []
            if name:
                filters.append(f"name='{name}'")
            else:
                filters.append(
                    f"tags.`{MLFLOW_NOTION_TAG}`='{MLFLOW_NOTION_TAG_VALUE}'"
                )

            filter_string = " AND ".join(filters) if filters else None

            mlflow_versions = self.mlflow_client.search_model_versions(
                filter_string=filter_string,
                max_results=count or 1000,
                order_by=[
                    f"creation_timestamp {'ASC' if order_by_date == 'asc' else 'DESC'}"
                ]
                if order_by_date
                else None,
            )

            versions = [
                self._mlflow_to_zenml_version(v) for v in mlflow_versions
            ]

            if stage:
                versions = [v for v in versions if v.stage == stage]

            if created_after:
                versions = [
                    v
                    for v in versions
                    if v.created_at and v.created_at >= created_after
                ]

            if created_before:
                versions = [
                    v
                    for v in versions
                    if v.created_at and v.created_at <= created_before
                ]

            return versions[:count] if count else versions

        except MlflowException as e:
            logger.error(f"Failed to list model versions: {str(e)}")
            return []

    def load_model_version(
        self,
        name: str,
        version: str,
        **kwargs: Any,
    ) -> Any:
        """Load a model version from MLflow.

        Args:
            name: The name of the model.
            version: The version of the model.
            **kwargs: Additional keyword arguments passed to mlflow.pyfunc.load_model.

        Returns:
            The loaded model.

        Raises:
            RuntimeError: If loading fails.
        """
        try:
            from mlflow.pyfunc import load_model

            model_uri = f"models:/{name}/{version}"
            return load_model(model_uri, **kwargs)

        except Exception as e:
            raise RuntimeError(
                f"Failed to load model {name}:{version}: {str(e)}"
            )

    def get_model_uri_artifact_store(
        self,
        model_version: RegistryModelVersion,
    ) -> str:
        """Get the model URI from the artifact store.

        Args:
            model_version: The model version.

        Returns:
            The model source URI.
        """
        return model_version.model_source_uri

    # ---------
    # Helper Methods
    # ---------

    def _mlflow_to_zenml_version(
        self, mlflow_version: MLflowModelVersion
    ) -> RegistryModelVersion:
        """Convert MLflow model version to ZenML format.

        Args:
            mlflow_version: MLflow model version object.

        Returns:
            ZenML RegistryModelVersion object.
        """
        stage_mapping = {
            "None": ModelVersionStage.NONE,
            "Staging": ModelVersionStage.STAGING,
            "Production": ModelVersionStage.PRODUCTION,
            "Archived": ModelVersionStage.ARCHIVED,
        }
        stage = stage_mapping.get(
            mlflow_version.current_stage, ModelVersionStage.NONE
        )

        created_at = datetime.fromtimestamp(
            mlflow_version.creation_timestamp / 1000
        )
        last_updated = datetime.fromtimestamp(
            mlflow_version.last_updated_timestamp / 1000
        )

        metadata = None
        if mlflow_version.tags:
            metadata_dict = {
                k: v
                for k, v in mlflow_version.tags.items()
                if k != MLFLOW_NOTION_TAG
            }
            if metadata_dict:
                try:
                    metadata = ModelRegistryModelMetadata(**metadata_dict)
                except Exception:
                    pass

        return RegistryModelVersion(
            registered_model=RegisteredModel(name=mlflow_version.name),
            model_format="mlflow",
            model_library=None,
            version=str(mlflow_version.version),
            created_at=created_at,
            stage=stage,
            description=mlflow_version.description,
            last_updated_at=last_updated,
            metadata=metadata,
            model_source_uri=mlflow_version.source,
        )

    # ---------
    # Comprehensive Sync Method
    # ---------

    def sync_to_notion(
        self,
        model_name: Optional[str] = None,
        cleanup_orphans: bool = False,
    ) -> Dict[str, int]:
        """One-way sync from MLflow to Notion.

        Only syncs models tagged with zenml.mlflow_notion_managed.

        Args:
            model_name: Sync specific model only, or all models if None.
            cleanup_orphans: Archive Notion entries not found in MLflow.

        Returns:
            Statistics dictionary with keys: created, updated, unchanged,
            orphaned, errors.
        """
        stats = {
            "created": 0,
            "updated": 0,
            "unchanged": 0,
            "orphaned": 0,
            "errors": 0,
        }

        try:
            if model_name:
                try:
                    mlflow_models = [
                        self.mlflow_client.get_registered_model(model_name)
                    ]
                except MlflowException:
                    logger.warning(f"Model '{model_name}' not found in MLflow")
                    return stats
            else:
                filter_string = (
                    f"tags.`{MLFLOW_NOTION_TAG}`='{MLFLOW_NOTION_TAG_VALUE}'"
                )
                mlflow_models = self.mlflow_client.search_registered_models(
                    filter_string=filter_string
                )

            logger.info(f"Found {len(mlflow_models)} model(s) to sync")

            mlflow_version_keys = set()

            for model in mlflow_models:
                try:
                    mlflow_versions = self.mlflow_client.search_model_versions(
                        f"name='{model.name}' AND tags.`{MLFLOW_NOTION_TAG}`='{MLFLOW_NOTION_TAG_VALUE}'"
                    )

                    logger.info(
                        f"Syncing {len(mlflow_versions)} version(s) of '{model.name}'"
                    )

                    for mlflow_ver in mlflow_versions:
                        version_key = (model.name, str(mlflow_ver.version))
                        mlflow_version_keys.add(version_key)

                        try:
                            notion_ver = self._find_notion_version(
                                model.name, str(mlflow_ver.version)
                            )

                            if not notion_ver:
                                self._create_in_notion(mlflow_ver)
                                stats["created"] += 1
                            else:
                                properties = notion_ver.get("properties", {})
                                stage_prop = properties.get("Stage", {})
                                current_stage = (
                                    stage_prop.get("select", {}).get(
                                        "name", "None"
                                    )
                                    if stage_prop.get("select")
                                    else "None"
                                )

                                if current_stage != mlflow_ver.current_stage:
                                    self._update_notion_stage(
                                        notion_ver["id"],
                                        mlflow_ver.current_stage,
                                    )

                                    # Also update ZenML Model if it exists
                                    self._update_zenml_model_stage(
                                        model.name,
                                        str(mlflow_ver.version),
                                        mlflow_ver.current_stage,
                                    )

                                    stats["updated"] += 1
                                else:
                                    stats["unchanged"] += 1

                        except Exception as e:
                            logger.error(
                                f"Error syncing {model.name}:{mlflow_ver.version}: {e}"
                            )
                            stats["errors"] += 1

                except MlflowException as e:
                    logger.error(f"Error processing model '{model.name}': {e}")
                    stats["errors"] += 1

            if cleanup_orphans:
                try:
                    orphaned_count = self._cleanup_orphaned_entries(
                        mlflow_version_keys, model_name
                    )
                    stats["orphaned"] = orphaned_count
                except Exception as e:
                    logger.error(f"Error cleaning up orphaned entries: {e}")

            logger.info(
                f"Sync complete: {stats['created']} created, {stats['updated']} updated, "
                f"{stats['unchanged']} unchanged, {stats['orphaned']} orphaned, "
                f"{stats['errors']} errors"
            )

            return stats

        except Exception as e:
            logger.error(f"Sync operation failed: {e}")
            stats["errors"] += 1
            return stats

    def _update_zenml_model_stage(
        self,
        model_name: str,
        version: str,
        stage: str,
    ) -> None:
        """Update ZenML Model stage if the model exists.

        This ensures that when a model stage is changed in MLflow UI,
        the ZenML Model object also gets updated.

        Args:
            model_name: Name of the model
            version: Version number
            stage: New stage value
        """
        try:
            # Get ZenML client
            client = Client()

            # Try to find the ZenML Model
            try:
                zenml_model = client.get_model(model_name)

                # Map MLflow stage (title case) to ZenML ModelStages (lowercase)
                stage_mapping = {
                    "None": ModelStages.NONE,
                    "Staging": ModelStages.STAGING,
                    "Production": ModelStages.PRODUCTION,
                    "Archived": ModelStages.ARCHIVED,
                }
                zenml_stage = stage_mapping.get(stage, ModelStages.NONE)

                # Get the model version
                model_version = client.get_model_version(
                    model_name_or_id=zenml_model.id,
                    model_version_name_or_number_or_id=version,
                )

                # Update the stage if different (convert ModelStages to ModelVersionStage for comparison)
                current_stage_str = (
                    model_version.stage.value
                    if model_version.stage
                    else "None"
                )
                new_stage_str = zenml_stage.value

                if current_stage_str.lower() != new_stage_str.lower():
                    client.update_model_version(
                        model_name_or_id=zenml_model.id,
                        version_name_or_id=version,
                        stage=zenml_stage,
                    )
                    logger.info(
                        f"Updated ZenML Model {model_name}:{version} stage to {zenml_stage.value}"
                    )

            except KeyError:
                # Model doesn't exist in ZenML, skip
                logger.debug(
                    f"ZenML Model '{model_name}' not found, skipping ZenML update"
                )

        except Exception as e:
            # Don't fail the sync if ZenML update fails
            logger.warning(
                f"Failed to update ZenML Model {model_name}:{version}: {e}"
            )

    def _cleanup_orphaned_entries(
        self,
        mlflow_version_keys: set,
        model_name: Optional[str] = None,
    ) -> int:
        """Archive Notion entries that don't exist in MLflow.

        Args:
            mlflow_version_keys: Set of (model_name, version) tuples from MLflow
            model_name: Optional model name filter

        Returns:
            Number of orphaned entries archived
        """
        orphaned_count = 0

        try:
            data_source_id = self._get_data_source_id()

            body: Dict[str, Any] = {}
            if model_name:
                body["filter"] = {
                    "property": "Model Name",
                    "title": {"equals": model_name},
                }

            response = self.notion_client.request(
                method="post",
                path=f"data_sources/{data_source_id}/query",
                body=body,
            )

            for page in response.get("results", []):
                try:
                    properties = page.get("properties", {})

                    model_name_prop = properties.get("Model Name", {})
                    if not model_name_prop.get("title"):
                        continue
                    notion_model_name = model_name_prop["title"][0]["text"][
                        "content"
                    ]

                    version_prop = properties.get("Version", {})
                    if not version_prop.get("rich_text"):
                        continue
                    notion_version = version_prop["rich_text"][0]["text"][
                        "content"
                    ]

                    version_key = (notion_model_name, notion_version)
                    if version_key not in mlflow_version_keys:
                        self.notion_client.pages.update(
                            page_id=page["id"],
                            archived=True,
                        )
                        logger.info(
                            f"Archived orphaned Notion entry: "
                            f"{notion_model_name}:{notion_version}"
                        )
                        orphaned_count += 1

                except Exception as e:
                    logger.warning(f"Error checking Notion page: {e}")

        except Exception as e:
            logger.error(f"Error during orphan cleanup: {e}")

        return orphaned_count
