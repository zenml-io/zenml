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
from zenml.core.pipelines.training_pipeline import TrainingPipeline


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
@click.argument('pipeline_id')
def get_pipeline_by_id(pipeline_id: Text):
    """
    Gets pipeline from current repository by matching a (partial) identifier
    against the pipeline yaml name.

    """
    config = return_pipeline_config_by_id(pipeline_id)

    if config is not None:
        click.echo(to_pretty_string(config))


@pipeline.command('run')
@click.argument('pipeline_id')
@click.option("--metadata_store", default=None,
              help="Path to a custom metadata store to use.")
@click.option("--artifact_store", default=None,
              help="Path to a custom metadata store to use.")
def run_pipeline_by_id(pipeline_id: Text,
                       metadata_store: Text,
                       artifact_store: Text):
    """
    Gets pipeline from current repository by matching a (partial) identifier
    against the pipeline yaml name.

    Args:
        pipeline_id: ID of the designated pipeline. Has to be partially
        matching the YAML file name.
    """
    config = return_pipeline_config_by_id(pipeline_id)
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


def return_pipeline_config_by_id(pipeline_id: Text):
    """
    Utility to get a pipeline object by matching a supplied ID against the
    pipeline YAML configuration associated with it.

    Args:
        pipeline_id: ID of the designated pipeline. Has to be partially
        matching the YAML file name.

    Returns:
        A Pipeline config object built from the matched config

    """
    try:
        repo: Repository = Repository.get_instance()
    except Exception as e:
        error(e)
        return None

    try:
        file_paths = repo.get_pipeline_file_paths()
        path = next(y for y in file_paths if pipeline_id in y)
    except StopIteration:
        error(f"No pipeline matching the identifier {pipeline_id} "
              f"was found.")
        return None

    return read_yaml(path)
