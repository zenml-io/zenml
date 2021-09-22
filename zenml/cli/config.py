#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""CLI for manipulating ZenML local and global config file."""

from typing import List, Text

import click

from zenml import enums
from zenml.cli import utils as cli_utils
from zenml.cli.cli import cli
from zenml.config.global_config import GlobalConfig
from zenml.core.component_factory import component_factory
from zenml.core.repo import Repository


# Analytics
@cli.group()
def analytics():
    """Analytics for opt-in and opt-out"""


@analytics.command(
    "opt-in", context_settings=dict(ignore_unknown_options=True)
)
def opt_in():
    """Opt-in to analytics"""
    GlobalConfig().analytics_opt_in = True
    click.echo("Opted in to analytics.")


@analytics.command(
    "opt-out", context_settings=dict(ignore_unknown_options=True)
)
def opt_out():
    """Opt-out to analytics"""
    GlobalConfig().analytics_opt_in = False
    click.echo("Opted in to analytics.")


# Metadata Store
@cli.group()
def metadata():
    """Utilities for metadata store"""


@metadata.command(
    "register", context_settings=dict(ignore_unknown_options=True)
)
@click.argument("metadata_store_name", type=str)
@click.argument("metadata_store_type", type=str)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def register_metadata_store(
    metadata_store_name: Text, metadata_store_type: Text, args: List[Text]
):
    """Register a metadata store."""

    try:
        parsed_args = cli_utils.parse_unknown_options(args)
    except AssertionError as e:
        cli_utils.error(str(e))
        return

    repo: Repository = Repository()
    comp = component_factory.get_single_component(
        metadata_store_type, enums.MLMetadataTypes
    )
    metadata_store = comp(**parsed_args)
    service = repo.get_service()
    service.register_metadata_store(metadata_store_name, metadata_store)


@metadata.command("get")
def get_metadata_stores():
    """Print metadata store from local config."""
    service = Repository().get_service()
    cli_utils.title("Metadata Stores:")
    cli_utils.echo_component_list(service.metadata_stores)


@metadata.command("delete")
@click.argument("metadata_store_name", type=str)
def delete_metadata_store(metadata_store_name: Text):
    """Delete a metadata store."""
    service = Repository().get_service()
    cli_utils.declare(f"Deleting metadata store: {metadata_store_name}")
    service.delete_metadata_store(metadata_store_name)
    cli_utils.declare("Deleted!")


#
# # Artifact Store
# @cli.group()
# def artifact():
#     """Utilities for artifact store"""
#
#
# @artifact.command("set")
# @click.argument("path", type=click.Path())
# def set_artifact_store(path: Text = None):
#     """Change artifact store for local config."""
#     repo: Repository = Repository.get_instance()
#     repo.zenml_config.set_artifact_store(path)
#     click.echo(f"Default artifact store updated to {path}")
#
#
# @artifacts.command("get")
# def get_artifact_store():
#     """Print artifact store from local config."""
#     repo: Repository = Repository.get_instance()
#     click.echo(
#         f"Default artifact store points to: "
#         f"{repo.get_default_artifact_store().path}"
#     )
#
#
# # Pipeline Directory
# @config.group()
# def pipelines():
#     """Utilities for pipelines dir store"""
#
#
# @pipelines.command("set")
# @click.argument("path", type=click.Path())
# def set_pipelines_dir(path: Text = None):
#     """Change pipelines dir for local config."""
#     repo: Repository = Repository.get_instance()
#     repo.zenml_config.set_pipelines_dir(path)
#     click.echo(f"Default pipelines dir updated to {path}")
#
#
# @pipelines.command("get")
# def get_pipelines_dir():
#     """Print pipelines dir from local config."""
#     repo: Repository = Repository.get_instance()
#     click.echo(
#         f"Default pipelines dir points to: "
#         f"{repo.get_default_pipelines_dir()}"
#     )
#
#
# @metadata.command("set")
# @click.argument("metadata_store_name", type=str)
# def set_active_provider(provider_name: Text):
#     """Sets a provider active."""
#     repo = Repository()
#     service = repo.get_service()
#     service.get_provider(provider_name)
#     # repo.set_active
