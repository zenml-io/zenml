#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Functionality for annotator CLI subcommands."""

from typing import TYPE_CHECKING, cast

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.enums import StackComponentType

if TYPE_CHECKING:
    from zenml.annotators.base_annotator import BaseAnnotator


def register_annotator_subcommands() -> None:
    """Registers CLI subcommands for the annotator."""
    annotator_group = cast(TagGroup, cli.commands.get("annotator"))
    if not annotator_group:
        return

    @annotator_group.group(
        cls=TagGroup,
        help="Commands for interacting with annotation datasets.",
    )
    @click.pass_context
    def dataset(ctx: click.Context) -> None:
        """Interact with ZenML annotator datasets.

        Args:
            ctx: The click Context object.
        """
        from zenml.client import Client

        annotator_models = Client().active_stack_model.components.get(
            StackComponentType.ANNOTATOR
        )
        if annotator_models is None:
            cli_utils.error(
                "No active annotator found. Please register an annotator "
                "first and add it to your stack."
            )
            return

        from zenml.stack.stack_component import StackComponent

        ctx.obj = StackComponent.from_model(annotator_models[0])

    @dataset.command(
        "list",
        help="List the available datasets.",
    )
    @click.pass_obj
    def dataset_list(annotator: "BaseAnnotator") -> None:
        """List the available datasets.

        Args:
            annotator: The annotator stack component.
        """
        cli_utils.print_list_items(
            list_items=annotator.get_dataset_names(),
            column_title="DATASETS",
        )

    @dataset.command("stats")
    @click.argument("dataset_name", type=click.STRING)
    @click.pass_obj
    def dataset_stats(annotator: "BaseAnnotator", dataset_name: str) -> None:
        """Display statistics about a dataset.

        Args:
            annotator: The annotator stack component.
            dataset_name: The name of the dataset.
        """
        try:
            stats = annotator.get_dataset_stats(dataset_name)
            labeled_task_count, unlabeled_task_count = stats
        except IndexError:
            cli_utils.error(
                f"Dataset {dataset_name} does not exist. Please use `zenml "
                f"annotator dataset list` to list the available datasets."
            )
            return

        total_task_count = unlabeled_task_count + labeled_task_count
        cli_utils.declare(
            f"Annotation stats for '{dataset_name}' dataset:", bold=True
        )
        cli_utils.declare(f"Total annotation tasks: {total_task_count}")
        cli_utils.declare(f"Labeled annotation tasks: {labeled_task_count}")
        cli_utils.declare(f"Unlabeled annotation tasks: {unlabeled_task_count}")

    @dataset.command("delete")
    @click.argument("dataset_name", type=click.STRING)
    @click.option(
        "--all",
        "-a",
        "all",
        is_flag=True,
        help="Use this flag to delete all datasets.",
        type=click.BOOL,
    )
    @click.pass_obj
    def dataset_delete(
        annotator: "BaseAnnotator", dataset_name: str, all_: bool
    ) -> None:
        """Delete a dataset.

        If the --all flag is used, all datasets will be deleted.

        Args:
            annotator: The annotator stack component.
            dataset_name: Name of the dataset to delete.
            all_: Whether to delete all datasets.
        """
        cli_utils.declare(f"Deleting your dataset '{dataset_name}'")
        dataset_names = (
            annotator.get_dataset_names() if all_ else [dataset_name]
        )
        for dataset_name in dataset_names:
            annotator.delete_dataset(dataset_name=dataset_name)
            cli_utils.declare(f"Dataset '{dataset_name}' has now been deleted.")

    @dataset.command(
        "annotate", context_settings={"ignore_unknown_options": True}
    )
    @click.argument("dataset_name", type=click.STRING)
    @click.pass_obj
    def dataset_annotate(annotator: "BaseAnnotator", dataset_name: str) -> None:
        """Command to launch the annotation interface for a dataset.

        Args:
            annotator: The annotator stack component.
            dataset_name: Name of the dataset

        Raises:
            ValueError: If the dataset does not exist.
        """
        cli_utils.declare(
            f"Launching the annotation interface for dataset '{dataset_name}'."
        )
        try:
            annotator.get_dataset(dataset_name=dataset_name)
            annotator.launch(url=annotator.get_url_for_dataset(dataset_name))
        except ValueError as e:
            raise ValueError("Dataset does not exist.") from e
