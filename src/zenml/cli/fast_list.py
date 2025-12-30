"""Fast-path list commands for the Rust CLI.

This module defines minimal Click commands invoked by the Rust CLI via PyO3,
keeping list output formatting identical to the standard Python CLI.
"""

from typing import Any, List

import click

from zenml.cli import utils as cli_utils
from zenml.cli.utils import OutputFormat, is_sorted_or_filtered, list_options
from zenml.client import Client
from zenml.console import console
from zenml.models import StackFilter


@click.command(help="List all stacks that fulfill the filter requirements.")
@list_options(
    StackFilter,
    default_columns=[
        "active",
        "id",
        "name",
        "user",
        "artifact_store",
        "orchestrator",
        "deployer",
    ],
)
@click.pass_context
def list_stacks(
    ctx: click.Context,
    /,
    columns: str,
    output_format: OutputFormat,
    **kwargs: Any,
) -> None:
    """List all stacks that fulfill the filter requirements.

    Args:
        ctx: The Click context.
        columns: Columns to display in output.
        output_format: Format for output (table/json/yaml/csv/tsv).
        **kwargs: Keyword arguments to filter the stacks.
    """
    client = Client()
    with console.status("Listing stacks...\n"):
        stacks = client.list_stacks(**kwargs)

    show_active = not is_sorted_or_filtered(ctx)
    if show_active and stacks.items:
        active_stack_id = client.active_stack_model.id
        if active_stack_id not in {s.id for s in stacks.items}:
            stacks.items.insert(0, client.active_stack_model)
        stacks.items.sort(key=lambda s: s.id != active_stack_id)
    else:
        active_stack_id = None

    cli_utils.print_page(
        stacks,
        columns,
        output_format,
        empty_message="No stacks found for the given filters.",
        row_generator=cli_utils.generate_stack_row,
        active_id=active_stack_id,
    )


def run_stack_list(argv: List[str]) -> int:
    """Run the fast-path stack list command invoked by the Rust CLI.

    Args:
        argv: Command-line arguments following `stack list`.

    Returns:
        Exit code for the command execution.
    """
    try:
        list_stacks.main(
            args=argv,
            prog_name="zenml stack list",
            standalone_mode=False,
        )
    except click.exceptions.Exit as exc:
        return int(exc.exit_code or 0)
    return 0