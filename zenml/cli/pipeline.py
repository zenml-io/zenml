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
from zenml.cli.utils import error, pretty_print
from zenml.core.repo.repo import Repository
from zenml.utils.yaml_utils import read_yaml
from zenml.core.pipelines.training_pipeline import TrainingPipeline


@cli.group()
def pipeline():
    """Pipeline group"""
    pass


@pipeline.command('compare')
def compare_pipelines():
    """Compares pipelines in repo"""
    click.echo('Comparing pipelines in repo: Starting app..')
    repo: Repository = Repository.get_instance()
    repo.compare_pipelines()


@pipeline.command('list')
def list_pipelines():
    """Lists pipelines in the current repository."""
    try:
        repo: Repository = Repository.get_instance()
    except Exception as e:
        error(e)
        return

    pipelines = repo.get_pipelines()

    names = [p.name for p in pipelines]
    types = [p.PIPELINE_TYPE for p in pipelines]
    statuses = [p.get_status() for p in pipelines]
    cache_enabled = [p.enable_cache for p in pipelines]
    filenames = [p.file_name for p in pipelines]

    headers = ["name", "type", "cache enabled", "status", "file name"]

    click.echo(tabulate(zip(names, types, cache_enabled, statuses, filenames),
                        headers=headers))


@pipeline.command('get')
@click.argument('pipeline_name')
def get_pipeline_by_name(pipeline_name: Text):
    """
    Gets pipeline from current repository by matching a name against a
    pipeline name in the repository.
    """
    repo: Repository = Repository.get_instance()
    try:
        p = repo.get_pipeline_by_name(pipeline_name)
    except Exception as e:
        error(e)
        return

    pretty_print(p)


@pipeline.command('run')
@click.argument('path_to_config')
@click.option("--metadata_store", default=None,
              help="Path to a custom metadata store to use.")
@click.option("--artifact_store", default=None,
              help="Path to a custom metadata store to use.")
def run_pipeline(path_to_config: Text,
                 metadata_store: Text,
                 artifact_store: Text):
    """
    Runs pipeline specified by the given config YAML object.

    Args:
        path_to_config: Path to config of the designated pipeline.
         Has to be matching the YAML file name.
        artifact_store: Path to a custom artifact store.
        metadata_store: Path to a custom metadata store. Currently not
         implemented.

    """
    # config has metadata store, backends and artifact store,
    # so no need to specify them
    config = read_yaml(path_to_config)
    repo: Repository = Repository.get_instance()

    if metadata_store is not None:
        # TODO[MEDIUM]: Figure out how to configure an alternative
        #  metadata store from a command line string
        click.echo("The option to configure the metadata store "
                   "from the command line is not yet implemented.")

    if artifact_store is not None:
        path = artifact_store
        repo.zenml_config.set_artifact_store(artifact_store_path=path)
    try:
        p: TrainingPipeline = TrainingPipeline.from_config(config)
        p.run(artifact_store=artifact_store)
    except Exception as e:
        error(e)
