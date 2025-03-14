#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Service connector CLI commands."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union, cast
from uuid import UUID

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import (
    is_sorted_or_filtered,
    list_options,
    print_page_info,
)
from zenml.client import Client
from zenml.console import console
from zenml.enums import CliCategories
from zenml.exceptions import AuthorizationException, IllegalOperationError
from zenml.models import (
    ServiceConnectorFilter,
    ServiceConnectorRequest,
    ServiceConnectorResourcesModel,
    ServiceConnectorResponse,
)
from zenml.utils.time_utils import seconds_to_human_readable, utc_now


# Service connectors
@cli.group(
    cls=TagGroup,
    tag=CliCategories.IDENTITY_AND_SECURITY,
)
def service_connector() -> None:
    """Configure and manage service connectors."""


def prompt_connector_name(
    default_name: Optional[str] = None, connector: Optional[UUID] = None
) -> str:
    """Prompt the user for a service connector name.

    Args:
        default_name: The default name to use if the user doesn't provide one.
        connector: The UUID of a service connector being renamed.

    Returns:
        The name provided by the user.
    """
    client = Client()

    while True:
        # Ask for a name
        title = "Please enter a name for the service connector"
        if connector:
            title += " or press Enter to keep the current name"

        name = click.prompt(
            title,
            type=str,
            default=default_name,
        )
        if not name:
            cli_utils.warning("The name cannot be empty")
            continue
        assert isinstance(name, str)

        # Check if the name is taken
        try:
            existing_connector = client.get_service_connector(
                name_id_or_prefix=name, allow_name_prefix_match=False
            )
        except KeyError:
            break
        else:
            if existing_connector.id == connector:
                break
            cli_utils.warning(
                f"A service connector with the name '{name}' already "
                "exists. Please choose a different name."
            )

    return name


def prompt_resource_type(available_resource_types: List[str]) -> Optional[str]:
    """Prompt the user for a resource type.

    Args:
        available_resource_types: The list of available resource types.

    Returns:
        The resource type provided by the user.
    """
    resource_type = None
    if len(available_resource_types) == 1:
        # Default to the first resource type if only one type is available
        click.echo(
            "Only one resource type is available for this connector"
            f" ({available_resource_types[0]})."
        )
        resource_type = available_resource_types[0]
    else:
        # Ask the user to select a resource type
        while True:
            resource_type = click.prompt(
                "Please select a resource type or leave it empty to create "
                "a connector that can be used to access any of the "
                "supported resource types "
                f"({', '.join(available_resource_types)}).",
                type=str,
                default="",
            )
            if resource_type and resource_type not in available_resource_types:
                cli_utils.warning(
                    f"The entered resource type '{resource_type}' is not "
                    "one of the listed values. Please try again."
                )
                continue
            break

        if resource_type == "":
            resource_type = None

    return resource_type


def prompt_resource_id(
    resource_name: str, resource_ids: List[str]
) -> Optional[str]:
    """Prompt the user for a resource ID.

    Args:
        resource_name: The name of the resource.
        resource_ids: The list of available resource IDs.

    Returns:
        The resource ID provided by the user.
    """
    resource_id: Optional[str] = None
    if resource_ids:
        resource_ids_list = "\n - " + "\n - ".join(resource_ids)
        prompt = (
            f"The following {resource_name} instances "
            "are reachable through this connector:"
            f"{resource_ids_list}\n"
            "Please select one or leave it empty to create a "
            "connector that can be used to access any of them"
        )
        while True:
            # Ask the user to enter an optional resource ID
            resource_id = click.prompt(
                prompt,
                default="",
                type=str,
            )
            if (
                not resource_ids
                or not resource_id
                or resource_id in resource_ids
            ):
                break

            cli_utils.warning(
                f"The selected '{resource_id}' value is not one of "
                "the listed values. Please try again."
            )
    else:
        prompt = (
            "The connector configuration can be used to access "
            f"multiple {resource_name} instances. If you "
            "would like to limit the scope of the connector to one "
            "instance, please enter the name of a particular "
            f"{resource_name} instance. Or leave it "
            "empty to create a multi-instance connector that can "
            f"be used to access any {resource_name}"
        )
        resource_id = click.prompt(
            prompt,
            default="",
            type=str,
        )

    if resource_id == "":
        resource_id = None

    return resource_id


def prompt_expiration_time(
    min: Optional[int] = None,
    max: Optional[int] = None,
    default: Optional[int] = None,
) -> int:
    """Prompt the user for an expiration time.

    Args:
        min: The minimum allowed expiration time.
        max: The maximum allowed expiration time.
        default: The default expiration time.

    Returns:
        The expiration time provided by the user.
    """
    if min is None:
        min = 0
    min_str = f"min: {min} = {seconds_to_human_readable(min)}; "
    if max is not None:
        max_str = str(max)
        max_str = f"max: {max} = {seconds_to_human_readable(max)}"
    else:
        max = -1
        max_str = "max: unlimited"
    if default:
        default_str = (
            f"; default: {default} = {seconds_to_human_readable(default)}"
        )
    else:
        default_str = ""

    while True:
        expiration_seconds = click.prompt(
            "The authentication method involves generating "
            "temporary credentials. Please enter the time that "
            "the credentials should be valid for, in seconds "
            f"({min_str}{max_str}{default_str})",
            type=int,
            default=default,
        )

        assert expiration_seconds is not None
        assert isinstance(expiration_seconds, int)
        if expiration_seconds < min:
            cli_utils.warning(
                f"The expiration time must be at least "
                f"{min} seconds. Please enter a larger value."
            )
            continue
        if max > 0 and expiration_seconds > max:
            cli_utils.warning(
                f"The expiration time must not exceed "
                f"{max} seconds. Please enter a smaller value."
            )
            continue

        confirm = click.confirm(
            f"Credentials will be valid for "
            f"{seconds_to_human_readable(expiration_seconds)}. Keep this "
            "value?",
            default=True,
        )
        if confirm:
            break

    return expiration_seconds


def prompt_expires_at(
    default: Optional[datetime] = None,
) -> Optional[datetime]:
    """Prompt the user for an expiration timestamp.

    Args:
        default: The default expiration time.

    Returns:
        The expiration time provided by the user.
    """
    if default is None:
        confirm = click.confirm(
            "Are the credentials you configured temporary? If so, you'll be asked "
            "to provide an expiration time in the next step.",
            default=False,
        )
        if not confirm:
            return None

    while True:
        default_str = ""
        if default is not None:
            seconds = int(
                (default - utc_now(tz_aware=default)).total_seconds()
            )
            default_str = (
                f" [{str(default)} i.e. in "
                f"{seconds_to_human_readable(seconds)}]"
            )

        expires_at = click.prompt(
            "Please enter the exact UTC date and time when the credentials "
            f"will expire e.g. '2023-12-31 23:59:59'{default_str}",
            type=click.DateTime(),
            default=default,
            show_default=False,
        )

        assert expires_at is not None
        assert isinstance(expires_at, datetime)
        if expires_at < utc_now(tz_aware=expires_at):
            cli_utils.warning(
                "The expiration time must be in the future. Please enter a "
                "later date and time."
            )
            continue

        seconds = int(
            (expires_at - utc_now(tz_aware=expires_at)).total_seconds()
        )

        confirm = click.confirm(
            f"Credentials will be valid until {str(expires_at)} UTC (i.e. "
            f"in {seconds_to_human_readable(seconds)}. Keep this value?",
            default=True,
        )
        if confirm:
            break

    return expires_at


