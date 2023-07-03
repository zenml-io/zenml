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

from zenml.client import Client
from zenml.constants import ENV_AUTO_OPEN_DASHBOARD, handle_bool_env_var
from zenml.enums import EnvironmentType, StoreType
from zenml.environment import get_environment
from zenml.logger import get_logger
from zenml.models.pipeline_run_models import PipelineRunResponseModel

logger = get_logger(__name__)


def get_run_url(run: PipelineRunResponseModel) -> Optional[str]:
    """Computes a dashboard url to directly view the run.

    Args:
        run: Pipeline run to be viewed.

    Returns:
        A direct url link to the pipeline run details page. If run does not exist,
        returns None.
    """
    client = Client()

    if client.zen_store.type != StoreType.REST:
        return ""

    url = client.zen_store.url + f"/workspaces/{client.active_workspace.name}"
    run_id = str(run.id)

    if run.pipeline:
        pipeline_id = str(run.pipeline.id)
        url += f"/pipelines/{pipeline_id}/runs"
    else:
        url += "/all-runs"

    url += f"/{run_id}/dag"

    return url


def print_run_url(run: PipelineRunResponseModel) -> None:
    """Logs a dashboard url to directly view the run.

    Args:
        run: Pipeline run to be viewed.
    """
    client = Client()

    if client.zen_store.type == StoreType.REST:
        url = get_run_url(run)
        if url:
            logger.info(f"Dashboard URL: {url}")
    elif client.zen_store.type == StoreType.SQL:
        # Connected to SQL Store Type, we're local
        logger.info(
            "Pipeline visualization can be seen in the ZenML Dashboard. "
            "Run `zenml up` to see your pipeline!"
        )


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
        if handle_bool_env_var(ENV_AUTO_OPEN_DASHBOARD, default=True):
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
