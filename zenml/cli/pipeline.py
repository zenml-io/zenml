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
"""CLI for pipelines."""

import click
from tabulate import tabulate
from typing import Text

from zenml.cli.cli import cli
from zenml.cli.utils import error
from zenml.core.repo.repo import Repository
from zenml.utils.yaml_utils import read_yaml
from zenml.utils.print_utils import to_pretty_string

@cli.group()
def pipeline():
    """Pipeline group"""
    pass


@pipeline.command('compare')
def set_metadata_store():
    """Compares pipelines in repo"""
    click.echo('Comparing pipelines in repo: Starting app..')
    repo: Repository = Repository.get_instance()
    repo.compare_pipelines()


@pipeline.command('list')
def list_pipelines():
    """Lists pipelines in the current repository."""
    repo: Repository = Repository.get_instance()

    pipelines = repo.get_pipelines()

    names = [p.name for p in pipelines]
    types = [p.PIPELINE_TYPE for p in pipelines]
    statuses = [p.get_status() for p in pipelines]
    cache_enabled = [p.enable_cache for p in pipelines]
    filenames = [p.file_name for p in pipelines]

    print(tabulate(zip(names, types, cache_enabled, statuses, filenames),
                   headers=["name", "type", "cache enabled", "status", "file name"]))


@pipeline.command('get')
@click.argument('pipeline_id')
def get_pipeline_by_id(pipeline_id: Text):
    """
    Gets pipeline from current repository by name.

    """
    repo: Repository = Repository.get_instance()

    file_paths = repo.get_pipeline_file_paths()
    try:
        path = next(y for y in file_paths if pipeline_id in y)
    except StopIteration:
        error(f"No pipeline matching the identifier {pipeline_id} "
              f"was found.")
        # assignment to disable pycharm warning
        path = ""

    click.echo(to_pretty_string(read_yaml(path)))
