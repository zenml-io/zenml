# type: ignore
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

# TODO [ENG-795]: Generalize these commands to all feature stores.

from typing import TYPE_CHECKING

import click

from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import declare, error
from zenml.enums import StackComponentType
from zenml.repository import Repository

if TYPE_CHECKING:
    from zenml.feature_stores.base_feature_store import BaseFeatureStore


# Features
@cli.group(cls=TagGroup)
@click.pass_context
def feature(ctx: click.Context) -> None:
    """Features as obtained from a feature store."""
    repo = Repository()
    active_stack = repo.zen_store.get_stack(name=repo.active_stack_name)
    feature_store_wrapper = active_stack.get_component_wrapper(
        StackComponentType.FEATURE_STORE
    )
    if feature_store_wrapper is None:
        error(
            "No active feature store found. Please create a feature store "
            "first and add it to your stack."
        )
        return
    ctx.obj = feature_store_wrapper.to_component()


@feature.command("get-data-sources")
@click.pass_obj
def get_data_sources(feature_store: "BaseFeatureStore") -> None:
    """Get all data sources from the feature store."""
    data_sources = feature_store.get_data_sources()
    declare(f"Data sources: {data_sources}")


@feature.command("get-entities")
@click.pass_obj
def get_entities(feature_store: "BaseFeatureStore") -> None:
    """Get all entities from the feature store."""
    entities = feature_store.get_entities()
    declare(f"Entities: {entities}")


@feature.command("get-feature-services")
@click.pass_obj
def get_feature_services(feature_store: "BaseFeatureStore") -> None:
    """Get all feature services from the feature store."""
    feature_services = feature_store.get_feature_services()
    declare(f"Feature services: {feature_services}")


@feature.command("get-feature-views")
@click.pass_obj
def get_feature_views(feature_store: "BaseFeatureStore") -> None:
    """Get all feature views from the feature store."""
    feature_views = feature_store.get_feature_views()
    declare(f"Feature views: {feature_views}")


@feature.command("get-project")
@click.pass_obj
def get_project(feature_store: "BaseFeatureStore") -> None:
    """Get the current project name from the feature store."""
    project = feature_store.get_project()
    declare(f"Project name: {project}")


@feature.command("get-feast-version")
@click.pass_obj
def get_feast_version(feature_store: "BaseFeatureStore") -> None:
    """Get the current Feast version being used."""
    version = feature_store.get_feast_version()
    declare(f"Feast version: {version}")
