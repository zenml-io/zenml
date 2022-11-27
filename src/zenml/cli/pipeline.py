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


import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.client import Client
from zenml.enums import CliCategories
from zenml.exceptions import EntityExistsError
from zenml.logger import get_logger

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
def list_pipelines() -> None:
    """List all registered pipelines."""
    cli_utils.print_active_config()
    pipelines = Client().list_pipelines()

    if not pipelines:
        cli_utils.declare("No piplines registered.")
        return

    cli_utils.print_pydantic_models(
        pipelines,
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
    confirmation = cli_utils.confirmation(
        f"Are you sure you want to delete pipeline `{pipeline_name_or_id}`? "
        "This will change all existing runs of this pipeline to become "
        "unlisted."
    )
    if not confirmation:
        cli_utils.declare("Pipeline deletion canceled.")
        return
    else:
        try:
            Client().delete_pipeline(name_id_or_prefix=pipeline_name_or_id)
            cli_utils.declare(f"Deleted pipeline '{pipeline_name_or_id}'.")
        except KeyError as e:
            cli_utils.error(str(e))


@pipeline.group()
def runs() -> None:
    """Commands for pipeline runs."""


@click.option("--pipeline", "-p", type=str, required=False)
@click.option("--stack", "-s", type=str, required=False)
@click.option("--user", "-u", type=str, required=False)
@click.option("--unlisted", is_flag=True)
@runs.command("list", help="List all registered pipeline runs.")
def list_pipeline_runs(
    pipeline: str, stack: str, user: str, unlisted: bool = False
) -> None:
    """List all registered pipeline runs.

    Args:
        pipeline: If provided, only return runs for this pipeline.
        stack: If provided, only return runs for this stack.
        user: If provided, only return runs for this user.
        unlisted: If True, only return unlisted runs that are not
            associated with any pipeline.
    """
    cli_utils.print_active_config()
    try:
        stack_id, pipeline_id, user_id = None, None, None
        client = Client()
        if stack:
            stack_id = client.get_stack(stack).id
        if pipeline:
            pipeline_id = client.get_pipeline(pipeline).id
        if user:
            user_id = client.get_user(user).id
        pipeline_runs = client.list_runs(
            pipeline_id=pipeline_id,
            stack_id=stack_id,
            user_name_or_id=user_id,
            unlisted=unlisted,
        )
    except KeyError as err:
        cli_utils.error(str(err))
    else:
        if not pipeline_runs:
            cli_utils.declare("No pipeline runs registered.")
            return

        cli_utils.print_pipeline_runs_table(pipeline_runs=pipeline_runs)


@runs.command("export", help="Export all pipeline runs to a YAML file.")
@click.argument("filename", type=str, required=True)
def export_pipeline_runs(filename: str) -> None:
    """Export all pipeline runs to a YAML file.

    Args:
        filename: The filename to export the pipeline runs to.
    """
    cli_utils.print_active_config()
    client = Client()
    client.export_pipeline_runs(filename=filename)


@runs.command("import", help="Import pipeline runs from a YAML file.")
@click.argument("filename", type=str, required=True)
def import_pipeline_runs(filename: str) -> None:
    """Import pipeline runs from a YAML file.

    Args:
        filename: The filename from which to import the pipeline runs.
    """
    cli_utils.print_active_config()
    client = Client()
    try:
        client.import_pipeline_runs(filename=filename)
    except EntityExistsError as err:
        cli_utils.error(str(err))


@runs.command(
    "migrate",
    help="Migrate pipeline runs from an existing metadata store database.",
)
@click.argument("database", type=str, required=True)
@click.option("--database_type", type=str, default="sqlite", required=False)
@click.option("--mysql_host", type=str, required=False)
@click.option("--mysql_port", type=int, default=3306, required=False)
@click.option("--mysql_username", type=str, required=False)
@click.option("--mysql_password", type=str, required=False)
def migrate_pipeline_runs(
    database: str,
    database_type: str,
    mysql_host: str,
    mysql_port: int,
    mysql_username: str,
    mysql_password: str,
) -> None:
    """Migrate pipeline runs from a metadata store of ZenML < 0.20.0.

    Args:
        database: The metadata store database from which to migrate the pipeline
            runs.
        database_type: The type of the metadata store database (sqlite | mysql).
        mysql_host: The host of the MySQL database.
        mysql_port: The port of the MySQL database.
        mysql_username: The username of the MySQL database.
        mysql_password: The password of the MySQL database.
    """
    cli_utils.print_active_config()
    client = Client()
    try:
        client.migrate_pipeline_runs(
            database=database,
            database_type=database_type,
            mysql_host=mysql_host,
            mysql_port=mysql_port,
            mysql_username=mysql_username,
            mysql_password=mysql_password,
        )
    except (
        EntityExistsError,
        NotImplementedError,
        RuntimeError,
        ValueError,
    ) as err:
        cli_utils.error(str(err))
