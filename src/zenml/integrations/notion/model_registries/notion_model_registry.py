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
"""Implementation of the Notion model registry for ZenML."""

from datetime import datetime
from typing import Any, Dict, List, Optional, cast

from notion_client import Client
from notion_client.errors import APIResponseError

from zenml import log_metadata
from zenml.integrations.notion.flavors.notion_model_registry_flavor import (
    NotionModelRegistryConfig,
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


class NotionModelRegistry(BaseModelRegistry):
    """Register models using Notion databases."""

    _client: Optional[Client] = None

    @property
    def config(self) -> NotionModelRegistryConfig:
        """Returns the `NotionModelRegistryConfig` config.

        Returns:
            The configuration.
        """
        return cast(NotionModelRegistryConfig, self._config)

    @property
    def notion_client(self) -> Client:
        """Get the Notion client.

        Returns:
            The Notion client.
        """
        if not self._client:
            token = self.config.notion_api_token
            self._client = Client(auth=token, notion_version="2025-09-03")
        return self._client

    def _get_data_source_id(self) -> str:
        """Get the data source ID for the configured database.

        For single-source databases, returns the ID of the first (and only)
        data source. For multi-source databases, returns the first data source.

        Returns:
            The data source ID.

        Raises:
            RuntimeError: If the database has no data sources.
        """
        try:
            response = self.notion_client.databases.retrieve(
                database_id=self.config.database_id
            )
            data_sources = response.get("data_sources", [])

            if not data_sources:
                raise RuntimeError(
                    f"Database {self.config.database_id} has no data sources. "
                    "This may indicate the database was deleted or the integration "
                    "doesn't have access to it."
                )

            # For now, we use the first data source
            # In the future, this could be configurable
            data_source_id = data_sources[0]["id"]
            logger.debug(
                f"Using data source {data_source_id} for database "
                f"{self.config.database_id}"
            )
            return data_source_id

        except APIResponseError as e:
            raise RuntimeError(
                f"Failed to retrieve data sources for database "
                f"{self.config.database_id}: {str(e)}"
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
        """Register a model in the Notion model registry.

        For Notion, we simply track models by their versions in the database.
        This method checks if any versions exist and returns a RegisteredModel.

        Args:
            name: The name of the model.
            description: The description of the model.
            metadata: The metadata of the model.

        Returns:
            The registered model.

        Raises:
            RuntimeError: If the model already exists.
        """
        try:
            self.get_model(name)
            raise RuntimeError(
                f"Model with name {name} already exists in the Notion model "
                f"registry. Please use a different name."
            )
        except KeyError:
            pass

        return RegisteredModel(
            name=name,
            description=description,
            metadata=metadata,
        )

    def delete_model(
        self,
        name: str,
    ) -> None:
        """Delete a model from the Notion model registry.

        This deletes all version pages associated with the model.

        Args:
            name: The name of the model.

        Raises:
            RuntimeError: If the model does not exist or deletion fails.
        """
        try:
            self.get_model(name=name)
        except KeyError as e:
            raise RuntimeError(f"Model does not exist: {str(e)}")

        try:
            data_source_id = self._get_data_source_id()
            response = self.notion_client.request(
                method="post",
                path=f"data_sources/{data_source_id}/query",
                body={
                    "filter": {
                        "property": "Model Name",
                        "title": {
                            "equals": name,
                        },
                    },
                },
            )

            for page in response.get("results", []):
                page_id = page["id"]
                self.notion_client.pages.update(
                    page_id=page_id,
                    archived=True,
                )

        except APIResponseError as e:
            raise RuntimeError(
                f"Failed to delete model with name {name} from Notion model "
                f"registry: {str(e)}"
            )

    def update_model(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        remove_metadata: Optional[List[str]] = None,
    ) -> RegisteredModel:
        """Update a model in the Notion model registry.

        Note: Notion doesn't have a separate "model" entity, so this method
        is primarily for API compatibility.

        Args:
            name: The name of the model.
            description: The description of the model.
            metadata: The metadata of the model.
            remove_metadata: The metadata to remove from the model.

        Returns:
            The updated model.
        """
        self.get_model(name=name)

        return RegisteredModel(
            name=name,
            description=description,
            metadata=metadata,
        )

    def get_model(self, name: str) -> RegisteredModel:
        """Get a model from the Notion model registry.

        Args:
            name: The name of the model.

        Returns:
            The model.

        Raises:
            KeyError: If the model does not exist.
        """
        try:
            data_source_id = self._get_data_source_id()
            response = self.notion_client.request(
                method="post",
                path=f"data_sources/{data_source_id}/query",
                body={
                    "filter": {
                        "property": "Model Name",
                        "title": {
                            "equals": name,
                        },
                    },
                    "page_size": 1,
                },
            )

            if not response.get("results"):
                raise KeyError(
                    f"Model with name {name} not found in the Notion model "
                    f"registry."
                )

            return RegisteredModel(
                name=name,
                description=None,
                metadata=None,
            )

        except APIResponseError as e:
            raise KeyError(
                f"Failed to get model with name {name} from the Notion model "
                f"registry: {str(e)}"
            )

    def list_models(
        self,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> List[RegisteredModel]:
        """List models in the Notion model registry.

        Args:
            name: A name to filter the models by.
            metadata: The metadata to filter the models by.

        Returns:
            A list of models (RegisteredModel)
        """
        try:
            data_source_id = self._get_data_source_id()
            body = {}
            if name:
                body["filter"] = {
                    "property": "Model Name",
                    "title": {
                        "equals": name,
                    },
                }

            response = self.notion_client.request(
                method="post",
                path=f"data_sources/{data_source_id}/query",
                body=body,
            )

            model_names = set()
            for page in response.get("results", []):
                properties = page.get("properties", {})
                model_name_prop = properties.get("Model Name", {})
                if model_name_prop.get("title"):
                    model_name = model_name_prop["title"][0]["text"]["content"]
                    model_names.add(model_name)

            return [
                RegisteredModel(
                    name=model_name, description=None, metadata=None
                )
                for model_name in sorted(model_names)
            ]

        except APIResponseError as e:
            logger.error(f"Failed to list models from Notion: {str(e)}")
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
        """Register a model version to the Notion model registry.

        This creates a new page in the Notion database with all the model
        metadata.

        Args:
            name: The name of the model.
            model_source_uri: The source URI of the model.
            version: The version of the model.
            description: The description of the model version.
            metadata: The registry metadata of the model version.
            **kwargs: Additional keyword arguments.

        Returns:
            The registered model version.

        Raises:
            ValueError: If no model source URI or version was provided.
            RuntimeError: If the registration fails.
        """
        if not model_source_uri:
            raise ValueError(
                "Unable to register model version without model source URI."
            )

        if not version:
            raise ValueError(
                "Unable to register model version without a version number."
            )

        metadata_dict = metadata.model_dump() if metadata else {}

        properties = self._convert_to_notion_properties(
            name=name,
            version=version,
            model_source_uri=model_source_uri,
            description=description,
            metadata=metadata_dict,
        )

        try:
            data_source_id = self._get_data_source_id()
            response = self.notion_client.pages.create(
                parent={
                    "type": "data_source_id",
                    "data_source_id": data_source_id,
                },
                properties=properties,
            )

            created_at = datetime.now()
            page_id = response["id"]

            logger.info(
                f"Successfully registered model version {name}:{version} "
                f"in Notion (page ID: {page_id})"
            )

            # Log metadata to ZenML's metadata system for tracking
            zenml_metadata = {
                "notion_registry": {
                    "model_name": name,
                    "version": version,
                    "model_source_uri": model_source_uri,
                    "notion_page_id": page_id,
                    "notion_database_id": self.config.database_id,
                    "stage": "None",
                }
            }

            if description:
                zenml_metadata["notion_registry"]["description"] = description

            # Add all metadata fields
            if metadata_dict:
                zenml_metadata["model_metadata"] = metadata_dict

            # Log the metadata (this will be associated with the current step if called from within a step)
            try:
                log_metadata(metadata=zenml_metadata)
                logger.debug("Metadata logged to ZenML tracking system")
            except Exception as e:
                # Don't fail the registration if metadata logging fails
                logger.warning(f"Failed to log metadata to ZenML: {e}")

            return RegistryModelVersion(
                registered_model=RegisteredModel(name=name),
                model_format="notion_tracked",
                model_library=None,
                version=version,
                created_at=created_at,
                stage=ModelVersionStage.NONE,
                description=description,
                last_updated_at=created_at,
                metadata=metadata,
                model_source_uri=model_source_uri,
            )

        except APIResponseError as e:
            raise RuntimeError(
                f"Failed to register model version with name '{name}' and "
                f"version '{version}' to the Notion model registry. "
                f"Error: {e}"
            )

    def delete_model_version(
        self,
        name: str,
        version: str,
    ) -> None:
        """Delete a model version from the Notion model registry.

        Args:
            name: The name of the model.
            version: The version of the model.

        Raises:
            RuntimeError: If the deletion fails.
        """
        self.get_model_version(name=name, version=version)

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
                                    "equals": name,
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

            for page in response.get("results", []):
                page_id = page["id"]
                self.notion_client.pages.update(
                    page_id=page_id,
                    archived=True,
                )

        except APIResponseError as e:
            raise RuntimeError(
                f"Failed to delete model version '{version}' of model '{name}' "
                f"from the Notion model registry: {str(e)}"
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
        """Update a model version in the Notion model registry.

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
            RuntimeError: If the update fails.
        """
        self.get_model_version(name=name, version=version)

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
                                    "equals": name,
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

            if not response.get("results"):
                raise RuntimeError(
                    f"Model version '{name}:{version}' not found."
                )

            page_id = response["results"][0]["id"]

            update_properties: Dict[str, Any] = {}

            if description:
                update_properties["Description"] = {
                    "rich_text": [{"text": {"content": description}}]
                }

            if stage:
                update_properties["Stage"] = {"select": {"name": stage.value}}

            if metadata:
                metadata_dict = metadata.model_dump()
                for key, value in metadata_dict.items():
                    if value and key not in [
                        "zenml_version",
                        "zenml_run_name",
                        "zenml_pipeline_name",
                        "zenml_pipeline_uuid",
                        "zenml_pipeline_run_uuid",
                        "zenml_step_name",
                        "zenml_project",
                    ]:
                        prop_key = key.replace("_", " ").title()
                        update_properties[prop_key] = {
                            "rich_text": [{"text": {"content": str(value)}}]
                        }

            if update_properties:
                self.notion_client.pages.update(
                    page_id=page_id,
                    properties=update_properties,
                )

            # Log the update to ZenML's metadata system
            update_metadata = {
                "notion_registry_update": {
                    "model_name": name,
                    "version": version,
                    "notion_page_id": page_id,
                    "updated_fields": list(update_properties.keys()),
                }
            }

            if stage:
                update_metadata["notion_registry_update"]["new_stage"] = (
                    stage.value
                )

            try:
                log_metadata(metadata=update_metadata)
                logger.debug(
                    f"Model version update logged to ZenML for {name}:{version}"
                )
            except Exception as e:
                logger.warning(f"Failed to log update metadata to ZenML: {e}")

            return self.get_model_version(name, version)

        except APIResponseError as e:
            raise RuntimeError(
                f"Failed to update model version '{name}:{version}' "
                f"in the Notion model registry: {str(e)}"
            )

    def get_model_version(
        self,
        name: str,
        version: str,
    ) -> RegistryModelVersion:
        """Get a model version from the Notion model registry.

        Args:
            name: The name of the model.
            version: The version of the model.

        Returns:
            The model version.

        Raises:
            KeyError: If the model version does not exist.
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
                                    "equals": name,
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

            if not response.get("results"):
                raise KeyError(
                    f"Failed to get model version '{name}:{version}' from the "
                    f"Notion model registry: Model version does not exist."
                )

            page = response["results"][0]
            return self._parse_notion_page_to_version(page)

        except APIResponseError as e:
            raise KeyError(
                f"Failed to get model version '{name}:{version}' from the "
                f"Notion model registry: {str(e)}"
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
        """List model versions from the Notion model registry.

        Args:
            name: The name of the model.
            model_source_uri: The model source URI.
            metadata: The metadata of the model version.
            stage: The stage of the model version.
            count: The maximum number of model versions to return.
            created_after: The minimum creation time of the model versions.
            created_before: The maximum creation time of the model versions.
            order_by_date: The order of the model versions by creation time.
            kwargs: Additional keyword arguments.

        Returns:
            The model versions.
        """
        try:
            data_source_id = self._get_data_source_id()
            filter_conditions: List[Dict[str, Any]] = []

            if name:
                filter_conditions.append(
                    {
                        "property": "Model Name",
                        "title": {
                            "equals": name,
                        },
                    }
                )

            if model_source_uri:
                filter_conditions.append(
                    {
                        "property": "Model Source URI",
                        "url": {
                            "equals": model_source_uri,
                        },
                    }
                )

            if stage:
                filter_conditions.append(
                    {
                        "property": "Stage",
                        "select": {
                            "equals": stage.value,
                        },
                    }
                )

            body: Dict[str, Any] = {}

            if filter_conditions:
                if len(filter_conditions) == 1:
                    body["filter"] = filter_conditions[0]
                else:
                    body["filter"] = {"and": filter_conditions}

            if order_by_date:
                sort_direction = (
                    "ascending" if order_by_date == "asc" else "descending"
                )
                body["sorts"] = [
                    {
                        "property": "Created At",
                        "direction": sort_direction,
                    }
                ]

            if count:
                body["page_size"] = min(count, 100)

            response = self.notion_client.request(
                method="post",
                path=f"data_sources/{data_source_id}/query",
                body=body,
            )

            model_versions = []
            for page in response.get("results", []):
                try:
                    version = self._parse_notion_page_to_version(page)

                    if created_after and version.created_at:
                        if version.created_at < created_after:
                            continue

                    if created_before and version.created_at:
                        if version.created_at > created_before:
                            continue

                    model_versions.append(version)

                    if count and len(model_versions) >= count:
                        break

                except Exception as e:
                    logger.warning(f"Error parsing Notion page: {e}")
                    continue

            return model_versions

        except APIResponseError as e:
            logger.error(
                f"Failed to list model versions from Notion: {str(e)}"
            )
            return []

    def load_model_version(
        self,
        name: str,
        version: str,
        **kwargs: Any,
    ) -> Any:
        """Load a model version from the Notion model registry.

        Note: Notion model registry is for metadata tracking only. Models
        are not stored in Notion, only their metadata.

        Args:
            name: The name of the model.
            version: The version of the model.
            kwargs: Additional keyword arguments.

        Raises:
            NotImplementedError: Always, as Notion is metadata-only.
        """
        raise NotImplementedError(
            "The Notion model registry is for metadata tracking only. "
            "Models are not stored in Notion. Please use the model_source_uri "
            "from the model version to load the actual model from the "
            "artifact store."
        )

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

    # ---------
    # Helper Methods
    # ---------

    def _convert_to_notion_properties(
        self,
        name: str,
        version: str,
        model_source_uri: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Convert ZenML metadata to Notion property format.

        Args:
            name: Model name.
            version: Model version.
            model_source_uri: Model source URI.
            description: Model description.
            metadata: Additional metadata.

        Returns:
            Notion properties dictionary.
        """
        properties: Dict[str, Any] = {
            "Model Name": {"title": [{"text": {"content": name}}]},
            "Version": {"rich_text": [{"text": {"content": version}}]},
            "Model Source URI": {"url": model_source_uri},
            "Created At": {"date": {"start": datetime.now().isoformat()}},
            "Stage": {"select": {"name": "None"}},
        }

        if description:
            properties["Description"] = {
                "rich_text": [{"text": {"content": description}}]
            }

        if metadata:
            if metadata.get("zenml_pipeline_name"):
                properties["ZenML Pipeline Name"] = {
                    "rich_text": [
                        {"text": {"content": metadata["zenml_pipeline_name"]}}
                    ]
                }
            if metadata.get("zenml_run_name"):
                properties["ZenML Run Name"] = {
                    "rich_text": [
                        {"text": {"content": metadata["zenml_run_name"]}}
                    ]
                }
            if metadata.get("zenml_pipeline_run_uuid"):
                properties["ZenML Run UUID"] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": metadata["zenml_pipeline_run_uuid"]
                            }
                        }
                    ]
                }
            if metadata.get("zenml_step_name"):
                properties["ZenML Step Name"] = {
                    "rich_text": [
                        {"text": {"content": metadata["zenml_step_name"]}}
                    ]
                }
            if metadata.get("zenml_version"):
                properties["ZenML Version"] = {
                    "rich_text": [
                        {"text": {"content": metadata["zenml_version"]}}
                    ]
                }

        return properties

    def _parse_notion_page_to_version(
        self, page: Dict[str, Any]
    ) -> RegistryModelVersion:
        """Parse Notion page back to RegistryModelVersion.

        Args:
            page: Notion page data.

        Returns:
            RegistryModelVersion object.
        """
        properties = page.get("properties", {})

        model_name_prop = properties.get("Model Name", {})
        model_name = ""
        if model_name_prop.get("title"):
            model_name = model_name_prop["title"][0]["text"]["content"]

        version_prop = properties.get("Version", {})
        version = ""
        if version_prop.get("rich_text"):
            version = version_prop["rich_text"][0]["text"]["content"]

        uri_prop = properties.get("Model Source URI", {})
        model_source_uri = uri_prop.get("url", "")

        description_prop = properties.get("Description", {})
        description = None
        if description_prop.get("rich_text"):
            description = description_prop["rich_text"][0]["text"]["content"]

        stage_prop = properties.get("Stage", {})
        stage = ModelVersionStage.NONE
        if stage_prop.get("select"):
            stage_name = stage_prop["select"]["name"]
            try:
                stage = ModelVersionStage(stage_name)
            except ValueError:
                stage = ModelVersionStage.NONE

        created_at_prop = properties.get("Created At", {})
        created_at = datetime.now()
        if created_at_prop.get("date") and created_at_prop["date"].get(
            "start"
        ):
            try:
                created_at = datetime.fromisoformat(
                    created_at_prop["date"]["start"].replace("Z", "+00:00")
                )
            except Exception:
                pass

        metadata_dict: Dict[str, Any] = {}

        pipeline_name_prop = properties.get("ZenML Pipeline Name", {})
        if pipeline_name_prop.get("rich_text"):
            metadata_dict["zenml_pipeline_name"] = pipeline_name_prop[
                "rich_text"
            ][0]["text"]["content"]

        run_name_prop = properties.get("ZenML Run Name", {})
        if run_name_prop.get("rich_text"):
            metadata_dict["zenml_run_name"] = run_name_prop["rich_text"][0][
                "text"
            ]["content"]

        run_uuid_prop = properties.get("ZenML Run UUID", {})
        if run_uuid_prop.get("rich_text"):
            metadata_dict["zenml_pipeline_run_uuid"] = run_uuid_prop[
                "rich_text"
            ][0]["text"]["content"]

        step_name_prop = properties.get("ZenML Step Name", {})
        if step_name_prop.get("rich_text"):
            metadata_dict["zenml_step_name"] = step_name_prop["rich_text"][0][
                "text"
            ]["content"]

        version_prop_meta = properties.get("ZenML Version", {})
        if version_prop_meta.get("rich_text"):
            metadata_dict["zenml_version"] = version_prop_meta["rich_text"][0][
                "text"
            ]["content"]

        metadata = (
            ModelRegistryModelMetadata(**metadata_dict)
            if metadata_dict
            else None
        )

        return RegistryModelVersion(
            registered_model=RegisteredModel(name=model_name),
            model_format="notion_tracked",
            model_library=None,
            version=version,
            created_at=created_at,
            stage=stage,
            description=description,
            last_updated_at=created_at,
            metadata=metadata,
            model_source_uri=model_source_uri,
        )
