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

import getpass
from typing import List

import click

from zenml.cli.cli import cli
from zenml.cli.utils import confirmation, error, print_table
from zenml.console import console
from zenml.enums import SecretSetFlavor, StackComponentType
from zenml.repository import Repository
from zenml.secret_sets.secret_set_class_registry import SecretSetClassRegistry
from zenml.secrets_manager.base_secrets_manager import BaseSecretsManager


# Secrets
@cli.group()
@click.pass_context
def secret(ctx: click.Context) -> None:
    """Secrets for storing key-value pairs for use in authentication."""
    # TODO [HIGH]: Ensure the stack actually contains an active secrets manager
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
    prompt=True,
    hide_input=True,
    confirmation_prompt=False,
)
@click.option(
    "--secret-set",
    "-ss",
    "secret_set_name",
    help="The secret set to create.",
    required=False,
    type=str,
    default="default",
)
@click.pass_obj
def register_secret(
    secrets_manager: "BaseSecretsManager",
    name: str,
    secret_value: str,
    secret_set_name: str,
) -> None:
    """Create a secret."""
    # TODO [MEDIUM] Implement interactive mode for registering secrets
    with console.status(
        f"Creating secret `{name}` whitin the `{secret_set_name}` secret set..."
    ):
        try:
            secrets_manager.register_secret(name, secret_value, secret_set_name)
            console.print(
                f"Secret `{name.upper()}` registered whitin the "
                f"`{secret_set_name}` secret set."
            )
        except KeyError:
            error(
                f"Secret `{name}` already exists in secret-set "
                f"'{secret_set_name}'."
            )


@secret.command("get")
@click.argument("name", type=str)
@click.option(
    "--secret-set",
    "-ss",
    "secret_set_name",
    help="The secret set to create.",
    required=False,
    type=str,
    default="default",
)
@click.pass_obj
def get_secret(
    secrets_manager: "BaseSecretsManager", name: str, secret_set_name: str
) -> None:
    """Get a secret, given its name."""
    with console.status(
        f"Getting secret `{name}` from the `{secret_set_name}` secret set..."
    ):
        try:
            secret_value = secrets_manager.get_secret_by_key(
                name, secret_set_name
            )
            console.print(f"Secret for `{name.upper()}` is `{secret_value}`.")
        except KeyError:
            error(
                "Secret `{name}` does not exist in secret-set "
                f"'{secret_set_name}'."
            )


@secret.command("list")
@click.option(
    "--secret-set",
    "-ss",
    "secret_set_name",
    help="The secret set to create.",
    required=False,
    type=str,
    default="default",
)
@click.pass_obj
def list_secrets(
    secrets_manager: "BaseSecretsManager", secret_set_name: str
) -> None:
    """Get a list of all the keys to secrets in the store."""
    with console.status("Getting secret keys..."):
        secret_keys = secrets_manager.get_all_secret_keys(secret_set_name)
        # TODO: [HIGH] implement as a table?
        console.print(secret_keys)


@secret.command("delete")
@click.argument("name", type=str)
@click.option(
    "--secret-set",
    "-ss",
    "secret_set_name",
    help="The secret set to create.",
    required=False,
    type=str,
    default="default",
)
@click.pass_obj
def delete_secret(
    secrets_manager: "BaseSecretsManager", name: str, secret_set_name: str
) -> None:
    """Delete a secret, given its name."""
    confirmation_response = confirmation(
        f"This will delete the secret associated with `{name}` from the "
        f"`{secret_set_name}` secret set. "
        "Are you sure you want to proceed?"
    )
    if not confirmation_response:
        console.print("Aborting secret deletion...")
    else:
        with console.status(f"Deleting secret `{name}`..."):
            try:
                secrets_manager.delete_secret_by_key(name, secret_set_name)
                console.print(
                    f"Deleted secret for `{name.upper()}` from the "
                    f"`{secret_set_name}` secret set."
                )
            except KeyError:
                error(
                    f"Secret `{name}` did not exist in secret-set "
                    f"'{secret_set_name}'."
                )


