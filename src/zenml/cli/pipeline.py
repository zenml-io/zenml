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

import json
import os
from typing import Any, Dict, Optional, Union

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import list_options
from zenml.client import Client
from zenml.console import console
from zenml.enums import CliCategories
from zenml.logger import get_logger
from zenml.models import (
    PipelineBuildBase,
    PipelineBuildFilter,
    PipelineFilter,
    PipelineRunFilter,
    ScheduleFilter,
)
from zenml.pipelines.pipeline_definition import Pipeline
from zenml.utils import source_utils, uuid_utils
from zenml.utils.yaml_utils import write_yaml

logger = get_logger(__name__)


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def pipeline() -> None:
    """Interact with pipelines, runs and schedules."""


@pipeline.command(
    "register",
    help="Register a pipeline instance. The SOURCE argument needs to be an "
    "importable source path resolving to a ZenML pipeline instance, e.g. "
    "`my_module.my_pipeline_instance`.",
)
@click.argument("source")
@click.option(
    "--parameters",
    "-p",
    "parameters_path",
    type=click.Path(exists=True, dir_okay=False),
    required=False,
    help="Path to JSON file containing parameters for the pipeline function.",
)
def register_pipeline(
    source: str, parameters_path: Optional[str] = None
) -> None:
    """Register a pipeline.

    Args:
        source: Importable source resolving to a pipeline instance.
        parameters_path: Path to pipeline parameters file.
    """
    if "." not in source:
        cli_utils.error(
            f"The given source path `{source}` is invalid. Make sure it looks "
            "like `some.module.name_of_pipeline_instance_variable` and "
            "resolves to a pipeline object."
        )

    if not Client().root:
        cli_utils.warning(
            "You're running the `zenml pipeline register` command without a "
            "ZenML repository. Your current working directory will be used "
            "as the source root relative to which the `source` argument is "
            "expected. To silence this warning, run `zenml init` at your "
            "source code root."
        )

    try:
        pipeline_instance = source_utils.load(source)
    except ModuleNotFoundError as e:
        source_root = source_utils.get_source_root()
        cli_utils.error(
            f"Unable to import module `{e.name}`. Make sure the source path is "
            f"relative to your source root `{source_root}`."
        )
    except AttributeError as e:
        cli_utils.error("Unable to load attribute from module: " + str(e))

    if not isinstance(pipeline_instance, Pipeline):
        cli_utils.error(
            f"The given source path `{source}` does not resolve to a pipeline "
            "object."
        )

    parameters: Dict[str, Any] = {}
    if parameters_path:
        with open(parameters_path, "r") as f:
            parameters = json.load(f)

    try:
        pipeline_instance.prepare(**parameters)
    except ValueError:
        cli_utils.error(
            "Pipeline preparation failed. This is most likely due to your "
            "pipeline entrypoint function requiring arguments that were not "
            "provided. Please provide a JSON file with the parameters for "
            f"your pipeline like this: `zenml pipeline register {source} "
            "--parameters=<PATH_TO_JSON>`."
        )

    pipeline_instance.register()


