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
from typing import TYPE_CHECKING, Any, List, Optional, cast

import click
from pydantic import ValidationError

from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import (
    confirmation,
    convert_structured_str_to_dict,
    declare,
    error,
    expand_argument_value_from_file,
    fail_secret_creation_on_secrets_manager,
    list_options,
    parse_name_and_extra_arguments,
    pretty_print_secret,
    print_list_items,
    print_page_info,
    print_table,
    validate_keys,
    warn_deprecated_secrets_manager,
    warning,
)
from zenml.client import Client
from zenml.console import console
from zenml.constants import ARBITRARY_SECRET_SCHEMA_TYPE, SECRET_VALUES
from zenml.enums import (
    CliCategories,
    SecretScope,
    SecretsStoreType,
    StackComponentType,
)
from zenml.exceptions import EntityExistsError, ZenKeyError
from zenml.logger import get_logger
from zenml.models.secret_models import SecretFilterModel, SecretResponseModel

if TYPE_CHECKING:
    from zenml.secrets_managers.base_secrets_manager import BaseSecretsManager

logger = get_logger(__name__)


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

        warn_deprecated_secrets_manager()

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
        default=ARBITRARY_SECRET_SCHEMA_TYPE,
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

        Examples:-

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
        fail_secret_creation_on_secrets_manager()
        return

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
        
        Examples:-

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
    @click.pass_obj
    def delete_all_secrets(
        secrets_manager: "BaseSecretsManager", yes: bool
    ) -> None:
        """Delete all secrets tracked by your Secrets Manager.

        Args:
            secrets_manager: The secrets manager to use.
            yes: Skip asking for confirmation.
        """
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

    @secret.command(
        "migrate",
        help="""
Migrate secrets to the centralized secrets store.

Using Secrets Manager stack components to manage your secrets is deprecated
and will be removed in a future release. You can use this command to migrate the
secrets managed through the active Secrets Manager stack component to
the centralized ZenML secrets store.

To migrate one or more secrets, pass the secret names as arguments:

    zenml secrets-manager secret migrate my-secret-1 my-secret-2

If you want to migrate all secrets managed by the Secrets Manager, omit
the secret names:

    zenml secrets-manager secret migrate

To delete the secret(s) from the Secrets Manager after successful migration,
use the `--delete` flag:

    zenml secrets-manager secret migrate --delete
    zenml secrets-manager secret migrate --delete my-secret my-other-secret

""",
    )
    @click.option(
        "--delete",
        is_flag=True,
        default=False,
        help="Remove the secret(s) from the Secrets Manager after successful "
        "migration.",
        type=click.BOOL,
    )
    @click.option(
        "--show-secrets",
        is_flag=True,
        default=False,
        help="Include the secrets values when prompting.",
        type=click.BOOL,
    )
    @click.option(
        "--non-interactive",
        is_flag=True,
        default=False,
        help="Do not prompt for confirmation. USE WITH CAUTION, as this will "
        "overwrite all existing secrets with the same name without asking.",
        type=click.BOOL,
    )
    @click.option(
        "--scope",
        "-s",
        "scope",
        help="The scope where to migrate the secrets.",
        type=click.Choice([scope.value for scope in list(SecretScope)]),
        default=SecretScope.WORKSPACE.value,
    )
    @click.argument("secret_names", nargs=-1, type=click.UNPROCESSED)
    @click.pass_obj
    def migrate_secrets(
        secrets_manager: "BaseSecretsManager",
        delete: bool,
        show_secrets: bool,
        non_interactive: bool,
        scope: str,
        secret_names: List[str],
    ) -> None:
        """Migrate secrets to the centralized secrets store.

        Args:
            secrets_manager: The secrets manager to use.
            delete: Whether to delete the secret(s) from the Secrets Manager
                after successful migration.
            show_secrets: Whether to include the secrets values when prompting.
            non_interactive: Whether to prompt for confirmation.
            scope: The scope where to migrate the secrets.
            secret_names: The names of the secrets to migrate.
        """
        client = Client()
        secret_scope = SecretScope(scope)

        if (
            client.zen_store.get_store_info().secrets_store_type
            == SecretsStoreType.NONE
        ):
            error(
                "A centralized secrets store has not been configured for your "
                "local ZenML deployment or server. Please update your ZenML "
                "deployment configuration to use a secrets store to enable "
                "centralized secrets management."
            )

        if secret_names:
            try:
                secret_names = [
                    secrets_manager.get_secret(secret_name).name
                    for secret_name in secret_names
                ]
            except KeyError as e:
                error(
                    f"Secret with name `{e.args[0]}` not found. Please "
                    f"double-check the name and try again."
                )
        else:
            secret_names = secrets_manager.get_all_secret_keys()

        if not secret_names:
            declare(
                "Your Secrets Manager is empty. Nothing to migrate. You should "
                "consider deleting the Secrets Manager stack component now."
            )

        prompt_migrate = not non_interactive
        prompt_delete = not non_interactive
        prompt_overwrite = not non_interactive

        migrated_secrets_count = 0
        for secret_name in secret_names:
            migrated_secret_name = secret_name

            try:
                secret = secrets_manager.get_secret(secret_name)
            except KeyError:
                warning(
                    f"Secret with name `{secret_name}` not found. "
                    f"Skipping..."
                )
                continue

            pretty_print_secret(
                secret, hide_secret=not show_secrets, print_name=True
            )

            secret_exists = False
            skip_migration = False
            try:
                # Check if a secret with the same name already exists in the
                # centralized store in the target scope.
                existing_secret = client.get_secret(
                    name_id_or_prefix=secret_name,
                    scope=secret_scope,
                    allow_partial_id_match=False,
                    allow_partial_name_match=False,
                )

                secret_exists = True

                # Check if the secret values are the same.
                if existing_secret.secret_values == secret.content:
                    # If so, skip the migration.
                    skip_migration = True
                    declare(
                        f"A {secret_scope.value} scoped secret with name "
                        f"`{secret_name}` already exists "
                        f"in the centralized secrets store and has the "
                        f"same values. Skipping migration..."
                    )
                else:
                    warning(
                        f"A {secret_scope.value} scoped secret with name "
                        f"`{secret_name}` already exists "
                        f"in the centralized secrets store and has different "
                        f"values."
                    )
            except KeyError:
                pass

            if not skip_migration:
                if prompt_migrate:
                    choice = click.prompt(
                        "Would you like to migrate this secret ?",
                        type=click.Choice(["y", "n", "all"]),
                        default="y",
                    )
                    if choice == "n":
                        continue
                    elif choice == "all":
                        prompt_migrate = False

                while secret_exists and prompt_overwrite:
                    choice = click.prompt(
                        f"A {secret_scope.value} scoped secret with name "
                        f"`{migrated_secret_name}` already "
                        f"exists in the centralized secrets store. Would you "
                        f"like to overwrite it ?",
                        type=click.Choice(["y", "n", "all"]),
                        default="n",
                    )
                    if choice == "y":
                        break
                    elif choice == "all":
                        prompt_overwrite = False
                        break

                    migrated_secret_name = click.prompt(
                        "Please enter a new name for the secret.",
                        type=click.STRING,
                        default=migrated_secret_name,
                    )

                    # Check if a secret with the same name already exists in the
                    # centralized store in the target scope.
                    try:
                        existing_secret = client.get_secret(
                            name_id_or_prefix=migrated_secret_name,
                            scope=secret_scope,
                            allow_partial_id_match=False,
                            allow_partial_name_match=False,
                        )
                    except KeyError:
                        secret_exists = False

                with console.status(f"Migrating secret `{secret_name}`..."):
                    if not secret_exists:
                        client.create_secret(
                            name=migrated_secret_name,
                            values=secret.content,
                            scope=secret_scope,
                        )
                    else:
                        client.update_secret(
                            name_id_or_prefix=existing_secret.id,
                            add_or_update_values=secret.content,
                            remove_values=[
                                k
                                for k in existing_secret.secret_values
                                if k not in secret.content
                            ],
                            scope=secret_scope,
                        )

                migrated_secrets_count += 1
                declare(f"Secret `{secret_name}` migrated successfully.")

            if delete:
                if prompt_delete:
                    choice = click.prompt(
                        "Would you like to delete the secret ?",
                        type=click.Choice(["y", "n", "all"]),
                        default="n",
                    )
                    if choice == "n":
                        continue
                    elif choice == "all":
                        prompt_delete = False

                with console.status(f"Deleting secret `{secret_name}`..."):
                    try:
                        secrets_manager.delete_secret(secret_name)
                    except KeyError:
                        pass

                declare(f"Secret `{secret_name}` deleted.")

        if migrated_secrets_count > 0:
            declare(
                "Congratulations! Your secrets were migrated successfully."
            )
            if not delete:
                declare(
                    "If you migrated all your secrets, we recommend removing "
                    "all secrets from your Secrets Manager. You can delete "
                    "secrets from the Secrets Manager one by one by running "
                    "`zenml secrets-manager secret delete <secret_name>` or "
                    "use the hidden CLI command `zenml secrets-manager secret "
                    "cleanup` to delete all secrets at once."
                )


