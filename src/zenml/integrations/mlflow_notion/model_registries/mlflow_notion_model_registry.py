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
from typing import Any, Dict, List, Optional, Tuple, cast

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

        If an MLflow experiment tracker is present in the stack, uses its
        configuration. Otherwise, uses the registry's own tracking_uri config.

        Returns:
            The MLflow client.
        """
        if not self._mlflow_client:
            # Reuse MLflow configuration from experiment tracker if available to avoid
            # duplicate configuration and ensure both components use the same tracking server
            from zenml.client import Client

            try:
                experiment_tracker = Client().active_stack.experiment_tracker
                if (
                    experiment_tracker
                    and experiment_tracker.flavor == "mlflow"
                ):
                    # Import here to avoid circular dependency
                    from zenml.integrations.mlflow.experiment_trackers.mlflow_experiment_tracker import (
                        MLFlowExperimentTracker,
                    )

                    if isinstance(experiment_tracker, MLFlowExperimentTracker):
                        experiment_tracker.configure_mlflow()
                        logger.info(
                            "Using MLflow configuration from experiment tracker"
                        )
                    else:
                        self._configure_mlflow_from_registry()
                else:
                    self._configure_mlflow_from_registry()
            except Exception:
                self._configure_mlflow_from_registry()

            self._mlflow_client = MlflowClient()
        return self._mlflow_client

    def _configure_mlflow_from_registry(self) -> None:
        """Configure MLflow using the registry's own config."""
        if self.config.tracking_uri:
            mlflow.set_tracking_uri(self.config.tracking_uri)
            logger.debug(
                f"Set MLflow tracking URI to {self.config.tracking_uri}"
            )

        if self.config.registry_uri:
            mlflow.set_registry_uri(self.config.registry_uri)
            logger.debug(
                f"Set MLflow registry URI to {self.config.registry_uri}"
            )

    def configure_mlflow(self) -> None:
        """Configure MLflow tracking for the current context.

        This method configures MLflow to use the same tracking server as the
        registry, enabling MLflow autologging and experiment tracking to work
        seamlessly with the model registry.

        Call this at the start of your training steps before using MLflow:
            ```python
            from zenml.client import Client

            registry = Client().active_stack.model_registry
            registry.configure_mlflow()

            mlflow.sklearn.autolog()
            model.fit(X, y)
            ```

        If an MLflow experiment tracker is in the stack, this uses its
        configuration. Otherwise, it uses the registry's tracking_uri.
        """
        # Accessing the property triggers MLflow configuration via the property getter
        _ = self.mlflow_client

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
            "Stage": {
                "select": {"name": mlflow_version.current_stage or "None"}
            },
        }

        if description or mlflow_version.description:
            desc_text = description or mlflow_version.description
            properties["Description"] = {
                "rich_text": [{"text": {"content": desc_text}}]
            }

        if zenml_model_url:
            properties["ZenML Model URL"] = {"url": zenml_model_url}

        # Include MLflow UI link for easy navigation from Notion to model version
        tracking_uri = self.config.tracking_uri or mlflow.get_tracking_uri()
        if tracking_uri:
            mlflow_url = f"{tracking_uri.rstrip('/')}/#/models/{mlflow_version.name}/versions/{mlflow_version.version}"
            properties["MLflow Model URL"] = {"url": mlflow_url}

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

    def _fetch_all_notion_versions(
        self, model_name: Optional[str] = None
    ) -> Dict[Tuple[str, str], Dict[str, Any]]:
        """Batch fetch all model versions from Notion database.

        This is much more efficient than querying for each version individually
        when syncing large numbers of models.

        Args:
            model_name: Optional model name to filter by

        Returns:
            Dictionary mapping (model_name, version) tuples to Notion page data
        """
        notion_index = {}

        try:
            data_source_id = self._get_data_source_id()

            body: Dict[str, Any] = {}
            if model_name:
                body["filter"] = {
                    "property": "Model Name",
                    "title": {"equals": model_name},
                }

            # Notion API paginates results, so we need to iterate until all pages are fetched
            has_more = True
            start_cursor = None

            while has_more:
                if start_cursor:
                    body["start_cursor"] = start_cursor

                response = self.notion_client.request(
                    method="post",
                    path=f"data_sources/{data_source_id}/query",
                    body=body,
                )

                # Index by (model_name, version) tuple for O(1) lookup during sync
                for page in response.get("results", []):
                    properties = page.get("properties", {})

                    title_prop = properties.get("Model Name", {})
                    title_list = title_prop.get("title", [])
                    page_model_name = (
                        title_list[0].get("text", {}).get("content", "")
                        if title_list and len(title_list) > 0
                        else ""
                    )

                    version_prop = properties.get("Version", {})
                    version_list = version_prop.get("rich_text", [])
                    page_version = (
                        version_list[0].get("text", {}).get("content", "")
                        if version_list and len(version_list) > 0
                        else ""
                    )

                    if page_model_name and page_version:
                        key = (page_model_name, page_version)
                        notion_index[key] = page

                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")

            logger.debug(
                f"Fetched {len(notion_index)} version(s) from Notion database"
            )
            return notion_index

        except APIResponseError as e:
            logger.warning(f"Error fetching Notion versions: {e}")
            return {}

    def _find_notion_version(
        self, model_name: str, version: str
    ) -> Optional[Dict[str, Any]]:
        """Find a model version in the Notion database.

        Note: For bulk operations, prefer _fetch_all_notion_versions() for better
        performance. This method makes individual API calls.

        Args:
            model_name: Name of the model
            version: Version number

        Returns:
            Notion page data if found, None otherwise.
        """
        if not model_name or not version:
            logger.warning(
                f"Invalid model_name or version provided: model_name={model_name}, version={version}"
            )
            return None

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

            results = response.get("results", [])
            if results:
                if len(results) > 1:
                    logger.warning(
                        f"Found {len(results)} duplicate Notion entries for "
                        f"{model_name}:{version}, using first result"
                    )
                return cast(Dict[str, Any], results[0])
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
    ) -> str:
        """Create a model version entry in Notion database.

        Args:
            mlflow_version: MLflow model version to create in Notion
            description: Optional description
            zenml_model_url: Optional ZenML Model URL for dashboard link

        Returns:
            Notion page ID of the created entry
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
        return page_id

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

    def _update_notion_page(
        self,
        page_id: str,
        mlflow_version: MLflowModelVersion,
        description: Optional[str] = None,
        zenml_model_url: Optional[str] = None,
    ) -> None:
        """Update all properties of a model version in Notion from MLflow.

        This method treats MLflow as the source of truth and updates all
        properties in Notion to match the MLflow state.

        Args:
            page_id: Notion page ID
            mlflow_version: MLflow model version with current state
            description: Optional description override
            zenml_model_url: Optional ZenML Model URL
        """
        properties = self._notion_properties_from_mlflow(
            mlflow_version=mlflow_version,
            description=description,
            zenml_model_url=zenml_model_url,
        )

        # Notion doesn't allow updating title properties after page creation
        properties.pop("Model Name", None)

        self.notion_client.pages.update(
            page_id=page_id,
            properties=properties,
        )
        logger.debug(
            f"Updated Notion page {page_id} with all properties from MLflow"
        )

    def _add_registry_links_metadata(
        self,
        model_name: str,
        version: str,
        mlflow_version: Optional[MLflowModelVersion] = None,
        notion_page_id: Optional[str] = None,
        use_infer: bool = True,
    ) -> None:
        """Add MLflow and Notion URLs to ZenML Model metadata.

        This creates clickable links in the ZenML dashboard for easy
        navigation between MLflow, Notion, and ZenML.

        Args:
            model_name: Name of the model
            version: Version number
            mlflow_version: MLflow model version object (for URL construction)
            notion_page_id: Notion page ID (for URL construction)
            use_infer: If True, use infer_model=True (for pipeline context).
                If False, use explicit model_name/version (for sync context).
        """
        registry_links = {}

        if mlflow_version:
            tracking_uri = (
                self.config.tracking_uri or mlflow.get_tracking_uri()
            )
            if tracking_uri:
                mlflow_url = f"{tracking_uri.rstrip('/')}/#/models/{model_name}/versions/{version}"
                registry_links["mlflow_model_url"] = mlflow_url

        if notion_page_id:
            notion_url = f"https://notion.so/{notion_page_id.replace('-', '')}"
            registry_links["notion_page_url"] = notion_url

        if registry_links:
            try:
                if use_infer:
                    # In pipeline context, infer_model=True automatically associates metadata
                    # with the current model version being created in this step
                    log_metadata(
                        metadata={"registry_links": registry_links},
                        infer_model=True,
                    )
                else:
                    # Outside pipeline context (e.g., sync operations), we must explicitly
                    # specify the model and version since there's no active pipeline context
                    log_metadata(
                        metadata={"registry_links": registry_links},
                        model_name=model_name,
                        model_version=version,
                    )
                logger.info(
                    f"Added cross-system URLs to ZenML Model {model_name}:{version}"
                )
            except Exception as e:
                logger.debug(f"Failed to add metadata to ZenML Model: {e}")

    def _add_cross_system_links_to_mlflow(
        self,
        model_name: str,
        version: str,
        notion_page_id: Optional[str] = None,
        zenml_model_url: Optional[str] = None,
    ) -> None:
        """Add Notion and ZenML URLs to MLflow model version tags.

        This creates clickable links in MLflow UI for easy navigation
        to Notion database and ZenML dashboard.

        Args:
            model_name: Name of the model
            version: Version number
            notion_page_id: Notion page ID (optional)
            zenml_model_url: ZenML Model URL (optional)
        """
        try:
            if notion_page_id:
                notion_url = (
                    f"https://notion.so/{notion_page_id.replace('-', '')}"
                )
                self.mlflow_client.set_model_version_tag(
                    name=model_name,
                    version=version,
                    key="notion_page_url",
                    value=notion_url,
                )
                logger.debug(
                    f"Added Notion URL to MLflow model {model_name}:{version}"
                )

            if zenml_model_url:
                self.mlflow_client.set_model_version_tag(
                    name=model_name,
                    version=version,
                    key="zenml_model_url",
                    value=zenml_model_url,
                )
                logger.debug(
                    f"Added ZenML URL to MLflow model {model_name}:{version}"
                )

            if notion_page_id or zenml_model_url:
                logger.info(
                    f"Added cross-system links to MLflow model {model_name}:{version}"
                )
        except Exception as e:
            logger.debug(f"Failed to add cross-system links to MLflow: {e}")

    def _sync_version_to_notion(
        self,
        mlflow_version: MLflowModelVersion,
        description: Optional[str] = None,
        zenml_model_url: Optional[str] = None,
    ) -> Optional[str]:
        """Sync a single model version from MLflow to Notion.

        This is used for auto-sync on write operations. It creates the version
        in Notion if it doesn't exist, or updates the stage if it changed.

        Args:
            mlflow_version: MLflow model version to sync.
            description: Optional description override.
            zenml_model_url: Optional ZenML Model URL for dashboard link.

        Returns:
            Notion page ID if created/found, None otherwise
        """
        notion_version = self._find_notion_version(
            mlflow_version.name, str(mlflow_version.version)
        )

        if not notion_version:
            page_id = self._create_in_notion(
                mlflow_version, description, zenml_model_url
            )
            return page_id
        else:
            properties = notion_version.get("properties", {})
            stage_prop = properties.get("Stage", {})
            current_stage = (
                stage_prop.get("select", {}).get("name", "None")
                if stage_prop.get("select")
                else "None"
            )

            mlflow_stage = mlflow_version.current_stage or "None"
            if current_stage != mlflow_stage:
                self._update_notion_stage(notion_version["id"], mlflow_stage)

            return notion_version.get("id")

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
                    notion_page_id = self._sync_version_to_notion(
                        mlflow_version, description, zenml_model_url
                    )
                    logger.info(
                        f"Synced {name}:{mlflow_version.version} to Notion"
                    )

                    # Add cross-system links to MLflow model version tags
                    self._add_cross_system_links_to_mlflow(
                        model_name=name,
                        version=str(mlflow_version.version),
                        notion_page_id=notion_page_id,
                        zenml_model_url=zenml_model_url,
                    )

                    # Add cross-system URLs to ZenML Model metadata
                    self._add_registry_links_metadata(
                        model_name=name,
                        version=str(mlflow_version.version),
                        mlflow_version=mlflow_version,
                        notion_page_id=notion_page_id,
                    )

                except Exception as e:
                    logger.warning(
                        f"Failed to sync {name}:{mlflow_version.version} to Notion: {e}"
                    )
                    try:
                        log_metadata(
                            metadata={"notion_sync_error": str(e)},
                            infer_model=True,
                        )
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
        mlflow_stage = mlflow_version.current_stage or "None"
        stage = stage_mapping.get(mlflow_stage, ModelVersionStage.NONE)

        created_at = datetime.fromtimestamp(
            mlflow_version.creation_timestamp / 1000
        )
        last_updated_timestamp = (
            mlflow_version.last_updated_timestamp
            or mlflow_version.creation_timestamp
        )
        last_updated = datetime.fromtimestamp(last_updated_timestamp / 1000)

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
                except Exception as e:
                    logger.debug(
                        f"Failed to parse metadata for {mlflow_version.name}:{mlflow_version.version}: {e}"
                    )

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
        """Comprehensive sync from MLflow to Notion and ZenML.

        This method ensures all three systems are consistent:
        - MLflow → Notion: Creates/updates Notion database entries
        - Notion → MLflow: Adds notion_page_url tag to MLflow versions
        - MLflow → ZenML: Updates stages and adds cross-system URLs

        Only syncs models tagged with zenml.mlflow_notion_managed.

        Recovery capabilities:
        - Creates missing Notion entries for MLflow versions
        - Adds missing cross-system links (MLflow tags, ZenML metadata)
        - Updates stages in Notion and ZenML to match MLflow
        - Handles incomplete syncs from transient failures

        Limitations:
        - Only syncs MLflow versions that exist in ZenML Model context
        - Cannot create ZenML Model versions (they must be created by pipelines)
        - Skips ZenML updates if Model or version doesn't exist
        - Version numbers may differ between MLflow and ZenML (independent counters)

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

            # Batch fetch all Notion versions upfront to avoid N+1 query problem during sync
            logger.info("Fetching existing Notion entries...")
            notion_index = self._fetch_all_notion_versions(
                model_name=model_name
            )
            logger.info(f"Found {len(notion_index)} existing Notion entries")

            mlflow_version_keys = set()

            for model_idx, model in enumerate(mlflow_models, 1):
                try:
                    mlflow_versions = self.mlflow_client.search_model_versions(
                        f"name='{model.name}' AND tags.`{MLFLOW_NOTION_TAG}`='{MLFLOW_NOTION_TAG_VALUE}'"
                    )

                    logger.info(
                        f"[{model_idx}/{len(mlflow_models)}] Syncing {len(mlflow_versions)} "
                        f"version(s) of '{model.name}'"
                    )

                    # Process versions in descending order to handle ZenML's constraint
                    # that only one version can occupy Production/Staging. When MLflow has
                    # multiple versions in the same stage, the highest version number wins.
                    sorted_versions = sorted(
                        mlflow_versions,
                        key=lambda v: int(v.version),
                        reverse=True,
                    )

                    for ver_idx, mlflow_ver in enumerate(sorted_versions, 1):
                        version_key = (model.name, str(mlflow_ver.version))
                        mlflow_version_keys.add(version_key)

                        if len(mlflow_versions) > 10 and ver_idx % 10 == 0:
                            logger.info(
                                f"  Progress: {ver_idx}/{len(mlflow_versions)} versions processed"
                            )

                        try:
                            notion_ver = notion_index.get(
                                (model.name, str(mlflow_ver.version))
                            )

                            notion_page_id: Optional[str] = None

                            if not notion_ver:
                                notion_page_id = self._create_in_notion(
                                    mlflow_ver
                                )
                                stats["created"] += 1

                                if notion_page_id:
                                    self._add_cross_system_links_to_mlflow(
                                        model_name=model.name,
                                        version=str(mlflow_ver.version),
                                        notion_page_id=notion_page_id,
                                    )
                            else:
                                # MLflow is source of truth - check if Notion needs updating
                                needs_update = False

                                properties = notion_ver.get("properties", {})

                                stage_prop = properties.get("Stage", {})
                                current_stage = (
                                    stage_prop.get("select", {}).get(
                                        "name", "None"
                                    )
                                    if stage_prop.get("select")
                                    else "None"
                                )
                                mlflow_stage = (
                                    mlflow_ver.current_stage or "None"
                                )
                                if current_stage != mlflow_stage:
                                    needs_update = True

                                desc_prop = properties.get("Description", {})
                                current_desc = (
                                    desc_prop.get("rich_text", [{}])[0]
                                    .get("text", {})
                                    .get("content", "")
                                    if desc_prop.get("rich_text")
                                    else ""
                                )
                                mlflow_desc = mlflow_ver.description or ""
                                if current_desc != mlflow_desc:
                                    needs_update = True

                                if needs_update:
                                    # Preserve ZenML Model URL to prevent data loss during updates
                                    zenml_model_url = None
                                    zenml_url_prop = properties.get(
                                        "ZenML Model URL", {}
                                    )
                                    if zenml_url_prop.get("url"):
                                        zenml_model_url = zenml_url_prop["url"]

                                    self._update_notion_page(
                                        notion_ver["id"],
                                        mlflow_ver,
                                        zenml_model_url=zenml_model_url,
                                    )
                                    stats["updated"] += 1
                                else:
                                    # Check if MLflow Model URL is missing (for older entries
                                    # created before we started adding this field)
                                    notion_mlflow_url = (
                                        notion_ver.get("properties", {})
                                        .get("MLflow Model URL", {})
                                        .get("url")
                                    )

                                    if not notion_mlflow_url:
                                        # Preserve existing ZenML URL while adding missing MLflow URL
                                        zenml_model_url = None
                                        zenml_url_prop = notion_ver.get(
                                            "properties", {}
                                        ).get("ZenML Model URL", {})

                                        # Handle both url property type and legacy rich_text format
                                        if zenml_url_prop:
                                            if zenml_url_prop.get("url"):
                                                zenml_model_url = (
                                                    zenml_url_prop["url"]
                                                )
                                            elif zenml_url_prop.get(
                                                "rich_text"
                                            ):
                                                rich_text = zenml_url_prop[
                                                    "rich_text"
                                                ]
                                                if (
                                                    rich_text
                                                    and len(rich_text) > 0
                                                ):
                                                    zenml_model_url = (
                                                        rich_text[0]
                                                        .get("text", {})
                                                        .get("content")
                                                    )

                                        self._update_notion_page(
                                            notion_ver["id"],
                                            mlflow_ver,
                                            zenml_model_url=zenml_model_url,
                                        )
                                        stats["updated"] += 1
                                        needs_update = True
                                    else:
                                        stats["unchanged"] += 1

                                notion_page_id = cast(str, notion_ver["id"])

                            # Ensure cross-system links exist in MLflow (recovery for incomplete syncs)
                            if notion_page_id:
                                existing_tags = mlflow_ver.tags or {}
                                if "notion_page_url" not in existing_tags:
                                    try:
                                        self._add_cross_system_links_to_mlflow(
                                            model_name=model.name,
                                            version=str(mlflow_ver.version),
                                            notion_page_id=notion_page_id,
                                        )
                                    except Exception as e:
                                        logger.debug(
                                            f"Failed to add cross-system links to MLflow: {e}"
                                        )

                            # Update ZenML Model stage to match MLflow (best-effort, won't fail sync)
                            mlflow_stage = mlflow_ver.current_stage or "None"
                            self._update_zenml_model_stage(
                                model.name,
                                str(mlflow_ver.version),
                                mlflow_stage,
                                mlflow_version=mlflow_ver,
                                notion_page_id=notion_page_id,
                            )

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
        mlflow_version: Optional[MLflowModelVersion] = None,
        notion_page_id: Optional[str] = None,
    ) -> None:
        """Update ZenML Model stage and metadata if the model exists.

        This ensures that when a model stage is changed in MLflow UI,
        the ZenML Model object also gets updated. It also stores links
        to MLflow and Notion for easy navigation between systems.

        Args:
            model_name: Name of the model
            version: Version number
            stage: New stage value
            mlflow_version: MLflow model version object (for URL construction)
            notion_page_id: Notion page ID (for URL construction)
        """
        try:
            client = Client()

            try:
                zenml_model = client.get_model(model_name)

                # MLflow uses title case ("Production") while ZenML uses lowercase ("production")
                stage_mapping = {
                    "None": ModelStages.NONE,
                    "Staging": ModelStages.STAGING,
                    "Production": ModelStages.PRODUCTION,
                    "Archived": ModelStages.ARCHIVED,
                }
                zenml_stage = stage_mapping.get(stage, ModelStages.NONE)

                model_version = client.get_model_version(
                    model_name_or_id=zenml_model.id,
                    model_version_name_or_number_or_id=version,
                )

                # Handle both enum and string representations of stage
                if model_version.stage:
                    current_stage_str = (
                        model_version.stage.value
                        if hasattr(model_version.stage, "value")
                        else str(model_version.stage)
                    )
                else:
                    current_stage_str = "None"

                new_stage_str = zenml_stage.value

                if current_stage_str.lower() != new_stage_str.lower():
                    # ZenML enforces single-version-per-stage for Production/Staging.
                    # When MLflow has multiple versions in the same stage, we process them
                    # in descending order so the highest version number wins.
                    if zenml_stage in (
                        ModelStages.PRODUCTION,
                        ModelStages.STAGING,
                    ):
                        try:
                            existing_version = client.list_model_versions(
                                model_name_or_id=zenml_model.id,
                                stage=zenml_stage,
                            )
                            if existing_version:
                                old_version = existing_version[0]
                                old_version_num = int(old_version.number)
                                new_version_num = int(version)

                                # Only demote existing version if new version is higher
                                # (we process versions descending, so highest wins)
                                if new_version_num > old_version_num:
                                    logger.info(
                                        f"Demoting {model_name}:{old_version.number} from "
                                        f"{zenml_stage.value} to make room for version {version}"
                                    )
                                    client.update_model_version(
                                        model_name_or_id=zenml_model.id,
                                        version_name_or_id=str(
                                            old_version.number
                                        ),
                                        stage=ModelStages.NONE,
                                        force=True,
                                    )
                                else:
                                    logger.info(
                                        f"Skipping {model_name}:{version} - version {old_version.number} "
                                        f"already occupies {zenml_stage.value} stage"
                                    )
                                    return
                        except Exception as e:
                            logger.debug(
                                f"Could not check for existing {zenml_stage.value} version: {e}"
                            )

                    # Override ZenML's stage transition validation since MLflow is source of truth
                    client.update_model_version(
                        model_name_or_id=zenml_model.id,
                        version_name_or_id=version,
                        stage=zenml_stage,
                        force=True,
                    )
                    logger.info(
                        f"Updated ZenML Model {model_name}:{version} stage to {zenml_stage.value}"
                    )

                # Add cross-system URLs for navigation between MLflow, Notion, and ZenML
                self._add_registry_links_metadata(
                    model_name=model_name,
                    version=version,
                    mlflow_version=mlflow_version,
                    notion_page_id=notion_page_id,
                    use_infer=False,
                )

            except KeyError:
                logger.info(
                    f"ZenML Model '{model_name}:{version}' not found. "
                    "This MLflow version was likely created outside a ZenML pipeline. "
                    "To track it in ZenML, create a pipeline that registers this model."
                )

        except Exception as e:
            # Don't fail sync operation if ZenML update fails (best-effort sync)
            logger.warning(
                f"Failed to update ZenML Model {model_name}:{version}: {e}"
            )

    def _cleanup_orphaned_entries(
        self,
        mlflow_version_keys: set[Tuple[str, str]],
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
                    title_list = model_name_prop.get("title", [])
                    if not title_list or len(title_list) == 0:
                        continue
                    notion_model_name = (
                        title_list[0].get("text", {}).get("content", "")
                    )
                    if not notion_model_name:
                        continue

                    version_prop = properties.get("Version", {})
                    version_list = version_prop.get("rich_text", [])
                    if not version_list or len(version_list) == 0:
                        continue
                    notion_version = (
                        version_list[0].get("text", {}).get("content", "")
                    )
                    if not notion_version:
                        continue

                    version_key = (notion_model_name, notion_version)
                    if version_key not in mlflow_version_keys:
                        try:
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
                            logger.warning(
                                f"Failed to archive orphaned entry "
                                f"{notion_model_name}:{notion_version}: {e}"
                            )

                except Exception as e:
                    logger.warning(f"Error checking Notion page: {e}")

        except Exception as e:
            logger.error(f"Error during orphan cleanup: {e}")

        return orphaned_count
