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
"""Base functionality for the CLI."""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import click

from zenml import __version__ as zenml_version
from zenml.cli.cli import cli
from zenml.cli.server import down
from zenml.cli.utils import confirmation, declare, error, warning
from zenml.client import Client
from zenml.config.global_config import GlobalConfiguration
from zenml.console import console
from zenml.constants import REPOSITORY_DIRECTORY_NAME
from zenml.enums import AnalyticsEventSource
from zenml.exceptions import GitNotFoundError, InitializationException
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils.analytics_utils import AnalyticsEvent, event_handler
from zenml.utils.io_utils import copy_dir, get_global_config_directory

logger = get_logger(__name__)
# WT_SESSION is a Windows Terminal specific environment variable. If it
# exists, we are on the latest Windows Terminal that supports emojis
_SHOW_EMOJIS = not os.name == "nt" or os.environ.get("WT_SESSION")

TUTORIAL_REPO = "https://github.com/zenml-io/zenml"


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
    """
    if path is None:
        path = Path.cwd()

    with console.status(f"Initializing ZenML repository at {path}.\n"):
        try:
            Client.initialize(root=path)
            declare(f"ZenML repository initialized at {path}.")
        except InitializationException as e:
            error(f"{e}")

    declare(
        f"The local active stack was initialized to "
        f"'{Client().active_stack_model.name}'. This local configuration "
        f"will only take effect when you're running ZenML from the initialized "
        f"repository root, or from a subdirectory. For more information on "
        f"repositories and configurations, please visit "
        f"https://docs.zenml.io/starter-guide/stacks/managing-stacks."
    )


def _delete_local_files(force_delete: bool = False) -> None:
    """Delete local files corresponding to the active stack.

    Args:
        force_delete: Whether to force delete the files.
    """
    if not force_delete:
        confirm = confirmation(
            "DANGER: This will completely delete metadata, artifacts and so "
            "on associated with all active stack components. \n\n"
            "Are you sure you want to proceed?"
        )
        if not confirm:
            declare("Aborting clean.")
            return

    client = Client()
    if client.active_stack_model:
        stack_components = client.active_stack_model.components
        for _, components in stack_components.items():
            # TODO: [server] this needs to be adjusted as the ComponentModel
            #  does not have the local_path property anymore
            from zenml.stack.stack_component import StackComponent

            local_path = StackComponent.from_model(components[0]).local_path
            if local_path:
                for path in Path(local_path).iterdir():
                    if fileio.isdir(str(path)):
                        fileio.rmtree(str(path))
                    else:
                        fileio.remove(str(path))
                    warning(f"Deleted `{path}`", italic=True)
    declare("Deleted all files relating to the local active stack.")


@cli.command(
    "clean",
    hidden=True,
    help="Delete all ZenML metadata, artifacts and stacks.",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Don't ask for confirmation.",
)
@click.option(
    "--local",
    "-l",
    is_flag=True,
    default=False,
    help="Delete local files relating to the active stack.",
)
@click.pass_context
def clean(ctx: click.Context, yes: bool = False, local: bool = False) -> None:
    """Delete all ZenML metadata, artifacts and stacks.

    This is a destructive operation, primarily intended for use in development.

    Args:
        ctx: The click context.
        yes: If you don't want a confirmation prompt.
        local: If you want to delete local files associated with the active
            stack.
    """
    ctx.invoke(
        down,
    )
    if local:
        _delete_local_files(force_delete=yes)
        return

    confirm = None
    if not yes:
        confirm = confirmation(
            "DANGER: This will completely delete all artifacts, metadata and "
            "stacks \never created during the use of ZenML. Pipelines and "
            "stack components running non-\nlocally will still exist. Please "
            "delete those manually. \n\nAre you sure you want to proceed?"
        )

    if yes or confirm:
        # delete the .zen folder
        local_zen_repo_config = Path.cwd() / REPOSITORY_DIRECTORY_NAME
        if fileio.exists(str(local_zen_repo_config)):
            fileio.rmtree(str(local_zen_repo_config))
            declare(f"Deleted local ZenML config from {local_zen_repo_config}.")

        # delete the zen store and all other files and directories used by ZenML
        # to persist information locally (e.g. artifacts)
        global_zen_config = Path(get_global_config_directory())
        if fileio.exists(str(global_zen_config)):
            gc = GlobalConfiguration()
            for dir_name in fileio.listdir(str(global_zen_config)):
                if fileio.isdir(str(global_zen_config / str(dir_name))):
                    warning(
                        f"Deleting '{str(dir_name)}' directory from global "
                        f"config."
                    )
            fileio.rmtree(str(global_zen_config))
            declare(f"Deleted global ZenML config from {global_zen_config}.")
            fresh_gc = GlobalConfiguration(
                user_id=gc.user_id,
                analytics_opt_in=gc.analytics_opt_in,
                version=gc.version,
            )
            fresh_gc.set_default_store()
            declare(f"Reinitialized ZenML global config at {Path.cwd()}.")

    else:
        declare("Aborting clean.")


@cli.command("go")
def go() -> None:
    """Quickly explore ZenML with this walk-through.

    Raises:
        GitNotFoundError: If git is not installed.
    """
    from zenml.cli.text_utils import (
        zenml_go_notebook_tutorial_message,
        zenml_go_privacy_message,
        zenml_go_welcome_message,
    )

    metadata = {}

    console.print(zenml_go_welcome_message, width=80)

    client = Client()

    # Only ask them if they haven't been asked before and the email
    # hasn't been supplied by other means
    if (
        not GlobalConfiguration().user_email
        and client.active_user.email_opted_in is None
    ):
        gave_email = _prompt_email()
        metadata = {"gave_email": gave_email}

    with event_handler(event=AnalyticsEvent.RUN_ZENML_GO, metadata=metadata):

        console.print(zenml_go_privacy_message, width=80)

        zenml_tutorial_path = os.path.join(os.getcwd(), "zenml_tutorial")

        if not os.path.isdir(zenml_tutorial_path):
            try:
                from git.repo.base import Repo
            except ImportError as e:
                logger.error(
                    "At this point we would want to clone our tutorial repo "
                    "onto your machine to let you dive right into our code. "
                    "However, this machine has no installation of Git. Feel "
                    "free to install git and rerun this command. Alternatively "
                    "you can also download the repo manually here: "
                    f"{TUTORIAL_REPO}. The tutorial is in the "
                    f"'examples/quickstart/notebooks' directory."
                )
                raise GitNotFoundError(e)

            with tempfile.TemporaryDirectory() as tmpdirname:
                tmp_cloned_dir = os.path.join(tmpdirname, "zenml_repo")
                with console.status(
                    "Cloning tutorial. This sometimes takes a minute..."
                ):
                    Repo.clone_from(
                        TUTORIAL_REPO,
                        tmp_cloned_dir,
                        branch=f"release/{zenml_version}",
                    )
                example_dir = os.path.join(
                    tmp_cloned_dir, "examples/quickstart"
                )
                copy_dir(example_dir, zenml_tutorial_path)
        else:
            logger.warning(
                f"{zenml_tutorial_path} already exists! Continuing without "
                "cloning."
            )

        # get list of all .ipynb files in zenml_tutorial_path
        ipynb_files = []
        for dirpath, _, filenames in os.walk(zenml_tutorial_path):
            for filename in filenames:
                if filename.endswith(".ipynb"):
                    ipynb_files.append(os.path.join(dirpath, filename))

        ipynb_files.sort()
        console.print(zenml_go_notebook_tutorial_message(ipynb_files), width=80)
        input("Press ENTER to continue...")
    notebook_path = os.path.join(zenml_tutorial_path, "notebooks")
    subprocess.check_call(["jupyter", "notebook"], cwd=notebook_path)


def _prompt_email() -> bool:
    """Ask the user to give their email address.

    Returns:
        bool: True if the user gave an email address, False otherwise.
    """
    from zenml.cli.text_utils import (
        zenml_go_email_prompt,
        zenml_go_thank_you_message,
    )

    console.print(zenml_go_email_prompt, width=80)

    email = click.prompt(
        click.style("Email", fg="blue"), default="", show_default=False
    )
    client = Client()
    if email:
        if len(email) > 0 and email.count("@") != 1:
            warning("That doesn't look like an email. Skipping ...")
        else:
            console.print(zenml_go_thank_you_message, width=80)

            # For now, hard-code to ZENML GO as the source
            GlobalConfiguration().record_email_opt_in_out(
                opted_in=True, email=email, source=AnalyticsEventSource.ZENML_GO
            )

            # Add consent and email to user model
            client.update_user(
                user_name_or_id=client.active_user.id,
                updated_email=email,
                updated_email_opt_in=True,
            )
            return True
    else:
        GlobalConfiguration().record_email_opt_in_out(
            opted_in=False, email=None, source=AnalyticsEventSource.ZENML_GO
        )

        # This is the case where user opts out
        client.update_user(
            client.active_user.id,
            updated_email_opt_in=False,
        )

    return False
