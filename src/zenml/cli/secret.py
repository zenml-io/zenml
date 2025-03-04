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
from typing import Any, List, Optional

import click

from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import (
    confirmation,
    convert_structured_str_to_dict,
    declare,
    error,
    expand_argument_value_from_file,
    list_options,
    parse_name_and_extra_arguments,
    pretty_print_secret,
    print_page_info,
    print_table,
    validate_keys,
    warning,
)
from zenml.client import Client
from zenml.console import console
from zenml.constants import SECRET_VALUES
from zenml.enums import (
    CliCategories,
)
from zenml.exceptions import EntityExistsError, ZenKeyError
from zenml.logger import get_logger
from zenml.models import SecretFilter, SecretResponse

logger = get_logger(__name__)


@cli.group(cls=TagGroup, tag=CliCategories.IDENTITY_AND_SECURITY)
def secret() -> None:
    """Create, list, update, or delete secrets."""


@secret.command(
    "create",
    context_settings={"ignore_unknown_options": True},
    help="Create a new secret.",
)
@click.argument("name", type=click.STRING)
@click.option(
    "--private",
    "-p",
    "private",
    is_flag=True,
    help="Whether the secret is private. A private secret is only accessible "
    "to the user who creates it.",
)
@click.option(
    "--interactive",
    "-i",
    "interactive",
    is_flag=True,
    help="Use interactive mode to enter the secret values.",
    type=click.BOOL,
)
@click.option(
    "--values",
    "-v",
    "values",
    help="Pass one or more values using JSON or YAML format or reference a file by prefixing the filename with the @ "
    "special character.",
    required=False,
    type=str,
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def create_secret(
    name: str, private: bool, interactive: bool, values: str, args: List[str]
) -> None:
    """Create a secret.

    Args:
        name: The name of the secret to create.
        private: Whether the secret is private.
        interactive: Whether to use interactive mode to enter the secret values.
        values: Secret key-value pairs to be passed as JSON or YAML.
        args: The arguments to pass to the secret.
    """
    name, parsed_args = parse_name_and_extra_arguments(  # type: ignore[assignment]
        list(args) + [name], expand_args=True
    )
    if values:
        inline_values = expand_argument_value_from_file(SECRET_VALUES, values)
        inline_values_dict = convert_structured_str_to_dict(inline_values)
        parsed_args.update(inline_values_dict)

    if "name" in parsed_args:
        error("You can't use 'name' as the key for one of your secrets.")
    elif name == "name":
        error("Secret names cannot be named 'name'.")

    try:
        client = Client()
        if interactive:
            if parsed_args:
                error(
                    "Cannot pass secret fields as arguments when using "
                    "interactive mode."
                )
            else:
                click.echo("Entering interactive mode:")
                while True:
                    k = click.prompt("Please enter a secret key")
                    if k in parsed_args:
                        warning(
                            f"Key {k} already in this secret. Please restart "
                            f"this process or use 'zenml "
                            f"secret update {name} --values=<JSON/YAML> or --{k}=...' to update this "
                            f"key after the secret is registered. Skipping ..."
                        )
                    else:
                        v = getpass.getpass(
                            f"Please enter the secret value for the key [{k}]:"
                        )
                        parsed_args[k] = v

                    if not confirmation(
                        "Do you want to add another key-value pair to this "
                        "secret?"
                    ):
                        break
        elif not parsed_args:
            error(
                "Secret fields must be passed as arguments when not using "
                "interactive mode."
            )

        for key in parsed_args:
            validate_keys(key)
        declare("The following secret will be registered.")
        pretty_print_secret(secret=parsed_args, hide_secret=True)

        with console.status(f"Saving secret `{name}`..."):
            try:
                client.create_secret(
                    name=name, values=parsed_args, private=private
                )
                declare(f"Secret '{name}' successfully created.")
            except EntityExistsError as e:
                # should never hit this on account of the check above
                error(f"Secret with name already exists. {str(e)}")
    except NotImplementedError as e:
        error(f"Centralized secrets management is disabled: {str(e)}")


@secret.command(
    "list", help="List all registered secrets that match the filter criteria."
)
@list_options(SecretFilter)
def list_secrets(**kwargs: Any) -> None:
    """List all secrets that fulfill the filter criteria.

    Args:
        kwargs: Keyword arguments to filter the secrets.
    """
    client = Client()
    with console.status("Listing secrets..."):
        try:
            secrets = client.list_secrets(**kwargs)
        except NotImplementedError as e:
            error(f"Centralized secrets management is disabled: {str(e)}")
        if not secrets.items:
            warning("No secrets found for the given filters.")
            return

        secret_rows = [
            dict(
                name=secret.name,
                id=str(secret.id),
                private=secret.private,
            )
            for secret in secrets.items
        ]
        print_table(secret_rows)
        print_page_info(secrets)


@secret.command("get", help="Get a secret with a given name, prefix or id.")
@click.argument(
    "name_id_or_prefix",
    type=click.STRING,
)
@click.option(
    "--private",
    "-p",
    "private",
    type=click.BOOL,
    required=False,
    help="Use this flag to explicitly fetch a private secret or a public secret.",
)
def get_secret(name_id_or_prefix: str, private: Optional[bool] = None) -> None:
    """Get a secret and print it to the console.

    Args:
        name_id_or_prefix: The name of the secret to get.
        private: Private status of the secret to filter for.
    """
    secret = _get_secret(name_id_or_prefix, private)
    scope = ""
    if private is not None:
        scope = "private " if private else "public "
    declare(
        f"Fetched {scope}secret with name `{secret.name}` and ID `{secret.id}`:"
    )
    if not secret.secret_values:
        warning(f"Secret with name `{name_id_or_prefix}` is empty.")
    else:
        pretty_print_secret(secret.secret_values, hide_secret=False)


def _get_secret(
    name_id_or_prefix: str, private: Optional[bool] = None
) -> SecretResponse:
    """Get a secret with a given name, prefix or id.

    Args:
        name_id_or_prefix: The name of the secret to get.
        private: Private status of the secret to filter for.

    Returns:
        The secret response model.
    """
    client = Client()
    try:
        return client.get_secret(
            name_id_or_prefix=name_id_or_prefix, private=private
        )
    except ZenKeyError as e:
        error(
            f"Error fetching secret with name id or prefix "
            f"`{name_id_or_prefix}`: {str(e)}."
        )
    except KeyError as e:
        error(
            f"Could not find a secret with name id or prefix "
            f"`{name_id_or_prefix}`: {str(e)}."
        )
    except NotImplementedError as e:
        error(f"Centralized secrets management is disabled: {str(e)}")


@secret.command(
    "update",
    context_settings={"ignore_unknown_options": True},
    help="Update a secret with a given name or id.",
)
@click.argument(
    "name_or_id",
    type=click.STRING,
)
@click.option(
    "--private",
    "-p",
    "private",
    type=click.BOOL,
    required=False,
    help="Update the private status of the secret.",
)
@click.option(
    "--interactive",
    "-i",
    "interactive",
    is_flag=True,
    help="Use interactive mode to update the secret values.",
    type=click.BOOL,
)
@click.option(
    "--values",
    "-v",
    "values",
    help="Pass one or more values using JSON or YAML format or reference a file by prefixing the filename with the @ "
    "special character.",
    required=False,
    type=str,
)
@click.option("--remove-keys", "-r", type=click.STRING, multiple=True)
@click.argument("extra_args", nargs=-1, type=click.UNPROCESSED)
def update_secret(
    name_or_id: str,
    extra_args: List[str],
    private: Optional[bool] = None,
    remove_keys: List[str] = [],
    interactive: bool = False,
    values: str = "",
) -> None:
    """Update a secret for a given name or id.

    Args:
        name_or_id: The name or id of the secret to update.
        private: Private status of the secret to update.
        extra_args: The arguments to pass to the secret.
        interactive: Whether to use interactive mode to update the secret.
        remove_keys: The keys to remove from the secret.
        values: Secret key-value pairs to be passed as JSON or YAML.
    """
    name, parsed_args = parse_name_and_extra_arguments(
        list(extra_args) + [name_or_id], expand_args=True
    )
    if values:
        inline_values = expand_argument_value_from_file(SECRET_VALUES, values)
        inline_values_dict = convert_structured_str_to_dict(inline_values)
        parsed_args.update(inline_values_dict)

    client = Client()

    with console.status(f"Checking secret `{name}`..."):
        try:
            secret = client.get_secret(
                name_id_or_prefix=name_or_id, allow_partial_name_match=False
            )
        except KeyError as e:
            error(
                f"Secret with name `{name}` does not exist or could not be "
                f"loaded: {str(e)}."
            )
        except NotImplementedError as e:
            error(f"Centralized secrets management is disabled: {str(e)}")

    declare(f"Updating secret with name '{secret.name}' and ID '{secret.id}'")

    if "name" in parsed_args:
        error("The word 'name' cannot be used as a key for a secret.")

    if interactive:
        if parsed_args:
            error(
                "Cannot pass secret fields as arguments when using "
                "interactive mode."
            )

        declare(
            "You will now have a chance to update each secret pair one by one."
        )
        secret_args_add_update = {}
        for k, _ in secret.secret_values.items():
            item_choice = (
                click.prompt(
                    text=f"Do you want to update key '{k}'? (enter to skip)",
                    type=click.Choice(["y", "n"]),
                    default="n",
                ),
            )
            if "n" in item_choice:
                continue
            elif "y" in item_choice:
                new_value = getpass.getpass(
                    f"Please enter the new secret value for the key '{k}'"
                )
                if new_value:
                    secret_args_add_update[k] = new_value

        # check if any additions to be made
        while True:
            addition_check = confirmation(
                "Do you want to add a new key:value pair?"
            )
            if not addition_check:
                break

            new_key = click.prompt(
                text="Please enter the new key name",
                type=click.STRING,
            )
            new_value = getpass.getpass(
                f"Please enter the new secret value for the key '{new_key}'"
            )
            secret_args_add_update[new_key] = new_value
    else:
        secret_args_add_update = parsed_args

    client.update_secret(
        name_id_or_prefix=secret.id,
        update_private=private,
        add_or_update_values=secret_args_add_update,
        remove_values=remove_keys,
    )
    declare(f"Secret '{secret.name}' successfully updated.")


@secret.command(
    "rename",
    context_settings={"ignore_unknown_options": True},
    help="Rename a secret with a given name or id.",
)
@click.argument(
    "name_or_id",
    type=click.STRING,
)
@click.option(
    "--new-name",
    "-n",
    type=click.STRING,
)
def rename_secret(
    name_or_id: str,
    new_name: str,
) -> None:
    """Update a secret for a given name or id.

    Args:
        name_or_id: The name or id of the secret to update.
        new_name: The new name of the secret.
    """
    if new_name == "name":
        error("Your secret cannot be called 'name'.")

    client = Client()

    with console.status(f"Checking secret `{name_or_id}`..."):
        try:
            client.get_secret(name_id_or_prefix=name_or_id)
        except KeyError as e:
            error(
                f"Secret with name `{name_or_id}` does not exist or could not "
                f"be loaded: {str(e)}."
            )
        except NotImplementedError as e:
            error(f"Centralized secrets management is disabled: {str(e)}")

    client.update_secret(
        name_id_or_prefix=name_or_id,
        new_name=new_name,
    )
    declare(f"Secret '{name_or_id}' successfully renamed to '{new_name}'.")


@secret.command("delete", help="Delete a secret with a given name or id.")
@click.argument(
    "name_or_id",
    type=click.STRING,
)
@click.option(
    "--yes",
    "-y",
    type=click.BOOL,
    default=False,
    is_flag=True,
    help="Skip asking for confirmation.",
)
def delete_secret(name_or_id: str, yes: bool = False) -> None:
    """Delete a secret for a given name or id.

    Args:
        name_or_id: The name or id of the secret to delete.
        yes: Skip asking for confirmation.
    """
    if not yes:
        confirmation_response = confirmation(
            f"This will delete all data associated with the `{name_or_id}` "
            f"secret. Are you sure you want to proceed?"
        )
        if not confirmation_response:
            console.print("Aborting secret deletion...")
            return

    client = Client()

    with console.status(f"Deleting secret `{name_or_id}`..."):
        try:
            client.delete_secret(name_id_or_prefix=name_or_id)
            declare(f"Secret '{name_or_id}' successfully deleted.")
        except KeyError as e:
            error(
                f"Secret with name or id `{name_or_id}` does not exist or "
                f"could not be loaded: {str(e)}."
            )
        except NotImplementedError as e:
            error(f"Centralized secrets management is disabled: {str(e)}")


@secret.command("export", help="Export a secret as a YAML file.")
@click.argument(
    "name_id_or_prefix",
    type=click.STRING,
)
@click.option(
    "--private",
    "-p",
    "private",
    type=click.BOOL,
    required=False,
    help="Use this flag to explicitly fetch a private secret or a public secret.",
)
@click.option(
    "--filename",
    "-f",
    type=click.STRING,
    default=None,
    help=(
        "The name of the file to export the secret to. Defaults to "
        "<secret_name>.yaml."
    ),
)
def export_secret(
    name_id_or_prefix: str,
    private: Optional[bool] = None,
    filename: Optional[str] = None,
) -> None:
    """Export a secret as a YAML file.

    The resulting YAML file can then be imported as a new secret using the
    `zenml secret create <new_secret_name> -v @<filename>` command.

    Args:
        name_id_or_prefix: The name of the secret to export.
        private: Private status of the secret to export.
        filename: The name of the file to export the secret to.
    """
    from zenml.utils.yaml_utils import write_yaml

    secret = _get_secret(name_id_or_prefix=name_id_or_prefix, private=private)
    if not secret.secret_values:
        warning(f"Secret with name `{name_id_or_prefix}` is empty.")
        return

    filename = filename or f"{secret.name}.yaml"
    write_yaml(filename, secret.secret_values)
    declare(f"Secret '{secret.name}' successfully exported to '{filename}'.")


@secret.command(
    "backup", help="Backup all secrets to the backup secrets store."
)
@click.option(
    "--ignore-errors",
    "-i",
    type=click.BOOL,
    default=True,
    help="Whether to ignore individual errors when backing up secrets and "
    "continue with the backup operation until all secrets have been backed up.",
)
@click.option(
    "--delete-secrets",
    "-d",
    is_flag=True,
    default=False,
    help="Whether to delete the secrets that have been successfully backed up "
    "from the primary secrets store. Setting this flag effectively moves all "
    "secrets from the primary secrets store to the backup secrets store.",
)
def backup_secrets(
    ignore_errors: bool = True, delete_secrets: bool = False
) -> None:
    """Backup all secrets to the backup secrets store.

    Args:
        ignore_errors: Whether to ignore individual errors when backing up
            secrets and continue with the backup operation until all secrets
            have been backed up.
        delete_secrets: Whether to delete the secrets that have been
            successfully backed up from the primary secrets store. Setting
            this flag effectively moves all secrets from the primary secrets
            store to the backup secrets store.
    """
    client = Client()

    with console.status("Backing up secrets..."):
        try:
            client.backup_secrets(
                ignore_errors=ignore_errors, delete_secrets=delete_secrets
            )
            declare("Secrets successfully backed up.")
        except NotImplementedError as e:
            error(f"Could not backup secrets: {str(e)}")


@secret.command(
    "restore", help="Restore all secrets from the backup secrets store."
)
@click.option(
    "--ignore-errors",
    "-i",
    type=click.BOOL,
    default=False,
    help="Whether to ignore individual errors when backing up secrets and "
    "continue with the backup operation until all secrets have been backed up.",
)
@click.option(
    "--delete-secrets",
    "-d",
    is_flag=True,
    default=False,
    help="Whether to delete the secrets that have been successfully restored "
    "from the backup secrets store. Setting this flag effectively moves all "
    "secrets from the backup secrets store to the primary secrets store.",
)
def restore_secrets(
    ignore_errors: bool = False, delete_secrets: bool = False
) -> None:
    """Backup all secrets to the backup secrets store.

    Args:
        ignore_errors: Whether to ignore individual errors when backing up
            secrets and continue with the backup operation until all secrets
            have been backed up.
        delete_secrets: Whether to delete the secrets that have been
            successfully restored from the backup secrets store. Setting
            this flag effectively moves all secrets from the backup secrets
            store to the primary secrets store.
    """
    client = Client()

    with console.status("Restoring secrets from backup..."):
        try:
            client.restore_secrets(
                ignore_errors=ignore_errors, delete_secrets=delete_secrets
            )
            declare("Secrets successfully restored.")
        except NotImplementedError as e:
            error(f"Could not restore secrets: {str(e)}")
