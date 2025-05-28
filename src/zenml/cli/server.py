#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""CLI for managing ZenML server deployments."""

import ipaddress
import re
from typing import List, Optional, Union

import click
from rich.errors import MarkupError

import zenml
from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.cli.login import login, logout
from zenml.client import Client
from zenml.config.global_config import GlobalConfiguration
from zenml.console import console
from zenml.enums import CliCategories, ServiceState, StoreType
from zenml.exceptions import AuthorizationException
from zenml.logger import get_logger
from zenml.login.credentials import ServerCredentials, ServerType
from zenml.utils.server_utils import (
    connected_to_local_server,
    get_local_server,
)

logger = get_logger(__name__)


@cli.command(
    "up",
    help="""Start the ZenML dashboard locally.

DEPRECATED: Please use `zenml login --local` instead.             
""",
)
@click.option(
    "--docker",
    is_flag=True,
    help="Start the ZenML dashboard as a Docker container instead of a local "
    "process.",
    default=False,
    type=click.BOOL,
)
@click.option(
    "--port",
    type=int,
    default=None,
    help="Use a custom TCP port value for the ZenML dashboard.",
)
@click.option(
    "--ip-address",
    type=ipaddress.ip_address,
    default=None,
    help="Have the ZenML dashboard listen on an IP address different than the "
    "localhost.",
)
@click.option(
    "--blocking",
    is_flag=True,
    help="Run the ZenML dashboard in blocking mode. The CLI will not return "
    "until the dashboard is stopped.",
    default=False,
    type=click.BOOL,
)
@click.option(
    "--image",
    type=str,
    default=None,
    help="Use a custom Docker image for the ZenML server. Only used when "
    "`--docker` is set.",
)
@click.option(
    "--ngrok-token",
    type=str,
    default=None,
    help="Specify an ngrok auth token to use for exposing the ZenML server.",
)
def up(
    docker: bool = False,
    ip_address: Union[
        ipaddress.IPv4Address, ipaddress.IPv6Address, None
    ] = None,
    port: Optional[int] = None,
    blocking: bool = False,
    image: Optional[str] = None,
    ngrok_token: Optional[str] = None,
) -> None:
    """Start the ZenML dashboard locally and connect the client to it.

    Args:
        docker: Use a docker deployment instead of the local process.
        ip_address: The IP address to bind the server to.
        port: The port to bind the server to.
        blocking: Block the CLI while the server is running.
        image: A custom Docker image to use for the server, when the
            `--docker` flag is set.
        ngrok_token: An ngrok auth token to use for exposing the ZenML dashboard
            on a public domain. Primarily used for accessing the dashboard in
            Colab.
    """
    cli_utils.warning(
        "The `zenml up` command is deprecated and will be removed in a "
        "future release. Please use the `zenml login --local` command instead."
    )

    # Calling the `zenml login` command
    cli_utils.declare("Calling `zenml login --local`...")
    login.callback(  # type: ignore[misc]
        local=True,
        docker=docker,
        ip_address=ip_address,
        port=port,
        blocking=blocking,
        image=image,
        ngrok_token=ngrok_token,
    )


@cli.command(
    "show",
    help="""Show the ZenML dashboard.

DEPRECATED: Please use `zenml server show` instead.             
""",
)
@click.option(
    "--ngrok-token",
    type=str,
    default=None,
    help="Specify an ngrok auth token to use for exposing the ZenML server.",
)
def legacy_show(ngrok_token: Optional[str] = None) -> None:
    """Show the ZenML dashboard.

    Args:
        ngrok_token: An ngrok auth token to use for exposing the ZenML dashboard
            on a public domain. Primarily used for accessing the dashboard in
            Colab.
    """
    cli_utils.warning(
        "The `zenml show` command is deprecated and will be removed in a "
        "future release. Please use the `zenml server show` command "
        "instead."
    )

    # Calling the `zenml server show` command
    cli_utils.declare("Calling `zenml server show`...")
    show(local=False, ngrok_token=ngrok_token)


@cli.command(
    "down",
    help="""Shut down the local ZenML dashboard.

DEPRECATED: Please use `zenml logout local` instead.
""",
)
def down() -> None:
    """Shut down the local ZenML dashboard."""
    cli_utils.warning(
        "The `zenml down` command is deprecated and will be removed in a "
        "future release. Please use the `zenml logout --local` command instead."
    )

    # Calling the `zenml logout` command
    cli_utils.declare("Calling `zenml logout --local`...")
    logout.callback(  # type: ignore[misc]
        local=True
    )


