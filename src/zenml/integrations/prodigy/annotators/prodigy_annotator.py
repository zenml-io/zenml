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
"""Implementation of the Prodigy annotation integration."""

import json
from typing import Any, List, Optional, Tuple, cast

import prodigy
from peewee import Database as PeeweeDatabase
from prodigy.components.db import (
    Database as ProdigyDatabase,
)
from prodigy.components.db import connect
from prodigy.errors import ProdigyError

from zenml.annotators.base_annotator import BaseAnnotator
from zenml.integrations.prodigy.flavors.prodigy_annotator_flavor import (
    ProdigyAnnotatorConfig,
)
from zenml.logger import get_logger
from zenml.stack.authentication_mixin import AuthenticationMixin

logger = get_logger(__name__)

DEFAULT_LOCAL_INSTANCE_HOST = "localhost"
DEFAULT_LOCAL_PRODIGY_PORT = 8080


class ProdigyAnnotator(BaseAnnotator, AuthenticationMixin):
    """Class to interact with the Prodigy annotation interface."""

    @property
    def config(self) -> ProdigyAnnotatorConfig:
        """Returns the `ProdigyAnnotatorConfig` config.

        Returns:
            The configuration.
        """
        return cast(ProdigyAnnotatorConfig, self._config)

    def get_url(self) -> str:
        """Gets the top-level URL of the annotation interface.

        Returns:
            The URL of the annotation interface.
        """
        instance_url = DEFAULT_LOCAL_INSTANCE_HOST
        port = DEFAULT_LOCAL_PRODIGY_PORT
        if self.config.custom_config_path:
            with open(self.config.custom_config_path, "r") as f:
                config = json.load(f)
            instance_url = config.get("instance_url", instance_url)
            port = config.get("port", port)
        return f"http://{instance_url}:{port}"

    def get_url_for_dataset(self, dataset_name: str) -> str:
        """Gets the URL of the annotation interface for the given dataset.

        Prodigy does not support dataset-specific URLs, so this method returns
        the top-level URL since that's what will be served for the user.

        Args:
            dataset_name: The name of the dataset. (Unuse)

        Returns:
            The URL of the annotation interface.
        """
        return self.get_url()

    def get_datasets(self) -> List[Any]:
        """Gets the datasets currently available for annotation.

        Returns:
            A list of datasets (str).
        """
        datasets = self._get_db().datasets
        return cast(List[Any], datasets)

    def get_dataset_names(self) -> List[str]:
        """Gets the names of the datasets.

        Returns:
            A list of dataset names.
        """
        return self.get_datasets()

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
        db = self._get_db()
        try:
            labeled_data_count = db.count_dataset(name=dataset_name)
        except ValueError as e:
            raise IndexError(
                f"Dataset {dataset_name} does not exist. Please use `zenml "
                f"annotator dataset list` to list the available datasets."
            ) from e
        return (labeled_data_count, 0)

    def launch(self, **kwargs: Any) -> None:
        """Launches the annotation interface.

        This method extracts the 'command' and additional config
            parameters from kwargs.

        Args:
            **kwargs: Should include:
                - command: The full recipe command without "prodigy".
                - Any additional config parameters to overwrite the
                    project-specific, global, and recipe config.

        Raises:
            ValueError: If the 'command' keyword argument is not provided.
        """
        command = kwargs.get("command")
        if not command:
            raise ValueError(
                "The 'command' keyword argument is required for launching Prodigy."
            )

        # Remove 'command' from kwargs to pass the rest as config parameters
        config = {
            key: value for key, value in kwargs.items() if key != "command"
        }
        prodigy.serve(command=command, **config)

    def _get_db(
        self,
        custom_database: PeeweeDatabase = None,
        display_id: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> ProdigyDatabase:
        """Gets Prodigy database / client.

        Args:
            custom_database: Custom database to use.
            display_id: The display id of the database.
            display_name: The display name of the database.

        Returns:
            Prodigy database client.
        """
        db_kwargs = {}
        if custom_database:
            db_kwargs["db"] = custom_database
        if display_id:
            db_kwargs["display_id"] = display_id
        if display_name:
            db_kwargs["display_name"] = display_name

        # database is passed in without the keyword argument
        if custom_database:
            return connect(custom_database, **db_kwargs)
        return connect(**db_kwargs)

    def add_dataset(self, **kwargs: Any) -> Any:
        """Registers a dataset for annotation.

        Args:
            **kwargs: Additional keyword arguments to pass to the Prodigy client.

        Returns:
            A Prodigy list representing the dataset.

        Raises:
            ValueError: if 'dataset_name' and 'label_config' aren't provided.
        """
        db = self._get_db()
        dataset_kwargs = {"dataset_name": kwargs.get("dataset_name")}
        if not dataset_kwargs["dataset_name"]:
            raise ValueError("`dataset_name` keyword argument is required.")

        if kwargs.get("dataset_meta"):
            dataset_kwargs["dataset_meta"] = kwargs.get("dataset_meta")
        return db.add_dataset(**dataset_kwargs)

    def delete_dataset(self, **kwargs: Any) -> None:
        """Deletes a dataset from the annotation interface.

        Args:
            **kwargs: Additional keyword arguments to pass to the Prodigy
                client.

        Raises:
            ValueError: If the dataset name is not provided or if the dataset
                does not exist.
        """
        db = self._get_db()
        if not (dataset_name := kwargs.get("dataset_name")):
            raise ValueError("`dataset_name` keyword argument is required.")
        try:
            db.drop_dataset(name=dataset_name)
        except ProdigyError as e:
            # see https://support.prodi.gy/t/how-to-import-datasetdoesnotexist-error/7205
            if type(e).__name__ == "DatasetNotFound":
                raise ValueError(
                    f"Dataset name '{dataset_name}' does not exist."
                ) from e

    def get_dataset(self, **kwargs: Any) -> Any:
        """Gets the dataset metadata for the given name.

        If you would like the labelled data, use `get_labeled_data` instead.

        Args:
            **kwargs: Additional keyword arguments to pass to the Prodigy client.

        Returns:
            The metadata associated with a Prodigy dataset

        Raises:
            ValueError: If the dataset name is not provided or if the dataset
                does not exist.
        """
        db = self._get_db()
        if dataset_name := kwargs.get("dataset_name"):
            try:
                return db.get_meta(name=dataset_name)
            except Exception as e:
                raise ValueError(
                    f"Dataset name '{dataset_name}' does not exist."
                ) from e

    def get_labeled_data(self, **kwargs: Any) -> Any:
        """Gets the labeled data for the given dataset.

        Args:
            **kwargs: Additional keyword arguments to pass to the Prodigy client.

        Returns:
            A list of all examples in the dataset serialized to the
                Prodigy Task format.

        Raises:
            ValueError: If the dataset name is not provided or if the dataset
                does not exist.
        """
        if dataset_name := kwargs.get("dataset_name"):
            return self._get_db().get_dataset_examples(dataset_name)
        else:
            raise ValueError("`dataset_name` keyword argument is required.")

    def get_unlabeled_data(self, **kwargs: str) -> Any:
        """Gets the unlabeled data for the given dataset.

        Args:
            **kwargs: Additional keyword arguments to pass to the Prodigy client.

        Raises:
            NotImplementedError: Prodigy doesn't allow fetching unlabeled data.
        """
        raise NotImplementedError(
            "Prodigy doesn't allow fetching unlabeled data."
        )
