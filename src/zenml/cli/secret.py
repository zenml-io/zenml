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
from typing import TYPE_CHECKING, List

import click
from pydantic import ValidationError

from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import (
    confirmation,
    error,
    parse_unknown_options,
    pretty_print_secret,
    print_secrets,
    warning,
)
from zenml.console import console
from zenml.enums import CliCategories, StackComponentType
from zenml.repository import Repository
from zenml.secret import ARBITRARY_SECRET_SCHEMA_TYPE

if TYPE_CHECKING:
    from zenml.secrets_managers.base_secrets_manager import BaseSecretsManager


# Secrets
@cli.group(cls=TagGroup, tag=CliCategories.IDENTITY_AND_SECURITY)
@click.pass_context
def secret(ctx: click.Context) -> None:
    """List and manage your secrets."""
    repo = Repository()
    active_stack = repo.zen_store.get_stack(name=repo.active_stack_name)
    secrets_manager_wrapper = active_stack.get_component_wrapper(
        StackComponentType.SECRETS_MANAGER
    )
    if secrets_manager_wrapper is None:
        error(
            "No active secrets manager found. Please create a secrets manager "
            "first and add it to your stack."
        )
        return

    ctx.obj = secrets_manager_wrapper.to_component()


@secret.command("register", context_settings={"ignore_unknown_options": True})
@click.argument("name", type=click.STRING)
@click.option(
    "--schema",
    "-s",
    "secret_schema_type",
    default=ARBITRARY_SECRET_SCHEMA_TYPE,
    help="Register a secret with an optional schema.",
    type=str,
)
@click.option(
    "--interactive",
    "-i",
    "interactive",
    is_flag=True,
    help="Use interactive mode to enter the secret values.",
    type=click.BOOL,
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.pass_obj
def register_secret(
    secrets_manager: "BaseSecretsManager",
    name: str,
    secret_schema_type: str,
    interactive: bool,
    args: List[str],
) -> None:
    """Register a secret with the given name and schema.

    Use this command to store sensitive information into a ZenML secret. The
    secret data consists of key-value pairs that can be configured interactively
    (if the `--interactive` option is set) or via command line arguments.
    If a schema is indicated, the secret key-value pairs will be validated
    against the schema.

    When passed as command line arguments, the secret field values may also be
    loaded from files instead of being issued inline, by prepending the field
    name with a `@` sign. For example, the following command line:

        zenml secret register my_secret --secret_token=@/path/to/file.json

    will load the value for the field `secret_token` from the file
    `/path/to/file.json`.

    To use the `@` sign as the first character of a field name without pointing
    to a file, double the `@` sign. For example, the following command line:

        zenml secret register my_secret --username=zenml --password=@@password

    will interpret the value of the field `password` as the literal string
    `@password`.

    Examples:

    - register a secret with the name `secret_one` and configure its values
    interactively:

        zenml secret register secret_one -i

    - register a secret with the name `secret_two` and configure its values
    via command line arguments:

        zenml secret register secret_two --username=admin --password=secret

    - register a secret with the name `secret_three` interactively and
    conforming to a schema named `aws` (which is defined in the `aws`
    integration):

        zenml integration install aws
        zenml secret register secret_three -i --schema=aws

    - register a secret with the name `secret_four` from command line arguments
    and conforming to a schema named `aws` (which is defined in the `aws`
    integration). Also load the value for the field `secret_token` from a
    local file:

        zenml integration install aws
        zenml secret register secret_four --schema=aws \
            --aws_access_key_id=1234567890 \
            --aws_secret_access_key=abcdefghij \
            --aws_session_token=@/path/to/token.txt

    """
    # flake8: noqa: C901

    # TODO [ENG-871]: Formatting for `zenml secret register --help` currently
    #  broken.
    # TODO [ENG-725]: Allow passing in json/dict when registering a secret as an
    #   additional option for the user on top of the interactive
    try:
        parsed_args = parse_unknown_options(args, expand_args=True)
    except AssertionError as e:
        error(str(e))
        return

    if name == "name":
        error("Secret names cannot be named 'name'.")

    if name.startswith("--"):
        error(
            "Secret names cannot start with '--' The first argument must be."
            "the secret name."
        )

    if "name" in parsed_args:
        error("Secret names cannot be passed as arguments.")

    try:
        from zenml.secret.secret_schema_class_registry import (
            SecretSchemaClassRegistry,
        )

        secret_schema = SecretSchemaClassRegistry.get_class(
            secret_schema=secret_schema_type
        )
    except KeyError as e:
        error(str(e))

    secret_keys = secret_schema.get_schema_keys()

    secret_contents = {"name": name}

    if interactive:

        if parsed_args:
            error(
                "Cannot pass secret fields as arguments when using interactive "
                "mode."
            )

        if secret_schema_type != ARBITRARY_SECRET_SCHEMA_TYPE:
            click.echo(
                "You have supplied a secret schema with predefined keys. "
                "You can fill these out sequentially now. Just press ENTER to "
                "skip optional secrets that you do not want to set"
            )
            for k in secret_keys:
                v = getpass.getpass(f"Secret value for {k}:")
                if v:
                    secret_contents[k] = v
        else:
            click.echo(
                "You have not supplied a secret schema with any "
                "predefined keys. Entering interactive mode:"
            )
            while True:
                k = click.prompt("Please enter a secret-key")
                if k not in secret_contents:
                    secret_contents[k] = getpass.getpass(
                        f"Please enter the secret_value for the key [{k}]:"
                    )
                else:
                    warning(
                        f"Key {k} already in this secret. Please restart this "
                        f"process or use 'zenml secret update {name} --{k}=...' "
                        f"to update this key after the secret is registered. "
                        f"Skipping ..."
                    )

                if not click.confirm(
                    "Do you want to add another key-value pair to this secret?"
                ):
                    break

    else:
        if not parsed_args:
            error(
                "Secret fields must be passed as arguments when not using "
                "interactive mode."
            )

        secret_contents.update(parsed_args)

    try:
        secret = secret_schema(**secret_contents)
    except ValidationError as e:
        error(f"Secret values do not conform with the secret schema: {str(e)}")

    click.echo("The following secret will be registered.")
    pretty_print_secret(secret=secret, hide_secret=True)

    with console.status(f"Saving secret `{name}`..."):
        secrets_manager.register_secret(secret=secret)


@secret.command("get")
@click.argument("name", type=click.STRING)
@click.pass_obj
def get_secret(
    secrets_manager: "BaseSecretsManager",
    name: str,
) -> None:
    """Get a secret, given its name."""
    try:
        secret = secrets_manager.get_secret(secret_name=name)
        pretty_print_secret(secret, hide_secret=False)
    except KeyError as e:
        error(
            f"Secret with name `{name}` does not exist or could not be loaded: "
            f"{str(e)}."
        )


@secret.command("list")
@click.pass_obj
def list_secret(secrets_manager: "BaseSecretsManager") -> None:
    """List all secrets tracked by your Secrets Manager."""
    with console.status("Getting secret names..."):
        secret_names = secrets_manager.get_all_secret_keys()
        print_secrets(secret_names)


@secret.command("update", context_settings={"ignore_unknown_options": True})
@click.argument("name", type=click.STRING)
@click.option(
    "--interactive",
    "-i",
    "interactive",
    is_flag=True,
    help="Use interactive mode to update the secret values.",
    type=click.BOOL,
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.pass_obj
def update_secret(
    secrets_manager: "BaseSecretsManager",
    name: str,
    interactive: bool,
    args: List[str],
) -> None:  # sourcery skip: use-named-expression
    """Update a secret with a given name.

    Use this command to update the information stored in an existing ZenML
    secret. The secret's key-value pairs can be updated interactively
    (if the `--interactive` option is set) or via command line arguments.
    If a schema is associated with the existing secret, the updated secret
    key-value pairs will be validated against the schema.

    When passed as command line arguments, the secret field values may also be
    loaded from files instead of being issued inline, by prepending the field
    name with a `@` sign. For example, the following command line:

        zenml secret update my_secret --secret_token=@/path/to/file.json

    will load the value for the field `secret_token` from the file
    `/path/to/file.json`.

    To use the `@` sign as the first character of a field name without pointing
    to a file, double the `@` sign. For example, the following command line:

        zenml secret update my_secret --username=zenml --password=@@password

    will interpret the value of the field `password` as the literal string
    `@password`.

    Examples:

    - update a secret with the name `secret_one` and configure its values
    interactively:

        zenml secret update secret_one -i

    - update a secret with the name `secret_two` from command line arguments
    and load the value for the field `secret_token` from a
    local file:

        zenml secret update secret_four \
            --aws_access_key_id=1234567890 \
            --aws_secret_access_key=abcdefghij \
            --aws_session_token=@/path/to/token.txt

    """
    # TODO [ENG-726]: allow users to pass in dict or json

    with console.status(f"Getting secret `{name}`..."):
        try:
            secret = secrets_manager.get_secret(secret_name=name)
        except KeyError as e:
            error(
                f"Secret with name `{name}` does not exist or could not be "
                f"loaded: {str(e)}."
            )

    try:
        parsed_args = parse_unknown_options(args, expand_args=True)
    except AssertionError as e:
        error(str(e))
        return

    if "name" in parsed_args:
        error("Secret names cannot be passed as arguments.")

    updated_contents = {"name": name}

    if interactive:
        if parsed_args:
            error(
                "Cannot pass secret fields as arguments when using interactive "
                "mode."
            )

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

    else:

        if not parsed_args:
            error(
                "Secret fields must be passed as arguments when not using "
                "interactive mode."
            )
        updated_contents.update(secret.content)
        updated_contents.update(parsed_args)

    try:
        updated_secret = secret.__class__(**updated_contents)
    except ValidationError as e:
        error(f"Secret values do not conform with the secret schema: {str(e)}")

    click.echo("The following secret will be updated.")
    pretty_print_secret(updated_secret, hide_secret=True)

    with console.status(f"Updating secret `{name}`..."):
        try:
            secrets_manager.update_secret(secret=updated_secret)
            console.print(f"Secret with name '{name}' has been updated")
        except KeyError:
            error(f"Secret with name `{name}` already exists.")


@secret.command("delete")
@click.argument("name", type=click.STRING)
@click.option(
    "--yes",
    "-y",
    type=click.BOOL,
    default=False,
    is_flag=True,
    help="Skip asking for confirmation.",
)
@click.pass_obj
def delete_secret_set(
    secrets_manager: "BaseSecretsManager",
    name: str,
    yes: bool = False,
) -> None:
    """Delete a secret identified by its name."""
    if not yes:
        confirmation_response = confirmation(
            f"This will delete all data associated with the `{name}` secret. "
            "Are you sure you want to proceed?"
        )
        if not confirmation_response:
            console.print("Aborting secret deletion...")
            return

    with console.status(f"Deleting secret `{name}`..."):
        try:
            secrets_manager.delete_secret(name)
            console.print(f"Deleted secret `{name}`.")
        except KeyError:
            error(f"Secret with name `{name}` no longer present.")


@secret.command("cleanup", hidden=True)
@click.option(
    "--yes",
    "-y",
    "force",
    is_flag=True,
    help="Force the deletion of all secrets",
    type=click.BOOL,
)
@click.option(
    "--force",
    "-f",
    "old_force",
    is_flag=True,
    help="DEPRECATED: Force the deletion of all secrets. Use `-y/--yes` "
    "instead.",
    type=click.BOOL,
)
@click.pass_obj
def delete_all_secrets(
    secrets_manager: "BaseSecretsManager", force: bool, old_force: bool
) -> None:
    """Delete all secrets tracked by your Secrets Manager.

    Use the --yes flag to specify if force should be applied when deleting all
    secrets. This might have differing implications depending on the underlying
    secrets manager
    """
    if old_force:
        force = old_force
        warning(
            "The `--force` flag will soon be deprecated. Use `--yes` or `-y` "
            "instead."
        )
    confirmation_response = confirmation(
        "This will delete all secrets. Are you sure you want to proceed?"
    )
    if not confirmation_response:
        console.print("Aborting secret deletion...")
    else:
        with console.status("Deleting all secrets ..."):
            secrets_manager.delete_all_secrets(force=force)
            console.print("Deleted all secrets.")