@pipeline.command(
    "build",
    help="Build Docker images for a pipeline. The SOURCE argument needs to be "
    " an importable source path resolving to a ZenML pipeline instance, e.g. "
    "`my_module.my_pipeline_instance`.",
)
@click.argument("source")
@click.option(
    "--config",
    "-c",
    "config_path",
    type=click.Path(exists=True, dir_okay=False),
    required=False,
    help="Path to configuration file for the build.",
)
@click.option(
    "--stack",
    "-s",
    "stack_name_or_id",
    type=str,
    required=False,
    help="Name or ID of the stack to use for the build.",
)
@click.option(
    "--output",
    "-o",
    "output_path",
    type=click.Path(exists=False, dir_okay=False),
    required=False,
    help="Output path for the build information.",
)
def build_pipeline(
    source: str,
    config_path: Optional[str] = None,
    stack_name_or_id: Optional[str] = None,
    output_path: Optional[str] = None,
) -> None:
    """Build Docker images for a pipeline.

    Args:
        source: Importable source resolving to a pipeline instance.
        config_path: Path to pipeline configuration file.
        stack_name_or_id: Name or ID of the stack for which the images should
            be built.
        output_path: Optional file path to write the output to.
    """
    if not Client().root:
        cli_utils.warning(
            "You're running the `zenml pipeline build` command without a "
            "ZenML repository. Your current working directory will be used "
            "as the source root relative to which the registered step classes "
            "will be resolved. To silence this warning, run `zenml init` at "
            "your source code root."
        )

    try:
        pipeline_instance = source_utils.load(source)
    except ModuleNotFoundError as e:
        source_root = source_utils.get_source_root()
        cli_utils.error(
            f"Unable to import module `{e.name}`. Make sure the source path is "
            f"relative to your source root `{source_root}`."
        )
    except AttributeError as e:
        cli_utils.error("Unable to load attribute from module: " + str(e))

    if not isinstance(pipeline_instance, Pipeline):
        cli_utils.error(
            f"The given source path `{source}` does not resolve to a pipeline "
            "object."
        )

    with cli_utils.temporary_active_stack(stack_name_or_id=stack_name_or_id):
        pipeline_instance = pipeline_instance.with_options(
            config_path=config_path
        )
        build = pipeline_instance.build()

    if build:
        cli_utils.declare(f"Created pipeline build `{build.id}`.")

        if output_path:
            cli_utils.declare(
                f"Writing pipeline build output to `{output_path}`."
            )
            write_yaml(output_path, build.to_yaml())
    else:
        cli_utils.declare("No docker builds required.")


@pipeline.command(
    "run",
    help="Run a pipeline. The SOURCE argument needs to be an "
    "importable source path resolving to a ZenML pipeline instance, e.g. "
    "`my_module.my_pipeline_instance`.",
)
@click.argument("source")
@click.option(
    "--config",
    "-c",
    "config_path",
    type=click.Path(exists=True, dir_okay=False),
    required=False,
    help="Path to configuration file for the run.",
)
@click.option(
    "--stack",
    "-s",
    "stack_name_or_id",
    type=str,
    required=False,
    help="Name or ID of the stack to run on.",
)
@click.option(
    "--build",
    "-b",
    "build_path_or_id",
    type=str,
    required=False,
    help="ID or path of the build to use.",
)
@click.option(
    "--prevent-build-reuse",
    is_flag=True,
    default=False,
    required=False,
    help="Prevent automatic build reusing.",
)
def run_pipeline(
    source: str,
    config_path: Optional[str] = None,
    stack_name_or_id: Optional[str] = None,
    build_path_or_id: Optional[str] = None,
    prevent_build_reuse: bool = False,
) -> None:
    """Run a pipeline.

    Args:
        source: Importable source resolving to a pipeline instance.
        config_path: Path to pipeline configuration file.
        stack_name_or_id: Name or ID of the stack on which the pipeline should
            run.
        build_path_or_id: ID of file path of the build to use for the pipeline
            run.
        prevent_build_reuse: If True, prevents automatic reusing of previous
            builds.
    """
    if not Client().root:
        cli_utils.warning(
            "You're running the `zenml pipeline run` command without a "
            "ZenML repository. Your current working directory will be used "
            "as the source root relative to which the registered step classes "
            "will be resolved. To silence this warning, run `zenml init` at "
            "your source code root."
        )

    try:
        pipeline_instance = source_utils.load(source)
    except ModuleNotFoundError as e:
        source_root = source_utils.get_source_root()
        cli_utils.error(
            f"Unable to import module `{e.name}`. Make sure the source path is "
            f"relative to your source root `{source_root}`."
        )
    except AttributeError as e:
        cli_utils.error("Unable to load attribute from module: " + str(e))

    if not isinstance(pipeline_instance, Pipeline):
        cli_utils.error(
            f"The given source path `{source}` does not resolve to a pipeline "
            "object."
        )

    build: Union[str, PipelineBuildBase, None] = None
    if build_path_or_id:
        if uuid_utils.is_valid_uuid(build_path_or_id):
            build = build_path_or_id
        elif os.path.exists(build_path_or_id):
            build = PipelineBuildBase.from_yaml(build_path_or_id)
        else:
            cli_utils.error(
                f"The specified build {build_path_or_id} is not a valid UUID "
                "or file path."
            )

    with cli_utils.temporary_active_stack(stack_name_or_id=stack_name_or_id):
        pipeline_instance = pipeline_instance.with_options(
            config_path=config_path,
            build=build,
            prevent_build_reuse=prevent_build_reuse,
        )
        pipeline_instance()


