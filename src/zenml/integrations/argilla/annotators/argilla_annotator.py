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
from typing import Any, List, Tuple, Type, cast

import argilla as rg
from argilla.client.client import Argilla as ArgillaClient
from argilla.client.sdk.commons.errors import BaseClientError, NotFoundApiError

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
        """Gets Argilla client.

        Returns:
            Argilla client.
        """
        config = self.config
        init_kwargs = {"api_url": self.get_url()}

        # set the API key from the secret or using settings
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

        if config.workspace is not None:
            init_kwargs["workspace"] = config.workspace
        if config.extra_headers is not None:
            init_kwargs["extra_headers"] = json.loads(config.extra_headers)
        if config.httpx_extra_kwargs is not None:
            init_kwargs["httpx_extra_kwargs"] = json.loads(
                config.httpx_extra_kwargs
            )

        try:
            _ = rg.active_client()
        except BaseClientError:
            rg.init(**init_kwargs)
        return rg.active_client()

    def get_url_for_dataset(self, dataset_name: str) -> str:
        """Gets the URL of the annotation interface for the given dataset.

        Args:
            dataset_name: The name of the dataset.

        Returns:
            The URL of the annotation interface.
        """
        dataset_id = self.get_dataset(dataset_name=dataset_name).id
        return f"{self.get_url()}/dataset/{dataset_id}/annotation-mode"

    def get_datasets(self) -> List[Any]:
        """Gets the datasets currently available for annotation.

        Returns:
            A list of datasets.
        """
        old_datasets = self._get_client().list_datasets()
        new_datasets = rg.FeedbackDataset.list()

        # Deduplicate datasets based on their names
        dataset_names = set()
        deduplicated_datasets = []
        for dataset in new_datasets + old_datasets:
            if dataset.name not in dataset_names:
                dataset_names.add(dataset.name)
                deduplicated_datasets.append(dataset)

        return deduplicated_datasets

    def get_dataset_stats(self, dataset_name: str) -> Tuple[int, int]:
        """Gets the statistics of the given dataset.

        Args:
            dataset_name: The name of the dataset.

        Returns:
            A tuple containing (labeled_task_count, unlabeled_task_count) for
                the dataset.
        """
        dataset = self.get_dataset(dataset_name=dataset_name)
        labeled_task_count = len(
            dataset.filter_by(response_status="submitted")
        )
        unlabeled_task_count = len(
            dataset.filter_by(response_status="pending")
        )
        return (labeled_task_count, unlabeled_task_count)

    def add_dataset(self, **kwargs: Any) -> Any:
        """Registers a dataset for annotation.

        You must pass a `dataset_name` and a `dataset` object to this method.

        Args:
            **kwargs: Additional keyword arguments to pass to the Argilla
                client.

        Returns:
            An Argilla dataset object.

        Raises:
            ValueError: if 'dataset_name' and 'dataset' aren't provided.
        """
        dataset_name = kwargs.get("dataset_name")
        dataset = kwargs.get("dataset")

        if not dataset_name:
            raise ValueError("`dataset_name` keyword argument is required.")
        elif dataset is None:
            raise ValueError("`dataset` keyword argument is required.")

        try:
            logger.info(f"Pushing dataset '{dataset_name}' to Argilla...")
            dataset.push_to_argilla(name=dataset_name)
            logger.info(f"Dataset '{dataset_name}' pushed successfully.")
        except Exception as e:
            logger.error(
                f"Failed to push dataset '{dataset_name}' to Argilla: {str(e)}"
            )
            raise ValueError(
                f"Failed to push dataset to Argilla: {str(e)}"
            ) from e
        return self.get_dataset(dataset_name=dataset_name)

    def delete_dataset(self, **kwargs: Any) -> None:
        """Deletes a dataset from the annotation interface.

        Args:
            **kwargs: Additional keyword arguments to pass to the Argilla
                client.

        Raises:
            ValueError: If the dataset name is not provided.
        """
        dataset_name = kwargs.get("dataset_name")
        if not dataset_name:
            raise ValueError("`dataset_name` keyword argument is required.")

        try:
            self._get_client().delete(name=dataset_name)
            self.get_dataset(dataset_name=dataset_name).delete()
            logger.info(f"Dataset '{dataset_name}' deleted successfully.")
        except ValueError:
            logger.warning(
                f"Dataset '{dataset_name}' not found. Skipping deletion."
            )

    def get_dataset(self, **kwargs: Any) -> Any:
        """Gets the dataset with the given name.

        Args:
            **kwargs: Additional keyword arguments to pass to the Argilla client.

        Returns:
            The Argilla DatasetModel object for the given name.

        Raises:
            ValueError: If the dataset name is not provided or if the dataset
                does not exist.
        """
        dataset_name = kwargs.get("dataset_name")
        if not dataset_name:
            raise ValueError("`dataset_name` keyword argument is required.")

        try:
            if rg.FeedbackDataset.from_argilla(name=dataset_name) is not None:
                return rg.FeedbackDataset.from_argilla(name=dataset_name)
            else:
                return self._get_client().get_dataset(name=dataset_name)
        except (NotFoundApiError, ValueError) as e:
            logger.error(f"Dataset '{dataset_name}' not found.")
            raise ValueError(f"Dataset '{dataset_name}' not found.") from e

    def get_data_by_status(self, dataset_name: str, status: str) -> Any:
        """Gets the dataset containing the data with the specified status.

        Args:
            dataset_name: The name of the dataset.
            status: The response status to filter by ('submitted' for labeled,
                'pending' for unlabeled).

        Returns:
            The dataset containing the data with the specified status.

        Raises:
            ValueError: If the dataset name is not provided.
        """
        if not dataset_name:
            raise ValueError("`dataset_name` argument is required.")

        return self.get_dataset(dataset_name=dataset_name).filter_by(
            response_status=status
        )

    def get_labeled_data(self, **kwargs: Any) -> Any:
        """Gets the dataset containing the labeled data.

        Args:
            **kwargs: Additional keyword arguments to pass to the Argilla client.

        Returns:
            The dataset containing the labeled data.

        Raises:
            ValueError: If the dataset name is not provided.
        """
        if dataset_name := kwargs.get("dataset_name"):
            return self.get_data_by_status(dataset_name, status="submitted")
        else:
            raise ValueError("`dataset_name` keyword argument is required.")

    def get_unlabeled_data(self, **kwargs: str) -> Any:
        """Gets the dataset containing the unlabeled data.

        Args:
            **kwargs: Additional keyword arguments to pass to the Argilla client.

        Returns:
            The dataset containing the unlabeled data.

        Raises:
            ValueError: If the dataset name is not provided.
        """
        if dataset_name := kwargs.get("dataset_name"):
            return self.get_data_by_status(dataset_name, status="pending")
        else:
            raise ValueError("`dataset_name` keyword argument is required.")
