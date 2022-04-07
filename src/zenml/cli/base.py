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
import textwrap
from pathlib import Path
from typing import Optional

import click

from zenml.cli.cli import cli
from zenml.cli.utils import confirmation, declare, error
from zenml.config.global_config import GlobalConfiguration
from zenml.console import console
from zenml.exceptions import InitializationException
from zenml.repository import Repository
from zenml.utils.analytics_utils import identify_user


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
    """Quickly explore zenml with this walk through.

    """

    # WT_SESSION is a Windows Terminal specific environment variable. If it
    # exists, we are on the latest Windows Terminal that supports emojis
    _SHOW_EMOJIS = not os.name == 'nt' or os.environ.get("WT_SESSION")

    # TODO [MEDIUM]: Only run first part if no email is registered

    _hello_message = (("⛩  " if _SHOW_EMOJIS else "")
                      + click.style("Welcome to ZenML!", bold=True))

    click.echo(_hello_message)

    _email_message = textwrap.dedent("""
    Here at ZenML we are working hard to produce the best 
    possible MLOps tool. In order to solve real world problems 
    we want to ask you, the user for feedback and ideas. If 
    you are interested in helping us shape the MLOps world 
    please leave your email below. We will only use this for the 
    purpose of reaching out to you for user interview.
    """)

    click.echo(_email_message)

    email = click.prompt(click.style("Email: ", fg="blue"))

    if email:
        if len(email) > 0 and email.count("@") != 1:
            cli.error("That doesn't look like an email")
        else:
            _thanks_message = (
                "\n" +
                ("🙏  " if _SHOW_EMOJIS else "")
                + click.style("Thank You!", bold=True)
                + "\n"
            )

            click.echo(_thanks_message)
            identify_user({"email": email})

    _privacy_message = textwrap.dedent(
        """
        As an open source project we rely on usage statistics to inform
        our decisions regarding new features. The statistics do not 
        contain an of your code, data or personal information. All we
        see on our end is metadata like operating system, stack 
        flavors and triggered events like pipeline runs.
        \n
        If  you wish to opt out, feel free to run the following command
            zenml analytics opt-out
        """)

    click.echo(click.style("Privacy Policy at ZenML!", bold=True)
               + _privacy_message)
