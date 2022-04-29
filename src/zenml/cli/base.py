#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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

from pathlib import Path
from typing import Optional

import click

from zenml.cli.cli import cli
from zenml.cli.utils import confirmation, declare, error
from zenml.config.global_config import GlobalConfiguration
from zenml.console import console
from zenml.constants import CONFIG_FILE_NAME, REPOSITORY_DIRECTORY_NAME
from zenml.exceptions import InitializationException
from zenml.io import fileio
from zenml.io.utils import get_global_config_directory
from zenml.repository import Repository
from zenml.utils import yaml_utils


@cli.command("init", help="Initialize a ZenML repository.")
@click.option(
    "--path",
    type=click.Path(
        exists=True, file_okay=False, dir_okay=True, path_type=Path
    ),
)
def init(path: Optional[Path]) -> None:
    """Initialize ZenML on given path.

    Args:
      path: Path to the repository.

    Raises:
        InitializationException: If the repo is already initialized.
    """
    if path is None:
        path = Path.cwd()

    with console.status(f"Initializing ZenML repository at {path}.\n"):
        try:
            Repository.initialize(root=path)
            declare(f"ZenML repository initialized at {path}.")
        except InitializationException as e:
            error(f"{e}")

    cfg = GlobalConfiguration()
    declare(
        f"The local active profile was initialized to "
        f"'{cfg.active_profile_name}' and the local active stack to "
        f"'{cfg.active_stack_name}'. This local configuration will only take "
        f"effect when you're running ZenML from the initialized repository "
        f"root, or from a subdirectory. For more information on profile "
        f"and stack configuration, please visit "
        f"https://docs.zenml.io."
    )


@cli.command("clean")
@click.option("--yes", "-y", is_flag=True, default=False)
def clean(yes: bool = False) -> None:
    """Delete all ZenML metadata and artifacts.

    This is a destructive operation, primarily intended for use in development.

    Args:
      yes: bool:  (Default value = False)
    """
    if not yes:
        confirm = confirmation(
            "DANGER: This will completely delete all artifacts and metadata ever created \n"
            "in this ZenML repository. Note: Pipelines and stack components running \n"
            "non-locally will still exist. Please delete them manually.\n"
            "Are you sure you want to proceed?"
        )

    if yes or confirm:
        local_zen_repo_config = Path.cwd() / REPOSITORY_DIRECTORY_NAME
        global_zen_config = Path(get_global_config_directory())
        if fileio.exists(str(local_zen_repo_config)):
            fileio.rmtree(str(local_zen_repo_config))
            declare(f"Deleted local ZenML config from {local_zen_repo_config}.")
        if fileio.exists(str(global_zen_config)):
            config_yaml_path = global_zen_config / CONFIG_FILE_NAME
            config_yaml_data = yaml_utils.read_yaml(str(config_yaml_path))
            config_yaml_data["profiles"]
            breakpoint()
            fileio.rmtree(str(global_zen_config))
            declare(f"Deleted global ZenML config from {global_zen_config}.")

        fileio.makedirs(str(global_zen_config))
        yaml_utils.write_yaml(str(config_yaml_path), config_yaml_data)
        Repository.initialize(root=Path.cwd())

    else:
        declare("Aborting clean.")
