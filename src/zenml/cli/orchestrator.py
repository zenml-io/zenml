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

import time
from typing import TYPE_CHECKING, List, Optional, Tuple, cast

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import cli
from zenml.core.repo import Repository

if TYPE_CHECKING:
    from zenml.orchestrators import BaseOrchestrator


@cli_utils.activate_integrations
def _get_orchestrator(
    orchestrator_name: Optional[str] = None,
) -> Tuple["BaseOrchestrator", str]:
    """Gets an orchestrator for a given name.

    Args:
        orchestrator_name: Name of the orchestrator to get. If `None`, the
            orchestrator of the active stack gets returned.

    Returns:
        A tuple containing the orchestrator and its name.

    Raises:
        DoesNotExistException: If no orchestrator for the name exists.
    """
    if not orchestrator_name:
        active_stack = Repository().get_active_stack()
        orchestrator_name = active_stack.orchestrator_name
        cli_utils.declare(
            f"No orchestrator name given, using `{orchestrator_name}` "
            f"from active stack."
        )

    service = Repository().get_service()
    return service.get_orchestrator(orchestrator_name), orchestrator_name


@cli.group()
def orchestrator() -> None:
    """Utilities for orchestrator"""


@orchestrator.command("get")
def get_active_orchestrator() -> None:
    """Gets the orchestrator of the active stack."""
    orchestrator_name = Repository().get_active_stack().orchestrator_name
    cli_utils.declare(f"Active orchestrator: {orchestrator_name}")


@orchestrator.command(
    "register", context_settings=dict(ignore_unknown_options=True)
)
@click.argument(
    "name",
    required=True,
    type=click.STRING,
)
@click.option(
    "--type",
    "-t",
    help="The type of the orchestrator to register.",
    required=True,
    type=click.STRING,
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@cli_utils.activate_integrations
def register_orchestrator(name: str, type: str, args: List[str]) -> None:
    """Register an orchestrator."""

    try:
        parsed_args = cli_utils.parse_unknown_options(args)
    except AssertionError as e:
        cli_utils.error(str(e))
        return

    repo: Repository = Repository()
    # TODO [ENG-186]: Remove when we rework the registry logic
    from zenml.core.component_factory import orchestrator_store_factory

    comp = orchestrator_store_factory.get_single_component(type)
    orchestrator_ = comp(repo_path=repo.path, **parsed_args)
    service = repo.get_service()
    service.register_orchestrator(name, cast("BaseOrchestrator", orchestrator_))
    cli_utils.declare(f"Orchestrator `{name}` successfully registered!")


@orchestrator.command("list")
def list_orchestrators() -> None:
    """List all available orchestrators from service."""
    repo = Repository()
    service = repo.get_service()
    if len(service.orchestrators) == 0:
        cli_utils.warning("No orchestrators registered!")
        return

    active_orchestrator = repo.get_active_stack().orchestrator_name
    cli_utils.title("Orchestrators:")
    cli_utils.print_table(
        cli_utils.format_component_list(
            service.orchestrators, active_orchestrator
        )
    )


@orchestrator.command(
    "describe",
    help="Show details about the current active orchestrator.",
)
@click.argument(
    "orchestrator_name",
    type=click.STRING,
    required=False,
)
def describe_orchestrator(orchestrator_name: Optional[str]) -> None:
    """Show details about the current active orchestrator."""
    repo = Repository()
    orchestrator_name = (
        orchestrator_name or repo.get_active_stack().orchestrator_name
    )

    orchestrators = repo.get_service().orchestrators
    if len(orchestrators) == 0:
        cli_utils.warning("No orchestrators registered!")
        return

    try:
        orchestrator_details = orchestrators[orchestrator_name]
    except KeyError:
        cli_utils.error(f"Orchestrator `{orchestrator_name}` does not exist.")
        return
    cli_utils.title("Orchestrator:")
    if repo.get_active_stack().orchestrator_name == orchestrator_name:
        cli_utils.declare("**ACTIVE**\n")
    else:
        cli_utils.declare("")
    cli_utils.declare(f"NAME: {orchestrator_name}")
    cli_utils.print_component_properties(orchestrator_details.dict())


@orchestrator.command("delete")
@click.argument("orchestrator_name", type=str)
def delete_orchestrator(orchestrator_name: str) -> None:
    """Delete an orchestrator."""
    service = Repository().get_service()
    service.delete_orchestrator(orchestrator_name)
    cli_utils.declare(f"Deleted orchestrator: `{orchestrator_name}`")


@orchestrator.command("up")
@click.argument("orchestrator_name", type=str, required=False)
def up_orchestrator(orchestrator_name: Optional[str] = None) -> None:
    """Provisions resources for the orchestrator"""
    orchestrator_, orchestrator_name = _get_orchestrator(orchestrator_name)

    cli_utils.declare(
        f"Bootstrapping resources for orchestrator: `{orchestrator_name}`. "
        f"This might take a few seconds..."
    )
    orchestrator_.up()


@orchestrator.command("down")
@click.argument("orchestrator_name", type=str, required=False)
def down_orchestrator(orchestrator_name: Optional[str] = None) -> None:
    """Tears down resources for the orchestrator"""
    orchestrator_, orchestrator_name = _get_orchestrator(orchestrator_name)

    cli_utils.declare(
        f"Tearing down resources for orchestrator: `{orchestrator_name}`."
    )
    orchestrator_.down()
    cli_utils.declare(
        f"Orchestrator: `{orchestrator_name}` resources are now torn down."
    )


@orchestrator.command("monitor")
@click.argument("orchestrator_name", type=str, required=False)
def monitor_orchestrator(orchestrator_name: Optional[str] = None) -> None:
    """Monitor a running orchestrator."""
    orchestrator_, orchestrator_name = _get_orchestrator(orchestrator_name)
    if not orchestrator_.is_running:
        cli_utils.warning(
            f"Can't monitor orchestrator '{orchestrator_name}' "
            f"because it isn't running."
        )
        return

    if not orchestrator_.log_file:
        cli_utils.warning(f"Can't monitor orchestrator '{orchestrator_name}'.")
        return

    cli_utils.declare(
        f"Monitoring orchestrator '{orchestrator_name}', press CTRL+C to stop."
    )
    try:
        with open(orchestrator_.log_file, "r") as log_file:
            # seek to the end of the file
            log_file.seek(0, 2)

            while True:
                line = log_file.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                line = line.rstrip("\n")
                click.echo(line)
    except KeyboardInterrupt:
        cli_utils.declare(
            f"Stopped monitoring orchestrator '{orchestrator_name}'."
        )
