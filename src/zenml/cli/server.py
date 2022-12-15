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
import sys
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

import click
import yaml
from rich.errors import MarkupError

from zenml.cli import utils as cli_utils
from zenml.cli.cli import cli
from zenml.client import Client
from zenml.config.global_config import GlobalConfiguration
from zenml.console import console
from zenml.constants import ENV_AUTO_OPEN_DASHBOARD, handle_bool_env_var
from zenml.enums import ServerProviderType, StoreType
from zenml.logger import get_logger
from zenml.utils import yaml_utils
from zenml.utils.analytics_utils import AnalyticsEvent, event_handler

logger = get_logger(__name__)

LOCAL_ZENML_SERVER_NAME = "local"

if TYPE_CHECKING:
    from zenml.zen_server.deploy.deployment import ServerDeployment


def get_active_deployment(local: bool = False) -> Optional["ServerDeployment"]:
    """Get the active local or remote server deployment.

    Call this function to retrieve the local or remote server deployment that
    was last provisioned on this machine.

    Args:
        local: Whether to return the local active deployment or the remote one.

    Returns:
        The local or remote active server deployment or None, if no deployment
        was found.
    """
    from zenml.zen_server.deploy.deployer import ServerDeployer

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
    "--connect",
    is_flag=True,
    help="Connect the client to the local server even when already connected "
    "to a remote ZenML server.",
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
def up(
    docker: bool = False,
    ip_address: Union[
        ipaddress.IPv4Address, ipaddress.IPv6Address, None
    ] = None,
    port: Optional[int] = None,
    blocking: bool = False,
    connect: bool = False,
    image: Optional[str] = None,
) -> None:
    """Start the ZenML dashboard locally and connect the client to it.

    Args:
        docker: Use a docker deployment instead of the local process.
        ip_address: The IP address to bind the server to.
        port: The port to bind the server to.
        blocking: Block the CLI while the server is running.
        connect: Connect the client to the local server even when already
            connected to a remote ZenML server.
        image: A custom Docker image to use for the server, when the
            `--docker` flag is set.
    """
    # flake8: noqa: C901
    with event_handler(
        AnalyticsEvent.ZENML_SERVER_STARTED
    ) as analytics_handler:
        from zenml.zen_server.deploy.deployer import ServerDeployer
        from zenml.zen_stores.sql_zen_store import SQLDatabaseDriver

        gc = GlobalConfiguration()

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
        elif image:
            config_attrs["image"] = image
        if port is not None:
            config_attrs["port"] = port
        if ip_address is not None and provider == ServerProviderType.DOCKER:
            config_attrs["ip_address"] = ip_address

        from zenml.zen_server.deploy.deployment import ServerDeploymentConfig

        server_config = ServerDeploymentConfig(**config_attrs)

        server = deployer.deploy_server(server_config)

        assert gc.store is not None

        analytics_handler.metadata = {
            "server_id": str(gc.user_id),
            "server_deployment": str(provider),
            "database_type": SQLDatabaseDriver.SQLITE.value,
        }

        if not blocking:
            from zenml.zen_stores.base_zen_store import (
                DEFAULT_PASSWORD,
                DEFAULT_USERNAME,
            )

            # Don't connect to the local server if the client is already
            # connected to a remote server.
            if (
                gc.store is not None
                and gc.store.type == StoreType.REST
                and not connect
            ):

                try:
                    if gc.zen_store.is_local_store():
                        connect = True
                    else:
                        cli_utils.declare(
                            "Skipped connecting to the local server. The "
                            "client is already connected to a remote ZenML "
                            "server. Pass the `--connect` flag to connect to "
                            "the local server anyway."
                        )
                except Exception as e:
                    logger.debug(
                        f"The current ZenML server configuration is no longer "
                        f"valid. Connecting to the local server: {e}"
                    )
                    # even when connected to a remote ZenML server, if the
                    # connection is not working, we default to connecting to the
                    # local server
                    connect = True
            else:
                connect = True

            if connect:
                deployer.connect_to_server(
                    LOCAL_ZENML_SERVER_NAME,
                    DEFAULT_USERNAME,
                    DEFAULT_PASSWORD,
                )

            if server.status and server.status.url:
                cli_utils.declare(
                    f"The local ZenML dashboard is available at "
                    f"'{server.status.url}'. You can connect to it using the "
                    f"'{DEFAULT_USERNAME}' username and an empty password. "
                    f"To open the dashboard in a browser automatically, "
                    f"set the env variable AUTO_OPEN_DASHBOARD=true."
                )

                if handle_bool_env_var(ENV_AUTO_OPEN_DASHBOARD, default=True):
                    try:
                        import webbrowser

                        webbrowser.open(server.status.url)
                        cli_utils.declare(
                            "Automatically opening the dashboard in your "
                            "browser. To disable this, set the env variable "
                            "AUTO_OPEN_DASHBOARD=false."
                        )
                    except Exception as e:
                        logger.error(e)


