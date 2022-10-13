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
"""Base class for ZenML annotator stack components."""

from abc import ABC, abstractmethod
from typing import Any, ClassVar, List, Optional, Tuple, Type, cast

from zenml.enums import StackComponentType
from zenml.stack import Flavor, StackComponent
from zenml.stack.stack_component import StackComponentConfig


class BaseAnnotatorConfig(StackComponentConfig):
    """Base config for annotators.

    Attributes:
        notebook_only: if the annotator can only be used in a notebook.
    """

    notebook_only: ClassVar[bool] = False


class BaseAnnotator(StackComponent, ABC):
    """Base class for all ZenML annotators."""

    @property
    def config(self) -> BaseAnnotatorConfig:
        """Returns the `BaseAnnotatorConfig` config.

        Returns:
            The configuration.
        """
        return cast(BaseAnnotatorConfig, self._config)

    @abstractmethod
    def get_url(self) -> str:
        """Gets the URL of the annotation interface.

        Returns:
            The URL of the annotation interface.
        """

    @abstractmethod
    def get_url_for_dataset(self, dataset_name: str) -> str:
        """Gets the URL of the annotation interface for a specific dataset.

        Args:
            dataset_name: name of the dataset.

        Returns:
            The URL of the dataset annotation interface.
        """

    @abstractmethod
    def get_datasets(self) -> List[Any]:
        """Gets the datasets currently available for annotation.

        Returns:
            The datasets currently available for annotation.
        """

    @abstractmethod
    def get_dataset_names(self) -> List[str]:
        """Gets the names of the datasets currently available for annotation.

        Returns:
            The names of the datasets currently available for annotation.
        """

    @abstractmethod
    def get_dataset_stats(self, dataset_name: str) -> Tuple[int, int]:
        """Gets the statistics of a dataset.

        Args:
            dataset_name: name of the dataset.

        Returns:
            A tuple containing (labeled_task_count, unlabeled_task_count) for
                the dataset.
        """

    @abstractmethod
    def launch(self, url: Optional[str]) -> None:
        """Launches the annotation interface.

        Args:
            url: The URL of the annotation interface.
        """

    @abstractmethod
    def add_dataset(self, **kwargs: Any) -> Any:
        """Registers a dataset for annotation.

        Args:
            **kwargs: keyword arguments.

        Returns:
            The dataset or confirmation object on adding the dataset.
        """

    @abstractmethod
    def get_dataset(self, **kwargs: Any) -> Any:
        """Gets the dataset with the given name.

        Args:
            **kwargs: keyword arguments.

        Returns:
            The dataset with the given name.
        """

    @abstractmethod
    def delete_dataset(self, **kwargs: Any) -> None:
        """Deletes a dataset.

        Args:
            **kwargs: keyword arguments.
        """

    @abstractmethod
    def get_labeled_data(self, **kwargs: Any) -> Any:
        """Gets the labeled data for the given dataset.

        Args:
            **kwargs: keyword arguments.

        Returns:
            The labeled data for the given dataset.
        """

    @abstractmethod
    def get_unlabeled_data(self, **kwargs: str) -> Any:
        """Gets the unlabeled data for the given dataset.

        Args:
            **kwargs: Additional keyword arguments to pass to the Label Studio client.

        Returns:
            The unlabeled data for the given dataset.
        """


class BaseAnnotatorFlavor(Flavor):
    """Base class for annotator flavors."""

    @property
    def type(self) -> StackComponentType:
        """Returns the flavor type.

        Returns:
            The flavor type.
        """
        return StackComponentType.ANNOTATOR

    @property
    def config_class(self) -> Type[BaseAnnotatorConfig]:
        """Config class for this flavor.

        Returns:
            The config class.
        """
        return BaseAnnotatorConfig

    @property
    @abstractmethod
    def implementation_class(self) -> Type[BaseAnnotator]:
        """Implementation class.

        Returns:
            The implementation class.
        """
        return BaseAnnotator
