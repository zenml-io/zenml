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
from importlib import import_module
from typing import Any, Dict, Optional, Union

import click
import yaml
from click_params import IP_ADDRESS  # type: ignore[import]
from rich.errors import MarkupError
from rich.markdown import Markdown

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.config.global_config import GlobalConfiguration
from zenml.config.store_config import StoreConfiguration
from zenml.console import console
from zenml.enums import CliCategories, ServerProviderType
from zenml.logger import get_logger
from zenml.repository import Repository
from zenml.utils import yaml_utils
from zenml.zen_server.deploy.deployer import ServerDeployer
from zenml.zen_server.deploy.deployment import (
    ServerDeployment,
    ServerDeploymentConfig,
)
from zenml.zen_server.deploy.exceptions import ServerDeploymentNotFoundError
from zenml.zen_stores.base_zen_store import DEFAULT_USERNAME, DEFAULT_PASSWORD

logger = get_logger(__name__)

LOCAL_ZENML_SERVER_NAME = "local"


def get_active_deployment(local: bool = False) -> Optional[ServerDeployment]:
    """Get the active local or remote server deployment.

    Call this function to retrieve the local or remote server deployment that
    was last provisioned on this machine.

    Args:
        local: Whether to return the local active deployment or the remote one.

    Returns:
        The local or remote active server deployment or None, if no deployment
        was found.
    """
    deployer = ServerDeployer()
    servers = deployer.list_servers()

    if not servers:
        return None

    for server in servers:
        if server.config.provider in [
            ServerProviderType.LOCAL,
            ServerProviderType.DOCKER,
        ]:
            if local:
                return server
        elif not local:
            return server

    return None


@cli.command("up", help="Start the ZenML dashboard locally.")
@click.option(
    "--docker",
    is_flag=True,
    help="Start the ZenML dashboard as a Docker container instead of a local "
    "process.",
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
    type=IP_ADDRESS,
    default=None,
    help="Have the ZenML dashboard listen on an IP address different than the "
    "localhost.",
)
@click.option(
    "--blocking",
    is_flag=True,
    help="Run the ZenML dashboard in blocking mode. The CLI will not return "
    "until the dashboard is stopped.",
    type=click.BOOL,
)
def up(
    docker: bool = False,
    ip_address: Union[
        ipaddress.IPv4Address, ipaddress.IPv6Address, None
    ] = None,
    port: Optional[int] = None,
    blocking: bool = False,
) -> None:
    """Start the ZenML dashboard locally and connect the client to it.

    Args:
        docker: Use a docker deployment instead of the local process.
        ip_address: The IP address to bind the server to.
        port: The port to bind the server to.
        blocking: Block the CLI while the server is running.
    """
    if docker:
        provider = ServerProviderType.DOCKER
    else:
        provider = ServerProviderType.LOCAL

    deployer = ServerDeployer()

    server = get_active_deployment(local=True)
    if server and server.config.provider != provider:
        deployer.remove_server(LOCAL_ZENML_SERVER_NAME)

    config_attrs: Dict[str, Any] = dict(
        name=LOCAL_ZENML_SERVER_NAME,
        provider=provider,
        blocking=blocking,
    )
    if port is not None:
        config_attrs["port"] = port
    if ip_address is not None:
        config_attrs["ip_address"] = ip_address

    server_config = ServerDeploymentConfig(**config_attrs)

    server = deployer.deploy_server(server_config)

    if not blocking:
        deployer.connect_to_server(
            LOCAL_ZENML_SERVER_NAME,
            DEFAULT_USERNAME,
            DEFAULT_PASSWORD,
        )

        if server.status and server.status.url:
            cli_utils.declare(
                f"The local ZenML dashboard is available at "
                f"'{server.status.url}'. You can connect to it using the "
                f"'{DEFAULT_USERNAME}' username and an empty password."
            )


@cli.command("down", help="Shut down the local ZenML dashboard.")
def down() -> None:
    """Shut down the local ZenML dashboard."""
    server = get_active_deployment(local=True)
    if not server:
        cli_utils.declare("The local ZenML dashboard is not running.")
        return

    deployer = ServerDeployer()
    deployer.remove_server(server.config.name)
    cli_utils.declare("The local ZenML dashboard has been shut down.")


