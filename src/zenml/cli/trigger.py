#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""CLI functionality to interact with triggers."""

from typing import Any
from uuid import UUID

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.client import Client
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration
from zenml.console import console
from zenml.enums import CliCategories, SourceType, TriggerRunConcurrency
from zenml.logger import get_logger
from zenml.models import TriggerFilter
from zenml.utils.time_utils import iso8601_to_utc_naive

logger = get_logger(__name__)


# CLI groups


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def trigger() -> None:
    """Interact with triggers."""


@trigger.group()
def schedule() -> None:
    """Commands for schedule triggers."""


@trigger.group()
def platform_event() -> None:
    """Commands for platform events triggers."""


# SCHEDULE commands


@schedule.command("create", help="Create a new schedule trigger.")
@click.argument("name", type=str)
@click.option(
    "--concurrency",
    type=click.Choice(TriggerRunConcurrency.values()),
    help="Option to control the concurrency of the schedule.",
    default=TriggerRunConcurrency.SKIP.value,
)
@click.option("--active", type=bool, default=True)
@click.option("--cron-expression", type=str)
@click.option("--interval", type=int)
@click.option(
    "--run_once_start_time",
    type=bool,
    help="One-off execution time (ISO 8601 format)",
)
@click.option(
    "--start_time",
    type=str,
    help="The start time of the schedule (ISO 8601 format).",
)
@click.option(
    "--end_time",
    type=str,
    help="The end time of the schedule (ISO 8601 format).",
)
def create_schedule(
    name: str,
    active: bool,
    concurrency: str,
    cron_expression: str | None = None,
    interval: int | None = None,
    run_once_start_time: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> None:
    """Create a schedule trigger.

    Args:
        name: The name of the trigger.
        active: The active status of the trigger.
        concurrency: Option controlling the concurrency of the schedule.
        cron_expression: The cron_expression of the trigger.
        interval: The interval of the trigger.
        start_time: The start time of the trigger.
        end_time: The end time of the trigger.
        run_once_start_time: The run_once_start_time of the trigger.
    """
    options = [cron_expression, interval, run_once_start_time]

    if not any(option is not None for option in options):
        cli_utils.declare("No schedule execution option provided.")
        return

    try:
        s = Client().create_schedule_trigger(
            name=name,
            active=active,
            concurrency=TriggerRunConcurrency(concurrency),
            cron_expression=cron_expression,
            interval=interval,
            run_once_start_time=iso8601_to_utc_naive(run_once_start_time)
            if run_once_start_time
            else None,
            start_time=iso8601_to_utc_naive(start_time)
            if start_time
            else None,
            end_time=iso8601_to_utc_naive(end_time) if end_time else None,
        )
    except Exception as e:
        cli_utils.exception(e)
    else:
        cli_utils.declare(f"Created schedule '{s.id}'.")


@schedule.command("update", help="Update a schedule trigger.")
@click.argument("schedule_id", type=UUID)
@click.option("--name", type=str)
@click.option("--active", type=bool)
@click.option("--cron-expression", type=str)
@click.option("--interval", type=int)
@click.option(
    "--run_once_start_time",
    type=bool,
    help="One-off execution time (ISO 8601 format)",
)
@click.option(
    "--start_time",
    type=str,
    help="The start time of the schedule (ISO 8601 format).",
)
@click.option(
    "--end_time",
    type=str,
    help="The end time of the schedule (ISO 8601 format).",
)
def update_schedule_trigger(
    schedule_id: UUID,
    name: str | None = None,
    active: bool | None = None,
    cron_expression: str | None = None,
    interval: int | None = None,
    run_once_start_time: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> None:
    """Update a schedule trigger.

    Args:
        schedule_id: The ID of the schedule.
        name: The new name of the trigger.
        active: The new active status of the trigger.
        cron_expression: The new cron_expression of the trigger.
        interval: The new interval of the trigger.
        start_time: The new start time of the trigger.
        end_time: The new end time of the trigger.
        run_once_start_time: The new run_once_start_time of the trigger.
    """
    options = [
        name,
        active,
        cron_expression,
        interval,
        start_time,
        end_time,
        run_once_start_time,
    ]

    if not any(option is not None for option in options):
        cli_utils.declare("No schedule update requested.")
        return

    try:
        Client().update_schedule_trigger(
            trigger_id=schedule_id,
            name=name,
            active=active,
            cron_expression=cron_expression,
            interval=interval,
            run_once_start_time=iso8601_to_utc_naive(run_once_start_time)
            if run_once_start_time
            else None,
            start_time=iso8601_to_utc_naive(start_time)
            if start_time
            else None,
            end_time=iso8601_to_utc_naive(end_time) if end_time else None,
        )
    except Exception as e:
        cli_utils.exception(e)
    else:
        cli_utils.declare(f"Updated schedule '{schedule_id}'.")


@schedule.command("list", help="List available schedules.")
@cli_utils.list_options(
    TriggerFilter,
    default_columns=[
        "id",
        "name",
        "active",
        "is_archived",
        "concurrency",
    ],
)
def list_schedules(
    columns: str,
    output_format: cli_utils.OutputFormat,
    **kwargs: Any,
) -> None:
    """List all schedule triggers that fulfill the filter requirements.

    Args:
        columns: Columns to display in output.
        output_format: Format for output (table/json/yaml/csv/tsv).
        **kwargs: Keyword arguments to filter the schedules.
    """
    client = Client()
    with console.status("Listing triggers...\n"):
        schedules = client.list_schedule_triggers(**kwargs)

    cli_utils.print_page(
        schedules,
        columns,
        output_format,
        empty_message="No triggers found for the given filters.",
    )


# COMMON COMMANDS


def make_delete_command() -> click.Command:
    """Delete command factory function.

    Returns:
        A Click.command for the delete method
    """

    def delete_trigger(trigger_id: UUID, soft: bool = True) -> None:
        """Delete a trigger trigger.

        Args:
            trigger_id: The ID of the trigger.
            soft: Deletion mode.
        """
        try:
            Client().delete_trigger(trigger_id=trigger_id, soft=soft)
        except Exception as e:
            cli_utils.exception(e)
        else:
            cli_utils.declare(f"Deleted trigger '{trigger_id}'.")

    f = delete_trigger

    f = click.argument("trigger_id", type=UUID)(f)
    f = click.option(
        "--soft",
        type=bool,
        default=True,
        help="Deletion mode. Soft deletion will archive the trigger preserving historical references. "
        "Hard deletion (soft=false) will purge the trigger along with its associated references "
        "(recommended only for retention). ",
    )(f)

    return click.command(name="delete", help="Delete a trigger.")(f)


def make_attach_command() -> click.Command:
    """Attach command factory function.

    Returns:
        A Click.command for the attach method
    """

    def attach_trigger(
        trigger_id: UUID,
        snapshot_id: UUID,
        config_path: str | None = None,
        allow_replace: bool = False,
    ) -> None:
        """Attach a trigger to a snapshot.

        Args:
            trigger_id: The ID of the trigger.
            snapshot_id: The ID of the snapshot.
            config_path: The path to the config file to use.
            allow_replace: Allow replacement if attachment already exists.
        """
        try:
            Client().attach_trigger_to_snapshot(
                trigger_id=trigger_id,
                pipeline_snapshot_id=snapshot_id,
                run_configuration=PipelineRunConfiguration.from_yaml(
                    config_path
                )
                if config_path
                else None,
                allow_replace=allow_replace,
            )
        except Exception as e:
            cli_utils.exception(e)
        else:
            cli_utils.declare(
                f"Attached trigger '{trigger_id}' to snapshot '{snapshot_id}'."
            )

    f = attach_trigger

    f = click.argument("trigger_id", type=UUID)(f)
    f = click.argument("snapshot_id", type=UUID)(f)
    f = click.option(
        "--config",
        "-c",
        "config_path",
        type=click.Path(exists=True, dir_okay=False),
        required=False,
        help="Path to config file (PipelineRunConfiguration) for triggered runs.",
    )(f)
    f = click.option(
        "--allow-replace",
        type=click.BOOL,
        required=False,
        help="Allow replacement if attachment already exists.",
        is_flag=True,
    )(f)

    return click.command("attach", help="Attach trigger to snapshot")(f)


def make_detach_command() -> click.Command:
    """Detach command factory function.

    Returns:
        A Click.command for the detach method
    """

    def detach_trigger(trigger_id: UUID, snapshot_id: UUID) -> None:
        """Detach a trigger from a snapshot.

        Args:
            trigger_id: The ID of the trigger.
            snapshot_id: The ID of the snapshot.
        """
        try:
            Client().detach_trigger_from_snapshot(
                trigger_id=trigger_id,
                pipeline_snapshot_id=snapshot_id,
            )
        except Exception as e:
            cli_utils.exception(e)
        else:
            cli_utils.declare(
                f"Detached trigger '{trigger_id}' from snapshot '{snapshot_id}'."
            )

    f = detach_trigger

    f = click.argument("trigger_id", type=UUID)(f)
    f = click.argument("snapshot_id", type=UUID)(f)

    return click.command("detach", help="Detach trigger from snapshot")(f)


# PLATFORM EVENT COMMANDS


@platform_event.command()
@click.argument("source_type", type=click.Choice(SourceType.values()))
def list_supported_events(source_type: SourceType) -> None:
    """List supported target events by SourceType.

    Args:
        source_type: The source type.
    """
    from zenml.utils.trigger_utils import list_supported_events

    click.echo(
        f"Support events for {source_type}:",
    )

    for index, e in enumerate(list_supported_events(source_type=source_type)):
        click.echo(f"{index + 1}) {e}")


@platform_event.command("create", help="Create a new platform event trigger.")
@click.argument("name", type=str)
@click.argument("source_type", type=click.Choice(SourceType.values()))
@click.argument("source_id", type=UUID)
@click.option(
    "--target_events",
    type=str,
    multiple=True,
    help="Use `list-supported-events` to view supported events by source type.",
)
@click.option(
    "--concurrency",
    type=click.Choice(TriggerRunConcurrency.values()),
    help="Option to control the concurrency of the trigger.",
    default=TriggerRunConcurrency.SKIP.value,
)
@click.option("--active", type=bool, default=True)
def create_platform_event(
    name: str,
    active: bool,
    concurrency: str,
    source_type: SourceType,
    source_id: UUID,
    target_events: list[str],
) -> None:
    """Create a platform event trigger.

    Args:
        name: The name of the trigger.
        source_type: The source type of the trigger.
        source_id: The source ID of the trigger.
        target_events: The trigger target events.
        active: The active status of the trigger.
        concurrency: Option controlling the concurrency of the trigger.
    """
    if not target_events:
        cli_utils.error("You must specify at least one target event.")

    try:
        s = Client().create_platform_event_trigger(
            name=name,
            active=active,
            concurrency=TriggerRunConcurrency(concurrency),
            source_id=source_id,
            source_type=source_type,
            target_events=target_events,
        )
    except Exception as e:
        cli_utils.exception(e)
    else:
        cli_utils.declare(f"Created platform event '{s.id}'.")


@platform_event.command("update", help="Update a platform event trigger.")
@click.argument("trigger_id", type=UUID)
@click.option("--name", type=str)
@click.option("--active", type=bool)
@click.option(
    "--concurrency",
    type=click.Choice(TriggerRunConcurrency.values()),
    help="Option to control the concurrency of the trigger.",
    default=TriggerRunConcurrency.SKIP.value,
)
@click.option("--source_type", type=click.Choice(SourceType.values()))
@click.option("--source_id", type=UUID)
@click.option(
    "--target_events",
    type=str,
    multiple=True,
    help="Use `list-supported-events` to view supported events by source type.",
)
def update_platform_event_trigger(
    trigger_id: UUID,
    name: str | None = None,
    active: bool | None = None,
    concurrency: TriggerRunConcurrency | None = None,
) -> None:
    """Update a platform event trigger.

    Args:
        trigger_id: The ID of the platform event.
        name: The new name of the trigger.
        active: The new active status of the trigger.
        concurrency: Option controlling the concurrency of the trigger.

    """
    options = [
        name,
        active,
        concurrency,
    ]

    if not any(option is not None for option in options):
        cli_utils.declare("No update requested.")
        return

    try:
        Client().update_platform_event_trigger(
            trigger_id=trigger_id,
            name=name,
            active=active,
            concurrency=concurrency,
        )
    except Exception as e:
        cli_utils.exception(e)
    else:
        cli_utils.declare(f"Updated platform event '{trigger_id}'.")


@platform_event.command("list", help="List available platform event triggers.")
@cli_utils.list_options(
    TriggerFilter,
    default_columns=[
        "id",
        "name",
        "active",
        "is_archived",
        "concurrency",
    ],
)
def list_platform_events(
    columns: str,
    output_format: cli_utils.OutputFormat,
    **kwargs: Any,
) -> None:
    """List all platform event triggers that fulfill the filter requirements.

    Args:
        columns: Columns to display in output.
        output_format: Format for output (table/json/yaml/csv/tsv).
        **kwargs: Keyword arguments to filter the platform event triggers.
    """
    client = Client()
    with console.status("Listing triggers...\n"):
        events = client.list_platform_event_triggers(**kwargs)

    cli_utils.print_page(
        events,
        columns,
        output_format,
        empty_message="No triggers found for the given filters.",
    )


for group in [schedule, platform_event]:
    group.add_command(make_delete_command())
    group.add_command(make_attach_command())
    group.add_command(make_detach_command())
