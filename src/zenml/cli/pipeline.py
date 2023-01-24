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
"""CLI functionality to interact with pipelines."""
from typing import Any

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import list_options
from zenml.client import Client
from zenml.console import console
from zenml.enums import CliCategories
from zenml.logger import get_logger
from zenml.models import PipelineFilterModel, PipelineRunFilterModel
from zenml.models.schedule_model import ScheduleFilterModel

logger = get_logger(__name__)


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def pipeline() -> None:
    """List, run, or delete pipelines."""


@pipeline.command("run", help="Run a pipeline with the given configuration.")
@click.option(
    "--config",
    "-c",
    "config_path",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
)
@click.argument("python_file")
def cli_pipeline_run(python_file: str, config_path: str) -> None:
    """Runs pipeline specified by the given config YAML object.

    Args:
        python_file: Path to the python file that defines the pipeline.
        config_path: Path to configuration YAML file.
    """
    from zenml.pipelines.run_pipeline import run_pipeline

    run_pipeline(python_file=python_file, config_path=config_path)


@pipeline.command("list", help="List all registered pipelines.")
@list_options(PipelineFilterModel)
def list_pipelines(**kwargs: Any) -> None:
    """List all registered pipelines."""
    cli_utils.print_active_config()
    client = Client()
    with console.status("Listing pipelines...\n"):

        pipelines = client.list_pipelines(**kwargs)

        if not pipelines.items:
            cli_utils.declare("No pipelines found for this filter.")
            return

        cli_utils.print_pydantic_models(
            pipelines,
            exclude_columns=["id", "created", "updated", "user", "project"],
        )


@pipeline.command("delete")
@click.argument("pipeline_name_or_id", type=str, required=True)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Don't ask for confirmation.",
)
def delete_pipeline(pipeline_name_or_id: str, yes: bool = False) -> None:
    """Delete a pipeline.

    Args:
        pipeline_name_or_id: The name or ID of the pipeline to delete.
        yes: If set, don't ask for confirmation.
    """
    cli_utils.print_active_config()

    if not yes:
        confirmation = cli_utils.confirmation(
            f"Are you sure you want to delete pipeline "
            f"`{pipeline_name_or_id}`? This will change all existing runs of "
            "this pipeline to become unlisted."
        )
        if not confirmation:
            cli_utils.declare("Pipeline deletion canceled.")
            return

    try:
        Client().delete_pipeline(name_id_or_prefix=pipeline_name_or_id)
    except KeyError as e:
        cli_utils.error(str(e))
    else:
        cli_utils.declare(f"Deleted pipeline '{pipeline_name_or_id}'.")


@pipeline.group()
def schedule() -> None:
    """Commands for pipeline run schedules."""


@schedule.command("list", help="List all pipeline schedules.")
@list_options(ScheduleFilterModel)
def list_schedules(**kwargs: Any) -> None:
    """List all pipeline schedules.

    Args:
        **kwargs: Keyword arguments to filter schedules.
    """
    cli_utils.print_active_config()
    client = Client()

    schedules = client.list_schedules(**kwargs)

    if not schedules:
        cli_utils.declare("No schedules found for this filter.")
        return

    cli_utils.print_pydantic_models(
        schedules,
        exclude_columns=["id", "created", "updated", "user", "project"],
    )


@schedule.command("delete", help="Delete a pipeline schedule.")
@click.argument("schedule_name_or_id", type=str, required=True)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Don't ask for confirmation.",
)
def delete_schedule(schedule_name_or_id: str, yes: bool = False) -> None:
    """Delete a pipeline schedule.

    Args:
        schedule_name_or_id: The name or ID of the schedule to delete.
        yes: If set, don't ask for confirmation.
    """
    cli_utils.print_active_config()

    if not yes:
        confirmation = cli_utils.confirmation(
            f"Are you sure you want to delete schedule "
            f"`{schedule_name_or_id}`?"
        )
        if not confirmation:
            cli_utils.declare("Schedule deletion canceled.")
            return

    try:
        Client().delete_schedule(name_id_or_prefix=schedule_name_or_id)
    except KeyError as e:
        cli_utils.error(str(e))
    else:
        cli_utils.declare(f"Deleted schedule '{schedule_name_or_id}'.")


@pipeline.group()
def runs() -> None:
    """Commands for pipeline runs."""


@runs.command("list", help="List all registered pipeline runs.")
@list_options(PipelineRunFilterModel)
def list_pipeline_runs(**kwargs: Any) -> None:
    """List all registered pipeline runs for the filter."""
    cli_utils.print_active_config()

    client = Client()
    try:
        with console.status("Listing roles...\n"):
            pipeline_runs = client.list_runs(**kwargs)
    except KeyError as err:
        cli_utils.error(str(err))
    else:
        if not pipeline_runs.items:
            cli_utils.declare("No pipeline runs found for this filter.")
            return

        cli_utils.print_pipeline_runs_table(pipeline_runs=pipeline_runs.items)
        cli_utils.print_page_info(pipeline_runs)


@runs.command("delete")
@click.argument("run_name_or_id", type=str, required=True)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Don't ask for confirmation.",
)
def delete_pipeline_run(
    run_name_or_id: str,
    yes: bool = False,
) -> None:
    """Delete a pipeline run.

    Args:
        run_name_or_id: The name or ID of the pipeline run to delete.
        yes: If set, don't ask for confirmation.
    """
    cli_utils.print_active_config()

    # Ask for confirmation to delete run.
    if not yes:
        confirmation = cli_utils.confirmation(
            f"Are you sure you want to delete pipeline run `{run_name_or_id}`?"
        )
        if not confirmation:
            cli_utils.declare("Pipeline run deletion canceled.")
            return

    # Delete run.
    try:
        Client().delete_pipeline_run(
            name_id_or_prefix=run_name_or_id,
        )
    except KeyError as e:
        cli_utils.error(str(e))
    else:
        cli_utils.declare(f"Deleted pipeline run '{run_name_or_id}'.")
