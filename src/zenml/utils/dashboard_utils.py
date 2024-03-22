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
from zenml.models import ComponentResponse, PipelineRunResponse, StackResponse

logger = get_logger(__name__)


def get_base_url() -> Optional[str]:
    """Function to get the base workspace-scoped url.

    Returns:
        the base url if the client is using a rest zen store, else None
    """
    client = Client()

    if client.zen_store.type == StoreType.REST:
        # if the server config has a base URL use that
        server_model = client.zen_store.get_store_info()
        if server_model.base_url:
            url = server_model.base_url
            # if the base url has cloud.zenml.io in it, then it is a cloud
            # deployment and there isn't a workspace in the URL
            if "cloud.zenml.io" in url:
                return url
            return (
                url + f"{constants.WORKSPACES}/{client.active_workspace.name}"
            )
        url = (
            client.zen_store.url
            + f"{constants.WORKSPACES}/{client.active_workspace.name}"
        )
        return url

    return None


def get_stack_url(stack: StackResponse) -> Optional[str]:
    """Function to get the dashboard URL of a given stack model.

    Args:
        stack: the response model of the given stack.

    Returns:
        the URL to the stack if the dashboard is available, else None.
    """
    base_url = get_base_url()
    if base_url:
        return base_url + f"{constants.STACKS}/{stack.id}/configuration"
    return None


def get_component_url(component: ComponentResponse) -> Optional[str]:
    """Function to get the dashboard URL of a given component model.

    Args:
        component: the response model of the given component.

    Returns:
        the URL to the component if the dashboard is available, else None.
    """
    base_url = get_base_url()
    if base_url:
        return (
            base_url
            + f"{constants.STACK_COMPONENTS}/{component.type.value}/{component.id}/configuration"
        )
    return None


def get_run_url(run: PipelineRunResponse) -> Optional[str]:
    """Function to get the dashboard URL of a given pipeline run.

    Args:
        run: the response model of the given pipeline run.

    Returns:
        the URL to the pipeline run if the dashboard is available, else None.
    """
    client = Client()
    base_url = get_base_url()
    if base_url:
        server_model = client.zen_store.get_store_info()
        # if the server is a zenml cloud tenant, use a different URL
        if server_model.metadata.get("organization_id"):
            return f"{base_url}{constants.RUNS}/{run.id}"
        if run.pipeline:
            return f"{base_url}{constants.PIPELINES}/{run.pipeline.id}{constants.RUNS}/{run.id}/dag"
        else:
            return f"{base_url}/all-runs/{run.id}/dag"
    return None


def get_model_version_url(model_version_id: UUID) -> Optional[str]:
    """Function to get the dashboard URL of a given model version.

    Args:
        model_version_id: the id of the model version.

    Returns:
        the URL to the model version if the dashboard is available, else None.
    """
    client = Client()
    server_model = client.zen_store.get_store_info()
    # if organization_id exists as key in server_config.metadata
    # only then output a URL.
    if server_model.metadata.get("organization_id"):
        base_url = get_base_url()
        if base_url:
            # TODO MODEL_VERSIONS resolves to /model_versions but on the
            # cloud, the URL is /model-versions. This should be fixed?
            return f"{base_url}/model-versions/{str(model_version_id)}"
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