@cli.command("down", help="Shut down the local ZenML dashboard.")
def down() -> None:
    """Shut down the local ZenML dashboard."""
    with event_handler(
        AnalyticsEvent.ZENML_SERVER_STOPPED
    ) as analytics_handler:
        server = get_active_deployment(local=True)

        if not server:
            cli_utils.declare("The local ZenML dashboard is not running.")
            return
        from zenml.zen_server.deploy.deployer import ServerDeployer

        deployer = ServerDeployer()
        deployer.remove_server(server.config.name)

        gc = GlobalConfiguration()
        analytics_handler.metadata = {
            "server_id": str(gc.user_id),
            "server_deployment": str(server.config.provider),
            "database_type": str(gc.store.type) if gc.store else "",
        }

        cli_utils.declare("The local ZenML dashboard has been shut down.")


@cli.command("deploy", help="Deploy ZenML in the cloud.")
@click.option(
    "--provider",
    "-p",
    type=click.Choice(
        [
            ServerProviderType.AWS.value,
            ServerProviderType.GCP.value,
            ServerProviderType.AZURE.value,
        ],
        case_sensitive=True,
    ),
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
    help="Time in seconds to wait for the server to be deployed.",
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
    default=False,
    type=click.BOOL,
)
@click.option(
    "--gcp-project-id",
    help="The project in GCP to deploy the server to. ",
    required=False,
    type=str,
)
def deploy(
    provider: Optional[str] = None,
    connect: bool = False,
    username: Optional[str] = None,
    password: Optional[str] = None,
    name: Optional[str] = None,
    timeout: Optional[int] = None,
    config: Optional[str] = None,
    gcp_project_id: Optional[str] = None,
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
        gcp_project_id: The project in GCP to deploy the server to.
    """
    with event_handler(
        AnalyticsEvent.ZENML_SERVER_DEPLOYED
    ) as analytics_handler:
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
                    [
                        ServerProviderType.AWS.value,
                        ServerProviderType.GCP.value,
                        ServerProviderType.AZURE.value,
                    ],
                    case_sensitive=True,
                ),
                default=ServerProviderType.AWS.value,
            )
        config_dict["provider"] = provider

        if provider == ServerProviderType.GCP.value:
            if "project_id" not in config_dict:
                if not gcp_project_id:
                    gcp_project_id = click.prompt(
                        "GCP project ID",
                    )
                config_dict["project_id"] = gcp_project_id

        if not username:
            username = click.prompt(
                "ZenML admin account username", default="default"
            )
        config_dict["username"] = username

        password = password or config_dict.get("password", None)
        if not password:
            password = click.prompt(
                "ZenML admin account password", hide_input=True
            )
        config_dict["password"] = password

        from zenml.zen_server.deploy.deployment import ServerDeploymentConfig

        server_config = ServerDeploymentConfig.parse_obj(config_dict)

        from zenml.zen_server.deploy.deployer import ServerDeployer

        deployer = ServerDeployer()

        server = get_active_deployment(local=False)
        if server:
            if server.config.provider != provider:
                cli_utils.error(
                    "ZenML is already deployed using a different provider "
                    f"({server.config.provider}). Please tear down the "
                    "existing deployment by running `zenml destroy` before "
                    "deploying a new one."
                )

            if server.config.name != name:
                cli_utils.error(
                    f"An existing deployment with a different name "
                    f"'{server.config.name}' already exists. Please tear down "
                    f"the existing deployment by running `zenml destroy` "
                    f"before deploying a new one."
                )

        server = deployer.deploy_server(server_config, timeout=timeout)

        metadata = {
            "server_deployment": str(server.config.provider),
        }

        analytics_handler.metadata = metadata

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
    with event_handler(
        AnalyticsEvent.ZENML_SERVER_DESTROYED
    ) as analytics_handler:
        server = get_active_deployment(local=False)
        if not server:
            cli_utils.declare("No cloud ZenML server has been deployed.")
            return

        from zenml.zen_server.deploy.deployer import ServerDeployer

        deployer = ServerDeployer()
        deployer.remove_server(server.config.name)

        metadata = {
            "server_deployment": str(server.config.provider),
        }

        analytics_handler.metadata = metadata

        cli_utils.declare(
            "The ZenML server has been torn down and all resources removed."
        )


@cli.command("status", help="Show information about the current configuration.")
def status() -> None:
    """Show details about the current configuration."""
    gc = GlobalConfiguration()
    client = Client()

    store_cfg = gc.store

    cli_utils.declare(f"Using configuration from: '{gc.config_directory}'")
    if client.root:
        cli_utils.declare(f"Active repository root: {client.root}")
    if store_cfg is not None:
        if gc.uses_default_store():
            cli_utils.declare(f"Using the local database ('{store_cfg.url}')")
        else:
            cli_utils.declare(f"Connected to a ZenML server: '{store_cfg.url}'")

    scope = "repository" if client.uses_local_configuration else "global"
    cli_utils.declare(f"The current user is: '{client.active_user.name}'")
    cli_utils.declare(
        f"The active project is: '{client.active_project.name}' " f"({scope})"
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

        zenml connect --url=http://zenml.example.com:8080 --username=admin

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

        http_timeout: The number of seconds to wait for HTTP requests to the
            ZenML server to be successful before issuing a timeout error
            (default: 5).

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
        http_timeout: 10

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
    "--config",
    help="Use a YAML or JSON configuration or configuration file.",
    required=False,
    type=str,
)
@click.option(
    "--raw-config",
    is_flag=True,
    help="Whether to use the configuration without prompting for missing "
    "fields.",
    default=False,
)
def connect(
    url: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    project: Optional[str] = None,
    no_verify_ssl: bool = False,
    ssl_ca_cert: Optional[str] = None,
    config: Optional[str] = None,
    raw_config: bool = False,
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
        raw_config: Whether to use the configuration without prompting for
            missing fields.
    """
    from zenml.config.store_config import StoreConfiguration
    from zenml.zen_stores.base_zen_store import BaseZenStore

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

        if raw_config:
            store_config = StoreConfiguration.parse_obj(store_dict)
            GlobalConfiguration().set_store(store_config)
            return

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
    assert url is not None

    store_dict["url"] = url
    if not username:
        username = click.prompt("Username", type=str)
    store_dict["username"] = username
    if password is None:
        password = click.prompt(
            f"Password for user {username} (press ENTER for empty password)",
            default="",
            hide_input=True,
        )
    store_dict["password"] = password

    store_type = BaseZenStore.get_store_type(url)
    if store_type == StoreType.REST:
        store_dict["verify_ssl"] = verify_ssl

    store_config_class = BaseZenStore.get_store_config_class(store_type)
    assert store_config_class is not None

    store_config = store_config_class.parse_obj(store_dict)
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
    from zenml.zen_server.deploy.deployer import ServerDeployer
    from zenml.zen_stores.base_zen_store import BaseZenStore

    gc = GlobalConfiguration()

    if gc.store is None:
        cli_utils.warning("No ZenML server is currently connected.")
        return

    url = gc.store.url
    store_type = BaseZenStore.get_store_type(url)
    if store_type == StoreType.REST:
        deployer = ServerDeployer()
        deployer.disconnect_from_server()
    else:
        gc.set_default_store()
        cli_utils.declare("Restored default store configuration.")


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

    from zenml.zen_server.deploy.deployer import ServerDeployer

    deployer = ServerDeployer()

    cli_utils.declare(f"Showing logs for server: {server_name}")

    from zenml.zen_server.deploy.exceptions import ServerDeploymentNotFoundError

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
