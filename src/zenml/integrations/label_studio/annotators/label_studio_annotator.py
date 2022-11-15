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

import os
import subprocess
import sys
import webbrowser
from typing import Any, Dict, List, Optional, Tuple, cast

from label_studio_sdk import Client, Project  # type: ignore[import]

from zenml.annotators.base_annotator import BaseAnnotator
from zenml.enums import StackComponentType
from zenml.exceptions import ProvisioningError
from zenml.integrations.azure import AZURE_ARTIFACT_STORE_FLAVOR
from zenml.integrations.gcp import GCP_ARTIFACT_STORE_FLAVOR
from zenml.integrations.label_studio.flavors.label_studio_annotator_flavor import (
    DEFAULT_LOCAL_INSTANCE_URL,
    LabelStudioAnnotatorConfig,
)
from zenml.integrations.label_studio.steps.label_studio_standard_steps import (
    LabelStudioDatasetRegistrationParameters,
    LabelStudioDatasetSyncParameters,
)
from zenml.integrations.s3 import S3_ARTIFACT_STORE_FLAVOR
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.secret.arbitrary_secret_schema import ArbitrarySecretSchema
from zenml.stack import Stack, StackValidator
from zenml.stack.authentication_mixin import AuthenticationMixin
from zenml.utils import io_utils, networking_utils

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
    def validator(self) -> Optional["StackValidator"]:
        """Validates that the stack contains a cloud artifact store.

        Returns:
            StackValidator: Validator for the stack.
        """

        def _ensure_cloud_artifact_stores(stack: Stack) -> Tuple[bool, str]:
            # For now this only works on cloud artifact stores.
            return (
                stack.artifact_store.flavor
                in [
                    AZURE_ARTIFACT_STORE_FLAVOR,
                    GCP_ARTIFACT_STORE_FLAVOR,
                    S3_ARTIFACT_STORE_FLAVOR,
                ],
                "Only cloud artifact stores are currently supported",
            )

        return StackValidator(
            required_components={StackComponentType.SECRETS_MANAGER},
            custom_validation_function=_ensure_cloud_artifact_stores,
        )

    def get_url(self) -> str:
        """Gets the top-level URL of the annotation interface.

        Returns:
            The URL of the annotation interface.
        """
        return f"{self.config.instance_url}:{self.config.port}"

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

    def launch(self, url: Optional[str]) -> None:
        """Launches the annotation interface.

        Args:
            url: The URL of the annotation interface.
        """
        if not url:
            url = self.get_url()
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
        secret = self.get_authentication_secret(ArbitrarySecretSchema)
        if not secret:
            raise ValueError(
                f"Unable to access predefined secret '{secret}' to access Label Studio API key."
            )
        api_key = secret.content["api_key"]
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
            NotImplementedError: If the deletion of a dataset is not supported.
        """
        raise NotImplementedError("Awaiting Label Studio release.")
        # TODO: Awaiting a new Label Studio version to be released with this method
        # ls = self._get_client()
        # dataset_name = kwargs.get("dataset_name")
        # if not dataset_name:
        #     raise ValueError("`dataset_name` keyword argument is required.")

        # dataset_id = self.get_id_from_name(dataset_name)
        # if not dataset_id:
        #     raise ValueError(
        #         f"Dataset name '{dataset_name}' has no corresponding `dataset_id` in Label Studio."
        #     )
        # ls.delete_project(dataset_id)

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
        params: LabelStudioDatasetRegistrationParameters,
    ) -> Any:
        """Registers a dataset for annotation.

        Args:
            params: Parameters for the dataset.

        Returns:
            A Label Studio Project object.
        """
        project_id = self.get_id_from_name(params.dataset_name)
        if project_id:
            dataset = self._get_client().get_project(project_id)
        else:
            dataset = self.add_dataset(
                dataset_name=params.dataset_name,
                label_config=params.label_config,
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
            storage_sources = self._get_azure_import_storage_sources(dataset_id)
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
            if not params.aws_access_key_id or not params.aws_secret_access_key:
                logger.warning(
                    "Authentication credentials for S3 aren't fully provided."
                    "Please update the storage synchronization settings in the "
                    " Label Studio web UI as per your needs."
                )
            storage = dataset.connect_s3_import_storage(
                bucket=uri,
                aws_access_key_id=params.aws_access_key_id,
                aws_secret_access_key=params.aws_secret_access_key,
                aws_session_token=params.aws_session_token,
                region_name=params.s3_region_name,
                s3_endpoint=params.s3_endpoint,
                **storage_connection_args,
            )
        else:
            raise ValueError(
                f"Invalid storage type. '{params.storage_type}' is not supported by ZenML's Label Studio integration. Please choose between 'azure', 'gcs' and 'aws'."
            )

        synced_storage = self._get_client().sync_storage(
            storage_id=storage["id"], storage_type=storage["type"]
        )
        return cast(Dict[str, Any], synced_storage)

    @property
    def root_directory(self) -> str:
        """Returns path to the root directory.

        Returns:
            Path to the root directory.
        """
        return os.path.join(
            io_utils.get_global_config_directory(),
            "annotators",
            str(self.id),
        )

    @property
    def _pid_file_path(self) -> str:
        """Returns path to the daemon PID file.

        Returns:
            Path to the daemon PID file.
        """
        return os.path.join(self.root_directory, "label_studio_daemon.pid")

    @property
    def _log_file(self) -> str:
        """Path of the daemon log file.

        Returns:
            Path to the daemon log file.
        """
        return os.path.join(self.root_directory, "label_studio_daemon.log")

    @property
    def is_provisioned(self) -> bool:
        """If the component provisioned resources to run locally.

        Returns:
            True if the component provisioned resources to run locally.
        """
        return fileio.exists(self.root_directory)

    @property
    def is_running(self) -> bool:
        """If the component is running locally.

        Returns:
            True if the component is running locally, False otherwise.
        """
        if not self.is_local_instance:
            return True

        if sys.platform != "win32":
            from zenml.utils.daemon import check_if_daemon_is_running

            if not check_if_daemon_is_running(self._pid_file_path):
                return False
        else:
            # Daemon functionality is not supported on Windows, so the PID
            # file won't exist. This if clause exists just for mypy to not
            # complain about missing functions
            pass

        return True

    @property
    def is_local_instance(self) -> bool:
        """Determines if the Label Studio instance is running locally.

        Returns:
            True if the component is running locally, False otherwise.
        """
        return self.config.instance_url == DEFAULT_LOCAL_INSTANCE_URL

    def provision(self) -> None:
        """Spins up the annotation server backend."""
        fileio.makedirs(self.root_directory)

    def deprovision(self) -> None:
        """Spins down the annotation server backend."""
        if fileio.exists(self._log_file):
            fileio.remove(self._log_file)

    def resume(self) -> None:
        """Resumes the annotation interface."""
        if self.is_running:
            logger.info("Local annotation deployment already running.")
            return

        if self.is_local_instance:
            self.start_annotator_daemon()

    def suspend(self) -> None:
        """Suspends the annotation interface."""
        if not self.is_running:
            logger.info("Local annotation server is not running.")
            return

        if self.is_local_instance:
            self.stop_annotator_daemon()

    def start_annotator_daemon(self) -> None:
        """Starts the annotation server backend.

        Raises:
            ProvisioningError: If the annotation server backend is already
                running or the port is already occupied.
        """
        command = [
            "label-studio",
            "start",
            "--no-browser",
            "--port",
            f"{self.config.port}",
        ]

        if sys.platform == "win32":
            logger.warning(
                "Daemon functionality not supported on Windows. "
                "In order to access the Label Studio server locally, "
                "please run '%s' in a separate command line shell.",
                self.config.port,
                " ".join(command),
            )
        elif not networking_utils.port_available(self.config.port):
            raise ProvisioningError(
                f"Unable to port-forward Label Studio to local "
                f"port {self.config.port} because the port is occupied. In order to "
                f"access Label Studio locally, please "
                f"change the configuration to use an available "
                f"port or stop the other process currently using the port."
            )
        else:
            from zenml.utils import daemon

            def _daemon_function() -> None:
                """Forwards the port of the Kubeflow Pipelines Metadata pod ."""
                subprocess.check_call(command)

            daemon.run_as_daemon(
                _daemon_function,
                pid_file=self._pid_file_path,
                log_file=self._log_file,
            )
            logger.info(
                "Started Label Studio daemon (check the daemon"
                "logs at `%s` in case you're not able to access the annotation "
                f"interface). Please visit `{self.get_url()}/` to use the Label Studio interface.",
                self._log_file,
            )

    def stop_annotator_daemon(self) -> None:
        """Stops the annotation server backend."""
        if fileio.exists(self._pid_file_path):
            if sys.platform == "win32":
                # Daemon functionality is not supported on Windows, so the PID
                # file won't exist. This if clause exists just for mypy to not
                # complain about missing functions
                pass
            else:
                from zenml.utils import daemon

                daemon.stop_daemon(self._pid_file_path)
                fileio.remove(self._pid_file_path)
