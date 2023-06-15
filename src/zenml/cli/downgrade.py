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
"""CLI command to downgrade the ZenML Global Configuration version."""

from zenml import __version__
from zenml.cli import utils as cli_utils
from zenml.cli.cli import cli
from zenml.config.global_config import GlobalConfiguration


@cli.command("downgrade", help="Downgrade zenml version in global config.")
def disconnect_server() -> None:
    """Downgrade zenml version in global config to match the current version."""
    gc = GlobalConfiguration()

    if gc.version == __version__:
        cli_utils.declare(
            "The ZenML Global Configuration version is already "
            "set to the same version as the current ZenML client."
        )
        return

    if cli_utils.confirmation(
        "Are you sure you want to downgrade the ZenML Global Configuration "
        "version to match the current ZenML client version? It is "
        "recommended to upgrade the ZenML Global Configuration version "
        "instead. Otherwise, you might experience unexpected behavior "
        "such as model schema validation failures or even data loss."
    ):
        gc.version = __version__
        cli_utils.declare(
            "The ZenML Global Configuration version has been "
            "downgraded to match the current ZenML client version."
        )