@cli.command(
    "status", help="Show information about the current configuration."
)
def status() -> None:
    """Show details about the current configuration."""
    from zenml.login.credentials_store import get_credentials_store
    from zenml.login.pro.client import ZenMLProClient
    from zenml.login.pro.constants import ZENML_PRO_API_URL

    gc = GlobalConfiguration()
    client = Client()
    _ = client.zen_store

    store_cfg = gc.store_configuration

    # Write about the current ZenML client
    cli_utils.declare("-----ZenML Client Status-----")
    if gc.uses_default_store():
        cli_utils.declare(
            f"Connected to the local ZenML database: '{store_cfg.url}'"
        )
    elif connected_to_local_server():
        cli_utils.declare(
            f"Connected to the local ZenML server: {store_cfg.url}"
        )
    elif re.match(r"^mysql://", store_cfg.url):
        cli_utils.declare(
            f"Connected directly to a SQL database: '{store_cfg.url}'"
        )
    else:
        credentials_store = get_credentials_store()
        server = credentials_store.get_credentials(store_cfg.url)
        if server:
            if server.type == ServerType.PRO:
                # If connected to a ZenML Pro server, refresh the server info
                pro_credentials = credentials_store.get_pro_credentials(
                    pro_api_url=server.pro_api_url or ZENML_PRO_API_URL,
                    allow_expired=False,
                )
                if pro_credentials:
                    pro_client = ZenMLProClient(pro_credentials.url)
                    pro_servers = pro_client.workspace.list(
                        url=store_cfg.url, member_only=True
                    )
                    if pro_servers:
                        credentials_store.update_server_info(
                            server_url=store_cfg.url,
                            server_info=pro_servers[0],
                        )

                cli_utils.declare(
                    f"Connected to a ZenML Pro server: `{server.server_name_hyperlink}`"
                    f" [{server.server_id_hyperlink}]"
                )

                cli_utils.declare(
                    f"  ZenML Pro Organization: {server.organization_hyperlink}"
                )
                if pro_credentials:
                    cli_utils.declare(
                        f"  ZenML Pro authentication: {pro_credentials.auth_status}"
                    )
            else:
                cli_utils.declare(
                    f"Connected to a remote ZenML server: `{server.dashboard_hyperlink}`"
                )

            cli_utils.declare(f"  Dashboard: {server.dashboard_hyperlink}")
            cli_utils.declare(f"  API: {server.api_hyperlink}")
            cli_utils.declare(f"  Server status: '{server.status}'")
            cli_utils.declare(f"  Server authentication: {server.auth_status}")

        else:
            cli_utils.declare(
                f"Connected to a remote ZenML server: [link={store_cfg.url}]"
                f"{store_cfg.url}[/link]"
            )

    try:
        client.zen_store.get_store_info()
    except Exception as e:
        cli_utils.warning(f"Error while initializing client: {e}")
    else:
        # Write about the active entities
        scope = "repository" if client.uses_local_configuration else "global"
        cli_utils.declare(f"  The active user is: '{client.active_user.name}'")

        try:
            cli_utils.declare(
                f"  The active project is: '{client.active_project.name}' ({scope})"
            )
        except RuntimeError:
            cli_utils.declare("  No active project set.")

        cli_utils.declare(
            f"  The active stack is: '{client.active_stack_model.name}' ({scope})"
        )

    if client.root:
        cli_utils.declare(f"Active repository root: {client.root}")

    # Write about the configuration files
    cli_utils.declare(f"Using configuration from: '{gc.config_directory}'")
    cli_utils.declare(
        f"Local store files are located at: '{gc.local_stores_path}'"
    )

    cli_utils.declare("\n-----Local ZenML Server Status-----")
    local_server = get_local_server()
    if local_server:
        if local_server.status:
            if local_server.status.status == ServiceState.ACTIVE:
                cli_utils.declare(
                    f"The local {local_server.config.provider} server is "
                    f"running at: {local_server.status.url}"
                )
            else:
                cli_utils.declare(
                    f"The local {local_server.config.provider} server is not "
                    "available."
                )
                cli_utils.declare(
                    f"  Server state: {local_server.status.status}"
                )
                if local_server.status.status_message:
                    cli_utils.declare(
                        f"  Status message: {local_server.status.status_message}"
                    )
        else:
            cli_utils.declare(
                f"The local {local_server.config.provider} server is not "
                "running."
            )
    else:
        cli_utils.declare("The local server has not been started.")


