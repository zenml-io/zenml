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
import os
import subprocess
from pathlib import Path
from typing import Optional

import click

from zenml.cli.cli import cli
from zenml.cli.text_utils import (
    zenml_go_email_prompt,
    zenml_go_notebook_tutorial_message,
    zenml_go_privacy_message,
    zenml_go_thank_you_message,
    zenml_go_welcome_message,
)
from zenml.cli.utils import confirmation, declare, error, warning
from zenml.config.global_config import GlobalConfiguration
from zenml.console import console
from zenml.exceptions import InitializationException, GitNotFoundError
from zenml.repository import Repository
from zenml.utils.analytics_utils import identify_user
from zenml.logger import get_logger

logger = get_logger(__name__)
# WT_SESSION is a Windows Terminal specific environment variable. If it
# exists, we are on the latest Windows Terminal that supports emojis
_SHOW_EMOJIS = not os.name == "nt" or os.environ.get("WT_SESSION")

TUTORIAL_REPO = "https://github.com/zenml-io/zenbytes"


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

    gc = GlobalConfiguration()
    declare(
        f"The local active profile was initialized to "
        f"'{gc.active_profile_name}' and the local active stack to "
        f"'{gc.active_stack_name}'. This local configuration will only take "
        f"effect when you're running ZenML from the initialized repository "
        f"root, or from a subdirectory. For more information on profile "
        f"and stack configuration, please visit "
        f"https://docs.zenml.io."
    )


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


@cli.command("go")
def go() -> None:
    """Quickly explore ZenML with this walkthrough."""
    console.print(zenml_go_welcome_message, width=80)

    from zenml.config.global_config import GlobalConfiguration

    gc = GlobalConfiguration()
    if not gc.user_metadata:
        _prompt_email(gc)

    console.print(zenml_go_privacy_message, width=80)

    if not os.path.isdir("zenml_tutorial"):
        try:
            from git.repo.base import Repo
        except ImportError as e:
            logger.error(
                "At this point we would want to clone our tutorial repo onto "
                "your machine to let you dive right into our code. However, "
                "this machine has no installation of Git. Feel free to install "
                "git and rerun this command. Alternatively you can also "
                f"download the repo manually here: {TUTORIAL_REPO}."
            )
            raise GitNotFoundError(e)
        Repo.clone_from(TUTORIAL_REPO, "zenml_tutorial")

    cwd = os.getcwd()
    zenml_tutorial_path = os.path.join(cwd, "zenml_tutorial")

    ipynb_files = [
        fi for fi in os.listdir(zenml_tutorial_path) if fi.endswith(".ipynb")
    ]
    console.print(zenml_go_notebook_tutorial_message(ipynb_files), width=80)

    subprocess.check_call(["jupyter", "notebook"], cwd=zenml_tutorial_path)


def _prompt_email(gc: GlobalConfiguration) -> None:
    """Ask the user to give their email address"""

    console.print(zenml_go_email_prompt, width=80)

    email = click.prompt(
        click.style("Email: ", fg="blue"), default="", show_default=False
    )
    if email:
        if len(email) > 0 and email.count("@") != 1:
            warning("That doesn't look like an email. Skipping ...")
        else:

            console.print(zenml_go_thank_you_message, width=80)

            gc.user_metadata = {"email": email}
            identify_user({"email": email})
