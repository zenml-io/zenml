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

from typing import Any, Dict, List, Optional, cast
from uuid import UUID

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import (
    list_options,
    print_page_info,
)
from zenml.client import Client
from zenml.console import console
from zenml.enums import CliCategories
from zenml.exceptions import AuthorizationException, IllegalOperationError
from zenml.models import (
    ServiceConnectorBaseModel,
    ServiceConnectorFilterModel,
    ServiceConnectorResourcesModel,
)


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
            "instance, please enter the ID of a particular "
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
    while True:
        if min is None:
            min = 0
        if max is not None:
            max_str = str(max)
        else:
            max = -1
            max_str = "unlimited"

        expiration_seconds = click.prompt(
            "The authentication method involves generating "
            "temporary credentials. Please enter the time that "
            "the credentials should be valid for, in seconds "
            f"({min}-{max_str})",
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
        break

    return expiration_seconds


@service_connector.command(
    "register",
    context_settings={"ignore_unknown_options": True},
    help="""Configure, validate and register a ZenML service connector.

This command can be used to configure and register a ZenML service connector.
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

- register a shared, multi-purpose AWS service connector capable of accessing
any of the resource types that it supports (e.g. S3 buckets, EKS Kubernetes
clusters) using auto-configured credentials (i.e. extracted from the environment
variables or AWS CLI configuration files):

    $ zenml service-connector register aws-auto-multi --description \\
"Multi-purpose AWS connector" --type aws --share --auto-configure \\
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
    "--share",
    "share",
    is_flag=True,
    default=False,
    help="Share this service connector with other users.",
    type=click.BOOL,
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
    expiration_seconds: Optional[int] = None,
    share: bool = False,
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
        expiration_seconds: The duration, in seconds, that the temporary
            credentials generated by this connector should remain valid.
        share: Share the service connector with other users.
        no_verify: Do not verify the service connector before
            registering.
        labels: Labels to be associated with the service connector.
        interactive: Register a new service connector interactively.
        no_docs: Don't show documentation details during the interactive
            configuration.
        show_secrets: Show security sensitive configuration attributes in
            the terminal.
        auto_configure: Auto configure the service connector.
    """
    from rich.markdown import Markdown

    client = Client()

    # Parse the given args
    name, parsed_args = cli_utils.parse_name_and_extra_arguments(
        list(args) + [name or ""],
        expand_args=True,
        name_mandatory=not interactive,
    )

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

        message = "# Available service connector types\n"
        # Print the name, type and description of all available service
        # connectors
        for spec in connector_types:
            message += f"## {spec.name} ({spec.connector_type})\n"
            message += f"{spec.description}\n"

        if not no_docs:
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

        message = "# Available resource types\n"
        # Print the name, resource type identifiers and description of all
        # available resource types
        for r in connector_type_spec.resource_types:
            message += f"## {r.name} ({r.resource_type})\n"
            message += f"{r.description}\n"

        if not no_docs:
            console.print(Markdown(f"{message}---"), justify="left", width=80)

        resource_type = prompt_resource_type(
            available_resource_types=available_resource_types
        )

        # Ask the user whether to use auto-configuration, if the connector
        # implementation is locally available
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

        auth_method = None
        connector_model: Optional[ServiceConnectorBaseModel] = None
        connector_resources: Optional[ServiceConnectorResourcesModel] = None
        if auto_configure:
            # Try to auto-configure the service connector
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
                        is_shared=share,
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
                cli_utils.declare(
                    "Service connector auto-configured successfully with the "
                    "following configuration:"
                )
                cli_utils.print_service_connector_configuration(
                    connector_model,
                    active_status=False,
                    show_secrets=show_secrets,
                )
                # Ask the user whether to continue with the auto configuration
                choice = click.prompt(
                    "Would you like to continue with the auto-discovered "
                    "configuration or switch to manual ?",
                    type=click.Choice(["auto", "manual"]),
                    default="auto",
                )
                if choice == "manual":
                    # Reset the auto-configured connector
                    connector_model = None
                    connector_resources = None

        if connector_model is not None and connector_resources is not None:
            assert auth_method is not None
            auth_method_spec = connector_type_spec.auth_method_map[auth_method]
        else:
            auth_methods = list(connector_type_spec.auth_method_map.keys())

            message = "# Available authentication methods\n"
            # Print the name, identifier and description of all available auth
            # methods
            for a in auth_methods:
                auth_method_spec = connector_type_spec.auth_method_map[a]
                message += f"## {auth_method_spec.name} ({a})\n"
                message += f"{auth_method_spec.description}\n"

            if not no_docs:
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
            auth_method_spec = connector_type_spec.auth_method_map[auth_method]

            cli_utils.declare(
                f"Please enter the configuration for the {auth_method_spec.name} "
                "authentication method."
            )

            config_schema = auth_method_spec.config_schema or {}
            config_dict = cli_utils.prompt_configuration(
                config_schema=config_schema,
                show_secrets=show_secrets,
            )

            if auth_method_spec.supports_temporary_credentials():
                expiration_seconds = prompt_expiration_time(
                    min=auth_method_spec.min_expiration_seconds,
                    max=auth_method_spec.max_expiration_seconds,
                    default=auth_method_spec.default_expiration_seconds,
                )

            try:
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
                        expiration_seconds=expiration_seconds,
                        is_shared=share,
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
            resource_type_spec = connector_type_spec.resource_type_map[
                resource_type
            ]
            if resource_type_spec.supports_instances:
                resource_ids: List[str] = []
                if resource_type_spec.supports_discovery:
                    assert connector_resources.resource_ids is not None
                    resource_ids = connector_resources.resource_ids

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
            client.create_service_connector(
                name=name,
                connector_type=connector_type,
                auth_method=auth_method,
                resource_type=resource_type,
                configuration=parsed_args,
                resource_id=resource_id,
                description=description or "",
                expiration_seconds=expiration_seconds,
                is_shared=share,
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

        cli_utils.declare(
            f"Successfully registered service connector `{name}`."
        )


@service_connector.command(
    "list",
    help="""List available service connectors.
""",
)
@list_options(ServiceConnectorFilterModel)
@click.option(
    "--label",
    "-l",
    "labels",
    help="Label to filter by. Takes the form `-l key1=value1` or `-l key` and "
    "can be used multiple times.",
    multiple=True,
)
def list_service_connectors(
    labels: Optional[List[str]] = None, **kwargs: Any
) -> None:
    """List all service connectors.

    Args:
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
    )
    print_page_info(connectors)


@service_connector.command(
    "describe",
    help="""Show detailed information about a service connector or a service
connector client.

Connector clients are the connector configurations generated from the original
connectors that are actually used to access a specific target resource (e.g. an
AWS connector generates a Kubernetes connector client to access a specific EKS
Kubernetes cluster). Connector clients have a limited lifetime and may contain
temporary credentials to access the target resource (e.g. an AWS connector
configured with an AWS secret key and IAM role generates a connector client
containing temporary STS credentials).

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

    if describe_client:
        try:
            connector_client = client.get_service_connector_client(
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
            resource_type = resource_type or "<unspecified>"
            resource_id = resource_id or "<unspecified>"
            cli_utils.error(
                f"Failed fetching a service connector client for connector "
                f"'{name_id_or_prefix}', resource type '{resource_type}' and "
                f"resource ID '{resource_id}': {e}"
            )

        connector = connector_client.to_response_model(
            workspace=client.active_workspace,
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
    help="""Update and verify a ZenML service connector.

This command can be used to update and verify a ZenML service connector.
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
--aws-access-key-id=<aws-key-id> \\                                 
--aws_secret_access_key=<aws-secret-key>  \\                      
--remove-attribute aws-sts-token

- update the foo label to a new value and delete the baz label from a connector:

    $ zenml service-connector update gcp-eu-multi \\                          
--label foo=bar --label baz

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
    "--remove-attribute",
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
    parsed_args: Dict[str, Optional[str]] = {}
    name_id_or_prefix, parsed_args = cli_utils.parse_name_and_extra_arguments(  # type: ignore[assignment]
        list(args) + [name_id_or_prefix or ""],
        expand_args=True,
        name_mandatory=True,
    )
    assert name_id_or_prefix is not None
    parsed_labels = cli_utils.get_parsed_labels(labels, allow_label_only=True)

    try:
        connector = client.get_service_connector(
            name_id_or_prefix,
            allow_name_prefix_match=False,
            load_secrets=True,
        )
    except KeyError as e:
        cli_utils.error(str(e))

    if interactive:

        if isinstance(connector.connector_type, str):
            connector_type_spec = client.get_service_connector_type(
                connector.connector_type
            )
        else:
            connector_type_spec = connector.connector_type

        name = prompt_connector_name(connector.name, connector=connector.id)

        # Ask for a new description
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
                list(connector_type_spec.auth_method_map.keys()),
            ),
            default=connector.auth_method,
        )

        assert auth_method is not None
        auth_method_spec = connector_type_spec.auth_method_map[auth_method]

        if auth_method != connector.auth_method:
            confirm = True
        else:
            confirm = click.confirm(
                "Would you like to update the authentication configuration?",
                default=False,
            )

        existing_config = connector.configuration.copy()
        existing_config.update(
            {
                k: v.get_secret_value()
                for k, v in connector.secrets.items()
                if v
            }
        )
        if confirm:

            cli_utils.declare(
                f"Please update or verify the existing configuration for the "
                f"'{auth_method_spec.name}' authentication method."
            )

            config_schema = auth_method_spec.config_schema or {}
            config_dict = cli_utils.prompt_configuration(
                config_schema=config_schema,
                show_secrets=show_secrets,
                existing_config=existing_config,
            )

        else:
            config_dict = existing_config

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
                    f'resource types ({", ".join(available_resource_types)}). '
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
                resource_type = prompt_resource_type(
                    available_resource_types=available_resource_types
                )

        expiration_seconds = None
        if auth_method_spec.supports_temporary_credentials():
            expiration_seconds = prompt_expiration_time(
                min=auth_method_spec.min_expiration_seconds,
                max=auth_method_spec.max_expiration_seconds,
                default=connector.expiration_seconds
                or auth_method_spec.default_expiration_seconds,
            )

        try:
            with console.status("Validating service connector update...\n"):

                (
                    connector_model,
                    connector_resources,
                ) = client.update_service_connector(
                    name_id_or_prefix=connector.id,
                    name=name,
                    description=description,
                    auth_method=auth_method,
                    resource_type=resource_type,
                    configuration=config_dict,
                    expiration_seconds=expiration_seconds,
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
            resource_type_spec = connector_type_spec.resource_type_map[
                resource_type
            ]
            if resource_type_spec.supports_instances:
                resource_ids: List[str] = []
                if resource_type_spec.supports_discovery:
                    assert connector_resources.resource_ids is not None
                    resource_ids = connector_resources.resource_ids

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
        # config_dict = connector_model.configuration
        parsed_args.update(
            {
                k: s.get_secret_value()
                for k, s in connector_model.secrets.items()
                if s is not None
            }
        )
        no_verify = False
        expiration_seconds = connector_model.expiration_seconds

    else:
        config_dict = connector.configuration.copy()
        config_dict.update(
            {
                k: v.get_secret_value()
                for k, v in connector.secrets.items()
                if v
            }
        )

        if remove_attrs:
            for remove_attr in remove_attrs:
                config_dict.pop(remove_attr, None)

        if not resource_type and not connector.is_multi_type:
            resource_type = connector.resource_types[0]

        resource_id = resource_id or connector.resource_id
        expiration_seconds = expiration_seconds or connector.expiration_seconds

    with console.status(
        f"Updating service connector {name_id_or_prefix}...\n"
    ):
        try:
            client.update_service_connector(
                name_id_or_prefix=connector.id,
                name=name,
                auth_method=auth_method,
                resource_type=resource_type,
                configuration=config_dict,
                resource_id=resource_id,
                description=description,
                expiration_seconds=expiration_seconds,
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

        cli_utils.declare(
            f"Successfully updated service connector `{connector.name}` "
        )


@service_connector.command(
    "share",
    help="""Share a service connector with other users.
""",
)
@click.argument(
    "name_id_or_prefix",
    type=str,
    required=False,
)
def share_service_connector_command(
    name_id_or_prefix: str,
) -> None:
    """Shares a service connector.

    Args:
        name_id_or_prefix: The name or id of the service connector to share.
    """
    client = Client()

    with console.status(
        f"Updating service connector '{name_id_or_prefix}'...\n"
    ):
        try:
            client.update_service_connector(
                name_id_or_prefix=name_id_or_prefix,
                is_shared=True,
            )
        except (KeyError, IllegalOperationError) as err:
            cli_utils.error(str(err))

        cli_utils.declare(
            "Successfully shared service connector " f"`{name_id_or_prefix}`."
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
    help="""Verifies if a service connector has access to one or more resources.
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
@click.argument("name_id_or_prefix", type=str, required=True)
def verify_service_connector(
    name_id_or_prefix: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
) -> None:
    """Verifies if a service connector has access to one or more resources.

    Args:
        name_id_or_prefix: The name or id of the service connector to verify.
        resource_type: The type of resource for which to verify access.
        resource_id: The ID of the resource for which to verify access.
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

        cli_utils.print_service_connector_resource_table(
            resources=[resources],
        )


@service_connector.command(
    "login",
    help="""Configure the local client/SDK with credentials extracted from
the service connector.
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
        resource_name = spec.resource_type_map[resource_type].name
        cli_utils.declare(
            f"The '{name_id_or_prefix}' {spec.name} connector was used to "
            f"successfully configure the local {resource_name} client/SDK."
        )


@service_connector.command(
    "list-resources",
    help="""List all resources that can be accessed by service connectors.
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
def list_service_connector_resources(
    connector_type: Optional[str] = None,
    resource_type: Optional[str] = None,
) -> None:
    """List resources that can be accessed by service connectors.

    Args:
        connector_type: The type of service connector to filter by.
        resource_type: The type of resource to filter by.
    """
    client = Client()

    with console.status("Fetching service connector resources...\n"):
        try:
            resource_list = client.list_service_connector_resources(
                connector_type=connector_type,
                resource_type=resource_type,
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

        if not resource_list:
            cli_utils.declare(
                "No service connector resources found for the given filters."
            )
            return

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
    help="Show detailed information about the service connectors.",
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
        cli_utils.error("No service connectors found matching the criteria.")

    if detailed:
        for connector_type in service_connector_types:
            cli_utils.print_service_connector_type(connector_type)
    else:
        cli_utils.print_service_connector_types_table(
            connector_types=service_connector_types
        )


@service_connector.command(
    "get-type",
    help="""Describe a service connector type.
""",
)
@click.argument(
    "type",
    type=str,
    required=True,
)
def describe_service_connector_type(type: str) -> None:
    """Describes a service connector type.

    Args:
        type: The connector type to describe.
    """
    client = Client()

    try:
        connector_type = client.get_service_connector_type(type)
    except KeyError:
        cli_utils.error(f"Service connector type '{type}' not found.")

    cli_utils.print_service_connector_type(connector_type)
