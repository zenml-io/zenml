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
"""Functionality to generate stack component CLI commands."""

import getpass
from typing import TYPE_CHECKING, List, cast

import click
from pydantic import ValidationError

from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import (
    confirmation,
    error,
    expand_argument_value_from_file,
    parse_name_and_extra_arguments,
    pretty_print_secret,
    print_list_items,
    warning,
)
from zenml.console import console
from zenml.enums import StackComponentType
from zenml.exceptions import SecretExistsError

if TYPE_CHECKING:
    from zenml.secrets_managers.base_secrets_manager import BaseSecretsManager


def register_secrets_manager_subcommands() -> None:
    """Registers CLI subcommands for the Secrets Manager."""
    secrets_manager_group = cast(TagGroup, cli.commands.get("secrets-manager"))
    if not secrets_manager_group:
        return

    @secrets_manager_group.group(
        cls=TagGroup,
        help="Commands for interacting with secrets.",
    )
    @click.pass_context
    def secret(ctx: click.Context) -> None:
        """List and manage your secrets.

        Args:
            ctx: Click context.
        """
        from zenml.client import Client
        from zenml.stack.stack_component import StackComponent

        client = Client()
        secrets_manager_models = client.active_stack_model.components.get(
            StackComponentType.SECRETS_MANAGER
        )
        if secrets_manager_models is None:
            error(
                "No active secrets manager found. Please create a secrets "
                "manager first and add it to your stack."
            )

        ctx.obj = StackComponent.from_model(secrets_manager_models[0])

    @secret.command(
        "register",
        context_settings={"ignore_unknown_options": True},
        help="Register a secret with the given name and schema.",
    )
    @click.argument("name", type=click.STRING)
    @click.option(
        "--schema",
        "-s",
        "secret_schema_type",
        default="arbitrary",  # TODO: Place in a constant outside secret module
        help="DEPRECATED: Register a secret with an optional schema. Secret "
        "schemas will be removed in an upcoming release of ZenML.",
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
        secret data consists of key-value pairs that can be configured
        interactively (if the `--interactive` option is set) or via command-line
        arguments. If a schema is indicated, the secret key-value pairs will be
        validated against the schema.

        When passed as command line arguments, the secret field values may also
        be loaded from files instead of being issued inline, by prepending the
        field name with a `@` sign. For example, the following command line:
            zenml secrets-manager secret register my_secret --secret_token=@/path/to/file.json
        will load the value for the field `secret_token` from the file
        `/path/to/file.json`.
        To use the `@` sign as the first character of a field name without pointing
        to a file, double the `@` sign. For example, the following command line:
            zenml secrets-manager secret register my_secret --username=zenml --password=@@password
        will interpret the value of the field `password` as the literal string
        `@password`.

        Examples:
        - register a secret with the name `secret_one` and configure its values
        interactively:
            zenml secrets-manager secret -manager secret register secret_one -i
        - register a secret with the name `secret_two` and configure its values
        via command line arguments:
            zenml secrets-manager secret register secret_two --username=admin --password=secret
        - register a secret with the name `secret_three` interactively and
        conforming to a schema named `aws` (which is defined in the `aws`
        integration):
            zenml integration install aws
            zenml secrets-manager secret register secret_three -i --schema=aws
        - register a secret with the name `secret_four` from command line
        arguments and conforming to a schema named `aws` (which is defined in
        the `aws` integration). Also load the value for the field `secret_token`
        from a local file:
            zenml integration install aws
            zenml secrets-manager secret register secret_four --schema=aws \
                --aws_access_key_id=1234567890 \
                --aws_secret_access_key=abcdefghij \
                --aws_session_token=@/path/to/token.txt


        Args:
            secrets_manager: The secrets manager to use.
            name: The name of the secret to register.
            secret_schema_type: The schema to use for validation.
            interactive: Whether to use interactive mode to enter the secret
                values.
            args: Command line arguments.
        """
        # flake8: noqa: C901

        # TODO [ENG-725]: Allow passing in json/dict when registering a secret
        #  as an additional option for the user on top of the interactive

        # Parse the given args
        # name is guaranteed to be set by parse_name_and_extra_arguments
        name, parsed_args = parse_name_and_extra_arguments(  # type: ignore[assignment]
            list(args) + [name], expand_args=True
        )

        if "name" in parsed_args:
            error("You can't use 'name' as the key for one of your secrets.")
        elif name == "name":
            error("Secret names cannot be named 'name'.")

        from zenml.constants import ARBITRARY_SECRET_SCHEMA_TYPE

        if secret_schema_type != ARBITRARY_SECRET_SCHEMA_TYPE:
            warning(
                "Secret schemas will be deprecated soon. You can still "
                "register secrets as a group of key-value pairs using the "
                "`ArbitrarySecretSchema` by not specifying a secret schema "
                "with the `--schema/-s` option."
            )

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
                    "Cannot pass secret fields as arguments when using "
                    "interactive mode."
                )

            if secret_schema_type != ARBITRARY_SECRET_SCHEMA_TYPE:
                click.echo(
                    "You have supplied a secret schema with predefined keys. "
                    "You can fill these out sequentially now. Just press ENTER "
                    "to skip optional secrets that you do not want to set"
                )
                for k in secret_keys:
                    v = getpass.getpass(f"Secret value for {k}:")
                    if v:
                        secret_contents[k] = expand_argument_value_from_file(
                            name=k, value=v
                        )
            else:
                click.echo(
                    "You have not supplied a secret schema with any "
                    "predefined keys. Entering interactive mode:"
                )
                while True:
                    k = click.prompt("Please enter a secret key")
                    if k not in secret_contents:
                        v = getpass.getpass(
                            f"Please enter the secret value for the key [{k}]:"
                        )
                        secret_contents[k] = expand_argument_value_from_file(
                            name=k, value=v
                        )
                    else:
                        warning(
                            f"Key {k} already in this secret. Please restart "
                            f"this process or use 'zenml secrets-manager "
                            f"secret update {name} --{k}=...' to update this "
                            f"key after the secret is registered. Skipping ..."
                        )

                    if not click.confirm(
                        "Do you want to add another key-value pair to this "
                        "secret?"
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
            error(
                f"Secret values do not conform with the secret schema: {str(e)}"
            )

        click.echo("The following secret will be registered.")
        pretty_print_secret(secret=secret, hide_secret=True)

        with console.status(f"Saving secret `{name}`..."):
            try:
                secrets_manager.register_secret(secret=secret)
            except SecretExistsError:
                error(f"A secret with name '{name}' already exists.")

    @secret.command("get", help="Get a secret, given its name.")
    @click.argument("name", type=click.STRING)
    @click.pass_obj
    def get_secret(
        secrets_manager: "BaseSecretsManager",
        name: str,
    ) -> None:
        """Get a secret, given its name.

        Args:
            secrets_manager: The secrets manager to use.
            name: The name of the secret to get.
        """
        try:
            secret = secrets_manager.get_secret(secret_name=name)
            pretty_print_secret(secret, hide_secret=False)
        except KeyError as e:
            error(
                f"Secret with name `{name}` does not exist or could not be "
                f"loaded: {str(e)}."
            )

    @secret.command(
        "list", help="List all secrets tracked by your Secrets Manager."
    )
    @click.pass_obj
    def list_secret(secrets_manager: "BaseSecretsManager") -> None:
        """List all secrets tracked by your Secrets Manager.

        Args:
            secrets_manager: The secrets manager to use.
        """
        with console.status("Getting secret names..."):
            secret_names = secrets_manager.get_all_secret_keys()
            if not secret_names:
                warning("No secrets registered.")
                return
            print_list_items(
                list_items=secret_names, column_title="SECRET_NAMES"
            )

    @secret.command(
        "update",
        context_settings={"ignore_unknown_options": True},
        help="Update a secret with a given name.",
    )
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
    ) -> None:
        """Update a secret with a given name.

        Use this command to update the information stored in an existing ZenML
        secret. The secret's key-value pairs can be updated interactively
        (if the `--interactive` option is set) or via command-line arguments.
        If a schema is associated with the existing secret, the updated secret
        key-value pairs will be validated against the schema.

        When passed as command line arguments, the secret field values may also
        be loaded from files instead of being issued inline, by prepending the
        field name with a `@` sign. For example, the following command line:

            zenml secrets-manager secret update my_secret --secret_token=@/path/to/file.json

        will load the value for the field `secret_token` from the file
        `/path/to/file.json`. To use the `@` sign as the first character of a
        field name without pointing to a file, double the `@` sign. For example,
        the following command line:

            zenml secrets-manager secret update my_secret --username=zenml --password=@@password

        will interpret the value of the field `password` as the literal string
        `@password`.
        
        Examples:
        - update a secret with the name `secret_one` and configure its values
        interactively:
            zenml secrets-manager secret update secret_one -i
        - update a secret with the name `secret_two` from command line arguments
        and load the value for the field `secret_token` from a
        local file:
            zenml secrets-manager secret update secret_four \
                --aws_access_key_id=1234567890 \
                --aws_secret_access_key=abcdefghij \
                --aws_session_token=@/path/to/token.txt

        Args:
            secrets_manager: The secrets manager to use.
            name: The name of the secret to update.
            interactive: Use interactive mode to update the secret values.
            args: The command line arguments to use to update the secret.
        """
        # TODO [ENG-726]: allow users to pass in dict or json

        # Parse the given args
        # name is guaranteed to be set by parse_name_and_extra_arguments
        name, parsed_args = parse_name_and_extra_arguments(  # type: ignore[assignment]
            list(args) + [name], expand_args=True
        )

        with console.status(f"Getting secret `{name}`..."):
            try:
                secret = secrets_manager.get_secret(secret_name=name)
            except KeyError as e:
                error(
                    f"Secret with name `{name}` does not exist or could not be "
                    f"loaded: {str(e)}."
                )

        if "name" in parsed_args:
            error("Secret names cannot be passed as arguments.")

        updated_contents = {"name": name}

        if interactive:
            if parsed_args:
                error(
                    "Cannot pass secret fields as arguments when using "
                    "interactive mode."
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
            error(
                f"Secret values do not conform with the secret schema: {str(e)}"
            )

        click.echo("The following secret will be updated.")
        pretty_print_secret(updated_secret, hide_secret=True)

        with console.status(f"Updating secret `{name}`..."):
            try:
                secrets_manager.update_secret(secret=updated_secret)
                console.print(f"Secret with name '{name}' has been updated")
            except KeyError:
                error(f"Secret with name `{name}` already exists.")

    @secret.command("delete", help="Delete a secret identified by its name.")
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
    def delete_secret(
        secrets_manager: "BaseSecretsManager",
        name: str,
        yes: bool = False,
    ) -> None:
        """Delete a secret identified by its name.

        Args:
            secrets_manager: The secrets manager to use.
            name: The name of the secret to delete.
            yes: Skip asking for confirmation.
        """
        if not yes:
            confirmation_response = confirmation(
                f"This will delete all data associated with the `{name}` "
                f"secret. Are you sure you want to proceed?"
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

    @secret.command(
        "cleanup",
        hidden=True,
        help="Delete all secrets tracked by your Secrets Manager.",
    )
    @click.option(
        "--yes",
        "-y",
        "yes",
        is_flag=True,
        help="Force the deletion of all secrets",
        type=click.BOOL,
    )
    @click.option(
        "--force",
        "-f",
        "force",
        is_flag=True,
        help="DEPRECATED: Force the deletion of all secrets. Use `-y/--yes` "
        "instead.",
        type=click.BOOL,
    )
    @click.pass_obj
    def delete_all_secrets(
        secrets_manager: "BaseSecretsManager", yes: bool, force: bool
    ) -> None:
        """Delete all secrets tracked by your Secrets Manager.

        Args:
            secrets_manager: The secrets manager to use.
            yes: Skip asking for confirmation.
            force: DEPRECATED: Skip asking for confirmation.
        """
        if force:
            warning(
                "The `--force` flag will soon be deprecated. Use `--yes` or "
                "`-y` instead."
            )
        if not yes:
            confirmation_response = confirmation(
                "This will delete all secrets. Are you sure you want to "
                "proceed?"
            )
            if not confirmation_response:
                console.print("Aborting deletion of all secrets...")
                return

        with console.status("Deleting all secrets..."):
            secrets_manager.delete_all_secrets()
            console.print("Deleted all secrets.")
