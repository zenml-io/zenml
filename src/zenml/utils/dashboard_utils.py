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

from typing import Optional
from uuid import UUID

from zenml import constants
from zenml.client import Client
from zenml.enums import EnvironmentType, StoreType
from zenml.environment import get_environment
from zenml.logger import get_logger
from zenml.models import (
    ComponentResponse,
    PipelineRunResponse,
    ServerDeploymentType,
    StackResponse,
)

logger = get_logger(__name__)


def get_cloud_dashboard_url() -> Optional[str]:
    """Get the base url of the cloud dashboard if the server is a cloud tenant.

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
    base_url = get_server_dashboard_url()

    if base_url:
        return base_url + constants.STACKS

    return None


def get_component_url(component: ComponentResponse) -> Optional[str]:
    """Function to get the dashboard URL of a given component model.

    Args:
        component: the response model of the given component.

    Returns:
        the URL to the component if the dashboard is available, else None.
    """
    base_url = get_server_dashboard_url()

    if base_url:
        return base_url + constants.STACKS

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
        return f"{cloud_url}{constants.RUNS}/{run.id}"

    dashboard_url = get_server_dashboard_url()
    if dashboard_url:
        return f"{dashboard_url}{constants.RUNS}/{run.id}"

    return None


def get_model_version_url(model_version_id: UUID) -> Optional[str]:
    """Function to get the dashboard URL of a given model version.

    Args:
        model_version_id: the id of the model version.

    Returns:
        the URL to the model version if the dashboard is available, else None.
    """
    cloud_url = get_cloud_dashboard_url()
    if cloud_url:
        return f"{cloud_url}/model-versions/{str(model_version_id)}"

    return None


def show_dashboard(url: str) -> None:
    """Show the ZenML dashboard at the given URL.

    In native environments, the dashboard is opened in the default browser.
    In notebook environments, the dashboard is embedded in an iframe.

    Args:
        url: URL of the ZenML dashboard.
    """
    environment = get_environment()
    if environment in (EnvironmentType.NOTEBOOK, EnvironmentType.COLAB):
        from IPython.core.display import display
        from IPython.display import IFrame

        display(IFrame(src=url, width="100%", height=720))

    elif environment in (EnvironmentType.NATIVE, EnvironmentType.WSL):
        if constants.handle_bool_env_var(
            constants.ENV_AUTO_OPEN_DASHBOARD, default=True
        ):
            try:
                import webbrowser

                if environment == EnvironmentType.WSL:
                    webbrowser.get("wslview %s").open(url)
                else:
                    webbrowser.open(url)
                logger.info(
                    "Automatically opening the dashboard in your "
                    "browser. To disable this, set the env variable "
                    "AUTO_OPEN_DASHBOARD=false."
                )
            except Exception as e:
                logger.error(e)
        else:
            logger.info(
                "To open the dashboard in a browser automatically, "
                "set the env variable AUTO_OPEN_DASHBOARD=true."
            )

    else:
        logger.info(f"The ZenML dashboard is available at {url}.")
