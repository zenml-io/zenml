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

from typing import List

import click

from zenml.cli.cli import cli
from zenml.cli.utils import confirmation, error
from zenml.console import console
from zenml.enums import StackComponentType
from zenml.repository import Repository
from zenml.secrets_manager.base_secrets_manager import BaseSecretsManager


# Secrets
@cli.group()
@click.pass_context
def secret(ctx) -> None:
    """Secrets for storing key-value pairs for use in authentication."""
    ctx.obj = Repository().active_stack.components.get(
        StackComponentType.SECRETS_MANAGER, None
    )


@secret.command("register")
@click.argument("name", type=click.STRING)
@click.option(
    "--secret",
    "-s",
    "secret_value",
    help="The secret to create.",
    required=True,
    type=str,
)
@click.pass_obj
def register_secret(
    secrets_manager: "BaseSecretsManager",
    name: str,
    secret_value: str,
) -> None:
    """Create a secret."""
    # TODO [MEDIUM] Implement interactive mode for registering secrets
    with console.status(f"Creating secret `{name}`..."):
        try:
            secrets_manager.register_secret(name, secret_value)
            console.print(f"Secret `{name.upper()}` registered.")
        except KeyError as e:
            error(e)


@secret.command("get")
@click.argument("name", type=str)
@click.pass_obj
def get_secret(secrets_manager: "BaseSecretsManager", name: str) -> None:
    """Get a secret, given its name."""
    with console.status(f"Getting secret `{name}`..."):
        try:
            secret_value = secrets_manager.get_secret_by_key(name)
            console.print(f"Secret for `{name.upper()}` is `{secret_value}`.")
        except KeyError as e:
            error(e)


@secret.command("list")
@click.pass_obj
def list_secrets(secrets_manager: "BaseSecretsManager") -> List[str]:
    """Get a list of all the keys to secrets in the store."""
    with console.status("Getting secret keys..."):
        try:
            secret_keys = secrets_manager.get_all_secret_keys()
            # TODO: [HIGH] implement as a table?
            console.print(secret_keys)
        except KeyError as e:
            error(e)


@secret.command("delete")
@click.argument("name", type=str)
@click.pass_obj
def delete_secret(secrets_manager: "BaseSecretsManager", name: str) -> None:
    """Delete a secret, given its name."""
    confirmation_response = confirmation(
        f"This will delete the secret associated with `{name}`. "
        "Are you sure you want to proceed?"
    )
    if not confirmation_response:
        console.print("Aborting secret deletion...")
    else:
        with console.status(f"Deleting secret `{name}`..."):
            try:
                secrets_manager.delete_secret_by_key(name)
                console.print(f"Deleted secret for `{name.upper()}`.")
            except KeyError as e:
                error(e)


@secret.command("update")
@click.argument("name", type=str)
@click.option(
    "--secret",
    "-s",
    "secret_value",
    help="The new secret value to update for a specific name.",
    required=True,
    type=str,
)
@click.pass_obj
def update_secret(
    secrets_manager: "BaseSecretsManager",
    name: str,
    secret_value: str,
) -> None:
    """Update a secret."""
    with console.status(f"Updating secret `{name}`..."):
        try:
            secrets_manager.update_secret_by_key(name, secret_value)
            console.print(f"Secret `{name.upper()}` updated.")
        except KeyError as e:
            error(e)
