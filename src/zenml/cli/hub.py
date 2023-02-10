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

import click
import requests

from zenml.cli.cli import TagGroup, cli
from zenml.constants import ENV_ZENML_HUB_URL
from zenml.enums import CliCategories
from zenml.logger import get_logger

HUB_URL = os.getenv(ENV_ZENML_HUB_URL)

logger = get_logger(__name__)


@cli.group(cls=TagGroup, tag=CliCategories.HUB)
def hub() -> None:
    """Interact with the ZenML Hub."""


@hub.command()
@click.argument("plugin_name", type=str, required=True)
def install(plugin_name: str):
    """Install a plugin from the hub."""

    # GET on /plugins/{plugin_id} to fetch the wheel url
    session = requests.Session()
    server_url = "https://demo-app-mc5klosfeq-lm.a.run.app"
    response = session.request(
        "GET",
        f"{server_url}/plugins/{plugin_name}",
        params={},
        verify=False,
        timeout=30,
    )
    payload = response.json()
    index_url = payload["index_url"]
    wheel_name = payload["wheel_name"]
    logger.info(
        f"Installing plugin '{plugin_name}' from {index_url}:{wheel_name}..."
    )

    # pip install the wheel
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