@cli.command(
    "connect",
    help=(
        """Connect to a remote ZenML server.

    DEPRECATED: Please use `zenml login` instead.

    Examples:

      * to re-login to the current ZenML server or connect to a ZenML Pro server:

        zenml connect

      * to log in to a particular ZenML server:

        zenml connect --url=http://zenml.example.com:8080
    """
    ),
)
@click.option(
    "--url",
    "-u",
    help="The URL where the ZenML server is running.",
    required=False,
    type=str,
)
@click.option(
    "--username",
    help="(Deprecated) The username that is used to authenticate with a ZenML "
    "server. If omitted, the web login will be used.",
    required=False,
    type=str,
)
@click.option(
    "--password",
    help="(Deprecated) The password that is used to authenticate with a ZenML "
    "server. If omitted, a prompt will be shown to enter the password.",
    required=False,
    type=str,
)
@click.option(
    "--api-key",
    help="Use an API key to authenticate with a ZenML server. If "
    "omitted, the web login will be used.",
    required=False,
    type=str,
)
@click.option(
    "--no-verify-ssl",
    is_flag=True,
    help="Whether to verify the server's TLS certificate",
    default=False,
)
@click.option(
    "--ssl-ca-cert",
    help="A path to a CA bundle file to use to verify the server's TLS "
    "certificate or the CA bundle value itself",
    required=False,
    type=str,
)
def connect(
    url: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    api_key: Optional[str] = None,
    no_verify_ssl: bool = False,
    ssl_ca_cert: Optional[str] = None,
) -> None:
    """Connect to a remote ZenML server.

    Args:
        url: The URL where the ZenML server is reachable.
        username: The username that is used to authenticate with the ZenML
            server.
        password: The password that is used to authenticate with the ZenML
            server.
        api_key: The API key that is used to authenticate with the ZenML
            server.
        no_verify_ssl: Whether to verify the server's TLS certificate.
        ssl_ca_cert: A path to a CA bundle to use to verify the server's TLS
            certificate or the CA bundle value itself.
    """
    cli_utils.warning(
        "The `zenml connect` command is deprecated and will be removed in a "
        "future release. Please use the `zenml login` command instead. "
    )

    if password is not None or username is not None:
        cli_utils.warning(
            "Connecting to a ZenML server using a username and password is "
            "insecure because the password is locally stored on your "
            "filesystem and is no longer supported. The web login workflow will "
            "be used instead. An alternative for non-interactive environments "
            "is to create and use a service account API key (see "
            "https://docs.zenml.io/how-to/manage-zenml-server/connecting-to-zenml/connect-with-a-service-account "
            "for more information)."
        )

    # Calling the `zenml login` command
    cli_utils.declare("Calling `zenml login`...")
    login.callback(  # type: ignore[misc]
        server=url,
        api_key=api_key,
        no_verify_ssl=no_verify_ssl,
        ssl_ca_cert=ssl_ca_cert,
    )


@cli.command(
    "disconnect",
    help="""Disconnect from a ZenML server.

DEPRECATED: Please use `zenml logout` instead.
""",
)
def disconnect_server() -> None:
    """Disconnect from a ZenML server."""
    cli_utils.warning(
        "The `zenml disconnect` command is deprecated and will be removed in a "
        "future release. Please use the `zenml logout` command instead."
    )

    # Calling the `zenml logout` command
    cli_utils.declare("Calling `zenml logout`...")
    logout.callback()  # type: ignore[misc]


@cli.command("logs", help="Show the logs for the local ZenML server.")
@click.option(
    "--follow",
    "-f",
    is_flag=True,
    help="Continue to output new log data as it becomes available.",
)
@click.option(
    "--tail",
    "-t",
    type=click.INT,
    default=None,
    help="Only show the last NUM lines of log output.",
)
@click.option(
    "--raw",
    "-r",
    is_flag=True,
    help="Show raw log contents (don't pretty-print logs).",
)
def logs(
    follow: bool = False,
    raw: bool = False,
    tail: Optional[int] = None,
) -> None:
    """Display the logs for a ZenML server.

    Args:
        follow: Continue to output new log data as it becomes available.
        tail: Only show the last NUM lines of log output.
        raw: Show raw log contents (don't pretty-print logs).
    """
    server = get_local_server()
    if server is None:
        cli_utils.error(
            "The local ZenML dashboard is not running. Please call `zenml "
            "login --local` first to start the ZenML dashboard locally."
        )

    from zenml.zen_server.deploy.deployer import LocalServerDeployer

    deployer = LocalServerDeployer()

    cli_utils.declare(
        f"Showing logs for the local {server.config.provider} server"
    )

    from zenml.zen_server.deploy.exceptions import (
        ServerDeploymentNotFoundError,
    )

    try:
        logs = deployer.get_server_logs(follow=follow, tail=tail)
    except ServerDeploymentNotFoundError as e:
        cli_utils.error(f"Server not found: {e}")

    for line in logs:
        # don't pretty-print log lines that are already pretty-printed
        if raw or line.startswith("\x1b["):
            console.print(line, markup=False)
        else:
            try:
                console.print(line)
            except MarkupError:
                console.print(line, markup=False)


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def server() -> None:
    """Commands for managing ZenML servers."""