### NEW SECRETS STORE PARADIGM


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
    "--scope",
    "-s",
    "scope",
    type=click.Choice([scope.value for scope in list(SecretScope)]),
    default=SecretScope.WORKSPACE.value,
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
    name: str, scope: str, interactive: bool, values: str, args: List[str]
) -> None:
    """Create a secret.

    Args:
        name: The name of the secret to create.
        scope: The scope of the secret to create.
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
                    name=name, values=parsed_args, scope=SecretScope(scope)
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
@list_options(SecretFilterModel)
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
                scope=secret.scope.value,
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
    "--scope",
    "-s",
    type=click.Choice([scope.value for scope in list(SecretScope)]),
    default=None,
)
def get_secret(name_id_or_prefix: str, scope: Optional[str] = None) -> None:
    """Get a secret and print it to the console.

    Args:
        name_id_or_prefix: The name of the secret to get.
        scope: The scope of the secret to get.
    """
    secret = _get_secret(name_id_or_prefix, scope)
    declare(
        f"Fetched secret with name `{secret.name}` and ID `{secret.id}` in "
        f"scope `{secret.scope.value}`:"
    )
    if not secret.secret_values:
        warning(f"Secret with name `{name_id_or_prefix}` is empty.")
    else:
        pretty_print_secret(secret.secret_values, hide_secret=False)


def _get_secret(
    name_id_or_prefix: str, scope: Optional[str] = None
) -> SecretResponseModel:
    """Get a secret with a given name, prefix or id.

    Args:
        name_id_or_prefix: The name of the secret to get.
        scope: The scope of the secret to get.

    Returns:
        The secret response model.
    """
    client = Client()
    try:
        if scope:
            return client.get_secret(
                name_id_or_prefix=name_id_or_prefix, scope=SecretScope(scope)
            )
        else:
            return client.get_secret(name_id_or_prefix=name_id_or_prefix)
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
    "--new-scope",
    "-s",
    type=click.Choice([scope.value for scope in list(SecretScope)]),
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
    new_scope: Optional[str] = None,
    remove_keys: List[str] = [],
    interactive: bool = False,
    values: str = "",
) -> None:
    """Update a secret for a given name or id.

    Args:
        name_or_id: The name or id of the secret to update.
        new_scope: The new scope of the secret.
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

    declare(
        f"Updating secret with name '{secret.name}' and ID '{secret.id}' in "
        f"scope '{secret.scope.value}:"
    )

    if "name" in parsed_args:
        error("The word 'name' cannot be used as a key for a secret.")

    if interactive:
        if parsed_args:
            error(
                "Cannot pass secret fields as arguments when using "
                "interactive mode."
            )

        declare(
            "You will now have a chance to update each secret pair "
            "one by one."
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
        new_scope=SecretScope(new_scope) if new_scope else None,
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
    "--scope",
    "-s",
    type=click.Choice([scope.value for scope in list(SecretScope)]),
    default=None,
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
    scope: Optional[str] = None,
    filename: Optional[str] = None,
) -> None:
    """Export a secret as a YAML file.

    The resulting YAML file can then be imported as a new secret using the
    `zenml secret create <new_secret_name> -v @<filename>` command.

    Args:
        name_id_or_prefix: The name of the secret to export.
        scope: The scope of the secret to export.
        filename: The name of the file to export the secret to.
    """
    from zenml.utils.yaml_utils import write_yaml

    secret = _get_secret(name_id_or_prefix=name_id_or_prefix, scope=scope)
    if not secret.secret_values:
        warning(f"Secret with name `{name_id_or_prefix}` is empty.")
        return

    filename = filename or f"{secret.name}.yaml"
    write_yaml(filename, secret.secret_values)
    declare(f"Secret '{secret.name}' successfully exported to '{filename}'.")
