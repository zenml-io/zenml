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
"""Utility class to help with interacting with the dashboard."""

import os
from typing import Optional
from urllib.parse import urlparse

from zenml import constants
from zenml.client import Client
from zenml.config.global_config import GlobalConfiguration
from zenml.enums import EnvironmentType, StoreType
from zenml.environment import get_environment
from zenml.logger import get_logger
from zenml.models import (
    ComponentResponse,
    ModelVersionResponse,
    PipelineRunResponse,
    ServerDeploymentType,
    StackResponse,
)
from zenml.utils.server_utils import get_local_server

logger = get_logger(__name__)


def get_cloud_dashboard_url() -> Optional[str]:
    """Get the base url of the cloud dashboard if the server is a ZenML Pro workspace.

    Returns:
        The base url of the cloud dashboard.
    """
    client = Client()

    if client.zen_store.type == StoreType.REST:
        server_info = client.zen_store.get_store_info()

        if server_info.deployment_type == ServerDeploymentType.CLOUD:
            return server_info.dashboard_url

    return None


def get_server_dashboard_url() -> Optional[str]:
    """Get the base url of the dashboard deployed by the server.

    Returns:
        The server dashboard url.
    """
    client = Client()

    if client.zen_store.type == StoreType.REST:
        server_info = client.zen_store.get_store_info()

        if server_info.server_url:
            url = server_info.server_url
        else:
            url = client.zen_store.url

        return url

    return None


def get_stack_url(stack: StackResponse) -> Optional[str]:
    """Function to get the dashboard URL of a given stack model.

    Args:
        stack: the response model of the given stack.

    Returns:
        the URL to the stack if the dashboard is available, else None.
    """
    cloud_url = get_cloud_dashboard_url()
    if cloud_url:
        # We don't have a stack detail page here, so just link to the filtered
        # list of stacks.
        return f"{cloud_url}{constants.STACKS}?id={stack.id}"

    base_url = get_server_dashboard_url()

    if base_url:
        # There is no filtering in OSS, we just link to the stack list.
        return f"{base_url}{constants.STACKS}"

    return None


def get_component_url(component: ComponentResponse) -> Optional[str]:
    """Function to get the dashboard URL of a given component model.

    Args:
        component: the response model of the given component.

    Returns:
        the URL to the component if the dashboard is available, else None.
    """
    cloud_url = get_cloud_dashboard_url()
    if cloud_url:
        return f"{cloud_url}{constants.STACK_COMPONENTS}/{component.id}"

    base_url = get_server_dashboard_url()

    if base_url:
        return f"{base_url}{constants.STACK_COMPONENTS}/{component.id}"

    return None


def get_run_url(run: PipelineRunResponse) -> Optional[str]:
    """Function to get the dashboard URL of a given pipeline run.

    Args:
        run: the response model of the given pipeline run.

    Returns:
        the URL to the pipeline run if the dashboard is available, else None.
    """
    cloud_url = get_cloud_dashboard_url()
    if cloud_url:
        return f"{cloud_url}{constants.PROJECTS}/{run.project_id}{constants.RUNS}/{run.id}"

    dashboard_url = get_server_dashboard_url()
    if dashboard_url:
        return f"{dashboard_url}{constants.PROJECTS}/{run.project.name}{constants.RUNS}/{run.id}"

    return None


def get_model_version_url(
    model_version: ModelVersionResponse,
) -> Optional[str]:
    """Function to get the dashboard URL of a given model version.

    Args:
        model_version: the response model of the given model version.

    Returns:
        the URL to the model version if the dashboard is available, else None.
    """
    cloud_url = get_cloud_dashboard_url()
    if cloud_url:
        return f"{cloud_url}{constants.PROJECTS}/{model_version.project_id}/model-versions/{str(model_version.id)}"

    return None


def show_dashboard_with_url(url: str) -> None:
    """Show the ZenML dashboard at the given URL.

    In native environments, the dashboard is opened in the default browser.
    In notebook environments, the dashboard is embedded in an iframe.

    Args:
        url: URL of the ZenML dashboard.
    """
    environment = get_environment()
    if environment in (EnvironmentType.NOTEBOOK, EnvironmentType.COLAB):
        from IPython.core.display_functions import display
        from IPython.display import IFrame

        display(IFrame(src=url, width="100%", height=720))

    elif environment in (EnvironmentType.NATIVE, EnvironmentType.WSL):
        open_dashboard = True

        if constants.ENV_AUTO_OPEN_DASHBOARD in os.environ:
            logger.warning(
                "The `%s` environment variable is deprecated, use the `%s` "
                "environment variable instead.",
                constants.ENV_AUTO_OPEN_DASHBOARD,
                constants.ENV_ZENML_AUTO_OPEN_DASHBOARD,
            )

        if not constants.handle_bool_env_var(
            constants.ENV_AUTO_OPEN_DASHBOARD, default=True
        ):
            open_dashboard = False

        if not constants.handle_bool_env_var(
            constants.ENV_ZENML_AUTO_OPEN_DASHBOARD, default=True
        ):
            open_dashboard = False

        if open_dashboard:
            try:
                import webbrowser

                if environment == EnvironmentType.WSL:
                    webbrowser.get("wslview %s").open(url)
                else:
                    webbrowser.open(url)
                logger.info(
                    "Automatically opening the dashboard in your "
                    "browser. To disable this, set the env variable "
                    "`%s=false`.",
                    constants.ENV_ZENML_AUTO_OPEN_DASHBOARD,
                )
            except Exception as e:
                logger.error(e)
        else:
            logger.info(
                "To open the dashboard in a browser automatically, "
                "set the env variable `%s=true`.",
                constants.ENV_ZENML_AUTO_OPEN_DASHBOARD,
            )

    else:
        logger.info(f"The ZenML dashboard is available at {url}.")


def show_dashboard(
    local: bool = False,
    ngrok_token: Optional[str] = None,
) -> None:
    """Show the ZenML dashboard.

    Args:
        local: Whether to show the dashboard for the local server or the
            one for the active server.
        ngrok_token: An ngrok auth token to use for exposing the ZenML
            dashboard on a public domain. Primarily used for accessing the
            dashboard in Colab.

    Raises:
        RuntimeError: If no server is connected.
    """
    from zenml.utils.networking_utils import get_or_create_ngrok_tunnel

    url: Optional[str] = None
    if not local:
        gc = GlobalConfiguration()
        if gc.store_configuration.type == StoreType.REST:
            url = gc.store_configuration.url

    if not url:
        # Else, check for local servers
        server = get_local_server()
        if server and server.status and server.status.url:
            url = server.status.url

    if not url:
        raise RuntimeError(
            "ZenML is not connected to any server right now. Please use "
            "`zenml login` to connect to a server or spin up a new local server "
            "via `zenml login --local`."
        )

    if ngrok_token:
        parsed_url = urlparse(url)

        ngrok_url = get_or_create_ngrok_tunnel(
            ngrok_token=ngrok_token, port=parsed_url.port or 80
        )
        logger.debug(f"Tunneling dashboard from {url} to {ngrok_url}.")
        url = ngrok_url

    show_dashboard_with_url(url)
