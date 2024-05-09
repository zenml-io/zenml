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

import webbrowser
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

        Raises:
            ValueError: when unable to access the Argilla API key.
        """
        # try:
        #     settings = cast(
        #         ArgillaAnnotatorSettings,
        #         self.get_settings(get_step_context().step_run),
        #     )
        #     if settings.api_key is None:
        #         raise RuntimeError
        #     else:
        #         api_key = settings.api_key
        # except RuntimeError as e:
        #     if secret := self.get_authentication_secret():
        #         api_key = secret.secret_values.get("api_key", "")
        #     else:
        #         raise ValueError(
        #             "Unable to access predefined secret to access Argilla API key."
        #         ) from e
        # if not api_key:
        #     raise ValueError("Unable to access Argilla API key from secret.")

        config = self.config
        if config.api_key and config.authentication_secret:
            raise ValueError(
                "Both API key and authentication secret are provided. "
                "Please provide only one."
            )
        init_kwargs = {"api_url": self.get_url()}

        # set the API key from the secret or using settings
        if self.get_authentication_secret():
            api_key = self.get_authentication_secret().secret_values.get(
                "api_key", ""
            )
            init_kwargs["api_key"] = api_key
            logger.debug("Using API key from secret.")
        elif config.api_key is not None:
            init_kwargs["api_key"] = config.api_key
            logger.debug("Using API key from settings.")

        if config.workspace is not None:
            init_kwargs["workspace"] = config.workspace
        if config.extra_headers is not None:
            init_kwargs["extra_headers"] = config.extra_headers
        if config.httpx_extra_kwargs is not None:
            init_kwargs["httpx_extra_kwargs"] = config.httpx_extra_kwargs

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
        project_id = self.get_id_from_name(dataset_name)
        return f"{self.get_url()}/projects/{project_id}/"

    def get_datasets(self) -> List[Any]:
        """Gets the datasets currently available for annotation.

        Returns:
            A list of datasets.
        """
        new_datasets = self._get_client().list_datasets()
        # TODO: update once Argilla updates to their 2.0 SDK
        old_datasets = rg.FeedbackDataset.list()
        return cast(List[Any], new_datasets + old_datasets)

    def get_dataset_names(self) -> List[str]:
        """Gets the names of the datasets sorted alphabetically.

        Returns:
            A list of dataset names sorted alphabetically.
        """
        datasets = [dataset.name for dataset in self.get_datasets()]
        datasets.sort()
        return cast(List[str], datasets)

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
        labeled_task_count = len(
            self.get_labeled_data(dataset_name=dataset_name)
        )
        unlabeled_task_count = len(
            self.get_unlabeled_data(dataset_name=dataset_name)
        )
        return (labeled_task_count, unlabeled_task_count)

    def launch(self, **kwargs: Any) -> None:
        """Launches the annotation interface.
        Args:
            **kwargs: Additional keyword arguments to pass to the annotation client.
        """
        url = kwargs.get("url") or self.get_url()
        if self._connection_available():
            webbrowser.open(url, new=1, autoraise=True)
        else:
            logger.warning(
                "Could not launch annotation interface"
                "because the connection could not be established."
            )

    def add_dataset(self, **kwargs: Any) -> Any:
        """Registers a dataset for annotation.

        Args:
            **kwargs: Additional keyword arguments to pass to the Argilla client.

        Returns:
            A Argilla Project object.

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
            dataset.push_to_argilla(name=dataset_name)
        except Exception as e:
            raise ValueError(f"Failed to push dataset to Argilla: {e}") from e

    def delete_dataset(self, **kwargs: Any) -> None:
        """Deletes a dataset from the annotation interface.

        Args:
            **kwargs: Additional keyword arguments to pass to the Argilla
                client.

        Raises:
            ValueError: If the dataset name is not provided or if the dataset
                does not exist.
        """
        if dataset_name := kwargs.get("dataset_name"):
            self._get_client().delete(name=dataset_name)
        else:
            raise ValueError("`dataset_name` keyword argument is required.")

    def get_dataset(self, **kwargs: Any) -> Any:
        """Gets the dataset with the given name.

        Learn more about the two different generations of Argilla datasets
            in the Argilla documentation:
            https://docs.argilla.io/en/develop/practical_guides/choose_dataset.html

        Args:
            **kwargs: Additional keyword arguments to pass to the Argilla client.

        Returns:
            The Argilla DatasetModel object for the given name.

        Raises:
            ValueError: If the dataset name is not provided or if the dataset
                does not exist.
        """
        if not (dataset_name := kwargs.get("dataset_name")):
            raise ValueError("`dataset_name` keyword argument is required.")
        try:
            dataset = self._get_client().get_dataset(name=dataset_name)
        except NotFoundApiError as e:
            dataset = rg.FeedbackDataset.from_argilla(name=dataset_name)
            if not dataset:
                raise ValueError(f"Dataset {dataset_name} not found.") from e
        return dataset

    def get_labeled_data(self, **kwargs: Any) -> Any:
        """Gets the labeled data for the given dataset.

        Args:
            **kwargs: Additional keyword arguments to pass to the Argilla client.

        Returns:
            The labeled data.

        Raises:
            ValueError: If the dataset name is not provided or if the dataset
                does not exist.
        """
        if dataset_name := kwargs.get("dataset_name"):
            return self.get_dataset(dataset_name=dataset_name).filter_by(
                response_status="submitted"
            )
        else:
            raise ValueError("`dataset_name` keyword argument is required.")

    def get_unlabeled_data(self, **kwargs: str) -> Any:
        """Gets the unlabeled data for the given dataset.

        Args:
            **kwargs: Additional keyword arguments to pass to the Argilla client.

        Returns:
            The unlabeled data.

        Raises:
            ValueError: If the dataset name is not provided.
        """
        if dataset_name := kwargs.get("dataset_name"):
            return self.get_dataset(dataset_name=dataset_name).filter_by(
                response_status="pending"
            )
        else:
            raise ValueError("`dataset_name` keyword argument is required.")
