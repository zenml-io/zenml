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

import sys
from pathlib import Path
from typing import Optional

import click

from zenml.cli.cli import cli
from zenml.cli.utils import confirmation, declare, error, warning
from zenml.exceptions import InitializationException
from zenml.repository import Repository


@cli.command("init", help="Initialize a ZenML repository.")
@click.option(
    "--path",
    type=click.Path(
        exists=True, file_okay=False, dir_okay=True, path_type=Path
    ),
)
def init(
    path: Optional[Path],
) -> None:
    """Initialize ZenML on given path.

    Args:
      path: Path to the repository.

    Raises:
        InitializationException: If the repo is already initialized.
    """
    if sys.version_info.minor == 6:
        warning(
            "ZenML support for Python 3.6 will be deprecated soon. Please "
            "consider upgrading your Python version to ensure ZenML works "
            "properly in the future."
        )
    if path is None:
        path = Path.cwd()

    declare(f"Initializing ZenML repository at {path}.")

    try:
        Repository.initialize(root=path)
        declare(f"ZenML repository initialized at {path}.")
    except InitializationException as e:
        error(f"{e}")


@cli.command("clean")
@click.option("--yes", "-y", type=click.BOOL, default=False)
def clean(yes: bool = False) -> None:
    """Clean everything in repository.

    Args:
      yes: bool:  (Default value = False)
    """
    if not yes:
        _ = confirmation(
            "This will completely delete all pipelines, their associated "
            "artifacts and metadata ever created in this ZenML repository. "
            "Are you sure you want to proceed?"
        )

    error("Not implemented for this version")
