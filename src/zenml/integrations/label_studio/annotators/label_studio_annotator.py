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
"""Implementation of the Label Studio annotation integration."""

import json
import os
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type, cast

from label_studio_sdk import Client, Project

from zenml import get_step_context
from zenml.annotators.base_annotator import BaseAnnotator
from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
from zenml.config.global_config import GlobalConfiguration
from zenml.integrations.label_studio.flavors import (
    LabelStudioAnnotatorSettings,
)
from zenml.integrations.label_studio.flavors.label_studio_annotator_flavor import (
    LabelStudioAnnotatorConfig,
)
from zenml.integrations.label_studio.steps.label_studio_standard_steps import (
    LabelStudioDatasetSyncParameters,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.stack.authentication_mixin import AuthenticationMixin

logger = get_logger(__name__)


class LabelStudioAnnotator(BaseAnnotator, AuthenticationMixin):
    """Class to interact with the Label Studio annotation interface."""

    @property
    def config(self) -> LabelStudioAnnotatorConfig:
        """Returns the `LabelStudioAnnotatorConfig` config.

        Returns:
            The configuration.
        """
        return cast(LabelStudioAnnotatorConfig, self._config)

    @property
    def settings_class(self) -> Type[LabelStudioAnnotatorSettings]:
        """Settings class for the Label Studio annotator.

        Returns:
            The settings class.
        """
        return LabelStudioAnnotatorSettings

    def get_url(self) -> str:
        """Gets the top-level URL of the annotation interface.

        Returns:
            The URL of the annotation interface.
        """
        return (
            f"{self.config.instance_url}:{self.config.port}"
            if self.config.port
            else self.config.instance_url
        )

    def get_url_for_dataset(self, dataset_name: str) -> str:
        """Gets the URL of the annotation interface for the given dataset.

        Args:
            dataset_name: The name of the dataset.

        Returns:
            The URL of the annotation interface.
        """
        project_id = self.get_id_from_name(dataset_name)
        return f"{self.get_url()}/projects/{project_id}/"

    def get_id_from_name(self, dataset_name: str) -> Optional[int]:
        """Gets the ID of the given dataset.

        Args:
            dataset_name: The name of the dataset.

        Returns:
            The ID of the dataset.
        """
        projects = self.get_datasets()
        for project in projects:
            if project.get_params()["title"] == dataset_name:
                return cast(int, project.get_params()["id"])
        return None

    def get_datasets(self) -> List[Any]:
        """Gets the datasets currently available for annotation.

        Returns:
            A list of datasets.
        """
        datasets = self._get_client().get_projects()
        return cast(List[Any], datasets)

    def get_dataset_names(self) -> List[str]:
        """Gets the names of the datasets.

        Returns:
            A list of dataset names.
        """
        return [
            dataset.get_params()["title"] for dataset in self.get_datasets()
        ]

    def get_dataset_stats(self, dataset_name: str) -> Tuple[int, int]:
        """Gets the statistics of the given dataset.

        Args:
            dataset_name: The name of the dataset.

        Returns:
            A tuple containing (labeled_task_count, unlabeled_task_count) for
                the dataset.

        Raises:
            IndexError: If the dataset does not exist.
        """
        for project in self.get_datasets():
            if dataset_name in project.get_params()["title"]:
                labeled_task_count = len(project.get_labeled_tasks())
                unlabeled_task_count = len(project.get_unlabeled_tasks())
                return (labeled_task_count, unlabeled_task_count)
        raise IndexError(
            f"Dataset {dataset_name} not found. Please use "
            f"`zenml annotator dataset list` to list all available datasets."
        )

    def launch(self, **kwargs: Any) -> None:
        """Launches the annotation interface.

        Args:
            **kwargs: Additional keyword arguments to pass to the
                annotation client.
        """
        url = kwargs.get("url") or self.get_url()
        if self._connection_available():
            webbrowser.open(url, new=1, autoraise=True)
        else:
            logger.warning(
                "Could not launch annotation interface"
                "because the connection could not be established."
            )

    def _get_client(self) -> Client:
        """Gets Label Studio client.

        Returns:
            Label Studio client.

        Raises:
            ValueError: when unable to access the Label Studio API key.
        """
        try:
            settings = cast(
                LabelStudioAnnotatorSettings,
                self.get_settings(get_step_context().step_run),
            )
            if settings.api_key is None:
                raise RuntimeError
            else:
                api_key = settings.api_key
        except RuntimeError:
            # Try to get from secret
            secret = self.get_authentication_secret()
            if not secret:
                raise ValueError(
                    "Unable to access predefined secret to access Label Studio API key."
                )
            api_key = secret.secret_values.get("api_key", "")
        if not api_key:
            raise ValueError(
                "Unable to access Label Studio API key from secret."
            )
        return Client(url=self.get_url(), api_key=api_key)

    def _connection_available(self) -> bool:
        """Checks if the connection to the annotation server is available.

        Returns:
            True if the connection is available, False otherwise.
        """
        try:
            result = self._get_client().check_connection()
            return result.get("status") == "UP"  # type: ignore[no-any-return]
        # TODO: [HIGH] refactor to use a more specific exception
        except Exception:
            logger.error(
                "Connection error: No connection was able to be established to the Label Studio backend."
            )
            return False

    def add_dataset(self, **kwargs: Any) -> Any:
        """Registers a dataset for annotation.

        Args:
            **kwargs: Additional keyword arguments to pass to the Label Studio client.

        Returns:
            A Label Studio Project object.

        Raises:
            ValueError: if 'dataset_name' and 'label_config' aren't provided.
        """
        dataset_name = kwargs.get("dataset_name")
        label_config = kwargs.get("label_config")
        if not dataset_name:
            raise ValueError("`dataset_name` keyword argument is required.")
        elif not label_config:
            raise ValueError("`label_config` keyword argument is required.")

        return self._get_client().start_project(
            title=dataset_name,
            label_config=label_config,
        )

    def delete_dataset(self, **kwargs: Any) -> None:
        """Deletes a dataset from the annotation interface.

        Args:
            **kwargs: Additional keyword arguments to pass to the Label Studio
                client.

        Raises:
            ValueError: If the dataset name is not provided or if the dataset
                does not exist.
        """
        ls = self._get_client()
        dataset_name = kwargs.get("dataset_name")
        if not dataset_name:
            raise ValueError("`dataset_name` keyword argument is required.")

        dataset_id = self.get_id_from_name(dataset_name)
        if not dataset_id:
            raise ValueError(
                f"Dataset name '{dataset_name}' has no corresponding `dataset_id` in Label Studio."
            )
        ls.delete_project(dataset_id)

    def get_dataset(self, **kwargs: Any) -> Any:
        """Gets the dataset with the given name.

        Args:
            **kwargs: Additional keyword arguments to pass to the Label Studio client.

        Returns:
            The LabelStudio Dataset object (a 'Project') for the given name.

        Raises:
            ValueError: If the dataset name is not provided or if the dataset
                does not exist.
        """
        # TODO: check for and raise error if client unavailable
        dataset_name = kwargs.get("dataset_name")
        if not dataset_name:
            raise ValueError("`dataset_name` keyword argument is required.")

        dataset_id = self.get_id_from_name(dataset_name)
        if not dataset_id:
            raise ValueError(
                f"Dataset name '{dataset_name}' has no corresponding `dataset_id` in Label Studio."
            )
        return self._get_client().get_project(dataset_id)

    def get_converted_dataset(
        self, dataset_name: str, output_format: str
    ) -> Dict[Any, Any]:
        """Extract annotated tasks in a specific converted format.

        Args:
            dataset_name: Id of the dataset.
            output_format: Output format.

        Returns:
            A dictionary containing the converted dataset.
        """
        project = self.get_dataset(dataset_name=dataset_name)
        return project.export_tasks(export_type=output_format)  # type: ignore[no-any-return]

    def get_labeled_data(self, **kwargs: Any) -> Any:
        """Gets the labeled data for the given dataset.

        Args:
            **kwargs: Additional keyword arguments to pass to the Label Studio client.

        Returns:
            The labeled data.

        Raises:
            ValueError: If the dataset name is not provided or if the dataset
                does not exist.
        """
        dataset_name = kwargs.get("dataset_name")
        if not dataset_name:
            raise ValueError("`dataset_name` keyword argument is required.")

        dataset_id = self.get_id_from_name(dataset_name)
        if not dataset_id:
            raise ValueError(
                f"Dataset name '{dataset_name}' has no corresponding `dataset_id` in Label Studio."
            )
        return self._get_client().get_project(dataset_id).get_labeled_tasks()

    def get_unlabeled_data(self, **kwargs: str) -> Any:
        """Gets the unlabeled data for the given dataset.

        Args:
            **kwargs: Additional keyword arguments to pass to the Label Studio client.

        Returns:
            The unlabeled data.

        Raises:
            ValueError: If the dataset name is not provided.
        """
        dataset_name = kwargs.get("dataset_name")
        if not dataset_name:
            raise ValueError("`dataset_name` keyword argument is required.")

        dataset_id = self.get_id_from_name(dataset_name)
        if not dataset_id:
            raise ValueError(
                f"Dataset name '{dataset_name}' has no corresponding `dataset_id` in Label Studio."
            )
        return self._get_client().get_project(dataset_id).get_unlabeled_tasks()

    def register_dataset_for_annotation(
        self,
        label_config: str,
        dataset_name: str,
    ) -> Any:
        """Registers a dataset for annotation.

        Args:
            label_config: The label config to use for the annotation interface.
            dataset_name: Name of the dataset to register.

        Returns:
            A Label Studio Project object.
        """
        project_id = self.get_id_from_name(dataset_name)
        if project_id:
            dataset = self._get_client().get_project(project_id)
        else:
            dataset = self.add_dataset(
                dataset_name=dataset_name,
                label_config=label_config,
            )

        return dataset

    def _get_azure_import_storage_sources(
        self, dataset_id: int
    ) -> List[Dict[str, Any]]:
        """Gets a list of all Azure import storage sources.

        Args:
            dataset_id: Id of the dataset.

        Returns:
            A list of Azure import storage sources.

        Raises:
            ConnectionError: If the connection to the Label Studio backend is unavailable.
        """
        # TODO: check if client actually is connected etc
        query_url = f"/api/storages/azure?project={dataset_id}"
        response = self._get_client().make_request(method="GET", url=query_url)
        if response.status_code == 200:
            return cast(List[Dict[str, Any]], response.json())
        else:
            raise ConnectionError(
                f"Unable to get list of import storage sources. Client raised HTTP error {response.status_code}."
            )

    def _get_gcs_import_storage_sources(
        self, dataset_id: int
    ) -> List[Dict[str, Any]]:
        """Gets a list of all Google Cloud Storage import storage sources.

        Args:
            dataset_id: Id of the dataset.

        Returns:
            A list of Google Cloud Storage import storage sources.

        Raises:
            ConnectionError: If the connection to the Label Studio backend is unavailable.
        """
        # TODO: check if client actually is connected etc
        query_url = f"/api/storages/gcs?project={dataset_id}"
        response = self._get_client().make_request(method="GET", url=query_url)
        if response.status_code == 200:
            return cast(List[Dict[str, Any]], response.json())
        else:
            raise ConnectionError(
                f"Unable to get list of import storage sources. Client raised HTTP error {response.status_code}."
            )

    def _get_s3_import_storage_sources(
        self, dataset_id: int
    ) -> List[Dict[str, Any]]:
        """Gets a list of all AWS S3 import storage sources.

        Args:
            dataset_id: Id of the dataset.

        Returns:
            A list of AWS S3 import storage sources.

        Raises:
            ConnectionError: If the connection to the Label Studio backend is unavailable.
        """
        # TODO: check if client actually is connected etc
        query_url = f"/api/storages/s3?project={dataset_id}"
        response = self._get_client().make_request(method="GET", url=query_url)
        if response.status_code == 200:
            return cast(List[Dict[str, Any]], response.json())
        else:
            raise ConnectionError(
                f"Unable to get list of import storage sources. Client raised HTTP error {response.status_code}."
            )

    def _storage_source_already_exists(
        self,
        uri: str,
        params: LabelStudioDatasetSyncParameters,
        dataset: Project,
    ) -> bool:
        """Returns whether a storage source already exists.

        Args:
            uri: URI of the storage source.
            params: Parameters for the dataset.
            dataset: Label Studio dataset.

        Returns:
            True if the storage source already exists, False otherwise.

        Raises:
            NotImplementedError: If the storage source type is not supported.
        """
        # TODO: check we are already connected
        dataset_id = int(dataset.get_params()["id"])
        if params.storage_type == "azure":
            storage_sources = self._get_azure_import_storage_sources(
                dataset_id
            )
        elif params.storage_type == "gcs":
            storage_sources = self._get_gcs_import_storage_sources(dataset_id)
        elif params.storage_type == "s3":
            storage_sources = self._get_s3_import_storage_sources(dataset_id)
        else:
            raise NotImplementedError(
                f"Storage type '{params.storage_type}' not implemented."
            )
        return any(
            (
                source.get("presign") == params.presign
                and source.get("bucket") == uri
                and source.get("regex_filter") == params.regex_filter
                and source.get("use_blob_urls") == params.use_blob_urls
                and source.get("title") == dataset.get_params()["title"]
                and source.get("description") == params.description
                and source.get("presign_ttl") == params.presign_ttl
                and source.get("project") == dataset_id
            )
            for source in storage_sources
        )

    def get_parsed_label_config(self, dataset_id: int) -> Dict[str, Any]:
        """Returns the parsed Label Studio label config for a dataset.

        Args:
            dataset_id: Id of the dataset.

        Returns:
            A dictionary containing the parsed label config.

        Raises:
            ValueError: If no dataset is found for the given id.
        """
        # TODO: check if client actually is connected etc
        dataset = self._get_client().get_project(dataset_id)
        if dataset:
            return cast(Dict[str, Any], dataset.parsed_label_config)
        raise ValueError("No dataset found for the given id.")

    def populate_artifact_store_parameters(
        self,
        params: LabelStudioDatasetSyncParameters,
        artifact_store: BaseArtifactStore,
    ) -> None:
        """Populate the dataset sync parameters with the artifact store credentials.

        Args:
            params: The dataset sync parameters.
            artifact_store: The active artifact store.

        Raises:
            RuntimeError: if the artifact store credentials cannot be fetched.
        """
        if artifact_store.flavor == "s3":
            from zenml.integrations.s3.artifact_stores import S3ArtifactStore

            assert isinstance(artifact_store, S3ArtifactStore)

            params.storage_type = "s3"

            (
                aws_access_key_id,
                aws_secret_access_key,
                aws_session_token,
            ) = artifact_store.get_credentials()

            if aws_access_key_id and aws_secret_access_key:
                # Convert the credentials into the format expected by Label
                # Studio
                params.aws_access_key_id = aws_access_key_id
                params.aws_secret_access_key = aws_secret_access_key
                params.aws_session_token = aws_session_token

                if artifact_store.config.client_kwargs:
                    if "endpoint_url" in artifact_store.config.client_kwargs:
                        params.s3_endpoint = (
                            artifact_store.config.client_kwargs["endpoint_url"]
                        )
                    if "region_name" in artifact_store.config.client_kwargs:
                        params.s3_region_name = str(
                            artifact_store.config.client_kwargs["region_name"]
                        )

                return

            raise RuntimeError(
                "No credentials are configured for the active S3 artifact "
                "store. The Label Studio annotator needs explicit credentials "
                "to be configured for your artifact store to sync data "
                "artifacts."
            )

        elif artifact_store.flavor == "gcp":
            from zenml.integrations.gcp.artifact_stores import GCPArtifactStore

            assert isinstance(artifact_store, GCPArtifactStore)

            params.storage_type = "gcs"

            gcp_credentials = artifact_store.get_credentials()

            if gcp_credentials:
                # Save the credentials to a file in secure location, because
                # Label Studio will need to read it from a file
                secret_folder = Path(
                    GlobalConfiguration().config_directory,
                    "label-studio",
                    str(self.id),
                )
                fileio.makedirs(str(secret_folder))
                file_path = Path(
                    secret_folder, "google_application_credentials.json"
                )
                with os.fdopen(
                    os.open(
                        file_path, flags=os.O_RDWR | os.O_CREAT, mode=0o600
                    ),
                    "w",
                ) as f:
                    f.write(json.dumps(gcp_credentials))

                params.google_application_credentials = str(file_path)

                return

            raise RuntimeError(
                "No credentials are configured for the active GCS artifact "
                "store. The Label Studio annotator needs explicit credentials "
                "to be configured for your artifact store to sync data "
                "artifacts."
            )

        elif artifact_store.flavor == "azure":
            from zenml.integrations.azure.artifact_stores import (
                AzureArtifactStore,
            )

            assert isinstance(artifact_store, AzureArtifactStore)

            params.storage_type = "azure"

            azure_credentials = artifact_store.get_credentials()

            if azure_credentials:
                # Convert the credentials into the format expected by Label
                # Studio
                if azure_credentials.connection_string is not None:
                    try:
                        # We need to extract the account name and key from the
                        # connection string
                        tokens = azure_credentials.connection_string.split(";")
                        token_dict = dict(
                            [token.split("=", maxsplit=1) for token in tokens]
                        )
                        params.azure_account_name = token_dict["AccountName"]
                        params.azure_account_key = token_dict["AccountKey"]
                    except (KeyError, ValueError) as e:
                        raise RuntimeError(
                            "The Azure connection string configured for the "
                            "artifact store expected format."
                        ) from e

                    return

                if (
                    azure_credentials.account_name is not None
                    and azure_credentials.account_key is not None
                ):
                    params.azure_account_name = azure_credentials.account_name
                    params.azure_account_key = azure_credentials.account_key

                    return

                raise RuntimeError(
                    "The Label Studio annotator could not use the "
                    "credentials currently configured in the active Azure "
                    "artifact store because it only supports Azure storage "
                    "account credentials. "
                    "Please use Azure storage account credentials for your "
                    "artifact store."
                )

            raise RuntimeError(
                "No credentials are configured for the active Azure artifact "
                "store. The Label Studio annotator needs explicit credentials "
                "to be configured for your artifact store to sync data "
                "artifacts."
            )

        elif artifact_store.flavor == "local":
            from zenml.artifact_stores.local_artifact_store import (
                LocalArtifactStore,
            )

            assert isinstance(artifact_store, LocalArtifactStore)

            params.storage_type = "local"
            if params.prefix is None:
                params.prefix = artifact_store.path
            elif not params.prefix.startswith(artifact_store.path.lstrip("/")):
                raise RuntimeError(
                    "The prefix for the local storage must be a subdirectory "
                    "of the local artifact store path."
                )
            return

        raise RuntimeError(
            f"The active artifact store type '{artifact_store.flavor}' is not "
            "supported by ZenML's Label Studio integration. "
            "Please use one of the supported artifact stores (S3, GCP, "
            "Azure or local)."
        )

    def connect_and_sync_external_storage(
        self,
        uri: str,
        params: LabelStudioDatasetSyncParameters,
        dataset: Project,
    ) -> Optional[Dict[str, Any]]:
        """Syncs the external storage for the given project.

        Args:
            uri: URI of the storage source.
            params: Parameters for the dataset.
            dataset: Label Studio dataset.

        Returns:
            A dictionary containing the sync result.

        Raises:
            ValueError: If the storage type is not supported.
        """
        # TODO: check if proposed storage source has differing / new data
        # if self._storage_source_already_exists(uri, config, dataset):
        #     return None

        storage_connection_args = {
            "prefix": params.prefix,
            "regex_filter": params.regex_filter,
            "use_blob_urls": params.use_blob_urls,
            "presign": params.presign,
            "presign_ttl": params.presign_ttl,
            "title": dataset.get_params()["title"],
            "description": params.description,
        }
        if params.storage_type == "azure":
            if not params.azure_account_name or not params.azure_account_key:
                logger.warning(
                    "Authentication credentials for Azure aren't fully "
                    "provided. Please update the storage synchronization "
                    "settings in the Label Studio web UI as per your needs."
                )
            storage = dataset.connect_azure_import_storage(
                container=uri,
                account_name=params.azure_account_name,
                account_key=params.azure_account_key,
                **storage_connection_args,
            )
        elif params.storage_type == "gcs":
            if not params.google_application_credentials:
                logger.warning(
                    "Authentication credentials for Google Cloud Storage "
                    "aren't fully provided. Please update the storage "
                    "synchronization settings in the Label Studio web UI as "
                    "per your needs."
                )
            storage = dataset.connect_google_import_storage(
                bucket=uri,
                google_application_credentials=params.google_application_credentials,
                **storage_connection_args,
            )
        elif params.storage_type == "s3":
            if (
                not params.aws_access_key_id
                or not params.aws_secret_access_key
            ):
                logger.warning(
                    "Authentication credentials for S3 aren't fully provided."
                    "Please update the storage synchronization settings in the "
                    "Label Studio web UI as per your needs."
                )

            # temporary fix using client method until LS supports
            # recursive_scan in their SDK
            # (https://github.com/heartexlabs/label-studio-sdk/pull/130)
            ls_client = self._get_client()
            payload = {
                "bucket": uri,
                "prefix": params.prefix,
                "regex_filter": params.regex_filter,
                "use_blob_urls": params.use_blob_urls,
                "aws_access_key_id": params.aws_access_key_id,
                "aws_secret_access_key": params.aws_secret_access_key,
                "aws_session_token": params.aws_session_token,
                "region_name": params.s3_region_name,
                "s3_endpoint": params.s3_endpoint,
                "presign": params.presign,
                "presign_ttl": params.presign_ttl,
                "title": dataset.get_params()["title"],
                "description": params.description,
                "project": dataset.id,
                "recursive_scan": True,
            }
            response = ls_client.make_request(
                "POST", "/api/storages/s3", json=payload
            )
            storage = response.json()

        elif params.storage_type == "local":
            if not params.prefix:
                raise ValueError(
                    "The 'prefix' parameter is required for local storage "
                    "synchronization."
                )

            # Drop arguments that are not used by the local storage
            storage_connection_args.pop("presign")
            storage_connection_args.pop("presign_ttl")
            storage_connection_args.pop("prefix")

            prefix = params.prefix
            if not prefix.startswith("/"):
                prefix = f"/{prefix}"
            root_path = Path(prefix).parent

            # Set the environment variables required by Label Studio
            # to allow local file serving (see https://labelstud.io/guide/storage.html#Prerequisites-2)
            os.environ["LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED"] = "true"
            os.environ["LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT"] = str(
                root_path
            )

            storage = dataset.connect_local_import_storage(
                local_store_path=prefix,
                **storage_connection_args,
            )

            del os.environ["LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED"]
            del os.environ["LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT"]
        else:
            raise ValueError(
                f"Invalid storage type. '{params.storage_type}' is not "
                "supported by ZenML's Label Studio integration. Please choose "
                "between 'azure', 'gcs', 'aws' or 'local'."
            )

        synced_storage = self._get_client().sync_storage(
            storage_id=storage["id"], storage_type=storage["type"]
        )
        return cast(Dict[str, Any], synced_storage)