@service_connector.command(
    "register",
    context_settings={"ignore_unknown_options": True},
    help="""Configure, validate and register a service connector.

This command can be used to configure and register a ZenML service connector and
to optionally verify that the service connector configuration and credentials
are valid and can be used to access the specified resource(s).

If the `-i|--interactive` flag is set, it will prompt the user for all the
information required to configure a service connector in a wizard-like fashion:

    $ zenml service-connector register -i

To trim down the amount of information displayed in interactive mode, pass the
`-n|--no-docs` flag:

    $ zenml service-connector register -ni

Secret configuration attributes are not shown by default. Use the
`-x|--show-secrets` flag to show them:

    $ zenml service-connector register -ix

Non-interactive examples:

- register a multi-purpose AWS service connector capable of accessing
any of the resource types that it supports (e.g. S3 buckets, EKS Kubernetes
clusters) using auto-configured credentials (i.e. extracted from the environment
variables or AWS CLI configuration files):

    $ zenml service-connector register aws-auto-multi --description \\
"Multi-purpose AWS connector" --type aws --auto-configure \\
--label auto=true --label purpose=multi

- register a Docker service connector providing access to a single DockerHub
repository named `dockerhub-hyppo` using explicit credentials:

    $ zenml service-connector register dockerhub-hyppo --description \\
"Hyppo's DockerHub repo" --type docker --resource-id dockerhub-hyppo \\
--username=hyppo --password=mypassword

- register an AWS service connector providing access to all the S3 buckets
that it's authorized to access using IAM role credentials:

    $ zenml service-connector register aws-s3-multi --description \\   
"Multi-bucket S3 connector" --type aws --resource-type s3-bucket \\    
--auth_method iam-role --role_arn=arn:aws:iam::<account>:role/<role> \\
--aws_region=us-east-1 --aws-access-key-id=<aws-key-id> \\            
--aws_secret_access_key=<aws-secret-key> --expiration-seconds 3600

All registered service connectors are validated before being registered. To
skip validation, pass the `--no-verify` flag.
""",
)
@click.argument(
    "name",
    type=str,
    required=False,
)
@click.option(
    "--description",
    "description",
    help="Short description for the connector instance.",
    required=False,
    type=str,
)
@click.option(
    "--type",
    "-t",
    "connector_type",
    help="The service connector type.",
    required=False,
    type=str,
)
@click.option(
    "--resource-type",
    "-r",
    "resource_type",
    help="The type of resource to connect to.",
    required=False,
    type=str,
)
@click.option(
    "--resource-id",
    "-ri",
    "resource_id",
    help="The ID of the resource to connect to.",
    required=False,
    type=str,
)
@click.option(
    "--auth-method",
    "-a",
    "auth_method",
    help="The authentication method to use.",
    required=False,
    type=str,
)
@click.option(
    "--expires-at",
    "expires_at",
    help="The exact UTC date and time when the credentials configured for this "
    "connector will expire. Takes the form 'YYYY-MM-DD HH:MM:SS'. This is only "
    "required if you are configuring a service connector with expiring "
    "credentials.",
    required=False,
    type=click.DateTime(),
)
@click.option(
    "--expires-skew-tolerance",
    "expires_skew_tolerance",
    help="The tolerance, in seconds, allowed when determining when the "
    "credentials configured for or generated by this connector will expire.",
    required=False,
    type=int,
)
@click.option(
    "--expiration-seconds",
    "expiration_seconds",
    help="The duration, in seconds, that the temporary credentials "
    "generated by this connector should remain valid.",
    required=False,
    type=int,
)
@click.option(
    "--label",
    "-l",
    "labels",
    help="Labels to be associated with the service connector. Takes the form "
    "-l key1=value1 and can be used multiple times.",
    multiple=True,
)
@click.option(
    "--no-verify",
    "no_verify",
    is_flag=True,
    default=False,
    help="Do not verify the service connector before registering.",
    type=click.BOOL,
)
@click.option(
    "--interactive",
    "-i",
    "interactive",
    is_flag=True,
    default=False,
    help="Register a new service connector interactively.",
    type=click.BOOL,
)
@click.option(
    "--no-docs",
    "-n",
    "no_docs",
    is_flag=True,
    default=False,
    help="Don't show documentation details during the interactive "
    "configuration.",
    type=click.BOOL,
)
@click.option(
    "--show-secrets",
    "-x",
    "show_secrets",
    is_flag=True,
    default=False,
    help="Show security sensitive configuration attributes in the terminal.",
    type=click.BOOL,
)
@click.option(
    "--auto-configure",
    "auto_configure",
    is_flag=True,
    default=False,
    help="Auto configure the service connector.",
    type=click.BOOL,
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def register_service_connector(
    name: Optional[str],
    args: List[str],
    description: Optional[str] = None,
    connector_type: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    auth_method: Optional[str] = None,
    expires_at: Optional[datetime] = None,
    expires_skew_tolerance: Optional[int] = None,
    expiration_seconds: Optional[int] = None,
    no_verify: bool = False,
    labels: Optional[List[str]] = None,
    interactive: bool = False,
    no_docs: bool = False,
    show_secrets: bool = False,
    auto_configure: bool = False,
) -> None:
    """Registers a service connector.

    Args:
        name: The name to use for the service connector.
        args: Configuration arguments for the service connector.
        description: Short description for the service connector.
        connector_type: The service connector type.
        resource_type: The type of resource to connect to.
        resource_id: The ID of the resource to connect to.
        auth_method: The authentication method to use.
        expires_at: The exact UTC date and time when the credentials configured
            for this connector will expire.
        expires_skew_tolerance: The tolerance, in seconds, allowed when
            determining when the credentials configured for or generated by
            this connector will expire.
        expiration_seconds: The duration, in seconds, that the temporary
            credentials generated by this connector should remain valid.
        no_verify: Do not verify the service connector before
            registering.
        labels: Labels to be associated with the service connector.
        interactive: Register a new service connector interactively.
        no_docs: Don't show documentation details during the interactive
            configuration.
        show_secrets: Show security sensitive configuration attributes in
            the terminal.
        auto_configure: Auto configure the service connector.

    Raises:
        TypeError: If the connector_model does not have the correct type.
    """
    from rich.markdown import Markdown

    client = Client()

    # Parse the given args
    name, parsed_args = cli_utils.parse_name_and_extra_arguments(
        list(args) + [name or ""],
        expand_args=True,
        name_mandatory=not interactive,
    )

    # Parse the given labels
    parsed_labels = cast(Dict[str, str], cli_utils.get_parsed_labels(labels))

    if interactive:
        # Get the list of available service connector types
        connector_types = client.list_service_connector_types(
            connector_type=connector_type,
            resource_type=resource_type,
            auth_method=auth_method,
        )
        if not connector_types:
            cli_utils.error(
                "No service connectors found with the given parameters: "
                + f"type={connector_type} "
                if connector_type
                else "" + f"resource_type={resource_type} "
                if resource_type
                else "" + f"auth_method={auth_method} "
                if auth_method
                else "",
            )

        # Ask for a connector name
        name = prompt_connector_name(name)

        # Ask for a description
        description = click.prompt(
            "Please enter a description for the service connector",
            type=str,
            default="",
        )

        available_types = {c.connector_type: c for c in connector_types}
        if len(available_types) == 1:
            # Default to the first connector type if not supplied and if
            # only one type is available
            connector_type = connector_type or list(available_types.keys())[0]

        # Print the name, type and description of all available service
        # connectors
        if not no_docs:
            message = "# Available service connector types\n"
            for spec in connector_types:
                message += cli_utils.print_service_connector_type(
                    connector_type=spec,
                    heading="##",
                    footer="",
                    include_auth_methods=False,
                    include_resource_types=False,
                    print=False,
                )
            console.print(Markdown(f"{message}---"), justify="left", width=80)

        # Ask the user to select a service connector type
        connector_type = click.prompt(
            "Please select a service connector type",
            type=click.Choice(list(available_types.keys())),
            default=connector_type,
        )

        assert connector_type is not None
        connector_type_spec = available_types[connector_type]

        available_resource_types = [
            t.resource_type for t in connector_type_spec.resource_types
        ]

        if not no_docs:
            # Print the name, resource type identifiers and description of all
            # available resource types
            message = "# Available resource types\n"
            for r in connector_type_spec.resource_types:
                message += cli_utils.print_service_connector_resource_type(
                    resource_type=r,
                    heading="##",
                    footer="",
                    print=False,
                )
            console.print(Markdown(f"{message}---"), justify="left", width=80)

        # Ask the user to select a resource type
        resource_type = prompt_resource_type(
            available_resource_types=available_resource_types
        )

        # Ask the user whether to use autoconfiguration, if the connector
        # implementation is locally available and if autoconfiguration is
        # supported
        if (
            connector_type_spec.supports_auto_configuration
            and connector_type_spec.local
        ):
            auto_configure = click.confirm(
                "Would you like to attempt auto-configuration to extract the "
                "authentication configuration from your local environment ?",
                default=False,
            )
        else:
            auto_configure = False

        connector_model: Optional[
            Union[ServiceConnectorRequest, ServiceConnectorResponse]
        ] = None
        connector_resources: Optional[ServiceConnectorResourcesModel] = None
        if auto_configure:
            # Try to autoconfigure the service connector
            try:
                with console.status("Auto-configuring service connector...\n"):
                    (
                        connector_model,
                        connector_resources,
                    ) = client.create_service_connector(
                        name=name,
                        description=description or "",
                        connector_type=connector_type,
                        resource_type=resource_type,
                        auth_method=auth_method,
                        expires_skew_tolerance=expires_skew_tolerance,
                        auto_configure=True,
                        verify=True,
                        register=False,
                    )

                assert connector_model is not None
                assert connector_resources is not None
            except (
                KeyError,
                ValueError,
                IllegalOperationError,
                NotImplementedError,
                AuthorizationException,
            ) as e:
                cli_utils.warning(
                    f"Auto-configuration was not successful: {e} "
                )
                # Ask the user whether to continue with manual configuration
                manual = click.confirm(
                    "Would you like to continue with manual configuration ?",
                    default=True,
                )
                if not manual:
                    return
            else:
                auth_method = connector_model.auth_method
                expiration_seconds = connector_model.expiration_seconds
                expires_at = connector_model.expires_at
                cli_utils.declare(
                    "Service connector auto-configured successfully with the "
                    "following configuration:"
                )

                # Print the configuration detected by the autoconfiguration
                # process
                # TODO: Normally, this could have been handled with setter
                #   functions over the connector type property in the response
                #   model. However, pydantic breaks property setter functions.
                #   We can find a more elegant solution here.
                if isinstance(connector_model, ServiceConnectorResponse):
                    connector_model.set_connector_type(connector_type_spec)
                elif isinstance(connector_model, ServiceConnectorRequest):
                    connector_model.connector_type = connector_type_spec
                else:
                    raise TypeError(
                        "The service connector must be an instance of either"
                        "`ServiceConnectorResponse` or "
                        "`ServiceConnectorRequest`."
                    )

                cli_utils.print_service_connector_configuration(
                    connector_model,
                    active_status=False,
                    show_secrets=show_secrets,
                )
                cli_utils.declare(
                    "The service connector configuration has access to the "
                    "following resources:"
                )
                cli_utils.print_service_connector_resource_table(
                    [connector_resources],
                    show_resources_only=True,
                )

                # Ask the user whether to continue with the autoconfiguration
                choice = click.prompt(
                    "Would you like to continue with the auto-discovered "
                    "configuration or switch to manual ?",
                    type=click.Choice(["auto", "manual"]),
                    default="auto",
                )
                if choice == "manual":
                    # Reset the connector configuration to default to let the
                    # manual configuration kick in the next step
                    connector_model = None
                    connector_resources = None
                    expires_at = None

        if connector_model is not None and connector_resources is not None:
            assert auth_method is not None
            auth_method_spec = connector_type_spec.auth_method_dict[
                auth_method
            ]
        else:
            # In this branch, we are either not using autoconfiguration or the
            # autoconfiguration failed or was dismissed. In all cases, we need
            # to ask the user for the authentication method to use and then
            # prompt for the configuration

            auth_methods = list(connector_type_spec.auth_method_dict.keys())

            if not no_docs:
                # Print the name, identifier and description of all available
                # auth methods
                message = "# Available authentication methods\n"
                for a in auth_methods:
                    message += cli_utils.print_service_connector_auth_method(
                        auth_method=connector_type_spec.auth_method_dict[a],
                        heading="##",
                        footer="",
                        print=False,
                    )
                console.print(
                    Markdown(f"{message}---"), justify="left", width=80
                )

            if len(auth_methods) == 1:
                # Default to the first auth method if only one method is
                # available
                confirm = click.confirm(
                    "Only one authentication method is available for this "
                    f"connector ({auth_methods[0]}). Would you like to use it?",
                    default=True,
                )
                if not confirm:
                    return

                auth_method = auth_methods[0]
            else:
                # Ask the user to select an authentication method
                auth_method = click.prompt(
                    "Please select an authentication method",
                    type=click.Choice(auth_methods),
                    default=auth_method,
                )

            assert auth_method is not None
            auth_method_spec = connector_type_spec.auth_method_dict[
                auth_method
            ]

            cli_utils.declare(
                f"Please enter the configuration for the {auth_method_spec.name} "
                "authentication method."
            )

            # Prompt for the configuration of the selected authentication method
            # field by field
            config_schema = auth_method_spec.config_schema or {}
            config_dict = cli_utils.prompt_configuration(
                config_schema=config_schema,
                show_secrets=show_secrets,
            )

            # Prompt for an expiration time if the auth method supports it
            if auth_method_spec.supports_temporary_credentials():
                expiration_seconds = prompt_expiration_time(
                    min=auth_method_spec.min_expiration_seconds,
                    max=auth_method_spec.max_expiration_seconds,
                    default=auth_method_spec.default_expiration_seconds,
                )

            # Prompt for the time when the credentials will expire
            expires_at = prompt_expires_at(expires_at)

            try:
                # Validate the connector configuration and fetch all available
                # resources that are accessible with the provided configuration
                # in the process
                with console.status(
                    "Validating service connector configuration...\n"
                ):
                    (
                        connector_model,
                        connector_resources,
                    ) = client.create_service_connector(
                        name=name,
                        description=description or "",
                        connector_type=connector_type,
                        auth_method=auth_method,
                        resource_type=resource_type,
                        configuration=config_dict,
                        expires_at=expires_at,
                        expires_skew_tolerance=expires_skew_tolerance,
                        expiration_seconds=expiration_seconds,
                        auto_configure=False,
                        verify=True,
                        register=False,
                    )
                assert connector_model is not None
                assert connector_resources is not None
            except (
                KeyError,
                ValueError,
                IllegalOperationError,
                NotImplementedError,
                AuthorizationException,
            ) as e:
                cli_utils.error(f"Failed to configure service connector: {e}")

        if resource_type:
            # Finally, for connectors that are configured with a particular
            # resource type, prompt the user to select one of the available
            # resources that can be accessed with the connector. We don't do
            # need to do this for resource types that don't support instances.
            resource_type_spec = connector_type_spec.resource_type_dict[
                resource_type
            ]
            if resource_type_spec.supports_instances:
                assert len(connector_resources.resources) == 1
                resource_ids = connector_resources.resources[0].resource_ids
                assert resource_ids is not None
                resource_id = prompt_resource_id(
                    resource_name=resource_type_spec.name,
                    resource_ids=resource_ids,
                )
            else:
                resource_id = None
        else:
            resource_id = None

        # Prepare the rest of the variables to fall through to the
        # non-interactive configuration case
        parsed_args = connector_model.configuration
        parsed_args.update(
            {
                k: s.get_secret_value()
                for k, s in connector_model.secrets.items()
                if s is not None
            }
        )
        auto_configure = False
        no_verify = False
        expiration_seconds = connector_model.expiration_seconds

    if not connector_type:
        cli_utils.error(
            "The connector type must be specified when using non-interactive "
            "configuration."
        )

    with console.status(f"Registering service connector '{name}'...\n"):
        try:
            # Create a new service connector
            assert name is not None
            (
                connector_model,
                connector_resources,
            ) = client.create_service_connector(
                name=name,
                connector_type=connector_type,
                auth_method=auth_method,
                resource_type=resource_type,
                configuration=parsed_args,
                resource_id=resource_id,
                description=description or "",
                expires_skew_tolerance=expires_skew_tolerance,
                expiration_seconds=expiration_seconds,
                expires_at=expires_at,
                labels=parsed_labels,
                verify=not no_verify,
                auto_configure=auto_configure,
                register=True,
            )
        except (
            KeyError,
            ValueError,
            IllegalOperationError,
            NotImplementedError,
            AuthorizationException,
        ) as e:
            cli_utils.error(f"Failed to register service connector: {e}")

    if connector_resources is not None:
        cli_utils.declare(
            f"Successfully registered service connector `{name}` with access "
            "to the following resources:"
        )

        cli_utils.print_service_connector_resource_table(
            [connector_resources],
            show_resources_only=True,
        )

    else:
        cli_utils.declare(
            f"Successfully registered service connector `{name}`."
        )


@service_connector.command(
    "list",
    help="""List available service connectors.
""",
)
@list_options(ServiceConnectorFilter)
@click.option(
    "--label",
    "-l",
    "labels",
    help="Label to filter by. Takes the form `-l key1=value1` or `-l key` and "
    "can be used multiple times.",
    multiple=True,
)
@click.pass_context
def list_service_connectors(
    ctx: click.Context, labels: Optional[List[str]] = None, **kwargs: Any
) -> None:
    """List all service connectors.

    Args:
        ctx: The click context object
        labels: Labels to filter by.
        kwargs: Keyword arguments to filter the components.
    """
    client = Client()

    if labels:
        kwargs["labels"] = cli_utils.get_parsed_labels(
            labels, allow_label_only=True
        )

    connectors = client.list_service_connectors(**kwargs)
    if not connectors:
        cli_utils.declare("No service connectors found for the given filters.")
        return

    cli_utils.print_service_connectors_table(
        client=client,
        connectors=connectors.items,
        show_active=not is_sorted_or_filtered(ctx),
    )
    print_page_info(connectors)


@service_connector.command(
    "describe",
    help="""Show detailed information about a service connector.

Display detailed information about a service connector configuration, or about
a service connector client generated from it to access a specific resource
(explained below).

Service connector clients are connector configurations generated from the
original service connectors that are actually used by clients to access a
specific target resource (e.g. an AWS connector generates a Kubernetes connector
client to access a specific EKS Kubernetes cluster). Unlike main service
connectors, connector clients are not persisted in the database. They have a
limited lifetime and may contain temporary credentials to access the target
resource (e.g. an AWS connector configured with an AWS secret key and IAM role
generates a connector client containing temporary STS credentials).

Asking to see service connector client details is equivalent to asking to see
the final configuration that the client sees, as opposed to the configuration
that was configured by the user. In some cases, they are the same, in others
they are completely different.

To show the details of a service connector client instead of the base connector
use the `--client` flag. If the service connector is configured to provide
access to multiple resources, you also need to use the `--resource-type` and
`--resource-id` flags to specify the scope of the connector client.

Secret configuration attributes are not shown by default. Use the
`-x|--show-secrets` flag to show them.
""",
)
@click.argument(
    "name_id_or_prefix",
    type=str,
    required=True,
)
@click.option(
    "--show-secrets",
    "-x",
    "show_secrets",
    is_flag=True,
    default=False,
    help="Show security sensitive configuration attributes in the terminal.",
    type=click.BOOL,
)
@click.option(
    "--client",
    "-c",
    "describe_client",
    is_flag=True,
    default=False,
    help="Fetch and describe a service connector client instead of the base "
    "connector.",
    type=click.BOOL,
)
@click.option(
    "--resource-type",
    "-r",
    "resource_type",
    help="Resource type to use when fetching the service connector client.",
    required=False,
    type=str,
)
@click.option(
    "--resource-id",
    "-ri",
    "resource_id",
    help="Resource ID to use when fetching the service connector client.",
    required=False,
    type=str,
)
def describe_service_connector(
    name_id_or_prefix: str,
    show_secrets: bool = False,
    describe_client: bool = False,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
) -> None:
    """Prints details about a service connector.

    Args:
        name_id_or_prefix: Name or id of the service connector to describe.
        show_secrets: Whether to show security sensitive configuration
            attributes in the terminal.
        describe_client: Fetch and describe a service connector client
            instead of the base connector if possible.
        resource_type: Resource type to use when fetching the service connector
            client.
        resource_id: Resource ID to use when fetching the service connector
            client.
    """
    client = Client()

    if resource_type or resource_id:
        describe_client = True

    if describe_client:
        try:
            connector_client = client.get_service_connector_client(
                name_id_or_prefix=name_id_or_prefix,
                resource_type=resource_type,
                resource_id=resource_id,
                verify=True,
            )
        except (
            KeyError,
            ValueError,
            IllegalOperationError,
            NotImplementedError,
            AuthorizationException,
        ) as e:
            resource_type = resource_type or "<unspecified>"
            resource_id = resource_id or "<unspecified>"
            cli_utils.error(
                f"Failed fetching a service connector client for connector "
                f"'{name_id_or_prefix}', resource type '{resource_type}' and "
                f"resource ID '{resource_id}': {e}"
            )

        connector = connector_client.to_response_model(
            user=client.active_user,
        )
    else:
        try:
            connector = client.get_service_connector(
                name_id_or_prefix=name_id_or_prefix,
                load_secrets=True,
            )
        except KeyError as err:
            cli_utils.error(str(err))

    with console.status(f"Describing connector '{connector.name}'..."):
        active_stack = client.active_stack_model
        active_connector_ids: List[UUID] = []
        for components in active_stack.components.values():
            active_connector_ids.extend(
                [
                    component.connector.id
                    for component in components
                    if component.connector
                ]
            )

        cli_utils.print_service_connector_configuration(
            connector=connector,
            active_status=connector.id in active_connector_ids,
            show_secrets=show_secrets,
        )


@service_connector.command(
    "update",
    context_settings={"ignore_unknown_options": True},
    help="""Update and verify an existing service connector.

This command can be used to update an existing ZenML service connector and
to optionally verify that the updated service connector configuration and
credentials are still valid and can be used to access the specified resource(s).

If the `-i|--interactive` flag is set, it will prompt the user for all the
information required to update the service connector configuration:

    $ zenml service-connector update -i <connector-name-or-id>

For consistency reasons, the connector type cannot be changed. If you need to
change the connector type, you need to create a new service connector.
You also cannot change the authentication method, resource type and resource ID
of a service connector that is already actively being used by one or more stack
components.

Secret configuration attributes are not shown by default. Use the
`-x|--show-secrets` flag to show them:

    $ zenml service-connector update -ix <connector-name-or-id>

Non-interactive examples:

- update the DockerHub repository that a Docker service connector is configured
to provide access to:

    $ zenml service-connector update dockerhub-hyppo --resource-id lylemcnew

- update the AWS credentials that an AWS service connector is configured to
use from an STS token to an AWS secret key. This involves updating some config
values and deleting others:

    $ zenml service-connector update aws-auto-multi \\
--aws_access_key_id=<aws-key-id> \\
--aws_secret_access_key=<aws-secret-key>  \\
--remove-attr aws-sts-token

- update the foo label to a new value and delete the baz label from a connector:

    $ zenml service-connector update gcp-eu-multi \\                          
--label foo=bar --label baz

All service connectors updates are validated before being applied. To skip
validation, pass the `--no-verify` flag.
""",
)
@click.argument(
    "name_id_or_prefix",
    type=str,
    required=True,
)
@click.option(
    "--name",
    "name",
    help="New connector name.",
    required=False,
    type=str,
)
@click.option(
    "--description",
    "description",
    help="Short description for the connector instance.",
    required=False,
    type=str,
)
@click.option(
    "--resource-type",
    "-r",
    "resource_type",
    help="The type of resource to connect to.",
    required=False,
    type=str,
)
@click.option(
    "--resource-id",
    "-ri",
    "resource_id",
    help="The ID of the resource to connect to.",
    required=False,
    type=str,
)
@click.option(
    "--auth-method",
    "-a",
    "auth_method",
    help="The authentication method to use.",
    required=False,
    type=str,
)
@click.option(
    "--expires-at",
    "expires_at",
    help="The time at which the credentials configured for this connector "
    "will expire.",
    required=False,
    type=click.DateTime(),
)
@click.option(
    "--expires-skew-tolerance",
    "expires_skew_tolerance",
    help="The tolerance, in seconds, allowed when determining when the "
    "credentials configured for or generated by this connector will expire.",
    required=False,
    type=int,
)
@click.option(
    "--expiration-seconds",
    "expiration_seconds",
    help="The duration, in seconds, that the temporary credentials "
    "generated by this connector should remain valid.",
    required=False,
    type=int,
)
@click.option(
    "--label",
    "-l",
    "labels",
    help="Labels to be associated with the service connector. Takes the form "
    "`-l key1=value1` or `-l key1` and can be used multiple times.",
    multiple=True,
)
@click.option(
    "--no-verify",
    "no_verify",
    is_flag=True,
    default=False,
    help="Do not verify the service connector before registering.",
    type=click.BOOL,
)
@click.option(
    "--interactive",
    "-i",
    "interactive",
    is_flag=True,
    default=False,
    help="Register a new service connector interactively.",
    type=click.BOOL,
)
@click.option(
    "--show-secrets",
    "-x",
    "show_secrets",
    is_flag=True,
    default=False,
    help="Show security sensitive configuration attributes in the terminal.",
    type=click.BOOL,
)
@click.option(
    "--remove-attr",
    "-r",
    "remove_attrs",
    help="Configuration attributes to be removed from the configuration. Takes "
    "the form `-r attr-name` and can be used multiple times.",
    multiple=True,
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def update_service_connector(
    args: List[str],
    name_id_or_prefix: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    connector_type: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    auth_method: Optional[str] = None,
    expires_at: Optional[datetime] = None,
    expires_skew_tolerance: Optional[int] = None,
    expiration_seconds: Optional[int] = None,
    no_verify: bool = False,
    labels: Optional[List[str]] = None,
    interactive: bool = False,
    show_secrets: bool = False,
    remove_attrs: Optional[List[str]] = None,
) -> None:
    """Updates a service connector.

    Args:
        args: Configuration arguments for the service connector.
        name_id_or_prefix: The name or ID of the service connector to
            update.
        name: New connector name.
        description: Short description for the service connector.
        connector_type: The service connector type.
        resource_type: The type of resource to connect to.
        resource_id: The ID of the resource to connect to.
        auth_method: The authentication method to use.
        expires_at: The time at which the credentials configured for this
            connector will expire.
        expires_skew_tolerance: The tolerance, in seconds, allowed when
            determining when the credentials configured for or generated by
            this connector will expire.
        expiration_seconds: The duration, in seconds, that the temporary
            credentials generated by this connector should remain valid.
        no_verify: Do not verify the service connector before
            updating.
        labels: Labels to be associated with the service connector.
        interactive: Register a new service connector interactively.
        show_secrets: Show security sensitive configuration attributes in
            the terminal.
        remove_attrs: Configuration attributes to be removed from the
            configuration.
    """
    client = Client()

    # Parse the given args
    name_id_or_prefix, parsed_args = cli_utils.parse_name_and_extra_arguments(
        list(args) + [name_id_or_prefix or ""],
        expand_args=True,
        name_mandatory=True,
    )
    assert name_id_or_prefix is not None

    # Parse the given labels
    parsed_labels = cli_utils.get_parsed_labels(labels, allow_label_only=True)

    # Start by fetching the existing connector configuration
    try:
        connector = client.get_service_connector(
            name_id_or_prefix,
            allow_name_prefix_match=False,
            load_secrets=True,
        )
    except KeyError as e:
        cli_utils.error(str(e))

    if interactive:
        # Fetch the connector type specification if not already embedded
        # into the connector model
        if isinstance(connector.connector_type, str):
            try:
                connector_type_spec = client.get_service_connector_type(
                    connector.connector_type
                )
            except KeyError as e:
                cli_utils.error(
                    "Could not find the connector type "
                    f"'{connector.connector_type}' associated with the "
                    f"'{connector.name}' connector: {e}."
                )
        else:
            connector_type_spec = connector.connector_type

        # Ask for a new name, if needed
        name = prompt_connector_name(connector.name, connector=connector.id)

        # Ask for a new description, if needed
        description = click.prompt(
            "Updated service connector description",
            type=str,
            default=connector.description,
        )

        # Ask for a new authentication method
        auth_method = click.prompt(
            "If you would like to update the authentication method, please "
            "select a new one from the following options, otherwise press "
            "enter to keep the existing one. Please note that changing "
            "the authentication method may invalidate the existing "
            "configuration and credentials and may require you to reconfigure "
            "the connector from scratch",
            type=click.Choice(
                list(connector_type_spec.auth_method_dict.keys()),
            ),
            default=connector.auth_method,
        )

        assert auth_method is not None
        auth_method_spec = connector_type_spec.auth_method_dict[auth_method]

        # If the authentication method has changed, we need to reconfigure
        # the connector from scratch; otherwise, we ask the user if they
        # want to update the existing configuration
        if auth_method != connector.auth_method:
            confirm = True
        else:
            confirm = click.confirm(
                "Would you like to update the authentication configuration?",
                default=False,
            )

        existing_config = connector.full_configuration

        if confirm:
            # Here we reconfigure the connector or update the existing
            # configuration. The existing configuration is used as much
            # as possible to avoid the user having to re-enter the same
            # values from scratch.

            cli_utils.declare(
                f"Please update or verify the existing configuration for the "
                f"'{auth_method_spec.name}' authentication method."
            )

            # Prompt for the configuration of the selected authentication method
            # field by field
            config_schema = auth_method_spec.config_schema or {}
            config_dict = cli_utils.prompt_configuration(
                config_schema=config_schema,
                show_secrets=show_secrets,
                existing_config=existing_config,
            )

        else:
            config_dict = existing_config

        # Next, we address resource type updates. If the connector is
        # configured to access a single resource type, we don't need to
        # ask the user for a new resource type. We only look at the
        # resource types that support the selected authentication method.
        available_resource_types = [
            r.resource_type
            for r in connector_type_spec.resource_types
            if auth_method in r.auth_methods
        ]
        if len(available_resource_types) == 1:
            resource_type = available_resource_types[0]
        else:
            if connector.is_multi_type:
                resource_type = None
                title = (
                    "The connector is configured to access any of the supported "
                    f"resource types ({', '.join(available_resource_types)}). "
                    "Would you like to restrict it to a single resource type?"
                )
            else:
                resource_type = connector.resource_types[0]
                title = (
                    "The connector is configured to access the "
                    f"{resource_type} resource type. "
                    "Would you like to change that?"
                )
            confirm = click.confirm(title, default=False)

            if confirm:
                # Prompt for a new resource type, if needed
                resource_type = prompt_resource_type(
                    available_resource_types=available_resource_types
                )

        # Prompt for a new expiration time if the auth method supports it
        expiration_seconds = None
        if auth_method_spec.supports_temporary_credentials():
            expiration_seconds = prompt_expiration_time(
                min=auth_method_spec.min_expiration_seconds,
                max=auth_method_spec.max_expiration_seconds,
                default=connector.expiration_seconds
                or auth_method_spec.default_expiration_seconds,
            )

        # Prompt for the time when the credentials will expire
        expires_at = prompt_expires_at(expires_at or connector.expires_at)

        try:
            # Validate the connector configuration and fetch all available
            # resources that are accessible with the provided configuration
            # in the process
            with console.status("Validating service connector update...\n"):
                (
                    connector_model,
                    connector_resources,
                ) = client.update_service_connector(
                    name_id_or_prefix=connector.id,
                    name=name,
                    description=description,
                    auth_method=auth_method,
                    # Use empty string to indicate that the resource type
                    # should be removed in the update if not set here
                    resource_type=resource_type or "",
                    configuration=config_dict,
                    expires_at=expires_at,
                    # Use zero value to indicate that the expiration time
                    # should be removed in the update if not set here
                    expiration_seconds=expiration_seconds or 0,
                    expires_skew_tolerance=expires_skew_tolerance,
                    verify=True,
                    update=False,
                )
            assert connector_model is not None
            assert connector_resources is not None
        except (
            KeyError,
            ValueError,
            IllegalOperationError,
            NotImplementedError,
            AuthorizationException,
        ) as e:
            cli_utils.error(f"Failed to verify service connector update: {e}")

        if resource_type:
            # Finally, for connectors that are configured with a particular
            # resource type, prompt the user to select one of the available
            # resources that can be accessed with the connector. We don't need
            # to do this for resource types that don't support instances.
            resource_type_spec = connector_type_spec.resource_type_dict[
                resource_type
            ]
            if resource_type_spec.supports_instances:
                assert len(connector_resources.resources) == 1
                resource_ids = connector_resources.resources[0].resource_ids
                assert resource_ids is not None
                resource_id = prompt_resource_id(
                    resource_name=resource_type_spec.name,
                    resource_ids=resource_ids,
                )
            else:
                resource_id = None
        else:
            resource_id = None

        # Prepare the rest of the variables to fall through to the
        # non-interactive configuration case
        no_verify = False

    else:
        # Non-interactive configuration

        # Apply the configuration from the command line arguments
        config_dict = connector.full_configuration
        config_dict.update(parsed_args)

        if not resource_type and not connector.is_multi_type:
            resource_type = connector.resource_types[0]

        resource_id = resource_id or connector.resource_id
        expiration_seconds = expiration_seconds or connector.expiration_seconds

        # Remove attributes that the user has indicated should be removed
        if remove_attrs:
            for remove_attr in remove_attrs:
                config_dict.pop(remove_attr, None)
            if "resource_id" in remove_attrs or "resource-id" in remove_attrs:
                resource_id = None
            if (
                "resource_type" in remove_attrs
                or "resource-type" in remove_attrs
            ):
                resource_type = None
            if (
                "expiration_seconds" in remove_attrs
                or "expiration-seconds" in remove_attrs
            ):
                expiration_seconds = None

    with console.status(
        f"Updating service connector {name_id_or_prefix}...\n"
    ):
        try:
            (
                connector_model,
                connector_resources,
            ) = client.update_service_connector(
                name_id_or_prefix=connector.id,
                name=name,
                auth_method=auth_method,
                # Use empty string to indicate that the resource type
                # should be removed in the update if not set here
                resource_type=resource_type or "",
                configuration=config_dict,
                # Use empty string to indicate that the resource ID
                # should be removed in the update if not set here
                resource_id=resource_id or "",
                description=description,
                expires_at=expires_at,
                # Use empty string to indicate that the expiration time
                # should be removed in the update if not set here
                expiration_seconds=expiration_seconds or 0,
                expires_skew_tolerance=expires_skew_tolerance,
                labels=parsed_labels,
                verify=not no_verify,
                update=True,
            )
        except (
            KeyError,
            ValueError,
            IllegalOperationError,
            NotImplementedError,
            AuthorizationException,
        ) as e:
            cli_utils.error(f"Failed to update service connector: {e}")

    if connector_resources is not None:
        cli_utils.declare(
            f"Successfully updated service connector `{connector.name}`. It "
            "can now be used to access the following resources:"
        )

        cli_utils.print_service_connector_resource_table(
            [connector_resources],
            show_resources_only=True,
        )

    else:
        cli_utils.declare(
            f"Successfully updated service connector `{connector.name}` "
        )


@service_connector.command(
    "delete",
    help="""Delete a service connector.
""",
)
@click.argument("name_id_or_prefix", type=str)
def delete_service_connector(name_id_or_prefix: str) -> None:
    """Deletes a service connector.

    Args:
        name_id_or_prefix: The name of the service connector to delete.
    """
    client = Client()

    with console.status(
        f"Deleting service connector '{name_id_or_prefix}'...\n"
    ):
        try:
            client.delete_service_connector(
                name_id_or_prefix=name_id_or_prefix,
            )
        except (KeyError, IllegalOperationError) as err:
            cli_utils.error(str(err))
        cli_utils.declare(f"Deleted service connector: {name_id_or_prefix}")


@service_connector.command(
    "verify",
    help="""Verify and list resources for a service connector.

Use this command to check if a registered ZenML service connector is correctly
configured with valid credentials and is able to actively access one or more
resources.

This command has a double purpose:

1. first, it can be used to check if a service connector is correctly configured
and has valid credentials, by actively exercising its credentials and trying to
gain access to the remote service or resource it is configured for.

2. second, it is used to fetch the list of resources that a service connector
has access to. This is useful when the service connector is configured to access
multiple resources, and you want to know which ones it has access to, or even
as a confirmation that it has access to the single resource that it is
configured for. 

You can use this command to answer questions like:

- is this connector valid and correctly configured?
- have I configured this connector to access the correct resource?
- which resources can this connector give me access to?

For connectors that are configured to access multiple types of resources, a
list of resources is not fetched, because it would be too expensive to list
all resources of all types that the connector has access to. In this case,
you can use the `--resource-type` argument to scope down the verification to
a particular resource type.

Examples:

- check if a Kubernetes service connector has access to the cluster it is
configured for:

    $ zenml service-connector verify my-k8s-connector

- check if a generic, multi-type, multi-instance AWS service connector has
access to a particular S3 bucket:

    $ zenml service-connector verify my-generic-aws-connector \\               
--resource-type s3-bucket --resource-id my-bucket

""",
)
@click.option(
    "--resource-type",
    "-r",
    "resource_type",
    help="The type of the resource for which to verify access.",
    required=False,
    type=str,
)
@click.option(
    "--resource-id",
    "-ri",
    "resource_id",
    help="The ID of the resource for which to verify access.",
    required=False,
    type=str,
)
@click.option(
    "--verify-only",
    "-v",
    "verify_only",
    help="Only verify the service connector, do not list resources.",
    required=False,
    is_flag=True,
)
@click.argument("name_id_or_prefix", type=str, required=True)
def verify_service_connector(
    name_id_or_prefix: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    verify_only: bool = False,
) -> None:
    """Verifies if a service connector has access to one or more resources.

    Args:
        name_id_or_prefix: The name or id of the service connector to verify.
        resource_type: The type of resource for which to verify access.
        resource_id: The ID of the resource for which to verify access.
        verify_only: Only verify the service connector, do not list resources.
    """
    client = Client()

    with console.status(
        f"Verifying service connector '{name_id_or_prefix}'...\n"
    ):
        try:
            resources = client.verify_service_connector(
                name_id_or_prefix=name_id_or_prefix,
                resource_type=resource_type,
                resource_id=resource_id,
                list_resources=not verify_only,
            )
        except (
            KeyError,
            ValueError,
            IllegalOperationError,
            NotImplementedError,
            AuthorizationException,
        ) as e:
            cli_utils.error(
                f"Service connector '{name_id_or_prefix}' verification failed: "
                f"{e}"
            )

    click.echo(
        f"Service connector '{name_id_or_prefix}' is correctly configured "
        f"with valid credentials and has access to the following resources:"
    )

    cli_utils.print_service_connector_resource_table(
        resources=[resources],
        show_resources_only=True,
    )


@service_connector.command(
    "login",
    help="""Configure the local client/SDK with credentials.

Some service connectors have the ability to configure clients or SDKs installed
on your local machine with credentials extracted from or generated by the
service connector. This command can be used to do that.

For connectors that are configured to access multiple types of resources or 
multiple resource instances, the resource type and resource ID must be
specified to indicate which resource is targeted by this command.

Examples:

- configure the local Kubernetes (kubectl) CLI with credentials generated from
a generic, multi-type, multi-instance AWS service connector:

    $ zenml service-connector login my-generic-aws-connector \\             
--resource-type kubernetes-cluster --resource-id my-eks-cluster

- configure the local Docker CLI with credentials configured in a Docker
service connector:

    $ zenml service-connector login my-docker-connector
""",
)
@click.option(
    "--resource-type",
    "-r",
    "resource_type",
    help="The type of resource to connect to.",
    required=False,
    type=str,
)
@click.option(
    "--resource-id",
    "-ri",
    "resource_id",
    help="Explicit resource ID to connect to.",
    required=False,
    type=str,
)
@click.argument("name_id_or_prefix", type=str, required=True)
def login_service_connector(
    name_id_or_prefix: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
) -> None:
    """Authenticate the local client/SDK with connector credentials.

    Args:
        name_id_or_prefix: The name or id of the service connector to use.
        resource_type: The type of resource to connect to.
        resource_id: Explicit resource ID to connect to.
    """
    client = Client()

    with console.status(
        "Attempting to configure local client using service connector "
        f"'{name_id_or_prefix}'...\n"
    ):
        try:
            connector = client.login_service_connector(
                name_id_or_prefix=name_id_or_prefix,
                resource_type=resource_type,
                resource_id=resource_id,
            )
        except (
            KeyError,
            ValueError,
            IllegalOperationError,
            NotImplementedError,
            AuthorizationException,
        ) as e:
            cli_utils.error(
                f"Service connector '{name_id_or_prefix}' could not configure "
                f"the local client/SDK: {e}"
            )

        spec = connector.get_type()
        resource_type = resource_type or connector.resource_type
        assert resource_type is not None
        resource_name = spec.resource_type_dict[resource_type].name
        cli_utils.declare(
            f"The '{name_id_or_prefix}' {spec.name} connector was used to "
            f"successfully configure the local {resource_name} client/SDK."
        )


@service_connector.command(
    "list-resources",
    help="""List all resources accessible by service connectors.

This command can be used to list all resources that can be accessed by the
currently registered service connectors. You can filter the list by connector
type and/or resource type.

Use this command to answer questions like:

- show a list of all Kubernetes clusters that can be accessed by way of service
connectors
- show a list of all connectors along with all the resources they can access or
the error state they are in, if any

NOTE: since this command exercises all service connectors currently registered
with ZenML, it may take a while to complete.

Examples:

- show a list of all S3 buckets that can be accessed by service connectors:

    $ zenml service-connector list-resources --resource-type s3-bucket

- show a list of all resources that the AWS connectors currently registered
with ZenML can access:

    $ zenml service-connector list-resources --connector-type aws
    
""",
)
@click.option(
    "--connector-type",
    "-c",
    "connector_type",
    help="The type of service connector to filter by.",
    required=False,
    type=str,
)
@click.option(
    "--resource-type",
    "-r",
    "resource_type",
    help="The type of resource to filter by.",
    required=False,
    type=str,
)
@click.option(
    "--resource-id",
    "-ri",
    "resource_id",
    help="The name of a resource to filter by.",
    required=False,
    type=str,
)
@click.option(
    "--exclude-errors",
    "-e",
    "exclude_errors",
    help="Exclude resources that cannot be accessed due to errors.",
    required=False,
    is_flag=True,
)
def list_service_connector_resources(
    connector_type: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    exclude_errors: bool = False,
) -> None:
    """List resources that can be accessed by service connectors.

    Args:
        connector_type: The type of service connector to filter by.
        resource_type: The type of resource to filter by.
        resource_id: The name of a resource to filter by.
        exclude_errors: Exclude resources that cannot be accessed due to
            errors.
    """
    client = Client()

    if not resource_type and not resource_id:
        cli_utils.warning(
            "Fetching all service connector resources can take a long time, "
            "depending on the number of connectors currently registered with "
            "ZenML. Consider using the '--connector-type', '--resource-type' "
            "and '--resource-id' options to narrow down the list of resources "
            "to fetch."
        )

    with console.status(
        "Fetching all service connector resources (this could take a while)...\n"
    ):
        try:
            resource_list = client.list_service_connector_resources(
                connector_type=connector_type,
                resource_type=resource_type,
                resource_id=resource_id,
            )
        except (
            KeyError,
            ValueError,
            IllegalOperationError,
            NotImplementedError,
            AuthorizationException,
        ) as e:
            cli_utils.error(
                f"Could not fetch service connector resources: {e}"
            )

        if exclude_errors:
            resource_list = [r for r in resource_list if r.error is None]

        if not resource_list:
            cli_utils.declare(
                "No service connector resources match the given filters."
            )
            return

    resource_str = ""
    if resource_type:
        resource_str = f" '{resource_type}'"
    connector_str = ""
    if connector_type:
        connector_str = f" '{connector_type}'"
    if resource_id:
        resource_str = f"{resource_str} resource with name '{resource_id}'"
    else:
        resource_str = f"following{resource_str} resources"

    click.echo(
        f"The {resource_str} can be accessed by"
        f"{connector_str} service connectors:"
    )

    cli_utils.print_service_connector_resource_table(
        resources=resource_list,
    )


@service_connector.command(
    "list-types",
    help="""List available service connector types.
""",
)
@click.option(
    "--type",
    "-t",
    "type",
    help="Filter by service connector type.",
    required=False,
    type=str,
)
@click.option(
    "--resource-type",
    "-r",
    "resource_type",
    help="Filter by the type of resource to connect to.",
    required=False,
    type=str,
)
@click.option(
    "--auth-method",
    "-a",
    "auth_method",
    help="Filter by the supported authentication method.",
    required=False,
    type=str,
)
@click.option(
    "--detailed",
    "-d",
    "detailed",
    help="Show detailed information about the service connector types.",
    required=False,
    is_flag=True,
)
def list_service_connector_types(
    type: Optional[str] = None,
    resource_type: Optional[str] = None,
    auth_method: Optional[str] = None,
    detailed: bool = False,
) -> None:
    """List service connector types.

    Args:
        type: Filter by service connector type.
        resource_type: Filter by the type of resource to connect to.
        auth_method: Filter by the supported authentication method.
        detailed: Show detailed information about the service connectors.
    """
    client = Client()

    service_connector_types = client.list_service_connector_types(
        connector_type=type,
        resource_type=resource_type,
        auth_method=auth_method,
    )

    if not service_connector_types:
        cli_utils.error(
            "No service connector types found matching the criteria."
        )

    if detailed:
        for connector_type in service_connector_types:
            cli_utils.print_service_connector_type(connector_type)
    else:
        cli_utils.print_service_connector_types_table(
            connector_types=service_connector_types
        )


@service_connector.command(
    "describe-type",
    help="""Describe a service connector type.
""",
)
@click.argument(
    "type",
    type=str,
    required=True,
)
@click.option(
    "--resource-type",
    "-r",
    "resource_type",
    help="Resource type to describe.",
    required=False,
    type=str,
)
@click.option(
    "--auth-method",
    "-a",
    "auth_method",
    help="Authentication method to describe.",
    required=False,
    type=str,
)
def describe_service_connector_type(
    type: str,
    resource_type: Optional[str] = None,
    auth_method: Optional[str] = None,
) -> None:
    """Describes a service connector type.

    Args:
        type: The connector type to describe.
        resource_type: The resource type to describe.
        auth_method: The authentication method to describe.
    """
    client = Client()

    try:
        connector_type = client.get_service_connector_type(type)
    except KeyError:
        cli_utils.error(f"Service connector type '{type}' not found.")

    if resource_type:
        if resource_type not in connector_type.resource_type_dict:
            cli_utils.error(
                f"Resource type '{resource_type}' not found for service "
                f"connector type '{type}'."
            )
        cli_utils.print_service_connector_resource_type(
            connector_type.resource_type_dict[resource_type]
        )
    elif auth_method:
        if auth_method not in connector_type.auth_method_dict:
            cli_utils.error(
                f"Authentication method '{auth_method}' not found for service"
                f" connector type '{type}'."
            )
        cli_utils.print_service_connector_auth_method(
            connector_type.auth_method_dict[auth_method]
        )
    else:
        cli_utils.print_service_connector_type(
            connector_type,
            include_resource_types=False,
            include_auth_methods=False,
        )