@cli.command("deploy", help="Deploy ZenML in the cloud.")
@click.option(
    "--provider",
    "-p",
    type=click.Choice([ServerProviderType.AWS.value], case_sensitive=True),
    default=None,
    help="Server deployment provider.",
)
@click.option(
    "--name",
    type=str,
    help="A name for the ZenML server deployment. This is used as a prefix for "
    "the names of deployed resources, such as database services and Kubernetes "
    "resources.",
)
@click.option(
    "--username",
    type=str,
    default=None,
    help="The username to use for the provisioned admin account.",
)
@click.option(
    "--email",
    type=str,
    default=None,
    help="The email address to use for the provisioned admin account.",
)
@click.option(
    "--password",
    type=str,
    default=None,
    help="The initial password to use for the provisioned admin account.",
)
@click.option(
    "--timeout",
    "-t",
    type=click.INT,
    default=None,
    help=("Time in seconds to wait for the server to be deployed."),
)
@click.option(
    "--config",
    help="Use a YAML or JSON configuration or configuration file.",
    required=False,
    type=str,
)
def deploy(
    provider: Optional[str] = None,
    connect: bool = False,
    username: Optional[str] = None,
    email: Optional[str] = None,
    password: Optional[str] = None,
    name: Optional[str] = None,
    timeout: Optional[int] = None,
    config: Optional[str] = None,
) -> None:
    """Deploy the ZenML server in a cloud provider.

    Args:
        name: Name for the ZenML server deployment.
        provider: ZenML server provider name.
        connect: Connecting the client to the ZenML server.
        username: The username for the provisioned admin account.
        email: The email address for the provisioned admin account.
        password: The initial password to use for the provisioned admin account.
        timeout: Time in seconds to wait for the server to start.
        config: A YAML or JSON configuration or configuration file to use.
    """
    config_dict: Dict[str, Any] = {}

    if config:
        if os.path.isfile(config):
            config_dict = yaml_utils.read_yaml(config)
        else:
            config_dict = yaml.safe_load(config)
        if not isinstance(config_dict, dict):
            cli_utils.error(
                "The configuration argument must be JSON/YAML content or "
                "point to a valid configuration file."
            )

        name = config_dict.get("name", name)
        provider = config_dict.get("provider", provider)
        username = config_dict.get("username", username)
        password = config_dict.get("password", password)
        email = config_dict.get("email", email)

    if not name:
        name = click.prompt(
            "ZenML server name (used as a prefix for the names of deployed "
            "resources",
            default="zenml",
        )
    config_dict["name"] = name

    if not provider:
        provider = click.prompt(
            "ZenML server provider",
            type=click.Choice(
                [ServerProviderType.AWS.value], case_sensitive=True
            ),
            default=ServerProviderType.AWS.value,
        )
    config_dict["provider"] = provider

    if not username:
        username = click.prompt("ZenML admin account username", default="admin")
    config_dict["username"] = username

    password = password or config_dict.get("password", None)
    if not password:
        password = click.prompt("ZenML admin account password", hide_input=True)
    config_dict["password"] = password

    email = email or config_dict.get("email", None)
    if not email:
        email = click.prompt(
            "ZenML admin account email address",
            default="",
        )
    config_dict["email"] = email

    server_config = ServerDeploymentConfig.parse_obj(config_dict)

    deployer = ServerDeployer()

    server = deployer.deploy_server(server_config, timeout=timeout)
    if server.status and server.status.url:
        cli_utils.declare(
            f"ZenML server '{name}' running at '{server.status.url}'."
        )

    if connect:
        deployer.connect_to_server(
            server_config.name,
            username,
            password,
        )


@cli.command(
    "destroy", help="Tear down and clean up the cloud ZenML deployment."
)
def destroy() -> None:
    """Tear down and clean up a cloud ZenML deployment."""
    server = get_active_deployment(local=False)
    if not server:
        cli_utils.declare("No cloud ZenML server has been deployed.")
        return

    deployer = ServerDeployer()
    deployer.remove_server(server.config.name)
    cli_utils.declare(
        "The ZenML server has been torn down and all resources removed."
    )


@cli.command("status", help="Show information about the current configuration.")
def status_server(server_name: Optional[str] = None) -> None:
    """Get the status of a ZenML server.

    Args:
        server_name: Name of the ZenML server deployment.
    """
    """Show details about the active global configuration."""
    gc = GlobalConfiguration()
    repo = Repository()

    store_cfg = gc.store

    if repo.root:
        cli_utils.declare(f"Active repository root: {repo.root}")
    if store_cfg is not None:
        if store_cfg == gc.get_default_store():
            cli_utils.declare(f"Using the local database ('{store_cfg.url}')")
        else:
            cli_utils.declare(f"Connected to a ZenML server: '{store_cfg.url}'")

    scope = "repository" if repo.uses_local_configuration else "global"
    cli_utils.declare(
        f"The current user is: '{repo.active_user.name}'"
    )
    cli_utils.declare(
        f"The active project is: '{repo.active_project_name}' " f"({scope})"
    )
    cli_utils.declare(
        f"The active stack is: '{repo.active_stack_model.name}' ({scope})"
    )

    server = get_active_deployment(local=False)
    if server:
        cli_utils.declare("The status for the local ZenML server:")
        cli_utils.print_server_deployment(server)

    server = get_active_deployment(local=True)
    if server:
        cli_utils.declare("The status for the cloud ZenML deployment:")
        cli_utils.print_server_deployment(server)


