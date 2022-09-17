#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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


from uuid import UUID

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.enums import CliCategories
from zenml.logger import get_logger
from zenml.pipelines.run_pipeline import run_pipeline
from zenml.repository import Repository
from zenml.utils.uuid_utils import is_valid_uuid

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
    run_pipeline(python_file=python_file, config_path=config_path)


@pipeline.command("list", help="List all registered pipelines.")
def list_pipelines() -> None:
    """List all registered pipelines."""
    cli_utils.print_active_config()
    pipelines = Repository().zen_store.list_pipelines(
        project_name_or_id=Repository().active_project.id
    )
    hydrated_pipelines = [p.to_hydrated_model() for p in pipelines]
    if not hydrated_pipelines:
        cli_utils.declare("No piplines registered.")
        return

    cli_utils.print_pydantic_models(
        hydrated_pipelines,
        exclude_columns=["id", "created", "updated", "user", "project"],
    )


@pipeline.command("delete")
@click.argument("pipeline_name_or_id", type=str, required=True)
def delete_pipeline(pipeline_name_or_id: str) -> None:
    """Delete a pipeline.

    Args:
        pipeline_name_or_id: The name or ID of the pipeline to delete.
    """
    cli_utils.print_active_config()
    active_project_id = Repository().active_project.id
    assert active_project_id is not None
    try:
        repo = Repository()
        if is_valid_uuid(pipeline_name_or_id):
            pipeline = repo.zen_store.get_pipeline(UUID(pipeline_name_or_id))
        else:
            pipeline = repo.zen_store.get_pipeline_in_project(
                pipeline_name=pipeline_name_or_id,
                project_name_or_id=active_project_id,
            )
    except KeyError as err:
        cli_utils.error(str(err))
    cli_utils.confirmation(
        f"Are you sure you want to delete pipeline `{pipeline_name_or_id}`? "
        "This will change all existing runs of this pipeline to become "
        "unlisted."
    )
    assert pipeline.id is not None
    Repository().zen_store.delete_pipeline(pipeline_id=pipeline.id)
    cli_utils.declare(f"Deleted pipeline '{pipeline_name_or_id}'.")
