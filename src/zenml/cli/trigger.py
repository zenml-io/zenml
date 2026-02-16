from typing import Any
from uuid import UUID

import click

from zenml.cli import OutputFormat, list_options
from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.client import Client
from zenml.console import console
from zenml.enums import CliCategories
from zenml.logger import get_logger
from zenml.models import TriggerFilter

logger = get_logger(__name__)


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def trigger() -> None:
    """Interact with triggers."""


@trigger.group()
def schedule() -> None:
    """Commands for schedules triggers."""


@schedule.command("create", help="Create a new schedule trigger.")
@click.argument("schedule_id", type=UUID)
@click.argument("name", type=str)
@click.argument("active", type=bool)
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
    schedule_id: UUID,
    name: str,
    active: bool,
    cron_expression: str | None = None,
    interval: int | None = None,
    run_once_start_time: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> None:
    """Create a schedule trigger.

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

    options = [cron_expression, interval, run_once_start_time]

    if not any(option is not None for option in options):
        cli_utils.declare("No schedule execution option provided.")
        return

    try:
        Client().update_schedule_trigger(
            trigger_id=schedule_id,
            name=name,
            active=active,
            cron_expression=cron_expression,
            interval=interval,
            run_once_start_time=run_once_start_time,
            start_time=start_time,
            end_time=end_time,
        )
    except Exception as e:
        cli_utils.exception(e)
    else:
        cli_utils.declare(f"Updated schedule '{schedule_id}'.")


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
            run_once_start_time=run_once_start_time,
            start_time=start_time,
            end_time=end_time,
        )
    except Exception as e:
        cli_utils.exception(e)
    else:
        cli_utils.declare(f"Updated schedule '{schedule_id}'.")


@schedule.command("delete", help="Delete a schedule trigger.")
@click.argument("schedule_id", type=UUID)
def delete_schedule_trigger(schedule_id: UUID) -> None:
    try:
        Client().delete_trigger(trigger_id=schedule_id)
    except Exception as e:
        cli_utils.exception(e)
    else:
        cli_utils.declare(f"Deleted schedule '{schedule_id}'.")


@schedule.command("attach", help="Attach schedule to snapshot")
@click.argument("schedule_id", type=UUID)
@click.argument("snapshot_id", type=UUID)
def attach_schedule_trigger(schedule_id: UUID, snapshot_id: UUID) -> None:

    try:
        Client().attach_trigger_to_snapshot(
            trigger_id=schedule_id,
            pipeline_snapshot_id=snapshot_id,
        )
    except Exception as e:
        cli_utils.exception(e)
    else:
        cli_utils.declare(f"Attached schedule '{schedule_id}' to snapshot '{snapshot_id}'.")


@schedule.command("attach", help="Detach schedule from snapshot")
@click.argument("schedule_id", type=UUID)
@click.argument("snapshot_id", type=UUID)
def detach_schedule_trigger(schedule_id: UUID, snapshot_id: UUID) -> None:

    try:
        Client().detach_trigger_from_snapshot(
            trigger_id=schedule_id,
            pipeline_snapshot_id=snapshot_id,
        )
    except Exception as e:
        cli_utils.exception(e)
    else:
        cli_utils.declare(f"Detached schedule '{schedule_id}' from snapshot '{snapshot_id}'.")


@schedule.command("list", help="List available schedules.")
@list_options(
    TriggerFilter,
    default_columns=[
        "id",
        "name",
        "active",
        "is_archived",
    ],
)
def list_schedules(
    columns: str,
    output_format: OutputFormat,
    **kwargs: Any,
):
    """List all schedule triggers that fulfill the filter requirements.

    Args:
        columns: Columns to display in output.
        output_format: Format for output (table/json/yaml/csv/tsv).
        **kwargs: Keyword arguments to filter the schedules.
    """
    client = Client()
    with console.status("Listing schedules...\n"):
        schedules = client.list_schedule_triggers(**kwargs)

    cli_utils.print_page(
        schedules,
        columns,
        output_format,
        empty_message="No schedule triggers found for the given filters.",
    )