@pipeline.command(
    "create-run-template",
    help="Create a run template for a pipeline. The SOURCE argument needs to "
    "be an importable source path resolving to a ZenML pipeline instance, e.g. "
    "`my_module.my_pipeline_instance`.",
)
@click.argument("source")
@click.option(
    "--name",
    "-n",
    type=str,
    required=True,
    help="Name for the template",
)
@click.option(
    "--config",
    "-c",
    "config_path",
    type=click.Path(exists=True, dir_okay=False),
    required=False,
    help="Path to configuration file for the build.",
)
@click.option(
    "--stack",
    "-s",
    "stack_name_or_id",
    type=str,
    required=False,
    help="Name or ID of the stack to use for the build.",
)
def create_run_template(
    source: str,
    name: str,
    config_path: Optional[str] = None,
    stack_name_or_id: Optional[str] = None,
) -> None:
    """Create a run template for a pipeline.

    Args:
        source: Importable source resolving to a pipeline instance.
        name: Name of the run template.
        config_path: Path to pipeline configuration file.
        stack_name_or_id: Name or ID of the stack for which the template should
            be created.
    """
    if not Client().root:
        cli_utils.warning(
            "You're running the `zenml pipeline create-run-template` command "
            "without a ZenML repository. Your current working directory will "
            "be used as the source root relative to which the registered step "
            "classes will be resolved. To silence this warning, run `zenml "
            "init` at your source code root."
        )

    try:
        pipeline_instance = source_utils.load(source)
    except ModuleNotFoundError as e:
        source_root = source_utils.get_source_root()
        cli_utils.error(
            f"Unable to import module `{e.name}`. Make sure the source path is "
            f"relative to your source root `{source_root}`."
        )
    except AttributeError as e:
        cli_utils.error("Unable to load attribute from module: " + str(e))

    if not isinstance(pipeline_instance, Pipeline):
        cli_utils.error(
            f"The given source path `{source}` does not resolve to a pipeline "
            "object."
        )

    with cli_utils.temporary_active_stack(stack_name_or_id=stack_name_or_id):
        pipeline_instance = pipeline_instance.with_options(
            config_path=config_path
        )
        template = pipeline_instance.create_run_template(name=name)

    cli_utils.declare(f"Created run template `{template.id}`.")


@pipeline.command("list", help="List all registered pipelines.")
@list_options(PipelineFilter)
def list_pipelines(**kwargs: Any) -> None:
    """List all registered pipelines.

    Args:
        **kwargs: Keyword arguments to filter pipelines.
    """
    client = Client()
    with console.status("Listing pipelines...\n"):
        pipelines = client.list_pipelines(**kwargs)

        if not pipelines.items:
            cli_utils.declare("No pipelines found for this filter.")
            return

        cli_utils.print_pydantic_models(
            pipelines,
            exclude_columns=["id", "created", "updated", "user", "workspace"],
        )


