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

from typing import Text

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import cli
from zenml.core.repo import Repository
from zenml.providers.base_provider import BaseProvider


# Providers
@cli.group()
def provider():
    """Providers to define various environments."""


@provider.command(
    "register", context_settings=dict(ignore_unknown_options=True)
)
@click.argument("provider_name", type=str)
@click.argument("metadata_store", type=str)
@click.argument("artifact_store", type=str)
@click.argument("orchestrator", type=str)
def register_provider(
    provider_name: Text,
    metadata_store: Text,
    artifact_store: Text,
    orchestrator: Text,
):
    """Register a provider."""

    service = Repository().get_service()
    provider = BaseProvider(
        artifact_store_name=artifact_store,
        orchestrator_name=orchestrator,
        metadata_store_name=metadata_store,
    )
    service.register_provider(provider_name, provider)


@provider.command("list")
def list_providers():
    """List all available providers from service."""
    service = Repository().get_service()
    cli_utils.title("Providers:")
    cli_utils.echo_component_list(service.providers)


@provider.command("delete")
@click.argument("provider_name", type=str)
def delete_provider(provider_name: Text):
    """Delete a provider."""
    service = Repository().get_service()
    cli_utils.declare(f"Deleting provider: {provider_name}")
    service.delete_provider(provider_name)
    cli_utils.declare("Deleted!")


@provider.command("set")
@click.argument("provider_name", type=str)
def set_active_provider(provider_name: Text):
    """Sets a provider active."""
    repo = Repository()
    repo.set_active_provider(provider_name)
    cli_utils.declare(f"Active provider: {provider_name}")


@provider.command("get")
def get_active_provider():
    """Gets the active provider."""
    repo = Repository()
    key = repo.get_active_provider_key()
    cli_utils.declare(f"Active provider: {key}")