@server.command(
    "list",
    help="""List all ZenML servers that this client is authenticated to.

    The CLI can be authenticated to multiple ZenML servers at the same time,
    even though it can only be connected to one server at a time. You can list
    all the ZenML servers that the client is currently authenticated to by
    using this command.

    When logged in to ZenML Pro, this list will also include all ZenML Pro
    servers that the authenticated user can access or could potentially access,
    including details such as their current state and the organization they
    belong to.

    The complete list of servers displayed by this command includes the
    following:

      * ZenML Pro servers that the authenticated ZenML Pro user can or could
        access. The client needs to be logged to ZenML Pro via
        `zenml login --pro` to access these servers.

      * ZenML servers that the client has logged in to via
        `zenml login --url` in the past.

      * the local ZenML server started with `zenml login --local`, if one is
        running.

    By default, this command does not display ZenML servers that are not
    accessible: servers that are not running, are no longer accessible due to
    an expired authentication and ZenML Pro servers where the user is not a
    member. To include these servers in the list, use the `--all` flag.
    """,
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show verbose output.",
)
@click.option(
    "--all",
    "-a",
    is_flag=True,
    help="Show all ZenML servers, including those that are not running "
    "and those with an expired authentication.",
)
@click.option(
    "--pro-api-url",
    type=str,
    default=None,
    help="Custom URL for the ZenML Pro API. Useful when disconnecting "
    "from a self-hosted ZenML Pro deployment.",
)
def server_list(
    verbose: bool = False,
    all: bool = False,
    pro_api_url: Optional[str] = None,
) -> None:
    """List all ZenML servers that this client is authorized to access.

    Args:
        verbose: Whether to show verbose output.
        all: Whether to show all ZenML servers.
        pro_api_url: Custom URL for the ZenML Pro API.
    """
    from zenml.login.credentials_store import get_credentials_store
    from zenml.login.pro.client import ZenMLProClient
    from zenml.login.pro.constants import ZENML_PRO_API_URL
    from zenml.login.pro.workspace.models import WorkspaceRead, WorkspaceStatus

    pro_api_url = pro_api_url or ZENML_PRO_API_URL
    pro_api_url = pro_api_url.rstrip("/")

    credentials_store = get_credentials_store()
    pro_token = credentials_store.get_pro_token(
        allow_expired=True, pro_api_url=pro_api_url
    )
    current_store_config = GlobalConfiguration().store_configuration

    # The list of ZenML Pro servers kept in the credentials store
    pro_servers = credentials_store.list_credentials(type=ServerType.PRO)
    # The list of regular remote ZenML servers kept in the credentials store
    servers = list(credentials_store.list_credentials(type=ServerType.REMOTE))
    # The list of local ZenML servers kept in the credentials store
    local_servers = list(
        credentials_store.list_credentials(type=ServerType.LOCAL)
    )

    if pro_token and not pro_token.expired:
        # If the ZenML Pro authentication is still valid, we include all ZenML
        # Pro servers that the current ZenML Pro user can access, even those
        # that the user has never connected to (and are therefore not stored in
        # the credentials store).

        accessible_pro_servers: List[WorkspaceRead] = []
        try:
            client = ZenMLProClient(pro_api_url)
            accessible_pro_servers = client.workspace.list(member_only=not all)
        except AuthorizationException as e:
            cli_utils.warning(f"ZenML Pro authorization error: {e}")

        # We update the list of stored ZenML Pro servers with the ones that the
        # client is a member of
        for accessible_server in accessible_pro_servers:
            for idx, stored_server in enumerate(pro_servers):
                if stored_server.server_id == accessible_server.id:
                    # All ZenML Pro servers accessible by the current ZenML Pro
                    # user have an authentication that is valid at least until
                    # the current ZenML Pro authentication token expires.
                    stored_server.update_server_info(
                        accessible_server,
                    )
                    updated_server = stored_server.model_copy()
                    # Replace the current server API token with the current
                    # ZenML Pro API token to reflect the current authentication
                    # status.
                    updated_server.api_token = pro_token
                    pro_servers[idx] = updated_server
                    break
            else:
                stored_server = ServerCredentials(
                    url=accessible_server.url or "",
                    api_token=pro_token,
                )
                stored_server.update_server_info(accessible_server)
                pro_servers.append(stored_server)

        if not all:
            accessible_pro_servers = [
                s
                for s in accessible_pro_servers
                if s.status == WorkspaceStatus.AVAILABLE
            ]

        if not accessible_pro_servers:
            cli_utils.declare(
                "No ZenML Pro servers that are accessible to the current "
                "user could be found."
            )
            if not all:
                cli_utils.declare(
                    "Hint: use the `--all` flag to show all ZenML servers, "
                    "including those that the client is not currently "
                    "authorized to access or are not running."
                )

    elif pro_servers:
        cli_utils.warning(
            "The ZenML Pro authentication has expired. Please re-login "
            "to ZenML Pro using `zenml login` to include all ZenML Pro servers "
            "that you are a member of in the list."
        )

    # We add the local server to the list of servers, if it is running
    local_server = get_local_server()
    if local_server:
        url = (
            local_server.status.url if local_server.status else None
        ) or local_server.config.url
        status = local_server.status.status if local_server.status else ""
        local_servers.append(
            ServerCredentials(
                url=url or "",
                status=status,
                version=zenml.__version__,
                server_id=GlobalConfiguration().user_id,
                server_name=f"local {local_server.config.provider} server",
            )
        )

    all_servers = pro_servers + local_servers + servers

    if not all:
        # Filter out servers that are expired or not running
        all_servers = [s for s in all_servers if s.is_available]

    if verbose:
        columns = [
            "type",
            "server_id_hyperlink",
            "server_name_hyperlink",
            "organization_hyperlink" if pro_servers else "",
            "version",
            "status",
            "dashboard_url",
            "api_hyperlink",
            "auth_status",
        ]
    elif all:
        columns = [
            "type",
            "server_id_hyperlink",
            "server_name_hyperlink",
            "organization_hyperlink" if pro_servers else "",
            "version",
            "status",
            "api_hyperlink",
        ]
    else:
        columns = [
            "type",
            "server_id_hyperlink" if pro_servers else "",
            "server_name_hyperlink",
            "organization_hyperlink" if pro_servers else "",
            "version",
            "api_hyperlink" if servers else "",
        ]

    # Remove empty columns
    columns = [c for c in columns if c]

    # Figure out if the client is already connected to one of the
    # servers in the list
    current_server: List[ServerCredentials] = []
    if current_store_config.type == StoreType.REST:
        current_server = [
            s for s in all_servers if s.url == current_store_config.url
        ]

    cli_utils.print_pydantic_models(  # type: ignore[type-var]
        all_servers,
        columns=columns,
        rename_columns={
            "server_name_hyperlink": "name",
            "server_id_hyperlink": "ID",
            "organization_hyperlink": "organization",
            "dashboard_url": "dashboard URL",
            "api_hyperlink": "API URL",
            "auth_status": "auth status",
        },
        active_models=current_server,
        show_active=True,
    )


@server.command(
    "show",
    help="Show the ZenML dashboard for the server that the client is connected to.",
)
@click.option(
    "--local",
    is_flag=True,
    help="Show the ZenML dashboard for the local server.",
    default=False,
    type=click.BOOL,
)
@click.option(
    "--ngrok-token",
    type=str,
    default=None,
    help="Specify an ngrok auth token to use for exposing the local ZenML "
    "server. Only used when `--local` is set. Primarily used for accessing the "
    "local dashboard in Colab.",
)
def show(local: bool = False, ngrok_token: Optional[str] = None) -> None:
    """Show the ZenML dashboard.

    Args:
        local: Whether to show the ZenML dashboard for the local server.
        ngrok_token: An ngrok auth token to use for exposing the ZenML dashboard
            on a public domain. Primarily used for accessing the local dashboard
            in Colab.
    """
    try:
        zenml.show(ngrok_token=ngrok_token)
    except RuntimeError as e:
        cli_utils.error(str(e))
