#  Copyright (c) maiot GmbH 2020. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import os
from typing import Text

import click
import git

from zenml.cli.cli import cli
from zenml.cli.utils import confirmation
from zenml.cli.utils import pass_repo
from zenml.repo import Repository
from zenml.utils.analytics_utils import track, INITIALIZE


@cli.command('init')
@click.option('--repo_path', type=click.Path(exists=True))
@click.option('--pipelines_dir', type=click.Path(exists=True))
@click.option('--analytics_opt_in', '-a', type=click.BOOL)
@track(event=INITIALIZE)
def init(repo_path: Text, pipelines_dir: Text = None,
         analytics_opt_in: bool = True):
    """Initialize ZenML on given path."""
    if repo_path is None:
        repo_path = os.getcwd()

    try:
        Repository.init_repo(
            repo_path,
            None,
            None,
            pipelines_dir,
            analytics_opt_in,
        )
        click.echo(f'ZenML repo initialized at {repo_path}')
    except git.InvalidGitRepositoryError:
        click.echo(f'{repo_path} is not a valid git repository! Please '
                   f'initialize ZenML within a git repository.')


@cli.command('clean')
@click.option('--yes', '-y', type=click.BOOL, default=False)
@pass_repo
def clean(repo: Repository, yes: bool = False):
    """Clean everything in repository."""
    if not yes:
        confirm = confirmation(
            "This will completely delete all pipelines, their associated "
            "artifacts and metadata ever created in this ZenML repository. "
            "Are you sure you want to proceed?")
    else:
        confirm = True

    click.echo("Not implemented for this version")
    # if confirm:
    #     repo.clean()
