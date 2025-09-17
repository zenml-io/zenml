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
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

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
    PipelineBuildResponse,
    PipelineFilter,
    PipelineResponse,
    PipelineRunFilter,
    PipelineRunResponse,
    PipelineSnapshotFilter,
    ScheduleFilter,
    ScheduleResponse,
)
from zenml.pipelines.pipeline_definition import Pipeline
from zenml.utils import run_utils, source_utils, uuid_utils
from zenml.utils.yaml_utils import write_yaml

logger = get_logger(__name__)


def _generate_pipeline_data(pipeline: PipelineResponse) -> Dict[str, Any]:
    """Generate additional data for pipeline display.

    Args:
        pipeline: The pipeline response.

    Returns:
        The additional data for the pipeline.
    """
    return {
        "latest_run_status": pipeline.latest_run_status or "",
        "latest_run_id": pipeline.latest_run_id or "",
        "tags": ", ".join(tag.name for tag in pipeline.tags)
        if pipeline.tags
        else "",
        "created": pipeline.created,
    }


def _generate_schedule_data(schedule: ScheduleResponse) -> Dict[str, Any]:
    """Generate additional data for schedule display.

    Args:
        schedule: The schedule response.

    Returns:
        The additional data for the schedule.
    """
    return {
        "active": schedule.active,
        "cron_expression": schedule.cron_expression,
    }


def _generate_pipeline_run_data(
    pipeline_run: PipelineRunResponse,
) -> Dict[str, Any]:
    """Generate additional data for pipeline run display.

    Args:
        pipeline_run: The pipeline run response.

    Returns:
        The additional data for the pipeline run.
    """
    return {
        "pipeline": pipeline_run.pipeline.name
        if pipeline_run.pipeline
        else "",
        "stack": pipeline_run.stack.name if pipeline_run.stack else "",
    }


def _generate_pipeline_build_data(
    pipeline_build: PipelineBuildResponse,
) -> Dict[str, Any]:
    """Generate additional data for pipeline build display.

    Args:
        pipeline_build: The pipeline build response.

    Returns:
        The additional data for the pipeline build.
    """
    return {
        "pipeline_name": pipeline_build.pipeline.name
        if pipeline_build.pipeline
        else "",
        "zenml_version": pipeline_build.zenml_version,
        "stack_name": pipeline_build.stack.name
        if pipeline_build.stack
        else "",
    }


def _import_pipeline(source: str) -> Pipeline:
    """Import a pipeline.

    Args:
        source: The pipeline source.

    Returns:
        The pipeline.
    """
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

    return pipeline_instance


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

    pipeline_instance = _import_pipeline(source=source)

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

    with cli_utils.temporary_active_stack(stack_name_or_id=stack_name_or_id):
        pipeline_instance = _import_pipeline(source=source)

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

    with cli_utils.temporary_active_stack(stack_name_or_id=stack_name_or_id):
        pipeline_instance = _import_pipeline(source=source)

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
    """DEPRECATED: Create a run template for a pipeline.

    Args:
        source: Importable source resolving to a pipeline instance.
        name: Name of the run template.
        config_path: Path to pipeline configuration file.
        stack_name_or_id: Name or ID of the stack for which the template should
            be created.
    """
    cli_utils.warning(
        "The `zenml pipeline create-run-template` command is deprecated and "
        "will be removed in a future version. Please use `zenml pipeline "
        "snapshot create` instead."
    )
    if not Client().root:
        cli_utils.warning(
            "You're running the `zenml pipeline create-run-template` command "
            "without a ZenML repository. Your current working directory will "
            "be used as the source root relative to which the registered step "
            "classes will be resolved. To silence this warning, run `zenml "
            "init` at your source code root."
        )

    with cli_utils.temporary_active_stack(stack_name_or_id=stack_name_or_id):
        pipeline_instance = _import_pipeline(source=source)

        pipeline_instance = pipeline_instance.with_options(
            config_path=config_path
        )
        template = pipeline_instance.create_run_template(name=name)

    cli_utils.declare(f"Created run template `{template.id}`.")


