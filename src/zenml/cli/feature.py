#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Functionality to generate stack component CLI commands."""

from typing import TYPE_CHECKING, cast

import click

from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import declare, error
from zenml.enums import StackComponentType

if TYPE_CHECKING:
    from zenml.feature_stores.base_feature_store import BaseFeatureStore


def register_feature_store_subcommands() -> None:
    """Registers CLI subcommands for the Feature Store."""
    feature_store_group = cast(TagGroup, cli.commands.get("feature-store"))
    if not feature_store_group:
        return

    @feature_store_group.group(
        cls=TagGroup,
        help="Commands for interacting with your features.",
    )
    @click.pass_context
    def feature(ctx: click.Context) -> None:
        """Features as obtained from a feature store.

        Args:
            ctx: The click context.
        """
        from zenml.client import Client
        from zenml.stack.stack_component import StackComponent

        client = Client()
        feature_store_models = client.active_stack_model.components[
            StackComponentType.FEATURE_STORE
        ]
        if feature_store_models is None:
            error(
                "No active feature store found. Please create a feature store "
                "first and add it to your stack."
            )
            return
        ctx.obj = StackComponent.from_model(feature_store_models[0])

    @feature.command("get-data-sources")
    @click.pass_obj
    def get_data_sources(feature_store: "BaseFeatureStore") -> None:
        """Get all data sources from the feature store.

        Args:
            feature_store: The feature store.
        """
        data_sources = feature_store.get_data_sources()  # type: ignore[attr-defined]
        declare(f"Data sources: {data_sources}")

    @feature.command("get-entities")
    @click.pass_obj
    def get_entities(feature_store: "BaseFeatureStore") -> None:
        """Get all entities from the feature store.

        Args:
            feature_store: The feature store.
        """
        entities = feature_store.get_entities()  # type: ignore[attr-defined]
        declare(f"Entities: {entities}")

    @feature.command("get-feature-services")
    @click.pass_obj
    def get_feature_services(feature_store: "BaseFeatureStore") -> None:
        """Get all feature services from the feature store.

        Args:
            feature_store: The feature store.
        """
        feature_services = feature_store.get_feature_services()  # type: ignore[attr-defined]
        declare(f"Feature services: {feature_services}")

    @feature.command("get-feature-views")
    @click.pass_obj
    def get_feature_views(feature_store: "BaseFeatureStore") -> None:
        """Get all feature views from the feature store.

        Args:
            feature_store: The feature store.
        """
        feature_views = feature_store.get_feature_views()  # type: ignore[attr-defined]
        declare(f"Feature views: {feature_views}")

    @feature.command("get-project")
    @click.pass_obj
    def get_project(feature_store: "BaseFeatureStore") -> None:
        """Get the current project name from the feature store.

        Args:
            feature_store: The feature store.
        """
        project = feature_store.get_project()  # type: ignore[attr-defined]
        declare(f"Project name: {project}")

    @feature.command("get-feast-version")
    @click.pass_obj
    def get_feast_version(feature_store: "BaseFeatureStore") -> None:
        """Get the current Feast version being used.

        Args:
            feature_store: The feature store.
        """
        version = feature_store.get_feast_version()  # type: ignore[attr-defined]
        declare(f"Feast version: {version}")
