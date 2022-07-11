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
from typing import Any, ClassVar, List

from zenml.enums import StackComponentType
from zenml.stack import StackComponent


class BaseAnnotator(StackComponent, ABC):
    """Base class for all ZenML annotators.

    Attributes:
        notebook_only: if the annotator can only be used in a notebook.
    """

    notebook_only: ClassVar[bool] = False

    # Class configuration
    TYPE: ClassVar[StackComponentType] = StackComponentType.ANNOTATOR
    FLAVOR: ClassVar[str]

    @abstractmethod
    def get_url(self) -> str:
        """Gets the URL of the annotation interface.

        Returns:
            The URL of the annotation interface.
        """

    @abstractmethod
    def get_datasets(self) -> List[Any]:
        """Gets the datasets currently available for annotation.

        Returns:
            The datasets currently available for annotation.
        """

    @abstractmethod
    def launch(self) -> None:
        """Launches the annotation interface."""

    @abstractmethod
    def add_dataset(self, *args, **kwargs) -> Any:
        """Registers a dataset for annotation.

        Args:
            *args: positional arguments.
            **kwargs: keyword arguments.

        Returns:
            The dataset or confirmation object on adding the dataset.
        """

    @abstractmethod
    def get_dataset(self, *args, **kwargs) -> Any:
        """Gets the dataset with the given name.

        Args:
            *args: positional arguments.
            **kwargs: keyword arguments.

        Returns:
            The dataset with the given name.
        """

    @abstractmethod
    def delete_dataset(self, *args, **kwargs) -> None:
        """Deletes a dataset.

        Args:
            *args: positional arguments.
            **kwargs: keyword arguments.
        """

    @abstractmethod
    def get_labeled_data(self, *args, **kwargs) -> Any:
        """Gets the labeled data for the given dataset.

        Args:
            *args: positional arguments.
            **kwargs: keyword arguments.

        Returns:
            The labeled data for the given dataset.
        """

    @abstractmethod
    def get_unlabeled_data(self, *args, **kwargs) -> Any:
        """Gets the unlabeled data for the given dataset.

        Args:
            *args: positional arguments.
            **kwargs: keyword arguments.

        Returns:
            The unlabeled data for the given dataset.
        """
