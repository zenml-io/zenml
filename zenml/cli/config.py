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
"""CLI for manipulating ZenML local config file."""

from typing import Text

import click

from zenml.cli.cli import cli
from zenml.cli.cli import pass_config
from zenml.cli.utils import parse_unknown_options
from zenml.core.repo.repo import Repository


@cli.group()
def config():
    """Config"""
    pass


# Analytics
@config.group()
def analytics():
    """Analytics for opt-in and opt-out"""
    pass


@analytics.command('opt-in',
                   context_settings=dict(ignore_unknown_options=True))
@pass_config
def opt_in(config):
    """Opt-in to analytics"""
    config.set_analytics_opt_in(True)
    click.echo('Opted in to analytics.')


@analytics.command('opt-out',
                   context_settings=dict(ignore_unknown_options=True))
@pass_config
def opt_out(config):
    """Opt-out of analytics"""
    config.set_analytics_opt_in(False)
    click.echo('Opted out of analytics.')


# Metadata Store
@config.group()
def metadata():
    """Utilities for metadata store"""
    pass


@metadata.command('set', context_settings=dict(ignore_unknown_options=True))
@click.argument('store_type', type=str)
@click.argument('args', nargs=-1, type=click.UNPROCESSED)
def set_metadata_store(store_type, args):
    """Set metadata store for local config."""

    try:
        parsed_args = parse_unknown_options(args)
    except AssertionError as e:
        click.echo(str(e))
        return

    # TODO: [LOW] Hard-coded
    config = {
        'type': store_type,
        'args': parsed_args
    }
    from zenml.core.metadata.metadata_wrapper import ZenMLMetadataStore

    store = ZenMLMetadataStore.from_config(config)
    repo: Repository = Repository.get_instance()
    repo.zenml_config.set_metadata_store(store)

    click.echo(f'Metadata store set to: {store.to_config()}')


@metadata.command('get')
def get_metadata_store():
    """Print metadata store from local config."""
    repo: Repository = Repository.get_instance()
    click.echo(f'Metadata store: '
               f'{repo.get_metadata_store().to_config()}')


# Artifact Store
@config.group()
def artifacts():
    """Utilities for artifact store"""
    pass


@artifacts.command('set')
@click.argument('path', type=click.Path())
def set_artifact_store(path: Text = None):
    """Change artifact store for local config."""
    repo: Repository = Repository.get_instance()
    repo.zenml_config.set_artifact_store(path)
    click.echo(f'Artifact store updated to {path}')


@artifacts.command('get')
def get_artifact_store():
    """Print artifact store from local config."""
    repo: Repository = Repository.get_instance()
    click.echo(f'Artifact store points to: {repo.get_artifact_store().path}')
