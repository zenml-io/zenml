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

from typing import Any, List, Optional
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
from zenml.models import ServiceConnectorFilterModel


# Service connectors
@cli.group(
    cls=TagGroup,
    tag=CliCategories.IDENTITY_AND_SECURITY,
)
def service_connector() -> None:
    """Configure and manage service connectors."""


@service_connector.command(
    "register",
    context_settings={"ignore_unknown_options": True},
    help="""Configure, validate and register a ZenML service connector.
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
    "type",
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
    type: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    auth_method: Optional[str] = None,
    share: bool = False,
    no_verify: bool = False,
    labels: Optional[List[str]] = None,
    interactive: bool = False,
    auto_configure: bool = False,
) -> None:
    """Registers a service connector.

    Args:
        name: The name to use for the service connector.
        args: Configuration arguments for the service connector.
        description: Short description for the service connector.
        type: The service connector type.
        resource_type: The type of resource to connect to.
        resource_id: The ID of the resource to connect to.
        auth_method: The authentication method to use.
        share: Share the service connector with other users.
        no_verify: Do not verify the service connector before
            registering.
        labels: Labels to be associated with the service connector.
        interactive: Register a new service connector interactively.
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

    parsed_labels = cli_utils.get_parsed_labels(labels)

    if interactive:
        from zenml.service_connectors.service_connector_registry import (
            service_connector_registry,
        )

        # Get the list of available service connector types
        connector_types = service_connector_registry.find_service_connector(
            connector_type=type,
            resource_type=resource_type,
            auth_method=auth_method,
        )
        if not connector_types:
            cli_utils.error(
                "No service connectors found with the given parameters: "
                + f"type={type} "
                if type
                else "" + f"resource_type={resource_type} "
                if resource_type
                else "" + f"auth_method={auth_method} "
                if auth_method
                else "",
            )

        available_types = {
            c.get_specification().type: c for c in connector_types
        }
        if len(available_types) == 1:
            # Default to the first connector type if not supplied and if
            # only one type is available
            type = type or list(available_types.keys())[0]

        message = "# Available service connector types\n"
        # Print the name, type and description of all available service
        # connectors
        for c in connector_types:
            spec = c.get_specification()
            message += f"## {spec.name} ({spec.type})\n"
            message += f"{spec.description}\n"

        console.print(Markdown(f"{message}---"), justify="left", width=80)

        # Ask the user to select a service connector type
        connector_type = click.prompt(
            "Please select a service connector type",
            type=click.Choice(list(available_types.keys())),
            default=type,
        )

        connector = available_types[connector_type]
        specification = connector.get_specification()

        available_resource_types = [
            t for t in specification.resource_type_map.keys() if t
        ]

        message = (
            f"# Available resource types for connector {specification.name}\n"
        )
        # Print the name, resource type identifiers and description of all
        # available resource types
        for r in specification.resource_types:
            resource_type_str = r.resource_type or "<arbitrary>"
            message += f"## {r.name} ({resource_type_str})\n"
            message += f"{r.description}\n"

        console.print(Markdown(f"{message}---"), justify="left", width=80)

        if len(available_resource_types) == 1:
            # Default to the first resource type if not supplied and if
            # only one type is available
            resource_type = resource_type or available_resource_types[0]

        if None in specification.resource_type_map:
            # Allow arbitrary resource types
            resource_type = click.prompt(
                "Please select a resource type "
                f"({', '.join(available_resource_types)}) "
                "or enter a custom resource type",
                type=str,
                default=resource_type,
            )
        else:
            # Ask the user to select a resource type
            resource_type = click.prompt(
                "Please select a resource type",
                type=click.Choice(available_resource_types),
                default=resource_type,
            )

        assert resource_type

        if resource_type not in specification.resource_type_map:
            resource_type_spec = specification.resource_type_map[None]
        else:
            resource_type_spec = specification.resource_type_map[resource_type]

        if resource_type_spec.multi_instance:
            # Ask the user to enter an optional resource ID
            resource_id = click.prompt(
                "The selected resource type supports multiple instances. "
                "Please enter a resource ID value or leave it empty to be "
                "supplied later at runtime",
                default=resource_id or "",
                type=str,
            )
            if resource_id == "":
                resource_id = None

            if not resource_id and not no_verify:
                cli_utils.warning(
                    "You have not specified a resource ID. "
                    "The service connector will not be verified before "
                    "registration because it cannot be fully configured. "
                    "You can verify the service connector later by running "
                    "`zenml service-connector verify`."
                )
                no_verify = True

        auth_methods = resource_type_spec.auth_methods

        message = (
            "# Available authentication methods for resource "
            f"{resource_type_spec.name}\n"
        )
        # Print the name, identifier and description of all available auth
        # methods
        for a in auth_methods:
            auth_method_spec = specification.auth_method_map[a]
            message += f"## {auth_method_spec.name} ({a})\n"
            message += f"{auth_method_spec.description}\n"

        console.print(Markdown(f"{message}---"), justify="left", width=80)

        if len(auth_methods) == 1:
            # Default to the first auth method if not supplied and if
            # only one type is available
            auth_method = auth_method or auth_methods[0]

        # Ask the user to select an authentication method
        auth_method = click.prompt(
            "Please select an authentication method",
            type=click.Choice(auth_methods),
            default=auth_method,
        )
        assert auth_method
        auth_method_spec = specification.auth_method_map[auth_method]

        while True:
            # Ask for a name
            name = click.prompt(
                "Please enter a name for the service connector",
                type=str,
                default=name,
            )
            if not name:
                cli_utils.warning("The name cannot be empty")
                continue
            # Check if the name is taken
            try:
                client.get_service_connector(
                    name_id_or_prefix=name, allow_name_prefix_match=False
                )
            except KeyError:
                break
            else:
                cli_utils.warning(
                    f"A service connector with the name '{name}' already "
                    "exists. Please choose a different name."
                )

        # Ask for a description
        description = click.prompt(
            "Please enter a description for the service connector",
            type=str,
            default="",
        )

        # Ask the user whether to use auto-configuration
        auto_configure = click.confirm(
            "Would you like to attempt auto-configuration to extract the "
            "authentication configuration from your local environment ?",
            default=False,
        )

        if auto_configure:
            # Try to auto-configure the service connector
            try:
                client.create_service_connector(
                    name=name,
                    description=description or "",
                    type=connector_type,
                    resource_type=resource_type,
                    auth_method=auth_method,
                    resource_id=resource_id,
                    is_shared=share,
                    auto_configure=True,
                    verify=not no_verify,
                    labels=parsed_labels,
                )
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
                cli_utils.declare(
                    f"Successfully registered service connector `{name}`."
                )
                return

        cli_utils.declare(
            f"Please enter the configuration for the {auth_method_spec.name} "
            "authentication method."
        )

        config_schema = auth_method_spec.config_schema or {}
        config_dict = {}
        for attr_name, attr_schema in config_schema.get(
            "properties", {}
        ).items():
            title = attr_schema.get("title", attr_name)
            title = f"[{attr_name}] {title}"
            required = attr_name in config_schema.get("required", [])
            hidden = attr_schema.get("format", "") == "password"
            subtitles: List[str] = []
            if hidden:
                subtitles.append("hidden")
            if required:
                subtitles.append("required")
            else:
                subtitles.append("optional")
            if subtitles:
                title += f" {{{', '.join(subtitles)}}}"

            while True:
                # Ask the user to enter a value for the attribute
                default = parsed_args.get(
                    attr_name, "" if not required else None
                )
                value = click.prompt(
                    title,
                    type=str,
                    hide_input=hidden,
                    default=default,
                    show_default=default not in (None, ""),
                )
                if not value:
                    if required:
                        cli_utils.warning(
                            f"The attribute '{title}' is mandatory. "
                            "Please enter a non-empty value."
                        )
                        continue
                    else:
                        value = None
                        break
                else:
                    config_dict[attr_name] = value
                    break

        try:
            client.create_service_connector(
                name=name,
                description=description or "",
                type=connector_type,
                resource_type=resource_type,
                auth_method=auth_method,
                resource_id=resource_id,
                configuration=config_dict,
                is_shared=share,
                auto_configure=False,
                verify=not no_verify,
                labels=parsed_labels,
            )
        except (
            KeyError,
            ValueError,
            IllegalOperationError,
            NotImplementedError,
            AuthorizationException,
        ) as e:
            cli_utils.error(f"Failed to register service connector: {e}")
        else:
            cli_utils.declare(
                f"Successfully registered service connector `{name}`."
            )
            return

    if not type or not resource_type:
        cli_utils.error(
            "The connector type and resource type must "
            "all be specified when using non-interactive configuration."
        )

    if not auth_method and not auto_configure:
        cli_utils.error(
            "The authentication method must be specified when using "
            "non-interactive configuration and not using auto-configuration."
        )

    with console.status(f"Registering service connector '{name}'...\n"):
        try:
            # Create a new service connector
            assert name is not None
            client.create_service_connector(
                name=name,
                type=type,
                auth_method=auth_method,
                resource_type=resource_type,
                configuration=parsed_args,
                resource_id=resource_id,
                description=description or "",
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
def list_service_connectors(**kwargs: Any) -> None:
    """List all service connectors.

    Args:
        kwargs: Keyword arguments to filter the components.
    """
    client = Client()

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
    help="""Show detailed information about a service connector.
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
def describe_service_connector(
    name_id_or_prefix: str, show_secrets: bool = False
) -> None:
    """Prints details about a service connector.

    Args:
        name_id_or_prefix: Name or id of the service connector to describe.
        show_secrets: Whether to show security sensitive configuration
            attributes in the terminal.
    """
    client = Client()
    try:
        connector = client.get_service_connector(
            name_id_or_prefix=name_id_or_prefix,
        )
    except KeyError as err:
        cli_utils.error(str(err))

    if connector.secret_id:
        try:
            secret = client.get_secret(
                name_id_or_prefix=connector.secret_id,
                allow_partial_id_match=False,
                allow_partial_name_match=False,
            )
        except KeyError as err:
            cli_utils.warning(
                "Unable to retrieve secret values associated with "
                f"service connector '{connector.name}': {err}"
            )
        else:
            # Add secret values to connector configuration
            connector.secrets.update(secret.values)

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


# def generate_stack_component_update_command(
#     component_type: StackComponentType,
# ) -> Callable[[str, List[str]], None]:
#     """Generates an `update` command for the specific stack component type.

#     Args:
#         component_type: Type of the component to generate the command for.

#     Returns:
#         A function that can be used as a `click` command.
#     """
#     display_name = _component_display_name(component_type)

#     @click.argument(
#         "name_id_or_prefix",
#         type=str,
#         required=False,
#     )
#     @click.argument("args", nargs=-1, type=click.UNPROCESSED)
#     def update_stack_component_command(
#         name_id_or_prefix: Optional[str], args: List[str]
#     ) -> None:
#         """Updates a stack component.

#         Args:
#             name_id_or_prefix: The name or id of the stack component to update.
#             args: Additional arguments to pass to the update command.
#         """
#         if component_type == StackComponentType.SECRETS_MANAGER:
#             warn_deprecated_secrets_manager()

#         client = Client()

#         # Parse the given args
#         args = list(args)
#         if name_id_or_prefix:
#             args.append(name_id_or_prefix)

#         name_or_id, parsed_args = cli_utils.parse_name_and_extra_arguments(
#             args,
#             expand_args=True,
#             name_mandatory=False,
#         )

#         with console.status(f"Updating {display_name}...\n"):
#             try:
#                 updated_component = client.update_stack_component(
#                     name_id_or_prefix=name_or_id,
#                     component_type=component_type,
#                     configuration=parsed_args,
#                 )
#             except KeyError as err:
#                 cli_utils.error(str(err))

#             cli_utils.declare(
#                 f"Successfully updated {display_name} "
#                 f"`{updated_component.name}`."
#             )

#     return update_stack_component_command


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


# def generate_stack_component_remove_attribute_command(
#     component_type: StackComponentType,
# ) -> Callable[[str, List[str]], None]:
#     """Generates `remove_attribute` command for a specific stack component type.

#     Args:
#         component_type: Type of the component to generate the command for.

#     Returns:
#         A function that can be used as a `click` command.
#     """
#     display_name = _component_display_name(component_type)

#     @click.argument(
#         "name_id_or_prefix",
#         type=str,
#         required=True,
#     )
#     @click.argument("args", nargs=-1, type=click.UNPROCESSED)
#     def remove_attribute_stack_component_command(
#         name_id_or_prefix: str, args: List[str]
#     ) -> None:
#         """Removes one or more attributes from a stack component.

#         Args:
#             name_id_or_prefix: The name of the stack component to remove the
#                 attribute from.
#             args: Additional arguments to pass to the remove_attribute command.
#         """
#         if component_type == StackComponentType.SECRETS_MANAGER:
#             warn_deprecated_secrets_manager()

#         client = Client()

#         with console.status(
#             f"Updating {display_name} '{name_id_or_prefix}'...\n"
#         ):
#             try:
#                 client.update_stack_component(
#                     name_id_or_prefix=name_id_or_prefix,
#                     component_type=component_type,
#                     configuration={k: None for k in args},
#                 )
#             except (KeyError, IllegalOperationError) as err:
#                 cli_utils.error(str(err))

#             cli_utils.declare(
#                 f"Successfully updated {display_name} `{name_id_or_prefix}`."
#             )

#     return remove_attribute_stack_component_command


# def generate_stack_component_rename_command(
#     component_type: StackComponentType,
# ) -> Callable[[str, str], None]:
#     """Generates a `rename` command for the specific stack component type.

#     Args:
#         component_type: Type of the component to generate the command for.

#     Returns:
#         A function that can be used as a `click` command.
#     """
#     display_name = _component_display_name(component_type)

#     @click.argument(
#         "name_id_or_prefix",
#         type=str,
#         required=True,
#     )
#     @click.argument(
#         "new_name",
#         type=str,
#         required=True,
#     )
#     def rename_stack_component_command(
#         name_id_or_prefix: str, new_name: str
#     ) -> None:
#         """Rename a stack component.

#         Args:
#             name_id_or_prefix: The name of the stack component to rename.
#             new_name: The new name of the stack component.
#         """
#         if component_type == StackComponentType.SECRETS_MANAGER:
#             warn_deprecated_secrets_manager()

#         client = Client()

#         with console.status(
#             f"Renaming {display_name} '{name_id_or_prefix}'...\n"
#         ):
#             try:
#                 client.update_stack_component(
#                     name_id_or_prefix=name_id_or_prefix,
#                     component_type=component_type,
#                     name=new_name,
#                 )
#             except (KeyError, IllegalOperationError) as err:
#                 cli_utils.error(str(err))

#             cli_utils.declare(
#                 f"Successfully renamed {display_name} `{name_id_or_prefix}` to"
#                 f" `{new_name}`."
#             )

#     return rename_stack_component_command


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


# def generate_stack_component_copy_command(
#     component_type: StackComponentType,
# ) -> Callable[[str, str], None]:
#     """Generates a `copy` command for the specific stack component type.

#     Args:
#         component_type: Type of the component to generate the command for.

#     Returns:
#         A function that can be used as a `click` command.
#     """
#     display_name = _component_display_name(component_type)

#     @click.argument(
#         "source_component_name_id_or_prefix", type=str, required=True
#     )
#     @click.argument("target_component", type=str, required=True)
#     @track(AnalyticsEvent.COPIED_STACK_COMPONENT)
#     def copy_stack_component_command(
#         source_component_name_id_or_prefix: str,
#         target_component: str,
#     ) -> None:
#         """Copies a stack component.

#         Args:
#             source_component_name_id_or_prefix: Name or id prefix of the
#                                          component to copy.
#             target_component: Name of the copied component.
#         """
#         if component_type == StackComponentType.SECRETS_MANAGER:
#             warn_deprecated_secrets_manager()

#         client = Client()

#         with console.status(
#             f"Copying {display_name} "
#             f"`{source_component_name_id_or_prefix}`..\n"
#         ):
#             try:
#                 component_to_copy = client.get_stack_component(
#                     name_id_or_prefix=source_component_name_id_or_prefix,
#                     component_type=component_type,
#                 )
#             except KeyError as err:
#                 cli_utils.error(str(err))

#             client.create_stack_component(
#                 name=target_component,
#                 flavor=component_to_copy.flavor,
#                 component_type=component_to_copy.type,
#                 configuration=component_to_copy.configuration,
#                 is_shared=component_to_copy.is_shared,
#             )

#     return copy_stack_component_command


@service_connector.command(
    "verify",
    help="""Verify that the connector can connect to the remote resource.
""",
)
@click.option(
    "--resource-id",
    "-ri",
    "resource_id",
    help="The ID of the resource to connect to.",
    required=False,
    type=str,
)
@click.argument("name_id_or_prefix", type=str, required=False)
def verify_service_connector(
    name_id_or_prefix: str,
    resource_id: Optional[str] = None,
) -> None:
    """Verify that the connector can connect to the remote resource.

    Args:
        name_id_or_prefix: The name or id of the service connector to verify.
        resource_id: The ID of the custom resource to connect to.
    """
    client = Client()

    with console.status(
        f"Verifying service connector '{name_id_or_prefix}'...\n"
    ):
        try:
            client.verify_service_connector(
                name_id_or_prefix=name_id_or_prefix,
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

        cli_utils.declare(
            f"Service connector '{name_id_or_prefix}' verified "
            "successfully."
        )


@service_connector.command(
    "login",
    help="""Configure the local client/SDK with credentials extracted from
the service connector.
""",
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
    resource_id: Optional[str] = None,
) -> None:
    """Authenticate the local client/SDK with connector credentials.

    Args:
        name_id_or_prefix: The name or id of the service connector to use.
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

        spec = connector.get_specification()
        resource_name = spec.get_resource_spec(connector.resource_type).name
        cli_utils.declare(
            f"The '{name_id_or_prefix}' {spec.name} connector was used to "
            f"successfully configure the local {resource_name} client/SDK."
        )


# def generate_stack_component_logs_command(
#     component_type: StackComponentType,
# ) -> Callable[[str, bool], None]:
#     """Generates a `logs` command for the specific stack component type.

#     Args:
#         component_type: Type of the component to generate the command for.

#     Returns:
#         A function that can be used as a `click` command.
#     """
#     display_name = _component_display_name(component_type)

#     @click.argument("name_id_or_prefix", type=str, required=False)
#     @click.option(
#         "--follow",
#         "-f",
#         is_flag=True,
#         help="Follow the log file instead of just displaying the current logs.",
#     )
#     def stack_component_logs_command(
#         name_id_or_prefix: str, follow: bool = False
#     ) -> None:
#         """Displays stack component logs.

#         Args:
#             name_id_or_prefix: The name of the stack component to display logs
#                 for.
#             follow: Follow the log file instead of just displaying the current
#                 logs.
#         """
#         client = Client()

#         with console.status(
#             f"Fetching the logs for the {display_name} "
#             f"'{name_id_or_prefix}'...\n"
#         ):
#             try:
#                 component_model = client.get_stack_component(
#                     name_id_or_prefix=name_id_or_prefix,
#                     component_type=component_type,
#                 )
#             except KeyError as err:
#                 cli_utils.error(str(err))

#             from zenml.stack import StackComponent

#             component = StackComponent.from_model(
#                 component_model=component_model
#             )
#             log_file = component.log_file

#             if not log_file or not fileio.exists(log_file):
#                 cli_utils.warning(
#                     f"Unable to find log file for {display_name} "
#                     f"'{name_id_or_prefix}'."
#                 )
#                 return

#         if not log_file or not fileio.exists(log_file):
#             cli_utils.warning(
#                 f"Unable to find log file for {display_name} "
#                 f"'{component.name}'."
#             )
#             return

#         if follow:
#             try:
#                 with open(log_file, "r") as f:
#                     # seek to the end of the file
#                     f.seek(0, 2)

#                     while True:
#                         line = f.readline()
#                         if not line:
#                             time.sleep(0.1)
#                             continue
#                         line = line.rstrip("\n")
#                         click.echo(line)
#             except KeyboardInterrupt:
#                 cli_utils.declare(f"Stopped following {display_name} logs.")
#         else:
#             with open(log_file, "r") as f:
#                 click.echo(f.read())

#     return stack_component_logs_command


# def generate_stack_component_explain_command(
#     component_type: StackComponentType,
# ) -> Callable[[], None]:
#     """Generates an `explain` command for the specific stack component type.

#     Args:
#         component_type: Type of the component to generate the command for.

#     Returns:
#         A function that can be used as a `click` command.
#     """

#     def explain_stack_components_command() -> None:
#         """Explains the concept of the stack component."""
#         if component_type == StackComponentType.SECRETS_MANAGER:
#             warn_deprecated_secrets_manager()

#         component_module = import_module(f"zenml.{component_type.plural}")

#         if component_module.__doc__ is not None:
#             md = Markdown(component_module.__doc__)
#             console.print(md)
#         else:
#             console.print(
#                 "The explain subcommand is yet not available for "
#                 "this stack component. For more information, you can "
#                 "visit our docs page: https://docs.zenml.io/ and "
#                 "stay tuned for future releases."
#             )

#     return explain_stack_components_command


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
    from zenml.service_connectors.service_connector_registry import (
        service_connector_registry,
    )

    service_connector_types = (
        service_connector_registry.find_service_connector(
            connector_type=type,
            resource_type=resource_type,
            auth_method=auth_method,
        )
    )

    if not service_connector_types:
        cli_utils.error("No service connectors found matching the criteria.")

    if detailed:
        from rich.markdown import Markdown

        message = ""
        for connector in service_connector_types:
            filtered_auth_methods = [auth_method] if auth_method else []
            spec = connector.get_specification()
            supported_auth_methods = list(spec.auth_method_map.keys())
            supported_resource_types = list(spec.resource_type_map.keys())
            # Replace the `None` resource type with `<arbitrary>`
            if None in supported_resource_types:
                supported_resource_types.remove(None)
                supported_resource_types.append("<arbitrary>")

            message += f"# {spec.name} (connector type: {spec.type})\n"
            message += f"**Authentication methods**: {', '.join(supported_auth_methods)}\n"
            message += (
                f"**Resource types**: {', '.join(supported_resource_types)}\n"
            )
            message += f"{spec.description}\n"

            for r in spec.resource_types:
                if resource_type and not r.is_supported_resource_type(
                    resource_type
                ):
                    continue
                resource_type_str = r.resource_type or "<arbitrary>"
                message += (
                    f"## {r.name} (resource type: {resource_type_str})\n"
                )
                message += f"**Authentication methods**: {', '.join(r.auth_methods)}\n"
                message += f"{r.description}\n"
                filtered_auth_methods.extend(r.auth_methods)

            for a in spec.auth_methods:
                if a.auth_method not in filtered_auth_methods:
                    continue
                message += f"## {a.name} (auth method: {a.auth_method})\n"
                message += f"{a.description}\n"

        console.print(Markdown(f"{message}---"), justify="left", width=80)
    else:
        cli_utils.print_service_connector_types_table(
            connector_types=[
                connector.get_specification()
                for connector in service_connector_types
            ]
        )


# def generate_stack_component_flavor_register_command(
#     component_type: StackComponentType,
# ) -> Callable[[str], None]:
#     """Generates a `register` command for the flavors of a stack component.

#     Args:
#         component_type: Type of the component to generate the command for.

#     Returns:
#         A function that can be used as a `click` command.
#     """
#     command_name = component_type.value.replace("_", "-")
#     display_name = _component_display_name(component_type)

#     @click.argument(
#         "source",
#         type=str,
#         required=True,
#     )
#     def register_stack_component_flavor_command(source: str) -> None:
#         """Adds a flavor for a stack component type.

#         Example:
#             Let's say you create an artifact store flavor class `MyArtifactStoreFlavor`
#             in the file path `flavors/my_flavor.py`. You would register it as:

#             ```shell
#             zenml artifact-store flavor register flavors.my_flavor.MyArtifactStoreFlavor
#             ```

#         Args:
#             source: The source path of the flavor class in dot notation format.
#         """
#         if component_type == StackComponentType.SECRETS_MANAGER:
#             warn_deprecated_secrets_manager()

#         client = Client()

#         if not client.root:
#             cli_utils.warning(
#                 f"You're running the `zenml {command_name} flavor register` "
#                 "command without a ZenML repository. Your current working "
#                 "directory will be used as the source root relative to which "
#                 "the `source` argument is expected. To silence this warning, "
#                 "run `zenml init` at your source code root."
#             )

#         with console.status(f"Registering a new {display_name} flavor`...\n"):
#             try:
#                 # Register the new model
#                 new_flavor = client.create_flavor(
#                     source=source,
#                     component_type=component_type,
#                 )
#             except ValueError as e:
#                 root_path = Client.find_repository()
#                 cli_utils.error(
#                     f"Flavor registration failed! ZenML tried loading the module `{source}` from path "
#                     f"`{root_path}`. If this is not what you expect, then please ensure you have run "
#                     f"`zenml init` at the root of your repository.\n\nOriginal exception: {str(e)}"
#                 )

#             cli_utils.declare(
#                 f"Successfully registered new flavor '{new_flavor.name}' "
#                 f"for stack component '{new_flavor.type}'."
#             )

#     return register_stack_component_flavor_command


# def generate_stack_component_flavor_describe_command(
#     component_type: StackComponentType,
# ) -> Callable[[str], None]:
#     """Generates a `describe` command for a single flavor of a component.

#     Args:
#         component_type: Type of the component to generate the command for.

#     Returns:
#         A function that can be used as a `click` command.
#     """
#     display_name = _component_display_name(component_type)

#     @click.argument(
#         "name",
#         type=str,
#         required=True,
#     )
#     def describe_stack_component_flavor_command(name: str) -> None:
#         """Describes a flavor based on its config schema.

#         Args:
#             name: The name of the flavor.
#         """
#         if component_type == StackComponentType.SECRETS_MANAGER:
#             warn_deprecated_secrets_manager()

#         client = Client()

#         with console.status(f"Describing {display_name} flavor: {name}`...\n"):
#             flavor_model = client.get_flavor_by_name_and_type(
#                 name=name, component_type=component_type
#             )

#             cli_utils.describe_pydantic_object(flavor_model.config_schema)

#     return describe_stack_component_flavor_command


# def generate_stack_component_flavor_delete_command(
#     component_type: StackComponentType,
# ) -> Callable[[str], None]:
#     """Generates a `delete` command for a single flavor of a component.

#     Args:
#         component_type: Type of the component to generate the command for.

#     Returns:
#         A function that can be used as a `click` command.
#     """
#     display_name = _component_display_name(component_type)

#     @click.argument(
#         "name_or_id",
#         type=str,
#         required=True,
#     )
#     def delete_stack_component_flavor_command(name_or_id: str) -> None:
#         """Deletes a flavor.

#         Args:
#             name_or_id: The name of the flavor.
#         """
#         client = Client()

#         with console.status(
#             f"Deleting a {display_name} flavor: {name_or_id}`...\n"
#         ):
#             client.delete_flavor(name_or_id)

#             cli_utils.declare(f"Successfully deleted flavor '{name_or_id}'.")

#     return delete_stack_component_flavor_command


# def register_single_stack_component_cli_commands(
#     component_type: StackComponentType, parent_group: click.Group
# ) -> None:
#     """Registers all basic stack component CLI commands.

#     Args:
#         component_type: Type of the component to generate the command for.
#         parent_group: The parent group to register the commands to.
#     """
#     command_name = component_type.value.replace("_", "-")
#     singular_display_name = _component_display_name(component_type)
#     plural_display_name = _component_display_name(component_type, plural=True)

#     @parent_group.group(
#         command_name,
#         cls=TagGroup,
#         help=f"Commands to interact with {plural_display_name}.",
#         tag=CliCategories.STACK_COMPONENTS,
#     )
#     def command_group() -> None:
#         """Group commands for a single stack component type."""
#         cli_utils.print_active_config()
#         cli_utils.print_active_stack()

#     # zenml stack-component get
#     get_command = generate_stack_component_get_command(component_type)
#     command_group.command(
#         "get", help=f"Get the name of the active {singular_display_name}."
#     )(get_command)

#     # zenml stack-component describe
#     describe_command = generate_stack_component_describe_command(
#         component_type
#     )
#     command_group.command(
#         "describe",
#         help=f"Show details about the (active) {singular_display_name}.",
#     )(describe_command)

#     # zenml stack-component list
#     list_command = generate_stack_component_list_command(component_type)
#     command_group.command(
#         "list", help=f"List all registered {plural_display_name}."
#     )(list_command)

#     # zenml stack-component register
#     register_command = generate_stack_component_register_command(
#         component_type
#     )
#     context_settings = {"ignore_unknown_options": True}
#     command_group.command(
#         "register",
#         context_settings=context_settings,
#         help=f"Register a new {singular_display_name}.",
#     )(register_command)

#     # zenml stack-component update
#     update_command = generate_stack_component_update_command(component_type)
#     context_settings = {"ignore_unknown_options": True}
#     command_group.command(
#         "update",
#         context_settings=context_settings,
#         help=f"Update a registered {singular_display_name}.",
#     )(update_command)

#     # zenml stack-component share
#     share_command = generate_stack_component_share_command(component_type)
#     context_settings = {"ignore_unknown_options": True}
#     command_group.command(
#         "share",
#         context_settings=context_settings,
#         help=f"Share a registered {singular_display_name}.",
#     )(share_command)

#     # zenml stack-component remove-attribute
#     remove_attribute_command = (
#         generate_stack_component_remove_attribute_command(component_type)
#     )
#     context_settings = {"ignore_unknown_options": True}
#     command_group.command(
#         "remove-attribute",
#         context_settings=context_settings,
#         help=f"Remove attributes from a registered {singular_display_name}.",
#     )(remove_attribute_command)

#     # zenml stack-component rename
#     rename_command = generate_stack_component_rename_command(component_type)
#     command_group.command(
#         "rename", help=f"Rename a registered {singular_display_name}."
#     )(rename_command)

#     # zenml stack-component delete
#     delete_command = generate_stack_component_delete_command(component_type)
#     command_group.command(
#         "delete", help=f"Delete a registered {singular_display_name}."
#     )(delete_command)

#     # zenml stack-component copy
#     copy_command = generate_stack_component_copy_command(component_type)
#     command_group.command(
#         "copy", help=f"Copy a registered {singular_display_name}."
#     )(copy_command)

#     # zenml stack-component up
#     up_command = generate_stack_component_up_command(component_type)
#     command_group.command(
#         "up",
#         help=f"Provisions or resumes local resources for the "
#         f"{singular_display_name} if possible.",
#     )(up_command)

#     # zenml stack-component down
#     down_command = generate_stack_component_down_command(component_type)
#     command_group.command(
#         "down",
#         help=f"Suspends resources of the local {singular_display_name} "
#         f"deployment.",
#     )(down_command)

#     # zenml stack-component logs
#     logs_command = generate_stack_component_logs_command(component_type)
#     command_group.command(
#         "logs", help=f"Display {singular_display_name} logs."
#     )(logs_command)

#     # zenml stack-component explain
#     explain_command = generate_stack_component_explain_command(component_type)
#     command_group.command(
#         "explain", help=f"Explaining the {plural_display_name}."
#     )(explain_command)

#     # zenml stack-component flavor
#     @command_group.group(
#         "flavor", help=f"Commands to interact with {plural_display_name}."
#     )
#     def flavor_group() -> None:
#         """Group commands to handle flavors for a stack component type."""

#     # zenml stack-component flavor register
#     register_flavor_command = generate_stack_component_flavor_register_command(
#         component_type=component_type
#     )
#     flavor_group.command(
#         "register",
#         help=f"Register a new {singular_display_name} flavor.",
#     )(register_flavor_command)

#     # zenml stack-component flavor list
#     list_flavor_command = generate_stack_component_flavor_list_command(
#         component_type=component_type
#     )
#     flavor_group.command(
#         "list",
#         help=f"List all registered flavors for {plural_display_name}.",
#     )(list_flavor_command)

#     # zenml stack-component flavor describe
#     describe_flavor_command = generate_stack_component_flavor_describe_command(
#         component_type=component_type
#     )
#     flavor_group.command(
#         "describe",
#         help=f"Describe a {singular_display_name} flavor.",
#     )(describe_flavor_command)

#     # zenml stack-component flavor delete
#     delete_flavor_command = generate_stack_component_flavor_delete_command(
#         component_type=component_type
#     )
#     flavor_group.command(
#         "delete",
#         help=f"Delete a {plural_display_name} flavor.",
#     )(delete_flavor_command)


# def register_all_stack_component_cli_commands() -> None:
#     """Registers CLI commands for all stack components."""
#     for component_type in StackComponentType:
#         register_single_stack_component_cli_commands(
#             component_type, parent_group=cli
#         )


# register_all_stack_component_cli_commands()
# register_annotator_subcommands()
# register_secrets_manager_subcommands()
# register_feature_store_subcommands()
# register_model_deployer_subcommands()
# register_model_registry_subcommands()