@list_options(
    PipelineFilter,
    default_columns=[
        "id",
        "name",
        "latest_run_status",
        "latest_run_id",
        "tags",
        "created",
    ],
)
@pipeline.command("list", help="List all registered pipelines.")
def list_pipelines(output_format: str, columns: str, **kwargs: Any) -> None:
    """List all registered pipelines.

    Args:
        output_format: Output format (table, json, yaml, tsv, csv).
        columns: Comma-separated list of columns to display.
        kwargs: Keyword arguments to filter pipelines.
    """
    with console.status("Listing pipelines..."):
        pipelines = Client().list_pipelines(**kwargs)

        pipeline_list = []
        for pipeline in pipelines.items:
            pipeline_data = cli_utils.prepare_response_data(pipeline)
            pipeline_data.update(_generate_pipeline_data(pipeline))
            pipeline_list.append(pipeline_data)

    cli_utils.handle_output(
        pipeline_list,
        pagination_info=pipelines.pagination_info,
        columns=columns,
        output_format=output_format,
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
            f"`{pipeline_name_or_id}`? This will delete all "
            "runs and snapshots of this pipeline."
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


@list_options(
    ScheduleFilter,
    default_columns=["name", "active", "cron_expression", "user", "created"],
)
@schedule.command("list", help="List all pipeline schedules.")
def list_schedules(output_format: str, columns: str, **kwargs: Any) -> None:
    """List all pipeline schedules.

    Args:
        output_format: Output format (table, json, yaml, tsv, csv).
        columns: Comma-separated list of columns to display.
        kwargs: Keyword arguments to filter schedules.
    """
    with console.status("Listing schedules..."):
        schedules = Client().list_schedules(**kwargs)

        schedule_list = []
        for schedule in schedules.items:
            schedule_data = cli_utils.prepare_response_data(schedule)
            schedule_data.update(_generate_schedule_data(schedule))
            schedule_list.append(schedule_data)

    cli_utils.handle_output(
        schedule_list,
        pagination_info=schedules.pagination_info,
        columns=columns,
        output_format=output_format,
    )


@schedule.command("update", help="Update a pipeline schedule.")
@click.argument("schedule_name_or_id", type=str, required=True)
@click.option(
    "--cron-expression",
    "-c",
    type=str,
    required=False,
    help="The cron expression to update the schedule with.",
)
def update_schedule(
    schedule_name_or_id: str, cron_expression: Optional[str] = None
) -> None:
    """Update a pipeline schedule.

    Args:
        schedule_name_or_id: The name or ID of the schedule to update.
        cron_expression: The cron expression to update the schedule with.
    """
    if not cron_expression:
        cli_utils.declare("No schedule update requested.")
        return

    try:
        Client().update_schedule(
            name_id_or_prefix=schedule_name_or_id,
            cron_expression=cron_expression,
        )
    except Exception as e:
        cli_utils.error(str(e))
    else:
        cli_utils.declare(f"Updated schedule '{schedule_name_or_id}'.")


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


@list_options(
    PipelineRunFilter,
    default_columns=[
        "id",
        "name",
        "status",
        "pipeline",
        "user",
        "stack",
        "created",
    ],
)
@runs.command("list", help="List all registered pipeline runs.")
def list_pipeline_runs(
    output_format: str, columns: str, **kwargs: Any
) -> None:
    """List all registered pipeline runs for the filter.

    Args:
        output_format: Output format (table, json, yaml, tsv, csv).
        columns: Comma-separated list of columns to display.
        kwargs: Keyword arguments to filter pipeline runs.
    """
    with console.status("Listing pipeline runs..."):
        pipeline_runs = Client().list_pipeline_runs(**kwargs)

        pipeline_run_list = []
        for pipeline_run in pipeline_runs.items:
            pipeline_run_data = cli_utils.prepare_response_data(pipeline_run)
            pipeline_run_data.update(_generate_pipeline_run_data(pipeline_run))
            pipeline_run_list.append(pipeline_run_data)

    cli_utils.handle_output(
        pipeline_run_list,
        pagination_info=pipeline_runs.pagination_info,
        columns=columns,
        output_format=output_format,
    )


@runs.command("stop")
@click.argument("run_name_or_id", type=str, required=True)
@click.option(
    "--graceful",
    "-g",
    is_flag=True,
    default=False,
    help="Use graceful shutdown (default is False).",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Don't ask for confirmation.",
)
def stop_pipeline_run(
    run_name_or_id: str,
    graceful: bool = False,
    yes: bool = False,
) -> None:
    """Stop a running pipeline.

    Args:
        run_name_or_id: The name or ID of the pipeline run to stop.
        graceful: If True, uses graceful shutdown. If False, forces immediate termination.
        yes: If set, don't ask for confirmation.
    """
    # Ask for confirmation to stop run.
    if not yes:
        action = "gracefully stop" if graceful else "force stop"
        confirmation = cli_utils.confirmation(
            f"Are you sure you want to {action} pipeline run `{run_name_or_id}`?"
        )
        if not confirmation:
            cli_utils.declare("Not stopping the pipeline run.")
            return

    # Stop run.
    try:
        run = Client().get_pipeline_run(name_id_or_prefix=run_name_or_id)
        run_utils.stop_run(run=run, graceful=graceful)
        action = "Gracefully stopped" if graceful else "Force stopped"
        cli_utils.declare(f"{action} pipeline run '{run.name}'.")
    except NotImplementedError:
        cli_utils.error(
            "The orchestrator used for this pipeline run does not support "
            f"{'gracefully' if graceful else 'forcefully'} stopping runs."
        )
    except Exception as e:
        cli_utils.error(f"Failed to stop pipeline run: {e}")


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
@click.option(
    "--include-steps",
    is_flag=True,
    default=False,
    help="Also refresh the status of individual steps.",
)
def refresh_pipeline_run(
    run_name_or_id: str, include_steps: bool = False
) -> None:
    """Refresh the status of a pipeline run.

    Args:
        run_name_or_id: The name or ID of the pipeline run to refresh.
        include_steps: If True, also refresh the status of individual steps.
    """
    try:
        # Fetch and update the run
        run = Client().get_pipeline_run(name_id_or_prefix=run_name_or_id)
        run_utils.refresh_run_status(
            run=run, include_step_updates=include_steps
        )

    except KeyError as e:
        cli_utils.error(str(e))
    else:
        cli_utils.declare(
            f"Refreshed the status of pipeline run '{run.name}'."
        )


@pipeline.group()
def builds() -> None:
    """Commands for pipeline builds."""


@list_options(
    PipelineBuildFilter,
    default_columns=[
        "id",
        "pipeline_name",
        "zenml_version",
        "stack_name",
        "created",
    ],
)
@builds.command("list", help="List all pipeline builds.")
def list_pipeline_builds(
    output_format: str, columns: str, **kwargs: Any
) -> None:
    """List all pipeline builds for the filter.

    Args:
        output_format: Output format (table, json, yaml, tsv, csv).
        columns: Comma-separated list of columns to display.
        kwargs: Keyword arguments to filter pipeline builds.
    """
    with console.status("Listing pipeline builds..."):
        pipeline_builds = Client().list_builds(hydrate=True, **kwargs)

        pipeline_build_list = []
        for pipeline_build in pipeline_builds.items:
            pipeline_build_data = cli_utils.prepare_response_data(
                pipeline_build
            )
            pipeline_build_data.update(
                _generate_pipeline_build_data(pipeline_build)
            )
            pipeline_build_list.append(pipeline_build_data)

    cli_utils.handle_output(
        pipeline_build_list,
        pagination_info=pipeline_builds.pagination_info,
        columns=columns,
        output_format=output_format,
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


@pipeline.group()
def snapshot() -> None:
    """Commands for pipeline snapshots."""


@snapshot.command("create", help="Create a snapshot of a pipeline.")
@click.argument("source")
@click.option(
    "--name",
    "-n",
    type=str,
    required=True,
    help="The name of the snapshot.",
)
@click.option(
    "--description",
    "-d",
    type=str,
    required=False,
    help="The description of the snapshot.",
)
@click.option(
    "--replace",
    "-r",
    is_flag=True,
    required=False,
    help="Whether to replace the existing snapshot with the same name.",
)
@click.option(
    "--tags",
    "-t",
    type=str,
    required=False,
    multiple=True,
    help="The tags to add to the snapshot.",
)
@click.option(
    "--config",
    "-c",
    "config_path",
    type=click.Path(exists=True, dir_okay=False),
    required=False,
    help="Path to configuration file for the snapshot.",
)
@click.option(
    "--stack",
    "-s",
    "stack_name_or_id",
    type=str,
    required=False,
    help="Name or ID of the stack to use for the snapshot.",
)
def create_pipeline_snapshot(
    source: str,
    name: str,
    description: Optional[str] = None,
    replace: Optional[bool] = None,
    tags: Optional[List[str]] = None,
    config_path: Optional[str] = None,
    stack_name_or_id: Optional[str] = None,
) -> None:
    """Create a snapshot of a pipeline.

    Args:
        source: Importable source resolving to a pipeline instance.
        name: Name of the snapshot.
        description: Description of the snapshot.
        tags: Tags to add to the snapshot.
        replace: Whether to replace the existing snapshot with the same name.
        config_path: Path to configuration file for the snapshot.
        stack_name_or_id: Name or ID of the stack for which the snapshot
            should be created.
    """
    if not Client().root:
        cli_utils.warning(
            "You're running the `zenml pipeline snapshot create` command "
            "without a ZenML repository. Your current working directory will "
            "be used as the source root relative to which the registered step "
            "classes will be resolved. To silence this warning, run `zenml "
            "init` at your source code root."
        )

    with cli_utils.temporary_active_stack(stack_name_or_id=stack_name_or_id):
        pipeline_instance = _import_pipeline(source=source)

        pipeline_instance = pipeline_instance.with_options(
            config_path=config_path
        )
        snapshot = pipeline_instance.create_snapshot(
            name=name,
            description=description,
            replace=replace,
            tags=tags,
        )

    cli_utils.declare(
        f"Created pipeline snapshot `{snapshot.id}`. You can now trigger "
        f"this snapshot from the dashboard or by calling `zenml pipeline "
        f"snapshot trigger {snapshot.id}`"
    )


@snapshot.command("trigger", help="Trigger a snapshot.")
@click.argument("snapshot_id")
@click.option(
    "--config",
    "-c",
    "config_path",
    type=click.Path(exists=True, dir_okay=False),
    required=False,
    help="Path to configuration file for the run.",
)
def trigger_snapshot(
    snapshot_id: str,
    config_path: Optional[str] = None,
) -> None:
    """Trigger a snapshot.

    Args:
        snapshot_id: The ID of the snapshot to trigger.
        config_path: Path to configuration file for the run.
    """
    if not uuid_utils.is_valid_uuid(snapshot_id):
        cli_utils.error(f"Invalid snapshot ID: {snapshot_id}")

    run = Client().trigger_pipeline(
        snapshot_id=UUID(snapshot_id),
        config_path=config_path,
    )
    cli_utils.declare(f"Triggered snapshot run `{run.id}`.")


@snapshot.command("list", help="List pipeline snapshots.")
@list_options(PipelineSnapshotFilter)
def list_pipeline_snapshots(**kwargs: Any) -> None:
    """List all pipeline snapshots for the filter.

    Args:
        **kwargs: Keyword arguments to filter pipeline snapshots.
    """
    client = Client()
    try:
        with console.status("Listing pipeline snapshots...\n"):
            pipeline_snapshots = client.list_snapshots(hydrate=True, **kwargs)
    except KeyError as err:
        cli_utils.error(str(err))
    else:
        if not pipeline_snapshots.items:
            cli_utils.declare("No pipeline snapshots found for this filter.")
            return

        cli_utils.print_pydantic_models(
            pipeline_snapshots,
            exclude_columns=[
                "created",
                "updated",
                "user_id",
                "project_id",
                "pipeline_configuration",
                "step_configurations",
                "client_environment",
                "client_version",
                "server_version",
                "run_name_template",
                "pipeline_version_hash",
                "pipeline_spec",
                "pipeline",
                "stack",
                "build",
                "schedule",
                "code_reference",
                "config_schema",
                "config_template",
                "source_snapshot_id",
                "template_id",
            ],
        )
