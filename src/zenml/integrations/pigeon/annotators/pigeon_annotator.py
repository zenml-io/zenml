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
"""Pigeon annotator

Credit for the implementation of this code to @agermanidis in the pigeon package
and library. This code has been slightly modified to fit the ZenML framework.

https://github.com/agermanidis/pigeon
"""

import json
import os
from datetime import datetime
from typing import Any, List, Optional, Tuple, cast

import ipywidgets as widgets
from IPython.display import clear_output, display

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
            A list of dataset names (annotation file names) (or empty list when no datasets are present).
        """
        output_dir = self.config.output_dir
        try:
            return [f for f in os.listdir(output_dir) if f.endswith(".txt")]
        except FileNotFoundError:
            return []

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

    def _annotate(
        self,
        data: List[Any],
        options: List[str],
        display_fn: Optional[Any] = None,
    ) -> List[Tuple[Any, Any]]:
        """Internal method to build an interactive widget for annotating.

        Args:
            data: List of examples to annotate.
            options: List of labels to choose from.
            display_fn: Optional function to display examples.

        Returns:
            A list of tuples containing (example, label) for each annotated example.
        """
        examples = list(data)
        annotations = []
        current_index = 0
        out = widgets.Output()

        def show_next():
            nonlocal current_index
            if current_index >= len(examples):
                with out:
                    clear_output(wait=True)
                    print("Annotation done.")
                return
            with out:
                clear_output(wait=True)
                if display_fn:
                    display_fn(examples[current_index])
                else:
                    display(examples[current_index])

        def add_annotation(btn):
            """Add an annotation to the list of annotations.

            Args:
                btn: The button that triggered the event.
            """
            nonlocal current_index
            annotation = btn.description
            annotations.append((examples[current_index], annotation))
            current_index += 1
            show_next()

        def submit_annotations(btn):
            """Submit all annotations and save them to a file.

            Args:
                btn: The button that triggered the event.
            """
            self._save_annotations(annotations)
            with out:
                clear_output(wait=True)
                print("Annotations saved.")

        count_label = widgets.Label()
        display(count_label)

        buttons = []
        for label in options:
            btn = widgets.Button(description=label)
            btn.on_click(add_annotation)
            buttons.append(btn)

        submit_btn = widgets.Button(
            description="Save labels", button_style="success"
        )
        submit_btn.on_click(submit_annotations)
        buttons.append(submit_btn)

        navigation_box = widgets.HBox(buttons)
        display(navigation_box)
        display(out)
        show_next()

        return annotations

    def launch(
        self,
        data: List[Any],
        options: List[str],
        display_fn: Optional[Any] = None,
    ) -> List[Tuple[Any, Any]]:
        """Launch the Pigeon annotator in the Jupyter notebook.

        Args:
            data: List of examples to annotate.
            options: List of labels to choose from.
            display_fn: Optional function to display examples.

        Returns:
            A list of tuples containing (example, label) for each annotated example.
        """
        annotations = self._annotate(data, options, display_fn)
        return annotations

    def _save_annotations(self, annotations: List[Tuple[Any, Any]]) -> None:
        """Save annotations to a file with a unique date-time suffix.

        Args:
            annotations: List of tuples containing (example, label) for each annotated example.
        """
        output_dir = self.config.output_dir
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f"annotations_{timestamp}.json")
        with open(output_file, "w") as f:
            json.dump(annotations, f)

    def add_dataset(self, **kwargs: Any) -> Any:
        """Add a dataset (annotation file) to the Pigeon annotator.

        Raises:
            NotImplementedError: Pigeon annotator does not support adding datasets.
        """
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
            annotations = json.load(f)
        return annotations

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
