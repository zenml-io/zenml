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
"""CLI functionality to interact with the ZenML Hub."""
import os
import subprocess
import sys
from importlib.util import find_spec
from typing import Any, Dict, List, Union

import click
import requests
from pydantic import BaseModel

from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import print_table
from zenml.constants import ENV_ZENML_HUB_URL
from zenml.enums import CliCategories
from zenml.logger import get_logger

HUB_URL = os.getenv(ENV_ZENML_HUB_URL)

logger = get_logger(__name__)


Json = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


class PluginResponseModel(BaseModel):
    """Response model for a plugin."""

    name: str
    logo: str
    index_url: str
    wheel_name: str


def server_url() -> str:
    """Helper function to get the hub url."""
    if HUB_URL:
        return HUB_URL
    return "https://demo-app-mc5klosfeq-lm.a.run.app"


def _hub_get(url: str) -> Json:
    """Helper function to make a GET request to the hub."""
    session = requests.Session()
    response = session.request(
        "GET",
        url,
        params={},
        verify=False,
        timeout=30,
    )
    payload: Json = response.json()
    return payload


def _list_plugins() -> List[PluginResponseModel]:
    """Helper function to list all plugins in the hub."""
    payload = _hub_get(f"{server_url()}/plugins")
    if not isinstance(payload, list):
        return []
    return [PluginResponseModel.parse_obj(plugin) for plugin in payload]


def _get_plugin(plugin_name: str) -> PluginResponseModel:
    """Helper function to get a specfic plugin from the hub."""
    payload = _hub_get(f"{server_url()}/plugins/{plugin_name}")
    return PluginResponseModel.parse_obj(payload)


def _is_plugin_installed(plugin_name: str) -> bool:
    """Helper function to check if a plugin is installed."""
    spec = find_spec(f"zenml.hub.{plugin_name}")
    return spec is not None


def _format_plugins_table(
    plugins: List[PluginResponseModel],
) -> List[Dict[str, str]]:
    """Helper function to format a list of plugins into a table."""
    plugins_table = []
    for plugin in plugins:
        if _is_plugin_installed(plugin.name):
            installed_icon = ":white_check_mark:"
        else:
            installed_icon = ":x:"
        plugins_table.append({"INSTALLED": installed_icon, **plugin.dict()})
    return plugins_table


@cli.group(cls=TagGroup, tag=CliCategories.HUB)
def hub() -> None:
    """Interact with the ZenML Hub."""


@hub.command("list")
def list_plugins() -> None:
    """List all plugins available on the hub."""
    plugins = _list_plugins()
    plugins_table = _format_plugins_table(plugins)
    print_table(plugins_table)


@hub.command("install")
@click.argument("plugin_name", type=str, required=True)
def install_plugin(plugin_name: str) -> None:
    """Install a plugin from the hub."""
    # Get plugin from hub
    plugin = _get_plugin(plugin_name)
    index_url = plugin.index_url
    wheel_name = plugin.wheel_name

    # pip install the wheel
    logger.info(
        f"Installing plugin '{plugin_name}' from {index_url}:{wheel_name}..."
    )
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--index-url",
            index_url,
            wheel_name,
        ]
    )
    logger.info(f"Successfully installed plugin '{plugin_name}'.")


@hub.command("uninstall")
@click.argument("plugin_name", type=str, required=True)
def uninstall_plugin(plugin_name: str) -> None:
    """Uninstall a plugin from the hub."""
    # Get plugin from hub
    plugin = _get_plugin(plugin_name)
    wheel_name = plugin.wheel_name

    # pip uninstall the wheel
    logger.info(f"Uninstalling plugin '{plugin_name}'...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "uninstall", wheel_name, "-y"]
    )
    logger.info(f"Successfully uninstalled plugin '{plugin_name}'.")