@cli.command(
    "connect",
    help=(
        """Configure your client to connect to a remote ZenML server.

    Example:

      - to connect to the ZenML server last deployed from your machine with
      `zenml deploy`:

        zenml server connect --username default

      - to connect to a ZenML deployment using a custom configuration:

        zenml connect --url=http://localhost:8080 --username=admin --project=default

        or:

        zenml connect --config=/path/to/zenml_config.yaml

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
    help="The username that is used to authenticate with a ZenML server.",
    required=False,
    type=str,
)
@click.option(
    "--password",
    help="The password that is used to authenticate with a ZenML server. If "
    "omitted, a prompt will be shown to enter the password.",
    required=False,
    type=str,
)
@click.option(
    "--project",
    help="The project to use when connecting to the ZenML server.",
    required=False,
    type=str,
)
@click.option(
    "--no-verify-ssl",
    is_flag=True,
    help="Whether to verify the server's TLS certificate",
)
@click.option(
    "--ssl-ca-cert",
    help="A path to a CA bundle file to use to verify the server's TLS "
    "certificate or the CA bundle value itself",
    required=False,
    type=str,
)
@click.option(
    "--config",
    help="Use a YAML or JSON configuration or configuration file.",
    required=False,
    type=str,
)
def connect(
    url: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    project: Optional[str] = None,
    no_verify_ssl: bool = False,
    ssl_ca_cert: Optional[str] = None,
    config: Optional[str] = None,
) -> None:
    """Connect to a remote ZenML server.

    Args:
        url: The URL where the ZenML server is reachable.
        local_store: Configure ZenML to use the local store.
        username: The username that is used to authenticate with the ZenML
            server.
        password: The password that is used to authenticate with the ZenML
            server.
        project: The active project that is used to connect to the ZenML
            server.
        no_verify_ssl: Whether to verify the server's TLS certificate.
        ssl_ca_cert: A path to a CA bundle to use to verify the server's TLS
            certificate or the CA bundle value itself.
        config: A YAML or JSON configuration or configuration file to use.
    """
    from zenml.zen_stores.rest_zen_store import RestZenStoreConfiguration

    if config:
        if url is not None or username is not None or password is not None:
            cli_utils.error(
                "You cannot pass a config file and pass the `--url`, "
                "`--username` or `--password` configuration options at the "
                "same time."
            )
        if os.path.isfile(config):
            store_dict = yaml_utils.read_yaml(config)
        else:
            store_dict = yaml.safe_load(config)
        if not isinstance(store_dict, dict):
            cli_utils.error(
                "The configuration argument must be JSON/YAML content or "
                "point to a valid configuration file."
            )
        store_config = StoreConfiguration.parse_obj(store_dict)
        GlobalConfiguration().set_store(store_config)
    elif url is None:
        if username is None:
            cli_utils.error(
                "The `--username` option is required to connect to a ZenML "
                "server deployed from this machine."
            )
        server = get_active_deployment(local=False)

        if server is None:
            cli_utils.error(
                "No ZenML server was deployed from this machine. Please deploy "
                "a ZenML server first by running `zenml deploy`, or use the "
                "other command line arguments to configure how to connect to a "
                "third party ZenML server. Alternatively, call `zenml up` to "
                "start the ZenML dashboard locally."
            )
        if password is None:
            password = click.prompt(
                f"Password for user {username}", hide_input=True, default=""
            )
        deployer = ServerDeployer()
        deployer.connect_to_server(server.config.name, username, password)
    else:
        if url is None or username is None:
            cli_utils.error(
                "Both `--url` and `--username` options are required to connect "
                "to a remote ZenML server."
            )
        if password is None:
            password = click.prompt(
                f"Password for user {username}", hide_input=True, default=""
            )
        store_config = RestZenStoreConfiguration(
            url=url,
            username=username,
            password=password,
            verify_ssl=ssl_ca_cert
            if ssl_ca_cert is not None
            else not no_verify_ssl,
        )
        GlobalConfiguration().set_store(store_config)

    if project:
        try:
            Repository().set_active_project(project_name_or_id=project)
        except KeyError:
            cli_utils.error(
                f"The project {project} does not exist or is not accessible. "
                f"Please set another project by running `zenml "
                f"project set`."
            )


@cli.command("disconnect", help="Disconnect from a ZenML server.")
def disconnect_server() -> None:
    """Disconnect from a ZenML server."""
    deployer = ServerDeployer()
    deployer.disconnect_from_server()


@cli.command("logs", help="Show the logs for the local or cloud ZenML server.")
@click.option(
    "--local",
    is_flag=True,
    help="Show the logs for the local ZenML server.",
)
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
    local: bool = False,
    follow: bool = False,
    raw: bool = False,
    tail: Optional[int] = None,
    server_name: Optional[str] = None,
) -> None:
    """Display the logs for a ZenML server.

    Args:
        local: Whether to show the logs for the local ZenML server.
        follow: Continue to output new log data as it becomes available.
        tail: Only show the last NUM lines of log output.
        raw: Show raw log contents (don't pretty-print logs).
    """
    server = get_active_deployment(local=True)
    if not local:
        remote_server = get_active_deployment(local=False)
        if remote_server is not None:
            server = remote_server

    if server is None:
        cli_utils.error(
            "The local ZenML dashboard is not running. Please call `zenml "
            "up` first to start the ZenML dashboard locally."
        )

    server_name = server.config.name
    deployer = ServerDeployer()

    cli_utils.declare(f"Showing logs for server: {server_name}")
    try:
        logs = deployer.get_server_logs(server_name, follow=follow, tail=tail)
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