@secret.command("update")
@click.argument("name", type=str)
@click.option(
    "--secret",
    "-s",
    "secret_value",
    help="The new secret value to update for a specific name.",
    required=True,
    type=str,
    prompt=True,
    hide_input=True,
)
@click.option(
    "--secret-set",
    "-ss",
    "secret_set_name",
    help="The secret set to create.",
    required=False,
    type=str,
    default="default",
)
@click.pass_obj
def update_secret(
    secrets_manager: "BaseSecretsManager",
    name: str,
    secret_value: str,
    secret_set_name: str,
) -> None:
    """Update a secret."""
    with console.status(
        f"Updating secret `{name}` from the `{secret_set_name}` secret set..."
    ):
        try:
            secrets_manager.update_secret_by_key(
                name, secret_value, secret_set_name
            )
            console.print(f"Secret `{name.upper()}` updated.")
        except KeyError:
            error(
                f"Secret `{name}` does not exist in secret-set "
                f"'{secret_set_name}'."
            )


@secret.command("register-set")
@click.argument("name", type=click.STRING)
@click.option(
    "--flavor",
    "-f",
    "secret_set_flavor",
    help="A registered secret set to create.",
    required=True,
    type=click.Choice(SecretSetFlavor.value_list()),
)
@click.pass_obj
def register_secret_set(
    secrets_manager: "BaseSecretsManager",
    name: str,
    secret_set_flavor: str,
) -> None:
    """Create a secret."""
    SecretSet = SecretSetClassRegistry.get_class(
        component_flavor=secret_set_flavor
    )
    secret_keys = [field for field in SecretSet.__fields__]

    secret_set_dict = {}
    for k in secret_keys:
        secret_set_dict[k] = getpass.getpass(f"Secret value for {k}:")

    secret_set = SecretSet(**secret_set_dict)
    secrets_manager.register_secret_set(
        secret_set_name=name, secret_set=secret_set
    )


@secret.command("get-set")
@click.argument("name", type=click.STRING)
@click.pass_obj
def get_secret_set(
    secrets_manager: "BaseSecretsManager",
    name: str,
) -> None:
    """Get a secret set, given its name."""
    with console.status(f"Getting secret set `{name}`..."):
        try:
            secret_set = secrets_manager.get_secret_set_by_key(
                secret_set_name=name
            )
            stack_dicts = []
            for secret, value in secret_set.items():
                stack_dicts.append(
                    {
                        "SECRET SET": name,
                        "SECRET_KEY": secret,
                        "SECRET_VALUE": "********",  # value,
                    }
                )
            print_table(stack_dicts)
        except KeyError:
            error(f"Secret Set with name:`{name}` does not exist.")


@secret.command("list-sets")
@click.pass_obj
def list_secret_sets(
    secrets_manager: "BaseSecretsManager",
) -> List[str]:
    """Get a list of all the keys to secrets sets in the store."""
    with console.status("Getting secret keys..."):
        secret_keys = secrets_manager.get_all_secret_sets_keys()
        # TODO: [HIGH] implement as a table?
        console.print(secret_keys)


@secret.command("update-set")
@click.argument("name", type=click.STRING)
@click.pass_obj
def update_secret_set(secrets_manager: "BaseSecretsManager", name: str) -> None:
    """Update a secret set, given its name."""
    with console.status(f"Getting secret set `{name}`..."):
        try:
            secret_set = secrets_manager.get_secret_set_by_key(
                secret_set_name=name
            )
        except KeyError:
            error(f"Secret Set with name:`{name}` does not exist.")

    click.echo(
        "You will now have a chance to overwrite each secret "
        "one by one. Press enter to skip."
    )
    for secret, value in secret_set.items():
        new_value = getpass.getpass(f"New value for " f"{secret}:")
        if new_value:
            secret_set[secret] = new_value

    with console.status(f"Updating secret set `{name}`..."):
        try:
            secrets_manager.update_secret_set_by_key(
                secret_set_name=name, secret_set=secret_set
            )
        except KeyError:
            error(f"Secret Set with name:`{name}` already exists.")


@secret.command("delete-set")
@click.argument("name", type=click.STRING)
@click.pass_obj
def delete_secret_set(
    secrets_manager: "BaseSecretsManager",
    name: str,
) -> None:
    """Delete a secret set."""
    confirmation_response = confirmation(
        f"This will delete the secret set associated with `{name}`. "
        "Are you sure you want to proceed?"
    )
    if not confirmation_response:
        console.print("Aborting secret set deletion...")
    else:
        with console.status(f"Deleting secret set `{name}`..."):
            try:
                secrets_manager.delete_secret_set_by_key(name)
                console.print(f"Deleted secret set for `{name.upper()}`.")
            except KeyError:
                error(f"Secret Set with name:`{name}` already did not exist.")
