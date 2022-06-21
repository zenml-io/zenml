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

from typing import Any, ClassVar, List

from zenml.annotators.base_annotator import BaseAnnotator
from zenml.integrations.label_studio import LABEL_STUDIO_ANNOTATOR_FLAVOR


class LabelStudioAnnotator(BaseAnnotator):
    """Class to interact with the Label Studio annotation interface."""

    FLAVOR: ClassVar[str] = LABEL_STUDIO_ANNOTATOR_FLAVOR

    def get_url(self) -> str:
        """Gets the URL of the annotation interface."""
        return "https://labelstudio.org"

    def get_datasets(self) -> List[str]:
        """Gets the datasets currently available for annotation."""

    def launch(self) -> None:
        """Launches the annotation interface."""

    def add_dataset(self, dataset_name: str) -> None:
        """Registers a dataset for annotation."""

    def delete_dataset(self, dataset_name: str) -> None:
        """Deletes a dataset from the annotation interface."""

    def get_dataset(self, dataset_name: str) -> None:
        """Gets the dataset with the given name."""

    def get_annotations(self, dataset_name: str) -> None:
        """Gets the annotations for the given dataset."""

    def tag_dataset(self, dataset_name: str, tag: str) -> None:
        """Tags the dataset with the given name with the given tag."""

    def untag_dataset(self, dataset_name: str, tag: str) -> None:
        """Untags the dataset with the given name with the given tag."""

    def get_labeled_data(self, dataset_name: str) -> None:
        """Gets the labeled data for the given dataset."""

    def get_unlabeled_data(self, dataset_name: str) -> None:
        """Gets the unlabeled data for the given dataset."""

    def export_data(self, identifier: str, export_config) -> Any:
        """Exports the data for the given identifier."""

    def import_data(self, identifier: str, import_config) -> None:
        """Imports the data for the given identifier."""
