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

import os
import sys
from typing import Optional

import click

from zenml.cli.cli import cli
from zenml.cli.utils import confirmation, declare, error, warning
from zenml.core.repo import Repository
from zenml.exceptions import InitializationException
from zenml.utils.analytics_utils import INITIALIZE_REPO, track


@cli.command("init", help="Initialize zenml on a given path.")
@click.option("--repo_path", type=click.Path(exists=True))
@track(event=INITIALIZE_REPO)
def init(
    repo_path: Optional[str],
) -> None:
    """Initialize ZenML on given path.

    Args:
      repo_path: Path to the repository.

    Raises:
        InitializationException: If the repo is already initialized.
    """
    if sys.version_info.minor == 6:
        warning(
            "ZenML support for Python 3.6 will be deprecated soon. Please "
            "consider upgrading your Python version to ensure ZenML works "
            "properly in the future."
        )
    if repo_path is None:
        repo_path = os.getcwd()

    declare(f"Initializing at {repo_path}")

    try:
        Repository.init_repo(path=repo_path)
        declare(f"ZenML repo initialized at {repo_path}")
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
