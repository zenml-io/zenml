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
from typing import Any, Dict, Optional, Union

import click
import yaml
from click_params import IP_ADDRESS  # type: ignore[import]
from rich.errors import MarkupError

from zenml.cli import utils as cli_utils
from zenml.cli.cli import cli
from zenml.client import Client
from zenml.config.global_config import GlobalConfiguration
from zenml.console import console
from zenml.enums import ServerProviderType, StoreType
from zenml.logger import get_logger
from zenml.utils import yaml_utils
from zenml.utils.analytics_utils import AnalyticsEvent, track_event
from zenml.zen_server.deploy.deployer import ServerDeployer
from zenml.zen_server.deploy.deployment import (
    ServerDeployment,
    ServerDeploymentConfig,
)
from zenml.zen_server.deploy.exceptions import ServerDeploymentNotFoundError
from zenml.zen_server.deploy.terraform.terraform_zen_server import (
    TerraformServerDeploymentConfig,
)
from zenml.zen_stores.base_zen_store import DEFAULT_PASSWORD, DEFAULT_USERNAME

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
    if local:
        servers = deployer.list_servers(provider_type=ServerProviderType.LOCAL)
        if not servers:
            servers = deployer.list_servers(
                provider_type=ServerProviderType.DOCKER
            )
    else:
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
    )
    if not docker:
        config_attrs["blocking"] = blocking
    if port is not None:
        config_attrs["port"] = port
    if ip_address is not None:
        config_attrs["ip_address"] = ip_address

    server_config = ServerDeploymentConfig(**config_attrs)

    server = deployer.deploy_server(server_config)

    gc = GlobalConfiguration()
    assert gc.store is not None
    track_event(
        AnalyticsEvent.ZENML_SERVER_STARTED,
        metadata={
            "server_id": str(gc.user_id),
            "server_deployment": str(provider),
            "database_type": str(gc.store.type),
        },
    )

    if not blocking:
        gc = GlobalConfiguration()
        # Don't connect to the local server if the client is already connected
        # to a remote server.
        if gc.zen_store.type == StoreType.REST:
            cli_utils.declare(
                "Skipped connecting to the local server. The client is "
                "already connected to a remote ZenML server."
            )
        else:
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

    gc = GlobalConfiguration()
    assert gc.store is not None
    track_event(
        AnalyticsEvent.ZENML_SERVER_STOPPED,
        metadata={
            "server_id": str(gc.user_id),
            "server_deployment": str(server.config.provider),
            "database_type": str(gc.store.type),
        },
    )

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
@click.option(
    "--connect",
    is_flag=True,
    help="Connect your client to the ZenML server after it is successfully "
    "deployed.",
    type=click.BOOL,
)
def deploy(
    provider: Optional[str] = None,
    connect: bool = False,
    username: Optional[str] = None,
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

    if not name:
        name = click.prompt(
            "ZenML server name (used as a prefix for the names of deployed "
            "resources)",
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
        username = click.prompt(
            "ZenML admin account username", default="default"
        )
    config_dict["username"] = username

    password = password or config_dict.get("password", None)
    if not password:
        password = click.prompt("ZenML admin account password", hide_input=True)
    config_dict["password"] = password

    server_config = ServerDeploymentConfig.parse_obj(config_dict)

    deployer = ServerDeployer()

    server = get_active_deployment(local=False)
    if server:
        if server.config.provider != provider:
            cli_utils.error(
                f"ZenML is already deployed using a different provider "
                f"({server.config.provider}). Please tear down the existing "
                f"deployment by running `zenml destroy` before deploying a new "
                f"one."
            )

        if server.config.name != name:
            cli_utils.error(
                f"An existing deployment with a different name "
                f"'{server.config.name}' already exists. Please tear down the "
                f"existing deployment by running `zenml destroy` before "
                f"deploying a new one."
            )

    server = deployer.deploy_server(server_config, timeout=timeout)

    metadata = {
        "server_deployment": str(server.config.provider),
    }
    if isinstance(server.config, TerraformServerDeploymentConfig):
        # TODO: maybe move the server ID into the ServerDeploymentConfig class
        metadata["server_id"] = str(server.config.server_id)

    track_event(
        AnalyticsEvent.ZENML_SERVER_DEPLOYED,
        metadata=metadata,
    )

    if server.status and server.status.url:
        cli_utils.declare(
            f"ZenML server '{name}' running at '{server.status.url}'."
        )

        if connect and username:
            deployer.connect_to_server(
                server_config.name,
                username,
                password or "",
                verify_ssl=server.status.ca_crt
                if server.status.ca_crt is not None
                else False,
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

    metadata = {
        "server_deployment": str(server.config.provider),
    }

    if isinstance(server.config, TerraformServerDeploymentConfig):
        metadata["server_id"] = str(server.config.server_id)

    track_event(
        AnalyticsEvent.ZENML_SERVER_DESTROYED,
        metadata=metadata,
    )

    cli_utils.declare(
        "The ZenML server has been torn down and all resources removed."
    )


@cli.command("status", help="Show information about the current configuration.")
def status() -> None:
    """Show details about the current configuration."""
    gc = GlobalConfiguration()
    client = Client()

    store_cfg = gc.store

    if client.root:
        cli_utils.declare(f"Active repository root: {client.root}")
    if store_cfg is not None:
        if store_cfg == gc.get_default_store():
            cli_utils.declare(f"Using the local database ('{store_cfg.url}')")
        else:
            cli_utils.declare(f"Connected to a ZenML server: '{store_cfg.url}'")

    scope = "repository" if client.uses_local_configuration else "global"
    cli_utils.declare(f"The current user is: '{client.active_user.name}'")
    cli_utils.declare(
        f"The active project is: '{client.active_project_name}' " f"({scope})"
    )
    cli_utils.declare(
        f"The active stack is: '{client.active_stack_model.name}' ({scope})"
    )

    server = get_active_deployment(local=True)
    if server:
        cli_utils.declare("The status of the local dashboard:")
        cli_utils.print_server_deployment(server)

    server = get_active_deployment(local=False)
    if server:
        cli_utils.declare(
            "The status of the cloud ZenML server deployed from this host:"
        )
        cli_utils.print_server_deployment(server)


@cli.command(
    "connect",
    help=(
        """Configure your client to connect to a remote ZenML server.

    Examples:

      * to connect to a ZenML deployment using command line arguments:

        zenml connect --url=http://zenml.example.com:8080 --username=admin --project=default

      * to use a configuration file:

        zenml connect --config=/path/to/zenml_config.yaml

      * when no arguments are supplied, ZenML will attempt to connect to the
        last ZenML server deployed from the local host using the 'zenml deploy'
        command.

    The configuration file must be a YAML or JSON file with the following
    attributes:

        url: The URL of the ZenML server.

        username: The username to use for authentication.

        password: The password to use for authentication.

        verify_ssl: Either a boolean, in which case it controls whether the
            server's TLS certificate is verified, or a string, in which case it
            must be a path to a CA certificate bundle to use or the CA bundle
            value itself.

    Example configuration:

        url: https://ac8ef63af203226194a7725ee71d85a-7635928635.us-east-1.elb.amazonaws.com/zenml\n
        username: admin\n
        password: Pa$$word123\n
        verify_ssl: |\n
        -----BEGIN CERTIFICATE-----
        MIIDETCCAfmgAwIBAgIQYUmQg2LR/pHAMZb/vQwwXjANBgkqhkiG9w0BAQsFADAT
        MREwDwYDVQQDEwh6ZW5tbC1jYTAeFw0yMjA5MjYxMzI3NDhaFw0yMzA5MjYxMzI3\n
        ...\n
        ULnzA0JkRWRnFqH6uXeJo1KAVqtxn1xf8PYxx3NlNDr9wi8KKwARf2lwm6sH4mvq
        1aZ/0iYnGKCu7rLJzxeguliMf69E\n
        -----END CERTIFICATE-----

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

    store_dict: Dict[str, Any] = {}
    verify_ssl = ssl_ca_cert if ssl_ca_cert is not None else not no_verify_ssl

    if config:

        if os.path.isfile(config):
            store_dict = yaml_utils.read_yaml(config)
        else:
            store_dict = yaml.safe_load(config)
        if not isinstance(store_dict, dict):
            cli_utils.error(
                "The configuration argument must be JSON/YAML content or "
                "point to a valid configuration file."
            )

        url = store_dict.get("url", url)
        username = username or store_dict.get("username")
        password = password or store_dict.get("password")
        verify_ssl = store_dict.get("verify_ssl", verify_ssl)

    elif url is None:
        server = get_active_deployment(local=False)

        if server is None or not server.status or not server.status.url:
            cli_utils.warning(
                "Running `zenml connect` without arguments can only be used to "
                "connect to a ZenML server previously deployed from this host "
                "with `zenml deploy`, but no such active deployment was found. "
                "Please use the `--url` or `--config` command line arguments "
                "to configure how to connect to a remote third party ZenML "
                "server. Alternatively, call `zenml up` to start the ZenML "
                "dashboard locally."
            )
            return
        url = server.status.url
        if server.status.ca_crt:
            verify_ssl = server.status.ca_crt

    if not url:
        url = click.prompt("ZenML server URL", type=str)
    else:
        cli_utils.declare(f"Connecting to: '{url}'...")
    store_dict["url"] = url
    if not username:
        username = click.prompt("Username", type=str)
    store_dict["username"] = username
    if password is None:
        password = click.prompt(
            f"Password for user {username}", hide_input=True
        )
    store_dict["password"] = password
    store_dict["verify_ssl"] = verify_ssl

    store_config = RestZenStoreConfiguration.parse_obj(store_dict)
    GlobalConfiguration().set_store(store_config)

    if project:
        try:
            Client().set_active_project(project_name_or_id=project)
        except KeyError:
            cli_utils.warning(
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
