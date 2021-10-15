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

from typing import List

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import cli
from zenml.config.global_config import GlobalConfig
from zenml.core.component_factory import (
    artifact_store_factory,
    metadata_store_factory,
    orchestrator_store_factory,
)
from zenml.core.repo import Repository


# Analytics
@cli.group()
def analytics():
    """Analytics for opt-in and opt-out"""


@analytics.command("opt-in", context_settings=dict(ignore_unknown_options=True))
def opt_in():
    """Opt-in to analytics"""
    GlobalConfig().analytics_opt_in = True
    cli_utils.declare("Opted in to analytics.")


@analytics.command(
    "opt-out", context_settings=dict(ignore_unknown_options=True)
)
def opt_out():
    """Opt-out to analytics"""
    GlobalConfig().analytics_opt_in = False
    cli_utils.declare("Opted in to analytics.")


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
    metadata_store_name: str, metadata_store_type: str, args: List[str]
):
    """Register a metadata store."""

    try:
        parsed_args = cli_utils.parse_unknown_options(args)
    except AssertionError as e:
        cli_utils.error(str(e))
        return

    repo: Repository = Repository()
    try:
        comp = metadata_store_factory.get_single_component(metadata_store_type)
    except AssertionError as e:
        cli_utils.error(str(e))
        return

    metadata_store = comp(**parsed_args)
    service = repo.get_service()
    service.register_metadata_store(metadata_store_name, metadata_store)


@metadata.command("list")
def list_metadata_stores():
    """List all available metadata stores from service."""
    service = Repository().get_service()
    cli_utils.title("Metadata Stores:")
    cli_utils.echo_component_list(service.metadata_stores)


@metadata.command("delete")
@click.argument("metadata_store_name", type=str)
def delete_metadata_store(metadata_store_name: str):
    """Delete a metadata store."""
    service = Repository().get_service()
    cli_utils.declare(f"Deleting metadata store: {metadata_store_name}")
    service.delete_metadata_store(metadata_store_name)
    cli_utils.declare("Deleted!")


# Artifact Store
@cli.group()
def artifact():
    """Utilities for artifact store"""


@artifact.command(
    "register", context_settings=dict(ignore_unknown_options=True)
)
@click.argument("artifact_store_name", type=str)
@click.argument("artifact_store_type", type=str)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def register_artifact_store(
    artifact_store_name: str, artifact_store_type: str, args: List[str]
):
    """Register an artifact store."""

    try:
        parsed_args = cli_utils.parse_unknown_options(args)
    except AssertionError as e:
        cli_utils.error(str(e))
        return

    repo: Repository = Repository()
    comp = artifact_store_factory.get_single_component(artifact_store_type)
    artifact_store = comp(**parsed_args)
    service = repo.get_service()
    service.register_artifact_store(artifact_store_name, artifact_store)


@artifact.command("list")
def list_artifact_stores():
    """List all available artifact stores from service."""
    service = Repository().get_service()
    cli_utils.title("Artifact Stores:")
    cli_utils.echo_component_list(service.artifact_stores)


@artifact.command("delete")
@click.argument("artifact_store_name", type=str)
def delete_artifact_store(artifact_store_name: str):
    """Delete a artifact store."""
    service = Repository().get_service()
    cli_utils.declare(f"Deleting artifact store: {artifact_store_name}")
    service.delete_artifact_store(artifact_store_name)
    cli_utils.declare("Deleted!")


# Orchestrator
@cli.group()
def orchestrator():
    """Utilities for orchestrator"""


@orchestrator.command(
    "register", context_settings=dict(ignore_unknown_options=True)
)
@click.argument("orchestrator_name", type=str)
@click.argument("orchestrator_type", type=str)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def register_orchestrator(
    orchestrator_name: str, orchestrator_type: str, args: List[str]
):
    """Register a orchestrator."""

    try:
        parsed_args = cli_utils.parse_unknown_options(args)
    except AssertionError as e:
        cli_utils.error(str(e))
        return

    repo: Repository = Repository()
    comp = orchestrator_store_factory.get_single_component(orchestrator_type)
    orchestrator = comp(**parsed_args)
    service = repo.get_service()
    service.register_orchestrator(orchestrator_name, orchestrator)


@orchestrator.command("list")
def list_orchestrators():
    """List all available orchestrators from service."""
    service = Repository().get_service()
    cli_utils.title("Orchestrators:")
    cli_utils.echo_component_list(service.orchestrators)


@orchestrator.command("delete")
@click.argument("orchestrator_name", type=str)
def delete_orchestrator(orchestrator_name: str):
    """Delete a orchestrator."""
    service = Repository().get_service()
    cli_utils.declare(f"Deleting orchestrator: {orchestrator_name}")
    service.delete_orchestrator(orchestrator_name)
    cli_utils.declare("Deleted!")
