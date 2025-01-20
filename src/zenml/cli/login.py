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
import os
import re
import sys
import time
from typing import Any, Dict, Optional, Tuple, Union
from uuid import UUID

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import cli
from zenml.config.global_config import GlobalConfiguration
from zenml.console import console
from zenml.enums import ServerProviderType, StoreType
from zenml.exceptions import (
    AuthorizationException,
    CredentialsNotValid,
    IllegalOperationError,
)
from zenml.logger import get_logger
from zenml.login.credentials import ServerType
from zenml.login.pro.constants import ZENML_PRO_API_URL
from zenml.login.web_login import web_login
from zenml.zen_server.utils import (
    connected_to_local_server,
    get_local_server,
    show_dashboard,
)

logger = get_logger(__name__)


def start_local_server(
    docker: bool = False,
    ip_address: Union[
        ipaddress.IPv4Address, ipaddress.IPv6Address, None
    ] = None,
    port: Optional[int] = None,
    blocking: bool = False,
    image: Optional[str] = None,
    ngrok_token: Optional[str] = None,
    restart: bool = False,
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
        restart: Restart the local ZenML server if it is already running.
    """
    from zenml.zen_server.deploy.deployer import LocalServerDeployer

    if docker:
        from zenml.utils.docker_utils import check_docker

        if not check_docker():
            cli_utils.error(
                "Docker does not seem to be installed on your system. Please "
                "install Docker to use the Docker ZenML server local "
                "deployment or use one of the other deployment options."
            )
        provider = ServerProviderType.DOCKER
    else:
        if sys.platform == "win32" and not blocking:
            cli_utils.error(
                "Running the ZenML server locally as a background process is "
                "not supported on Windows. Please use the `--blocking` flag "
                "to run the server in blocking mode, or run the server in "
                "a Docker container by setting `--docker` instead."
            )
        else:
            pass
        provider = ServerProviderType.DAEMON
    if cli_utils.requires_mac_env_var_warning():
        cli_utils.error(
            "The `OBJC_DISABLE_INITIALIZE_FORK_SAFETY` environment variable "
            "is recommended to run the ZenML server locally on a Mac. "
            "Please set it to `YES` and try again."
        )

    deployer = LocalServerDeployer()

    config_attrs: Dict[str, Any] = dict(
        provider=provider,
    )
    if not docker:
        config_attrs["blocking"] = blocking
    elif image:
        config_attrs["image"] = image
    if port is not None:
        config_attrs["port"] = port
    if ip_address is not None:
        config_attrs["ip_address"] = ip_address

    from zenml.zen_server.deploy.deployment import LocalServerDeploymentConfig

    server_config = LocalServerDeploymentConfig(**config_attrs)
    if blocking:
        deployer.remove_server()
        cli_utils.declare(
            "The local ZenML dashboard is about to deploy in a "
            "blocking process."
        )

    server = deployer.deploy_server(server_config, restart=restart)

    if not blocking:
        deployer.connect_to_server()

        if server.status and server.status.url:
            cli_utils.declare(
                f"The local ZenML dashboard is available at "
                f"'{server.status.url}'."
            )
            show_dashboard(
                local=True,
                ngrok_token=ngrok_token,
            )


def connect_to_server(
    url: str,
    api_key: Optional[str] = None,
    verify_ssl: Union[str, bool] = True,
    refresh: bool = False,
    pro_server: bool = False,
) -> None:
    """Connect the client to a ZenML server or a SQL database.

    Args:
        url: The URL of the ZenML server or the SQL database to connect to.
        api_key: The API key to use to authenticate with the ZenML server.
        verify_ssl: Whether to verify the server's TLS certificate. If a string
            is passed, it is interpreted as the path to a CA bundle file.
        refresh: Whether to force a new login flow with the ZenML server.
        pro_server: Whether the server is a ZenML Pro server.
    """
    from zenml.login.credentials_store import get_credentials_store
    from zenml.zen_stores.base_zen_store import BaseZenStore

    url = url.rstrip("/")

    store_type = BaseZenStore.get_store_type(url)
    if store_type == StoreType.REST:
        from zenml.zen_stores.rest_zen_store import RestZenStoreConfiguration

        credentials_store = get_credentials_store()
        if api_key:
            cli_utils.declare(
                f"Authenticating to ZenML server '{url}' using an API key..."
            )
            credentials_store.set_api_key(url, api_key)
        elif pro_server:
            # We don't have to do anything here assuming the user has already
            # logged in to the ZenML Pro server using the ZenML Pro web login
            # flow.
            cli_utils.declare(f"Authenticating to ZenML server '{url}'...")
        else:
            if refresh or not credentials_store.has_valid_authentication(url):
                cli_utils.declare(
                    f"Authenticating to ZenML server '{url}' using the web "
                    "login..."
                )
                web_login(url=url, verify_ssl=verify_ssl)
            else:
                cli_utils.declare(f"Connecting to ZenML server '{url}'...")

        rest_store_config = RestZenStoreConfiguration(
            url=url,
            verify_ssl=verify_ssl,
        )
        try:
            GlobalConfiguration().set_store(rest_store_config)
        except IllegalOperationError:
            cli_utils.error(
                f"You do not have sufficient permissions to "
                f"access the server at '{url}'."
            )
        except CredentialsNotValid as e:
            cli_utils.error(f"Authorization error: {e}")

    else:
        from zenml.zen_stores.sql_zen_store import SqlZenStoreConfiguration

        # Connect to a SQL database
        sql_store_config = SqlZenStoreConfiguration(
            url=url,
        )
        cli_utils.declare(f"Connecting to SQL database '{url}'...")

        try:
            GlobalConfiguration().set_store(sql_store_config)
        except IllegalOperationError:
            cli_utils.warning(
                f"You do not have sufficient permissions to "
                f"access the SQL database at '{url}'."
            )
        except CredentialsNotValid as e:
            cli_utils.warning(f"Authorization error: {e}")

        cli_utils.declare(f"Connected to SQL database '{url}'")


def connect_to_pro_server(
    pro_server: Optional[str] = None,
    api_key: Optional[str] = None,
    refresh: bool = False,
    pro_api_url: Optional[str] = None,
) -> None:
    """Connect the client to a ZenML Pro server.

    Args:
        pro_server: The UUID, name or URL of the ZenML Pro server to connect to.
            If not provided, the web login flow will be initiated.
        api_key: The API key to use to authenticate with the ZenML Pro server.
        refresh: Whether to force a new login flow with the ZenML Pro server.
        pro_api_url: The URL for the ZenML Pro API.

    Raises:
        ValueError: If incorrect parameters are provided.
        AuthorizationException: If the user does not have access to the ZenML
            Pro server.
    """
    from zenml.login.credentials_store import get_credentials_store
    from zenml.login.pro.client import ZenMLProClient
    from zenml.login.pro.tenant.models import TenantStatus

    pro_api_url = pro_api_url or ZENML_PRO_API_URL

    server_id, server_url, server_name = None, None, None
    login = False
    if not pro_server:
        login = True
        if api_key:
            raise ValueError(
                "You must provide the URL of the ZenML Pro server when "
                "connecting with an API key."
            )

    elif not re.match(r"^https?://", pro_server):
        # The server argument is not a URL, so it must be a ZenML Pro server
        # name or UUID.
        try:
            server_id = UUID(pro_server)
        except ValueError:
            # The server argument is not a UUID, so it must be a ZenML Pro
            # server name.
            server_name = pro_server
    else:
        server_url = pro_server

    credentials_store = get_credentials_store()
    if not credentials_store.has_valid_pro_authentication(pro_api_url):
        # Without valid ZenML Pro credentials, we can only connect to a ZenML
        # Pro server with an API key and we also need to know the URL of the
        # server to connect to.
        if api_key:
            if server_url:
                connect_to_server(server_url, api_key=api_key, pro_server=True)
                return
            else:
                raise ValueError(
                    "You must provide the URL of the ZenML Pro server when "
                    "connecting with an API key."
                )
        else:
            login = True

    if login or refresh:
        try:
            token = web_login(
                pro_api_url=pro_api_url,
            )
        except AuthorizationException as e:
            cli_utils.error(f"Authorization error: {e}")

        cli_utils.declare(
            "You can now run 'zenml server list' to view the available ZenML "
            "Pro servers and then 'zenml login <server-url-name-or-id>' to "
            "connect to a specific server without having to log in again until "
            "your session expires."
        )

        tenant_id: Optional[str] = None
        if token.device_metadata:
            tenant_id = token.device_metadata.get("tenant_id")

        if tenant_id is None and pro_server is None:
            # This is not really supposed to happen, because the implementation
            # of the web login workflow should always return a tenant ID, but
            # we're handling it just in case.
            cli_utils.declare(
                "A valid server was not selected during the login process. "
                "Please run `zenml server list` to display a list of available "
                "servers and then `zenml login <server-url-name-or-id>` to "
                "connect to a server."
            )
            return

        # The server selected during the web login process overrides any
        # server argument passed to the command.
        server_id = UUID(tenant_id)

    client = ZenMLProClient(pro_api_url)

    if server_id:
        server = client.tenant.get(server_id)
    elif server_url:
        servers = client.tenant.list(url=server_url, member_only=True)
        if not servers:
            raise AuthorizationException(
                f"The '{server_url}' URL belongs to a ZenML Pro server, "
                "but it doesn't look like you have access to it. Please "
                "check the server URL and your permissions and try again."
            )

        server = servers[0]
    elif server_name:
        servers = client.tenant.list(tenant_name=server_name, member_only=True)
        if not servers:
            raise AuthorizationException(
                f"No ZenML Pro server with the name '{server_name}' exists "
                "or you don't have access to it. Please check the server name "
                "and your permissions and try again."
            )
        server = servers[0]
    else:
        raise ValueError(
            "No server ID, URL, or name was provided. Please provide one of "
            "these values to connect to a ZenML Pro server."
        )

    server_id = server.id

    if server.status == TenantStatus.PENDING:
        with console.status(
            f"Waiting for your `{server.name}` ZenML Pro server to be set up..."
        ):
            timeout = 180  # 3 minutes
            while True:
                time.sleep(5)
                server = client.tenant.get(server_id)
                if server.status != TenantStatus.PENDING:
                    break
                timeout -= 5
                if timeout <= 0:
                    cli_utils.error(
                        f"Your `{server.name}` ZenML Pro server is taking "
                        "longer than expected to set up. Please try again "
                        "later or manage the server state by visiting the "
                        f"ZenML Pro dashboard at {server.dashboard_url}."
                    )

    if server.status == TenantStatus.FAILED:
        cli_utils.error(
            f"Your `{server.name}` ZenML Pro server is currently in a "
            "failed state. Please manage the server state by visiting the "
            f"ZenML Pro dashboard at {server.dashboard_url}, or contact "
            "your server administrator."
        )

    elif server.status == TenantStatus.DEACTIVATED:
        cli_utils.error(
            f"Your `{server.name}` ZenML Pro server is currently "
            "deactivated. Please manage the server state by visiting the "
            f"ZenML Pro dashboard at {server.dashboard_url}, or contact "
            "your server administrator."
        )

    elif server.status == TenantStatus.AVAILABLE:
        if not server.url:
            cli_utils.error(
                f"The ZenML Pro server '{server.name}' is not currently "
                f"running. Visit the ZenML Pro dashboard to manage the server "
                f"status at: {server.dashboard_url}"
            )
    else:
        cli_utils.error(
            f"Your `{server.name}` ZenML Pro server is currently "
            "being deleted. Please select a different server or set up a "
            "new server by visiting the ZenML Pro dashboard at "
            f"{server.dashboard_organization_url}."
        )

    cli_utils.declare(
        f"Connecting to ZenML Pro server: {server.name} [{str(server.id)}] "
    )

    connect_to_server(server.url, api_key=api_key, pro_server=True)

    # Update the stored server info with more accurate data taken from the
    # ZenML Pro tenant object.
    credentials_store.update_server_info(server.url, server)

    cli_utils.declare(f"Connected to ZenML Pro server: {server.name}.")


def is_pro_server(
    url: str,
) -> Tuple[Optional[bool], Optional[str]]:
    """Check if the server at the given URL is a ZenML Pro server.

    Args:
        url: The URL of the server to check.

    Returns:
        True if the server is a ZenML Pro server, False otherwise, and the
        extracted pro API URL if the server is a ZenML Pro server, or None if
        no information could be extracted.
    """
    from zenml.login.credentials_store import get_credentials_store
    from zenml.login.server_info import get_server_info

    # First, check the credentials store
    credentials_store = get_credentials_store()
    credentials = credentials_store.get_credentials(url)
    if credentials:
        if credentials.type == ServerType.PRO:
            return True, credentials.pro_api_url
        else:
            return False, None

    # Next, make a request to the server itself
    server_info = get_server_info(url)
    if not server_info:
        return None, None

    if server_info.is_pro_server():
        return True, server_info.pro_api_url

    return False, None


def _fail_if_authentication_environment_variables_set() -> None:
    """Fail if any of the authentication environment variables are set."""
    environment_variables = [
        "ZENML_STORE_URL",
        "ZENML_STORE_API_KEY",
        "ZENML_STORE_USERNAME",
        "ZENML_STORE_PASSWORD",
    ]

    if any(env_var in os.environ for env_var in environment_variables):
        cli_utils.error(
            "You're running to login/logout while having one of the "
            f"{environment_variables} environment variables set. "
            "If you want to use those environment variables to authenticate "
            "to your ZenML server, there is no need to login/logout, you can "
            "start interacting with your server right away. If you want to use "
            "the `zenml login` command for authentication, please unset these "
            "environment variables first."
        )


@cli.command(
    "login",
    help=(
        """Login to a ZenML server.

    Call `zenml login` to connect and authenticate your client to a ZenML
    server. This can be used with ZenML Pro servers or self-hosted ZenML
    servers. The same command can also be used to start and connect to a
    local ZenML server deployment running on your machine and managed by the
    ZenML CLI.

    Quick start:

      * To connect to a ZenML Pro server, simply run: `zenml login`. This
        also works if you have never signed up for ZenML Pro before and is a
        great way to get started with the ZenML Pro trial in less than 2 minutes
        hassle-free.
        
      * To connect to any remote ZenML server, run: `zenml login <server-url>`

      * To start a local ZenML server and connect to it, run:
        `zenml login --local`

    When used without any arguments, the command has a different behavior based
    on the current client state:

      * if the client is not connected to a non-local ZenML server, the command
        will take the user to the ZenML Pro login / signup page to authenticate
        and connect to a ZenML Pro server.

      * if the client is already connected to a non-local ZenML server, the
        command triggers a new web login flow with the same server. This allows
        you to simply call `zenml login` again when your CLI session expires to
        refresh the current session and continue using the same server. The
        `--pro` flag can be used to launch a ZenML Pro server login regardless
        of the current client state.
    
    This command accepts an optional SERVER argument. This is meant to
    be used to log in to a specific ZenML server and easily switch between
    different ZenML servers that the client is already logged in to.
    The SERVER argument can be one of the following:

      * a URL to a ZenML server

      * a ZenML Pro server name

      * a ZenML Pro server UUID

      * a SQL database URL in the format `mysql://<username>:<password>@<host>:<port>/<database>`

    NOTE: Passing a SERVER argument will not trigger a web login flow if the
    current session is still valid. To force a new login flow to be triggered
    to re-authenticate with the target server regardless of the current CLI
    session state, you can pass the `--refresh` flag.

    The CLI can be authenticated to multiple ZenML servers at the same time,
    even though it can only be connected to one server at a time. You can list
    all the ZenML servers that the client is currently authenticated to by
    running `zenml server list`. Any of these servers can be used as the SERVER
    argument to connect to them.

    When the `--local` flag is used, the command will start a local ZenML
    server running as a daemon process or a Docker container on your machine.
    The following options can be used to customize the local server deployment:

      * `--blocking`: run the local ZenML server in blocking mode. Use this to
        run the server as a foreground process instead of a daemon. The CLI will
        not return until the server exits or is stopped with CTRL+C

      * `--docker`: start the local ZenML server as a Docker container instead
        of a local process

      * `--port`: use a custom TCP port value for the local ZenML server

      * `--ip-address`: have the local ZenML server listen on an IP address
        different than the default localhost

      * `--image`: use a custom Docker image for the local Docker server. Only
        relevant when `--docker` is also set

      * `--ngrok-token`: specify an ngrok auth token to use for exposing the
        local ZenML dashboard on a public domain. Primarily used for accessing
        the dashboard in Google Colab

      * `--restart`: force a restart of the local ZenML server.

    The `--api-key` flag can be used to authenticate with a ZenML server using
    an API key instead of the web login flow.

    Examples:

      * connect to a ZenML Pro server using the web login flow:

        zenml login

      * connect to a remote ZenML server using the web login flow:

        zenml login https://zenml.example.com

      * start a local ZenML server running as a background daemon process and
        connect to it:

        zenml login --local

      * start a local ZenML server running as a docker container and
        connect to it:

        zenml login --local --docker

      * login and connect to a ZenML server with an API key:

        zenml login https://zenml.example.com --api-key
    """
    ),
)
@click.argument("server", type=str, required=False)
@click.option(
    "--pro",
    is_flag=True,
    help="Login to ZenML Pro.",
    default=False,
    type=click.BOOL,
)
@click.option(
    "--refresh",
    is_flag=True,
    help="Force a new login flow with the ZenML server, even if the client "
    "is already authenticated.",
    default=False,
    type=click.BOOL,
)
@click.option(
    "--api-key",
    help="Use an API key to authenticate with a ZenML server. If "
    "omitted, the web login will be used. If set, you will be prompted "
    "to enter the API key.",
    is_flag=True,
    default=False,
    type=click.BOOL,
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
@click.option(
    "--local",
    is_flag=True,
    help="Start a local ZenML server as a background process and connect the "
    "client to it.",
    default=False,
    type=click.BOOL,
)
@click.option(
    "--docker",
    is_flag=True,
    help="Start a local ZenML server as a Docker container instead of a local "
    "background process. Only used when running `zenml login --local`.",
    default=False,
    type=click.BOOL,
)
@click.option(
    "--restart",
    is_flag=True,
    help="Force a restart of the local ZenML server. Only used when running "
    "`zenml login --local`.",
    default=False,
    type=click.BOOL,
)
@click.option(
    "--port",
    type=int,
    default=None,
    help="Use a custom TCP port value for the local ZenML server. Only used "
    "when running `zenml login --local`.",
)
@click.option(
    "--ip-address",
    type=ipaddress.ip_address,
    default=None,
    help="Have the local ZenML server listen on an IP address different than "
    "the default localhost. Only used when running `zenml login --local`.",
)
@click.option(
    "--blocking",
    is_flag=True,
    help="Run the local ZenML server in blocking mode. The CLI will not return "
    "until the server exits or is stopped with CTRL+C. Only used when running "
    "`zenml login --local`.",
    default=False,
    type=click.BOOL,
)
@click.option(
    "--image",
    type=str,
    default=None,
    help="Use a custom Docker image for the local ZenML server. Only used when "
    "running `zenml login --local --docker`.",
)
@click.option(
    "--ngrok-token",
    type=str,
    default=None,
    help="Specify an ngrok auth token to use for exposing the local ZenML "
    "dashboard on a public domain. Primarily used for accessing the "
    "dashboard in Colab. Only used when running `zenml login --local`.",
)
@click.option(
    "--pro-api-url",
    type=str,
    default=None,
    help="Custom URL for the ZenML Pro API. Useful when connecting "
    "to a self-hosted ZenML Pro deployment.",
)
def login(
    server: Optional[str] = None,
    pro: bool = False,
    refresh: bool = False,
    api_key: bool = False,
    no_verify_ssl: bool = False,
    ssl_ca_cert: Optional[str] = None,
    local: bool = False,
    docker: bool = False,
    restart: bool = False,
    ip_address: Union[
        ipaddress.IPv4Address, ipaddress.IPv6Address, None
    ] = None,
    port: Optional[int] = None,
    blocking: bool = False,
    image: Optional[str] = None,
    ngrok_token: Optional[str] = None,
    pro_api_url: Optional[str] = None,
) -> None:
    """Connect to a remote ZenML server.

    Args:
        server: The URL where the ZenML server is reachable, or a ZenML Pro
            server name or ID.
        pro: Log in to a ZenML Pro server.
        refresh: Force a new login flow with the ZenML server.
        api_key: Whether to use an API key to authenticate with the ZenML
            server.
        no_verify_ssl: Whether to verify the server's TLS certificate.
        ssl_ca_cert: A path to a CA bundle to use to verify the server's TLS
            certificate or the CA bundle value itself.
        local: Start a local ZenML server and connect the client to it.
        docker: Use a local Docker server instead of a local process.
        restart: Force a restart of the local ZenML server.
        ip_address: The IP address to bind the local server to.
        port: The port to bind the local server to.
        blocking: Block the CLI while the local server is running.
        image: A custom Docker image to use for the local Docker server, when
            the `docker` flag is set.
        ngrok_token: An ngrok auth token to use for exposing the local ZenML
            dashboard on a public domain. Primarily used for accessing the
            dashboard in Colab.
        pro_api_url: Custom URL for the ZenML Pro API.
    """
    _fail_if_authentication_environment_variables_set()

    if local:
        if api_key:
            cli_utils.error(
                "An API key cannot be used with the local ZenML server."
            )

        start_local_server(
            docker=docker,
            ip_address=ip_address,
            port=port,
            blocking=blocking,
            image=image,
            ngrok_token=ngrok_token,
            restart=restart,
        )
        return

    if pro:
        connect_to_pro_server(
            pro_server=server,
            refresh=True,
            pro_api_url=pro_api_url,
        )
        return

    # Get the server that the client is currently connected to, if any
    current_non_local_server: Optional[str] = None
    gc = GlobalConfiguration()
    store_cfg = gc.store_configuration
    if store_cfg.type == StoreType.REST:
        if not connected_to_local_server():
            current_non_local_server = store_cfg.url

    api_key_value: Optional[str] = None
    if api_key:
        # Read the API key from the user
        api_key_value = click.prompt(
            "Please enter the API key for the ZenML server",
            type=str,
            hide_input=True,
        )

    verify_ssl: Union[str, bool] = (
        ssl_ca_cert if ssl_ca_cert is not None else not no_verify_ssl
    )

    if server is not None:
        if not re.match(r"^(https?|mysql)://", server):
            # The server argument is a ZenML Pro server name or UUID
            connect_to_pro_server(
                pro_server=server,
                api_key=api_key_value,
                refresh=refresh,
                pro_api_url=pro_api_url,
            )
        else:
            # The server argument is a server URL

            # First, try to discover if the server is a ZenML Pro server or not
            server_is_pro, server_pro_api_url = is_pro_server(server)
            if server_is_pro:
                connect_to_pro_server(
                    pro_server=server,
                    api_key=api_key_value,
                    refresh=refresh,
                    # Prefer the pro API URL extracted from the server info if
                    # available
                    pro_api_url=server_pro_api_url or pro_api_url,
                )
            else:
                connect_to_server(
                    url=server,
                    api_key=api_key_value,
                    verify_ssl=verify_ssl,
                    refresh=refresh,
                )

    elif current_non_local_server:
        # The server argument is not provided, so we default to
        # re-authenticating to the current non-local server that the client is
        # connected to.
        server = current_non_local_server
        # First, try to discover if the server is a ZenML Pro server or not
        server_is_pro, server_pro_api_url = is_pro_server(server)

        if server_is_pro:
            cli_utils.declare(
                "No server argument was provided. Re-authenticating to "
                "ZenML Pro...\n"
                "Hint: You can run 'zenml login <server-url-id-or-name>' to "
                "connect to a specific ZenML Pro server."
            )
            connect_to_pro_server(
                pro_server=server,
                api_key=api_key_value,
                refresh=True,
                # Prefer the pro API URL extracted from the server info if
                # available
                pro_api_url=server_pro_api_url or pro_api_url,
            )
        else:
            cli_utils.declare(
                "No server argument was provided. Re-authenticating to "
                f"the current ZenML server at '{server}'...\n"
                "Hint: You can run zenml login <server-url>' to connect "
                "to a specific ZenML server. If you wish to login to a ZenML Pro "
                "server, you can run 'zenml login --pro'."
            )
            connect_to_server(
                url=server,
                api_key=api_key_value,
                verify_ssl=verify_ssl,
                refresh=True,
            )
    else:
        # If no server argument is provided, and the client is not currently
        # connected to any non-local server, we default to logging in to ZenML
        # Pro.
        cli_utils.declare(
            "No server argument was provided. Logging to ZenML Pro...\n"
            "Hint: You can run 'zenml login --local' to start a local ZenML "
            "server and connect to it or 'zenml login <server-url>' to connect "
            "to a specific ZenML server. If you wish to login to a ZenML Pro "
            "server, you can run 'zenml login --pro'."
        )
        connect_to_pro_server(
            api_key=api_key_value,
            pro_api_url=pro_api_url,
        )


@cli.command(
    "logout",
    help="""Log out from a ZenML server and optionally clear stored credentials.

    When called without any arguments, the command will log out from the ZenML
    server that the client is currently connected to. If the client is connected
    to a local ZenML server, the command will also shut down the local server.
    
    Examples:

      * log out from the ZenML server the client is currently connected to:

        zenml logout
    
      * disconnect from the local ZenML server and shut it down, if running:

        zenml logout --local

      * clear all stored credentials (API keys and tokens) for a specific ZenML
        server:

        zenml logout https://zenml.example.com --clear

      * log out from all ZenML Pro servers and clear all stored ZenML Pro
        credentials with the exception of API keys:

        zenml logout --pro --clear
        
""",
)
@click.argument("server", type=str, required=False)
@click.option(
    "--clear",
    is_flag=True,
    help="Clear all stored credentials for the specified server(s).",
    default=False,
    type=click.BOOL,
)
@click.option(
    "--local",
    is_flag=True,
    help="Disconnect from and shut down the local ZenML server.",
    default=False,
    type=click.BOOL,
)
@click.option(
    "--pro",
    is_flag=True,
    help="Log out from ZenML Pro. Use this with the --clear flag to clear all "
    "stored ZenML Pro credentials with the exception of API keys.",
    default=False,
    type=click.BOOL,
)
@click.option(
    "--pro-api-url",
    type=str,
    default=None,
    help="Custom URL for the ZenML Pro API. Useful when disconnecting "
    "from a self-hosted ZenML Pro deployment.",
)
def logout(
    server: Optional[str] = None,
    local: bool = False,
    clear: bool = False,
    pro: bool = False,
    pro_api_url: Optional[str] = None,
) -> None:
    """Disconnect from a ZenML server.

    Args:
        server: The URL of the ZenML server to disconnect from.
        clear: Clear all stored credentials and tokens.
        local: Disconnect from the local ZenML server.
        pro: Log out from ZenML Pro.
        pro_api_url: Custom URL for the ZenML Pro API.
    """
    from zenml.login.credentials_store import get_credentials_store

    _fail_if_authentication_environment_variables_set()

    credentials_store = get_credentials_store()
    gc = GlobalConfiguration()
    store_cfg = gc.store_configuration

    if pro:
        if server:
            cli_utils.error(
                "The `--pro` flag cannot be used with a specific server URL."
            )

        pro_api_url = pro_api_url or ZENML_PRO_API_URL
        if credentials_store.has_valid_pro_authentication(pro_api_url):
            credentials_store.clear_pro_credentials(pro_api_url)
            cli_utils.declare("Logged out from ZenML Pro.")
        else:
            cli_utils.declare(
                "The client is not currently connected to ZenML Pro."
            )

        if clear:
            # Try to determine if the client is currently connected to a ZenML
            # Pro server with the given pro API URL
            credentials = credentials_store.get_credentials(store_cfg.url)
            if credentials and credentials.pro_api_url == pro_api_url:
                gc.set_default_store()

            credentials_store.clear_all_pro_tokens(pro_api_url)
            cli_utils.declare("Logged out from all ZenML Pro servers.")
        return

    if server is None:
        # Log out from the current server

        if gc.uses_default_store():
            cli_utils.declare(
                "The client is not currently connected to a ZenML server.\n"
                "Hint: You can run 'zenml server list' to view the available "
                "ZenML servers and then 'zenml login <server-url-name-or-id>' "
                "to connect to a specific server."
            )
            return

        if connected_to_local_server():
            local = True
        else:
            server = store_cfg.url

    if local:
        from zenml.zen_server.deploy.deployer import LocalServerDeployer

        deployer = LocalServerDeployer()

        if not get_local_server():
            cli_utils.declare("The local ZenML dashboard is not running.")
        else:
            cli_utils.declare("Logging out from the local ZenML server...")
            deployer.remove_server()
            cli_utils.declare(
                "The local ZenML dashboard has been shut down.\n"
                "Hint: You can run 'zenml login --local' to start it again."
            )
        return

    assert server is not None

    gc.set_default_store()
    credentials = credentials_store.get_credentials(server)

    if credentials and (clear or store_cfg.url == server):
        if credentials.type == ServerType.PRO:
            cli_utils.declare(
                f"Logging out from ZenML Pro server '{credentials.server_name}'."
            )
            if clear:
                credentials_store.clear_credentials(server_url=server)
            cli_utils.declare(
                "Logged out from ZenML Pro.\n"
                f"Hint: You can run 'zenml login {credentials.server_name}' to "
                "login again to the same ZenML Pro server or 'zenml server "
                "list' to view other available servers that you can connect to "
                "with 'zenml login <server-id-name-or-url>'."
            )
        else:
            cli_utils.declare(f"Logging out from {server}.")
            if clear:
                credentials_store.clear_credentials(server_url=server)
            cli_utils.declare(
                f"Logged out from {server}."
                f"Hint: You can run 'zenml login {server}' to log in again "
                "to the same server or 'zenml server list' to view other available "
                "servers that you can connect to with 'zenml login <server-url>'."
            )
    else:
        cli_utils.declare(
            f"The client is not currently connected to the ZenML server at "
            f"'{server}'."
        )
