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
from typing import ClassVar, List

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
        """Gets the URL of the annotation interface."""

    @abstractmethod
    def get_datasets(self) -> List[str]:
        """Gets the datasets currently available for annotation."""

    @abstractmethod
    def launch(self) -> None:
        """Launches the annotation interface."""

    @abstractmethod
    def add_dataset(self, dataset_name: str) -> None:
        """Registers a dataset for annotation."""

    @abstractmethod
    def delete_dataset(self, dataset_name: str) -> None:
        """Deletes a dataset from the annotation interface."""

    @abstractmethod
    def get_dataset(self, dataset_name: str) -> None:
        """Gets the dataset with the given name."""

    @abstractmethod
    def get_annotations(self, dataset_name: str) -> None:
        """Gets the annotations for the given dataset."""

    @abstractmethod
    def tag_dataset(self, dataset_name: str, tag: str) -> None:
        """Tags the dataset with the given name with the given tag."""

    @abstractmethod
    def untag_dataset(self, dataset_name: str, tag: str) -> None:
        """Untags the dataset with the given name with the given tag."""

    @abstractmethod
    def get_labeled_data(self, dataset_name: str) -> None:
        """Gets the labeled data for the given dataset."""

    @abstractmethod
    def get_unlabeled_data(self, dataset_name: str) -> None:
        """Gets the unlabeled data for the given dataset."""

    # @abstractmethod
    # def export_data(self, identifier: str, export_config) -> Any:
    #     """Exports the data for the given identifier."""

    @abstractmethod
    def import_data(self, identifier: str, import_config) -> None:
        """Imports the data for the given identifier."""