@pipeline.command("delete")
@click.argument("pipeline_name_or_id", type=str, required=True)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Don't ask for confirmation.",
)
def delete_pipeline(
    pipeline_name_or_id: str,
    yes: bool = False,
) -> None:
    """Delete a pipeline.

    Args:
        pipeline_name_or_id: The name or ID of the pipeline to delete.
        yes: If set, don't ask for confirmation.
    """
    if not yes:
        confirmation = cli_utils.confirmation(
            f"Are you sure you want to delete pipeline "
            f"`{pipeline_name_or_id}`? This will change all "
            "existing runs of this pipeline to become unlisted."
        )
        if not confirmation:
            cli_utils.declare("Pipeline deletion canceled.")
            return

    try:
        Client().delete_pipeline(
            name_id_or_prefix=pipeline_name_or_id,
        )
    except KeyError as e:
        cli_utils.error(str(e))
    else:
        cli_utils.declare(f"Deleted pipeline `{pipeline_name_or_id}`.")


@pipeline.group()
def schedule() -> None:
    """Commands for pipeline run schedules."""


@schedule.command("list", help="List all pipeline schedules.")
@list_options(ScheduleFilter)
def list_schedules(**kwargs: Any) -> None:
    """List all pipeline schedules.

    Args:
        **kwargs: Keyword arguments to filter schedules.
    """
    client = Client()

    schedules = client.list_schedules(**kwargs)

    if not schedules:
        cli_utils.declare("No schedules found for this filter.")
        return

    cli_utils.print_pydantic_models(
        schedules,
        exclude_columns=["id", "created", "updated", "user", "workspace"],
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
@list_options(PipelineRunFilter)
def list_pipeline_runs(**kwargs: Any) -> None:
    """List all registered pipeline runs for the filter.

    Args:
        **kwargs: Keyword arguments to filter pipeline runs.
    """
    client = Client()
    try:
        with console.status("Listing pipeline runs...\n"):
            pipeline_runs = client.list_pipeline_runs(**kwargs)
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


@runs.command("refresh")
@click.argument("run_name_or_id", type=str, required=True)
def refresh_pipeline_run(run_name_or_id: str) -> None:
    """Refresh the status of a pipeline run.

    Args:
        run_name_or_id: The name or ID of the pipeline run to refresh.
    """
    try:
        # Fetch and update the run
        run = Client().get_pipeline_run(name_id_or_prefix=run_name_or_id)
        run.refresh_run_status()

    except KeyError as e:
        cli_utils.error(str(e))
    else:
        cli_utils.declare(
            f"Refreshed the status of pipeline run '{run.name}'."
        )


@pipeline.group()
def builds() -> None:
    """Commands for pipeline builds."""


@builds.command("list", help="List all pipeline builds.")
@list_options(PipelineBuildFilter)
def list_pipeline_builds(**kwargs: Any) -> None:
    """List all pipeline builds for the filter.

    Args:
        **kwargs: Keyword arguments to filter pipeline builds.
    """
    client = Client()
    try:
        with console.status("Listing pipeline builds...\n"):
            pipeline_builds = client.list_builds(hydrate=True, **kwargs)
    except KeyError as err:
        cli_utils.error(str(err))
    else:
        if not pipeline_builds.items:
            cli_utils.declare("No pipeline builds found for this filter.")
            return

        cli_utils.print_pydantic_models(
            pipeline_builds,
            exclude_columns=[
                "created",
                "updated",
                "user",
                "workspace",
                "images",
                "stack_checksum",
            ],
        )


@builds.command("delete")
@click.argument("build_id", type=str, required=True)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Don't ask for confirmation.",
)
def delete_pipeline_build(
    build_id: str,
    yes: bool = False,
) -> None:
    """Delete a pipeline build.

    Args:
        build_id: The ID of the pipeline build to delete.
        yes: If set, don't ask for confirmation.
    """
    if not yes:
        confirmation = cli_utils.confirmation(
            f"Are you sure you want to delete pipeline build `{build_id}`?"
        )
        if not confirmation:
            cli_utils.declare("Pipeline build deletion canceled.")
            return

    try:
        Client().delete_build(build_id)
    except KeyError as e:
        cli_utils.error(str(e))
    else:
        cli_utils.declare(f"Deleted pipeline build '{build_id}'.")
