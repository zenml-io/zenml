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
"""ZenML test deployment CLI."""

import sys
from typing import List

import click

from tests.harness.cli.cli import cli
from tests.harness.harness import TestHarness


@cli.group()
def deployment() -> None:
    """View and manage test deployments."""


@deployment.command("list", help="List all configured deployments.")
def list_deployments() -> None:
    """List configured deployments."""
    from zenml.cli.utils import print_table

    harness = TestHarness()
    deployments = []
    for deployment in harness.deployments.values():
        deployment_cfg = deployment.config
        values = dict(
            name=deployment_cfg.name,
            server=deployment_cfg.server.name,
            database=deployment_cfg.database.name,
            description=deployment_cfg.description,
        )
        disabled = deployment_cfg.disabled
        values["disabled"] = ":x:" if disabled else ""
        is_running = deployment.is_running
        values["running"] = ":white_check_mark:" if is_running else ""
        values["url"] = ""
        if is_running:
            store_cfg = deployment.get_store_config()
            if store_cfg:
                values["url"] = store_cfg.url

        deployments.append(values)

    print_table(deployments)


@deployment.command("up", help="Start a configured deployment.")
@click.argument("name", type=str, required=True)
def start_deployment(name: str) -> None:
    """Start a configured deployment.

    Args:
        name: The name of the deployment to start.
    """
    harness = TestHarness()
    deployment = harness.get_deployment(name)
    deployment.up()
    store_cfg = deployment.get_store_config()
    url = f" at {store_cfg.url}" if store_cfg else ""
    print(f"Deployment '{name}' running{url}.")


@deployment.command(
    "down",
    help="Stop a configured deployment.",
)
@click.argument("name", type=str, required=True)
def stop_deployment(name: str) -> None:
    """Stop a configured deployment.

    Args:
        name: The name of the deployment to stop.
    """
    harness = TestHarness()
    deployment = harness.get_deployment(name)
    deployment.down()


@deployment.command(
    "cleanup",
    help="Stop a configured deployment and clean up all the local files.",
)
@click.argument("name", type=str, required=True)
def cleanup_deployment(name: str) -> None:
    """Stop a configured deployment and clean up all the local files.

    Args:
        name: The name of the deployment to cleanup.
    """
    harness = TestHarness()
    deployment = harness.get_deployment(name)
    deployment.cleanup()


@deployment.command(
    "exec",
    context_settings={"ignore_unknown_options": True},
    help="""Run a ZenML CLI command while connected to a deployment.

    Usage:

        zen-test deployment run <deployment-name> <zenml args>...

    Examples:

        zen-test deployment run local-docker status

        zen-test deployment run mysql stack list
""",
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def exec_in_deployment(
    args: List[str],
) -> None:
    """Run a ZenML CLI command while connected to a deployment.

    Args:
        args: The ZenML CLI command arguments to run.
    """
    from zenml.cli.cli import cli as zenml_cli

    if len(args) == 0:
        print("No deployment name specified.")
        sys.exit(1)

    name = args[0]
    harness = TestHarness()
    deployment = harness.get_deployment(name)
    if not deployment.is_running:
        print(f"Deployment '{name}' is not running.")
        sys.exit(1)

    with deployment.connect():
        print(
            f"Running ZenML CLI command in test deployment '{name}': 'zenml {' '.join(args[1:])}'"
        )
        sys.argv = ["zenml"] + list(args[1:])

        sys.exit(zenml_cli())
