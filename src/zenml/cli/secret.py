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
from typing import Optional

import click

from zenml.cli.cli import cli
from zenml.cli.utils import (
    confirmation,
    error,
    pretty_print_secret,
    print_secrets,
    warning,
)
from zenml.console import console
from zenml.enums import SecretSchemaType, StackComponentType
from zenml.repository import Repository
from zenml.secret.secret_schema_class_registry import SecretSchemaClassRegistry
from zenml.secrets_managers.base_secrets_manager import BaseSecretsManager


def validate_kv_pairs(key: Optional[str], value: Optional[str]) -> bool:
    """Check that the key and value are valid

    Args:
        key: key of the secret
        value: value of the secret
    """
    return bool((not key or value) and (not value or key))


# Secrets
@cli.group()
@click.pass_context
def secret(ctx: click.Context) -> None:
    """Secrets for storing key-value pairs for use in authentication."""
    # TODO [ENG-724]: Ensure the stack actually contains an active secrets manager
    ctx.obj = Repository().active_stack.components.get(
        StackComponentType.SECRETS_MANAGER, None
    )
    if ctx.obj is None:
        error(
            "No active secrets manager found. Please create a secrets manager "
            "first and add it to your stack."
        )


@secret.command("register")
@click.argument("name", type=click.STRING)
@click.option(
    "--schema",
    "-s",
    "secret_schema_type",
    default=SecretSchemaType.ARBITRARY.value,
    help="Register a secret with an optional schema.",
    type=click.Choice(SecretSchemaType.values()),
)
@click.option(
    "--key",
    "-k",
    "secret_key",
    default=None,
    help="The key to associate with the secret.",
    type=click.STRING,
)
@click.option(
    "--value",
    "-v",
    "secret_value",
    default=None,
    help="The value to associate with the secret key.",
    type=click.STRING,
)
@click.pass_obj
def register_secret(
    secrets_manager: "BaseSecretsManager",
    name: str,
    secret_schema_type: str,
    secret_key: Optional[str],
    secret_value: Optional[str],
) -> None:
    """Register a secret with the given name as key

    Args:
        secrets_manager: Stack component that implements the interface to the
            underlying secrets engine
        name: Name of the secret
        secret_schema_type: Type of the secret schema - make sure the schema of
            choice is registered with the secret_schema_class_registry
        secret_key: Key of the secret key-value pair
        secret_value: Value of the secret Key-value pair
    """
    # TODO [ENG-725]: Allow passing in json/dict when registering a secret as an
    #   additional option for the user on top of the interactive
    if not validate_kv_pairs(secret_key, secret_value):
        error(
            "To directly pass in key-value pairs, you must pass in values"
            " for both."
        )

    if name == "name":
        error("Secret names cannot be named 'name'.")

    secret_schema = SecretSchemaClassRegistry.get_class(
        secret_schema=secret_schema_type
    )
    secret_keys = secret_schema.get_schema_keys()

    secret_contents = {"name": name}

    if secret_keys:
        click.echo(
            "You have supplied a secret_set_schema with predefined keys. "
            "You can fill these out sequentially now. Just press ENTER to skip "
            "optional secrets that you do not want to set"
        )
        for k in secret_keys:
            v = getpass.getpass(f"Secret value for {k}:")
            secret_contents[k] = v

    elif secret_key and secret_value:
        secret_contents[secret_key] = secret_value

    else:
        click.echo(
            "You have not supplied a secret_set_schema with any "
            "predefined keys. Entering interactive mode:"
        )
        while True:
            k = click.prompt("Please enter a secret-key")
            if k not in secret_contents:
                secret_contents[k] = getpass.getpass(
                    f"Please enter the secret_value " f"for the key [{k}]:"
                )
            else:
                warning(
                    f"Key {k} already in this secret. Please restart this"
                    f" process or use "
                    f"'zenml secret update {name} --{secret_schema_type}'"
                    f" to update this key. "
                    f"Skipping ..."
                )

            if not click.confirm(
                "Do you want to add another key-value pair to this secret?"
            ):
                break

    click.echo("The following secret will be registered.")
    secret = secret_schema(**secret_contents)
    pretty_print_secret(secret=secret, hide_secret=True)

    with console.status(f"Saving secret set `{name}`..."):
        secrets_manager.register_secret(secret=secret)


