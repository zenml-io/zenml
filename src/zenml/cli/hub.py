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

from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import print_table
from zenml.constants import ENV_ZENML_HUB_URL
from zenml.enums import CliCategories
from zenml.logger import get_logger

HUB_URL = os.getenv(ENV_ZENML_HUB_URL)

logger = get_logger(__name__)


Json = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


def server_url():
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
    payload = response.json()
    return payload


def _list_plugins() -> Json:
    """Helper function to list all plugins in the hub."""
    return _hub_get(f"{server_url()}/plugins")


def _get_plugin(plugin_name: str) -> Json:
    """Helper function to get a specfic plugin from the hub."""
    return _hub_get(f"{server_url()}/plugins/{plugin_name}")


def _is_package_installed(package_name: str) -> bool:
    """Helper function to check if a pip package is installed."""
    spec = find_spec(package_name)
    return spec is not None


def _format_plugins_table(
    plugins: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    """Helper function to add an 'INSTALLED' column to the plugins table."""
    formatted_plugins = []
    for plugin in plugins:
        if _is_package_installed(plugin["wheel_name"]):
            installed_icon = ":white_check_mark:"
        else:
            installed_icon = ":x:"
        formatted_plugins.append({"INSTALLED": installed_icon, **plugin})
    return formatted_plugins


@cli.group(cls=TagGroup, tag=CliCategories.HUB)
def hub() -> None:
    """Interact with the ZenML Hub."""


@hub.command("list")
def list_plugins() -> None:
    """List all plugins available on the hub."""
    plugins = _list_plugins()
    if isinstance(plugins, list):
        plugins = _format_plugins_table(plugins)
    print_table(plugins)


@hub.command("install")
@click.argument("plugin_name", type=str, required=True)
def install_plugin(plugin_name: str):
    """Install a plugin from the hub."""

    # GET on /plugins/{plugin_id} to fetch the index url and wheel name
    plugin = _get_plugin(plugin_name)
    index_url = plugin["index_url"]
    wheel_name = plugin["wheel_name"]

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
def uninstall_plugin(plugin_name: str):
    """Uninstall a plugin from the hub."""
    # GET on /plugins/{plugin_id} to fetch the index url and wheel name
    plugin = _get_plugin(plugin_name)
    wheel_name = plugin["wheel_name"]

    # pip uninstall the wheel
    logger.info(f"Uninstalling plugin '{plugin_name}'...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "uninstall", wheel_name, "-y"]
    )
    logger.info(f"Successfully uninstalled plugin '{plugin_name}'.")
