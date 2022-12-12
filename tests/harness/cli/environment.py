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
"""ZenML test environment CLI."""

import importlib

import click

from tests.harness.cli.cli import cli
from tests.harness.harness import TestHarness
from tests.harness.model.deployment import DeploymentConfig


@cli.group()
def environment() -> None:
    """View and manage test environments."""


@environment.command("list", help="List all configured environments.")
@click.option(
    "--detailed",
    type=str,
    is_flag=True,
    help="Show detailed output.",
)
def list_environment(detailed: bool = False) -> None:
    """List configured environment.

    Args:
        detailed: Whether to show detailed output.
    """
    from zenml.cli.utils import print_table

    harness = TestHarness()
    environments = []
    for environment in harness.environments.values():
        environment_cfg = environment.config

        deployment = environment_cfg.deployment
        assert isinstance(deployment, DeploymentConfig)

        values = dict(
            name=environment_cfg.name,
            deployment=deployment.name,
            description=environment_cfg.description,
        )

        disabled = environment.is_disabled
        values["disabled"] = ":x:" if disabled else ""
        is_running = environment.is_running
        is_provisioned = is_running and environment.is_provisioned
        values["running"] = ":white_check_mark:" if is_running else ""
        values["provisioned"] = ":white_check_mark:" if is_provisioned else ""

        if detailed:
            requirements = ", ".join(
                [
                    r.name
                    for r in environment_cfg.compiled_requirements
                    if r.name
                ]
            )
            values["requirements"] = requirements
            capabilities = environment.config.capabilities
            values["capabilities"] = ", ".join(
                [c for c, v in capabilities.items() if v]
            )
            values["url"] = ""
            if is_running:
                store_cfg = environment.deployment.get_store_config()
                if store_cfg:
                    values["url"] = store_cfg.url

        environments.append(values)

    print_table(environments)


@environment.command(
    "up",
    help="Start a configured environment.",
)
@click.argument("name", type=str, required=True)
def start_environment(name: str) -> None:
    """Start a configured environment.

    Args:
        name: Name of the environment to start.
    """
    harness = TestHarness()
    environment = harness.get_environment(name)
    environment.up()
    store_cfg = environment.deployment.get_store_config()
    url = f" at {store_cfg.url}" if store_cfg else ""
    print(f"Environment '{name}' is running{url}.")


@environment.command(
    "down",
    help="Deprovision and stop a configured environment.",
)
@click.argument("name", type=str, required=True)
def stop_environment(name: str) -> None:
    """Deprovision and stop a configured environment.

    Args:
        name: Name of the environment to stop.
    """
    harness = TestHarness()
    environment = harness.get_environment(name)
    environment.down()


@environment.command(
    "provision",
    help="Provision a configured environment.",
)
@click.argument("name", type=str, required=True)
def provision_environment(name: str) -> None:
    """Provision a configured environment.

    Args:
        name: Name of the environment to provision.
    """
    harness = TestHarness()
    environment = harness.get_environment(name)
    environment.provision()
    store_cfg = environment.deployment.get_store_config()
    url = f" at {store_cfg.url}" if store_cfg else ""
    print(f"Environment '{name}' is provisioned and running{url}.")


@environment.command(
    "deprovision",
    help="Deprovision a configured environment.",
)
@click.argument("name", type=str, required=True)
def deprovision_environment(name: str) -> None:
    """Deprovision a configured environment.

    Args:
        name: Name of the environment to deprovision.
    """
    harness = TestHarness()
    environment = harness.get_environment(name)
    environment.deprovision()


@environment.command(
    "cleanup",
    help="Deprovision, stop a configured environment and clean up all the "
    "local files.",
)
@click.argument("name", type=str, required=True)
def cleanup_environment(name: str) -> None:
    """Deprovision, stop a configured environment and clean up all the local files.

    Args:
        name: Name of the environment to cleanup.
    """
    harness = TestHarness()
    environment = harness.get_environment(name)
    environment.cleanup()


@environment.command(
    "check",
    help="Check if the requirements for a given pytest test module are "
    "satisfied.",
)
@click.option(
    "--module-name",
    type=str,
    required=True,
    help="Pytest test module name.",
)
@click.argument("name", type=str, required=True)
def check_environment(module_name: str, name: str) -> None:
    """Check if the requirements for a given pytest test module.

    Args:
        module_name: Pytest test module name.
        name: Name of the environment to use.
    """
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        print(f"Module '{module_name}' could not be imported.")
        return

    harness = TestHarness()
    environment = harness.set_environment(name)
    with environment.deployment.connect() as client:
        result, msg = harness.check_requirements(module=module, client=client)

    if result:
        print(f"Requirements for '{module_name}' are satisfied.")
    else:
        print(f"Requirements for '{module_name}' are not satisfied: {msg}")
