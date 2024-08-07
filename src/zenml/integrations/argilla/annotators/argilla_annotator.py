#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Implementation of the Argilla annotation integration."""

import json
import webbrowser
from typing import Any, Dict, List, Optional, Tuple, Type, Union, cast

import argilla as rg
from argilla._exceptions._api import ArgillaAPIError
from argilla.client import Argilla as ArgillaClient

from zenml.annotators.base_annotator import BaseAnnotator
from zenml.integrations.argilla.flavors import (
    ArgillaAnnotatorSettings,
)
from zenml.integrations.argilla.flavors.argilla_annotator_flavor import (
    ArgillaAnnotatorConfig,
)
from zenml.logger import get_logger
from zenml.stack.authentication_mixin import AuthenticationMixin

logger = get_logger(__name__)


class ArgillaAnnotator(BaseAnnotator, AuthenticationMixin):
    """Class to interact with the Argilla annotation interface."""

    @property
    def config(self) -> ArgillaAnnotatorConfig:
        """Returns the `ArgillaAnnotatorConfig` config.

        Returns:
            The configuration.
        """
        return cast(ArgillaAnnotatorConfig, self._config)

    @property
    def settings_class(self) -> Type[ArgillaAnnotatorSettings]:
        """Settings class for the Argilla annotator.

        Returns:
            The settings class.
        """
        return ArgillaAnnotatorSettings

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

    def _get_client(self) -> ArgillaClient:
        """Gets the Argilla client.

        Returns:
            Argilla client.
        """
        config = self.config
        init_kwargs = {"api_url": self.get_url()}

        # Set the API key from the secret or using settings
        authentication_secret = self.get_authentication_secret()
        if config.api_key and authentication_secret:
            api_key = config.api_key
            logger.debug(
                "Both API key and authentication secret are provided. Using API key from settings as priority."
            )
        elif authentication_secret:
            api_key = authentication_secret.secret_values.get("api_key", "")
            logger.debug("Using API key from secret.")
        elif config.api_key is not None:
            api_key = config.api_key
            logger.debug("Using API key from settings.")

        if api_key:
            init_kwargs["api_key"] = api_key

        if config.headers is not None:
            init_kwargs["headers"] = json.loads(config.headers)
        if config.httpx_extra_kwargs is not None:
            init_kwargs["httpx_extra_kwargs"] = json.loads(
                config.httpx_extra_kwargs
            )

        try:
            _ = rg.Argilla(**init_kwargs).me
        except ArgillaAPIError as e:
            print(f"Failed to verify the Argilla instance: {str(e)}")
        return rg.Argilla(**init_kwargs)

    def get_url_for_dataset(self, dataset_name: str, **kwargs) -> str:
        """Gets the URL of the annotation interface for the given dataset.

        Args:
            dataset_name: The name of the dataset.
            **kwargs: Additional keyword arguments to pass to the Argilla client.
                -workspace: The name of the workspace. By default, the first available.

        Returns:
            The URL of of the dataset annotation interface.
        """
        workspace = kwargs.get("workspace")

        dataset_id = self.get_dataset(
            dataset_name=dataset_name, workspace=workspace
        ).id
        return f"{self.get_url()}/dataset/{dataset_id}/annotation-mode"

    def get_datasets(self, **kwargs) -> List[Any]:
        """Gets the datasets currently available for annotation.

        Args:
            **kwargs: Additional keyword arguments to pass to the Argilla client.
                -workspace: The name of the workspace. By default, the first available.
                    If set, only the datasets in the workspace will be returned.

        Returns:
            A list of datasets.
        """
        workspace = kwargs.get("workspace")

        if workspace is None:
            datasets = list(self._get_client().datasets)
        else:
            datasets = list(self._get_client().workspaces(workspace).datasets)

        return datasets

    def get_dataset_names(self, **kwargs) -> List[str]:
        """Gets the names of the datasets.

        Args:
            **kwargs: Additional keyword arguments to pass to the Argilla client.
                -workspace: The name of the workspace. By default, the first available.
                    If set, only the dataset names in the workspace will be returned.

        Returns:
            A list of dataset names.
        """
        workspace = kwargs.get("workspace")

        if workspace is None:
            dataset_names = [dataset.name for dataset in self.get_datasets()]
        else:
            dataset_names = [
                dataset.name
                for dataset in self.get_datasets(workspace=workspace)
            ]

        return dataset_names

    def _get_data_by_status(
        self, dataset_name: str, status: str, workspace: Optional[str]
    ) -> Any:
        """Gets the dataset containing the data with the specified status.

        Args:
            dataset_name: The name of the dataset.
            status: The response status to filter by ('completed' for labeled,
                'pending' for unlabeled).
            workspace: The name of the workspace. By default, the first available.

        Returns:
            The list of records with the specified status.
        """
        dataset = self.get_dataset(
            dataset_name=dataset_name, workspace=workspace
        )

        query = rg.Query(filter=rg.Filter([("status", "==", status)]))

        return dataset.records(
            query=query,
            with_suggestions=True,
            with_vectors=True,
            with_responses=True,
        ).to_list()

    def get_dataset_stats(
        self, dataset_name: str, **kwargs
    ) -> Tuple[int, int]:
        """Gets the statistics of the given dataset.

        Args:
            dataset_name: The name of the dataset.
            **kwargs: Additional keyword arguments to pass to the Argilla client.
                -workspace: The name of the workspace. By default, the first available.

        Returns:
            A tuple containing (labeled_task_count, unlabeled_task_count) for
                the dataset.
        """
        workspace = kwargs.get("workspace")

        labeled_task_count = len(
            self._get_data_by_status(
                dataset_name=dataset_name,
                status="completed",
                workspace=workspace,
            )
        )
        unlabeled_task_count = len(
            self._get_data_by_status(
                dataset_name=dataset_name,
                status="pending",
                workspace=workspace,
            )
        )

        return (labeled_task_count, unlabeled_task_count)

    def launch(self, **kwargs: Any) -> None:
        """Launches the annotation interface.

        Args:
            **kwargs: Additional keyword arguments to pass to the Argilla client.
        """
        url = kwargs.get("api_url") or self.get_url()

        if self._get_client():
            webbrowser.open(url, new=1, autoraise=True)
        else:
            logger.warning(
                "Could not launch annotation interface"
                "because the connection could not be established."
            )

    def add_dataset(self, **kwargs: Any) -> Any:
        """Create a dataset for annotation.

        Args:
            **kwargs: Additional keyword arguments to pass to the Argilla client.
                -dataset_name: The name of the dataset.
                -settings: The settings for the dataset.
                -workspace: The name of the workspace. By default, the first available.

        Returns:
            An Argilla dataset object.

        Raises:
            ValueError: if `dataset_name` or `settings` aren't provided.
            RuntimeError: if the workspace creation fails.
            RuntimeError: if the dataset creation fails.
        """
        dataset_name = kwargs.get("dataset_name")
        settings = kwargs.get("settings")
        workspace = kwargs.get("workspace")

        if dataset_name is None or settings is None:
            raise ValueError(
                "`dataset_name` and `settings` keyword arguments are required."
            )

        if workspace is None and not self._get_client().workspaces:
            workspace_to_create = rg.Workspace(name="argilla")
            try:
                workspace = workspace_to_create.create()
            except Exception as e:
                raise RuntimeError(
                    "Failed to create the `argilla` workspace."
                ) from e

        try:
            dataset = rg.Dataset(
                name=dataset_name, workspace=workspace, settings=settings
            )
            logger.info(f"Creating the dataset '{dataset_name}' in Argilla...")
            dataset.create()
            logger.info(f"Dataset '{dataset_name}' successfully created.")
            return self.get_dataset(
                dataset_name=dataset_name, workspace=workspace
            )
        except Exception as e:
            logger.error(
                f"Failed to create dataset '{dataset_name}' in Argilla: {str(e)}"
            )
            raise RuntimeError(
                f"Failed to create the dataset '{dataset_name}' in Argilla: {str(e)}"
            ) from e

    def add_records(
        self,
        dataset_name: str,
        records: Union[Any, Dict],
        workspace: Optional[str] = None,
        mapping: Optional[Dict] = None,
    ) -> Any:
        """Add records to an Argilla dataset for annotation.

        Args:
            dataset_name: The name of the dataset.
            records: The records to add to the dataset.
            workspace: The name of the workspace. By default, the first available.
            mapping: The mapping of the records to the dataset fields. By default, None.

        Raises:
            RuntimeError: If the records cannot be loaded to Argilla.
        """
        dataset = self.get_dataset(
            dataset_name=dataset_name, workspace=workspace
        )

        try:
            logger.info(
                f"Loading the records to '{dataset_name}' in Argilla..."
            )
            dataset.records.log(records=records, mapping=mapping)
            logger.info(
                f"Records loaded successfully to Argilla for '{dataset_name}'."
            )
        except Exception as e:
            logger.error(
                f"Failed to load the records to Argilla for '{dataset_name}': {str(e)}"
            )
            raise RuntimeError(
                f"Failed to load the records to Argilla: {str(e)}"
            ) from e

    def get_dataset(self, **kwargs: Any) -> Any:
        """Gets the dataset with the given name.

        Args:
            **kwargs: Additional keyword arguments to pass to the Argilla client.
                -dataset_name: The name of the dataset.
                -workspace: The name of the workspace. By default, the first available.

        Returns:
            The Argilla Dataset for the given name and workspace, if specified.

        Raises:
            ValueError: If the dataset name is not provided or if the dataset
                does not exist.
        """
        dataset_name = kwargs.get("dataset_name")
        workspace = kwargs.get("workspace")

        if not dataset_name:
            raise ValueError("`dataset_name` keyword argument is required.")

        try:
            dataset = self._get_client().datasets(
                name=dataset_name, workspace=workspace
            )
            if dataset is None:
                logger.error(f"Dataset '{dataset_name}' not found.")
            else:
                return dataset
        except ValueError as e:
            logger.error(f"Dataset '{dataset_name}' not found.")
            raise ValueError(f"Dataset '{dataset_name}' not found.") from e

    def delete_dataset(self, **kwargs: Any) -> None:
        """Deletes a dataset from the annotation interface.

        Args:
            **kwargs: Additional keyword arguments to pass to the Argilla client.
                -dataset_name: The name of the dataset.
                -workspace: The name of the workspace. By default, the first available

        Raises:
            ValueError: If the dataset name is not provided or if the datasets
                is not found.
        """
        dataset_name = kwargs.get("dataset_name")
        workspace = kwargs.get("workspace")

        if not dataset_name:
            raise ValueError("`dataset_name` keyword argument is required.")

        try:
            dataset = self.get_dataset(
                dataset_name=dataset_name, workspace=workspace
            )
            dataset.delete()
            logger.info(f"Dataset '{dataset_name}' deleted successfully.")
        except ValueError:
            logger.warning(
                f"Dataset '{dataset_name}' not found. Skipping deletion."
            )

    def get_labeled_data(self, **kwargs: Any) -> Any:
        """Gets the dataset containing the labeled data.

        Args:
            **kwargs: Additional keyword arguments to pass to the Argilla client.
                -dataset_name: The name of the dataset.
                -workspace: The name of the workspace. By default, the first available.

        Returns:
            The list of annotated records.

        Raises:
            ValueError: If the dataset name is not provided.
        """
        dataset_name = kwargs.get("dataset_name")
        workspace = kwargs.get("workspace")

        if not dataset_name:
            raise ValueError("`dataset_name` keyword argument is required.")

        return self._get_data_by_status(
            dataset_name, workspace=workspace, status="completed"
        )

    def get_unlabeled_data(self, **kwargs: str) -> Any:
        """Gets the dataset containing the unlabeled data.

        Args:
            **kwargs: Additional keyword arguments to pass to the Argilla client.

        Returns:
            The list of pending records for annotation.

        Raises:
            ValueError: If the dataset name is not provided.
        """
        dataset_name = kwargs.get("dataset_name")
        workspace = kwargs.get("workspace")

        if not dataset_name:
            raise ValueError("`dataset_name` keyword argument is required.")

        return self._get_data_by_status(
            dataset_name, workspace=workspace, status="pending"
        )