@secret.command("get")
@click.argument("name", type=click.STRING)
@click.pass_obj
def get_secret(
    secrets_manager: "BaseSecretsManager",
    name: str,
) -> None:
    """Get a secret set, given its name.

    Args:
        secrets_manager: Stack component that implements the interface to the
            underlying secrets engine
        name: Name of the secret
    """
    # with console.status(f"Getting secret set `{name}`..."):
    try:
        secret = secrets_manager.get_secret(secret_name=name)
        pretty_print_secret(secret, hide_secret=False)
    except KeyError:
        error(f"Secret Set with name:`{name}` does not exist.")


@secret.command("list")
@click.pass_obj
def list_secret(secrets_manager: "BaseSecretsManager") -> None:
    """Get a list of all the keys to secrets sets in the store.
    Args:
        secrets_manager: Stack component that implements the interface to the
            underlying secrets engine
    """
    with console.status("Getting secret names..."):
        secret_names = secrets_manager.get_all_secret_keys()
        # TODO: [HIGH] implement as a table?
        print_secrets(secret_names)


@secret.command("update")
@click.argument("name", type=click.STRING)
@click.option(
    "--key",
    "-k",
    "secret_key",
    default=None,
    help="The key to update.",
    type=click.STRING,
)
@click.option(
    "--value",
    "-v",
    "secret_value",
    default=None,
    help="The new value to associate with the secret key.",
    type=click.STRING,
)
@click.pass_obj
def update_secret(
    secrets_manager: "BaseSecretsManager",
    name: str,
    secret_key: Optional[str],
    secret_value: Optional[str],
) -> None:  # sourcery skip: use-named-expression
    """Update a secret set, given its name.

    Args:
        secrets_manager: Stack component that implements the interface to the
            underlying secrets engine
        name: Name of the secret
    """
    # TODO [ENG-726]: allow users to pass in dict or json
    # TODO [ENG-727]: allow adding new key value pairs to the secret

    with console.status(f"Getting secret set `{name}`..."):
        try:
            secret = secrets_manager.get_secret(secret_name=name)
        except KeyError:
            error(f"Secret Set with name:`{name}` does not exist.")

    if not validate_kv_pairs(secret_key, secret_value):
        error(
            "To directly pass in a key-value pair for updating, you must pass in values for both."
        )

    updated_contents = {"name": name}

    if secret_key and secret_value:
        updated_contents[secret_key] = secret_value
    else:
        click.echo(
            "You will now have a chance to overwrite each secret "
            "one by one. Press enter to skip."
        )
        for key, value in secret.content.items():
            new_value = getpass.getpass(f"New value for " f"{key}:")
            if new_value:
                updated_contents[key] = new_value
            else:
                updated_contents[key] = value

    updated_secret = secret.__class__(**updated_contents)

    pretty_print_secret(updated_secret, hide_secret=True)

    with console.status(f"Updating secret set `{name}`..."):
        try:
            secrets_manager.update_secret(secret=updated_secret)
            console.print(f"Secret with name '{name}' has been updated")
        except KeyError:
            error(f"Secret Set with name:`{name}` already exists.")


@secret.command("delete")
@click.argument("name", type=click.STRING)
@click.pass_obj
def delete_secret_set(
    secrets_manager: "BaseSecretsManager",
    name: str,
) -> None:
    """Delete a secret set given its name.

    Args:
        secrets_manager: Stack component that implements the interface to the
            underlying secrets engine
        name: Name of the secret
    """
    confirmation_response = confirmation(
        f"This will delete the secret associated with `{name}`. "
        "Are you sure you want to proceed?"
    )
    if not confirmation_response:
        console.print("Aborting secret set deletion...")
    else:
        with console.status(f"Deleting secret `{name}`..."):
            try:
                secrets_manager.delete_secret(name)
                console.print(f"Deleted secret for `{name.upper()}`.")
            except KeyError:
                error(f"Secret with name:`{name}` already did not exist.")


@secret.command("cleanup")
@click.option(
    "--force",
    "-f",
    "force",
    is_flag=True,
    help="Force the deletion of all secrets",
    type=click.BOOL,
)
@click.pass_obj
def delete_all_secrets(
    secrets_manager: "BaseSecretsManager", force: bool
) -> None:
    """Delete all secrets.

    Args:
        secrets_manager: Stack component that implements the interface to the
            underlying secrets engine
        force: Specify if force should be applied when deleting all secrets.
            This might have differing implications depending on the underlying
            secrets manager
    """
    confirmation_response = confirmation(
        "This will delete all secrets and the `secrets.yaml` file. Are you sure you want to proceed?"
    )
    if not confirmation_response:
        console.print("Aborting secret set deletion...")
    else:
        with console.status("Deleting all secrets ..."):
            secrets_manager.delete_all_secrets(force=force)
            console.print("Deleted all secrets.")
