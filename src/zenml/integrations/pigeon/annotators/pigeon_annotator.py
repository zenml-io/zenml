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
"""Pigeon annotator."""

import os
from datetime import datetime
from typing import Any, List, Optional, Tuple, cast

from pigeon import annotate

from zenml.annotators.base_annotator import BaseAnnotator
from zenml.integrations.pigeon.flavors.pigeon_annotator_flavor import (
    PigeonAnnotatorConfig,
)
from zenml.logger import get_logger

logger = get_logger(__name__)


class PigeonAnnotator(BaseAnnotator):
    """Annotator for using Pigeon in Jupyter notebooks."""

    @property
    def config(self) -> PigeonAnnotatorConfig:
        """Get the Pigeon annotator config.

        Returns:
            The Pigeon annotator config.
        """
        return cast(PigeonAnnotatorConfig, self._config)

    def get_url(self) -> str:
        """Get the URL of the Pigeon annotator.

        Raises:
            NotImplementedError: Pigeon annotator does not have a URL.
        """
        raise NotImplementedError("Pigeon annotator does not have a URL.")

    def get_url_for_dataset(self, dataset_name: str) -> str:
        """Get the URL of the Pigeon annotator for a specific dataset.

        Args:
            dataset_name: Name of the dataset (annotation file).

        Raises:
            NotImplementedError: Pigeon annotator does not have a URL.
        """
        raise NotImplementedError("Pigeon annotator does not have a URL.")

    def get_datasets(self) -> List[str]:
        """Get a list of datasets (annotation files) in the output directory.

        Returns:
            A list of dataset names (annotation file names).
        """
        output_dir = self.config.output_dir
        return [f for f in os.listdir(output_dir) if f.endswith(".txt")]

    def get_dataset_names(self) -> List[str]:
        """Get a list of dataset names (annotation file names) in the output
        directory.

        Returns:
            A list of dataset names (annotation file names).
        """
        return self.get_datasets()

    def get_dataset_stats(self, dataset_name: str) -> Tuple[int, int]:
        """Get the number of labeled and unlabeled examples in a dataset (annotation file).

        Args:
            dataset_name: Name of the dataset (annotation file).

        Returns:
            A tuple containing (num_labeled_examples, num_unlabeled_examples).
        """
        dataset_path = os.path.join(self.config.output_dir, dataset_name)
        num_labeled_examples = sum(1 for _ in open(dataset_path))
        num_unlabeled_examples = 0  # Assuming all examples are labeled
        return num_labeled_examples, num_unlabeled_examples

    def launch(
        self,
        type: str,
        data: List[Any],
        options: List[str],
        display_fn: Optional[Any] = None,
    ) -> None:
        """Launch the Pigeon annotator in the Jupyter notebook.

        Args:
            type: Type of annotation task ('text_classification', 'image_classification', etc.).
            data: List of data items to annotate.
            options: List of options for classification tasks.
            display_fn: Optional function for displaying data items.
        """
        annotations = annotate(
            examples=data,
            options=options,
            display_fn=display_fn,
        )
        self._save_annotations(annotations)

    def add_dataset(self, **kwargs: Any) -> Any:
        raise NotImplementedError(
            "Pigeon annotator does not support adding datasets."
        )

    def delete_dataset(self, dataset_name: str) -> None:
        """Delete a dataset (annotation file).

        Args:
            dataset_name: Name of the dataset (annotation file) to delete.
        """
        dataset_path = os.path.join(self.config.output_dir, dataset_name)
        os.remove(dataset_path)

    def get_dataset(self, dataset_name: str) -> List[Tuple[Any, Any]]:
        """Get the annotated examples from a dataset (annotation file).

        Args:
            dataset_name: Name of the dataset (annotation file).

        Returns:
            A list of tuples containing (example, label) for each annotated example.
        """
        dataset_path = os.path.join(self.config.output_dir, dataset_name)
        with open(dataset_path, "r") as f:
            lines = f.readlines()
        annotations = [line.strip().split("\t") for line in lines]
        return list(annotations)

    def get_labeled_data(self, dataset_name: str) -> List[Tuple[Any, Any]]:
        """Get the labeled examples from a dataset (annotation file).

        Args:
            dataset_name: Name of the dataset (annotation file).

        Returns:
            A list of tuples containing (example, label) for each labeled example.
        """
        return self.get_dataset(dataset_name)

    def get_unlabeled_data(self, **kwargs: Any) -> Any:
        """Get the unlabeled examples from a dataset (annotation file).

        Raises:
            NotImplementedError: Pigeon annotator does not support retrieving unlabeled data.
        """
        raise NotImplementedError(
            "Pigeon annotator does not support retrieving unlabeled data."
        )

    def _save_annotations(self, annotations: List[Any]) -> None:
        """Save annotations to a file with a unique date-time suffix.

        Args:
            annotations: List of annotated examples.
        """
        output_dir = self.config.output_dir
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f"annotations_{timestamp}.txt")
        with open(output_file, "w") as f:
            for example, label in annotations:
                f.write(f"{example}\t{label}\n")
