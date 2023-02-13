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
"""Functionality for model-deployer CLI subcommands."""

from typing import TYPE_CHECKING, Optional, cast

import click

from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import (
    declare,
    error,
    pretty_print_model_version_details,
    pretty_print_model_version_table,
    pretty_print_registered_model_table,
)
from zenml.enums import StackComponentType

if TYPE_CHECKING:
    from zenml.model_registries import BaseModelRegistry


def register_model_registry_subcommands() -> None:  # noqa: C901
    """Registers CLI subcommands for the Model Registry."""
    model_registry_group = cast(TagGroup, cli.commands.get("model-registry"))
    if not model_registry_group:
        return

    @model_registry_group.group(
        cls=TagGroup,
        help="Commands for interacting with registered models group of commands.",
    )
    @click.pass_context
    def models(ctx: click.Context) -> None:
        """List and manage models with the active model registry.

        Args:
            ctx: The click context.
        """
        from zenml.client import Client
        from zenml.stack.stack_component import StackComponent

        client = Client()
        model_registry_models = client.active_stack_model.components.get(
            StackComponentType.MODEL_REGISTRY
        )
        if model_registry_models is None:
            error(
                "No active model registry found. Please add a model_registry "
                "to your stack."
            )
            return
        ctx.obj = StackComponent.from_model(model_registry_models[0])

    @models.command(
        "list",
        help="Get a list of all registered models within the model registry.",
    )
    @click.option(
        "--tags",
        "-t",
        type=(str, str),
        default=None,
        help="Filter models by tags. can be used like: --tags key1 value1 key2 value",
        multiple=True,
    )
    @click.pass_obj
    def list_registered_models(
        model_registry: "BaseModelRegistry",
        tags: Optional[dict],
    ) -> None:
        """List of all registered models within the model registry.

        The list can be filtered by tags using the --tags flag.
        Example: zenm model-registry models listy-model --tags '{"key1":"value1","key2":"value2"}'

        Args:
            model_registry: The model registry stack component.
            tags: Filter models by tags.
        """
        # Set tags to None if empty
        tags = dict(tags) if tags else None
        # Get registered models
        registered_models = model_registry.list_models(tags=tags)
        # Print registered models if any
        if registered_models:
            pretty_print_registered_model_table(registered_models)
        else:
            declare("No models found.")

    @models.command(
        "register",
        help="Register a model with the active model registry.",
    )
    @click.option(
        "--name",
        "-n",
        type=str,
        default=None,
        help="Name of the model to register.",
        required=True,
    )
    @click.option(
        "--description",
        "-d",
        type=str,
        default=None,
        help="Description of the model to register.",
    )
    @click.option(
        "--tags",
        "-t",
        type=(str, str),
        default=None,
        help="Tags to add to the model. can be used like: --tags key1 value1 key2 value",
        multiple=True,
    )
    @click.pass_obj
    def register_model(
        model_registry: "BaseModelRegistry",
        name: str,
        description: Optional[str],
        tags: Optional[dict],
    ) -> None:
        """Register a model with the active model registry.

        Args:
            model_registry: The model registry stack component.
            name: Name of the model to register.
            description: Description of the model to register.
            tags: Tags to add to the model.
        """
        # Set tags to None if empty
        tags = dict(tags) if tags else None
        # Check if model already exists in registry
        if model_registry.check_model_exists(name):
            error(f"Model with name {name} already exists.")
            return
        # Register model
        model_registry.register_model(
            name=name,
            description=description,
            tags=tags,
        )
        # Declare success
        declare(f"Model {name} registered successfully.")

    @models.command(
        "delete",
        help="Delete a model from the active model registry.",
    )
    @click.option(
        "--name",
        "-n",
        type=str,
        default=None,
        help="Name of the model to delete.",
        required=True,
    )
    @click.pass_obj
    def delete_model(
        model_registry: "BaseModelRegistry",
        name: str,
    ) -> None:
        """Delete a model from the active model registry.

        Args:
            model_registry: The model registry stack component.
            name: Name of the model to delete.
        """
        # Check if model exists in registry
        if not model_registry.check_model_exists(name):
            error(f"Model with name {name} does not exist.")
            return
        # Delete model
        model_registry.delete_model(name)
        # Declare success
        declare(f"Model {name} deleted successfully.")

    @models.command(
        "update",
        help="Update a model in the active model registry.",
    )
    @click.option(
        "--name",
        "-n",
        type=str,
        default=None,
        help="Name of the model to update.",
        required=True,
    )
    @click.option(
        "--description",
        "-d",
        type=str,
        default=None,
        help="Description of the model to update.",
    )
    @click.option(
        "--tags",
        "-t",
        type=(str, str),
        default=None,
        help="Tags to add to the model. can be used like: --tags key1 value1 key2 value",
        multiple=True,
    )
    @click.pass_obj
    def update_model(
        model_registry: "BaseModelRegistry",
        name: str,
        description: Optional[str],
        tags: Optional[dict],
    ) -> None:
        """Update a model in the active model registry.

        Args:
            model_registry: The model registry stack component.
            name: Name of the model to update.
            description: Description of the model to update.
            tags: Tags to add to the model.
        """
        # Set tags to None if empty
        tags = dict(tags) if tags else None
        # Check if model exists in registry
        if not model_registry.check_model_exists(name):
            error(f"Model with name {name} does not exist.")
            return
        # Update model
        model_registry.update_model(
            name=name,
            description=description,
            tags=tags,
        )
        # Declare success
        declare(f"Model {name} updated successfully.")

    @models.command(
        "get",
        help="Get a model from the active model registry.",
    )
    @click.option(
        "--name",
        "-n",
        type=str,
        default=None,
        help="Name of the model to get.",
        required=True,
    )
    @click.pass_obj
    def get_model(
        model_registry: "BaseModelRegistry",
        name: str,
    ) -> None:
        """Get a model from the active model registry.

        Args:
            model_registry: The model registry stack component.
            name: Name of the model to get.
        """
        # Check if model exists in registry
        if not model_registry.check_model_exists(name):
            error(f"Model with name {name} does not exist.")
            return
        # Get model
        model = model_registry.get_model(name)
        # Print model
        pretty_print_registered_model_table([model])

    @models.command(
        "get-version",
        help="Get a model version from the active model registry.",
    )
    @click.option(
        "--name",
        "-n",
        type=str,
        default=None,
        help="Name of the model to get.",
        required=True,
    )
    @click.option(
        "--version",
        "-v",
        type=str,
        default=None,
        help="Version of the model to get.",
        required=True,
    )
    @click.pass_obj
    def get_model_version(
        model_registry: "BaseModelRegistry",
        name: str,
        version: int,
    ) -> None:
        """Get a model version from the active model registry.

        Args:
            model_registry: The model registry stack component.
            name: Name of the model to get.
            version: Version of the model to get.
        """
        # Check if model exists in registry
        if not model_registry.check_model_version_exists(name, version):
            error(
                f"Model with name {name} and version {version} does not exist."
            )
            return
        # Get model version
        model_version = model_registry.get_model_version(name, version)
        # Print model version
        pretty_print_model_version_details(model_version)

    @models.command(
        "delete-version",
        help="Delete a model version from the active model registry.",
    )
    @click.option(
        "--name",
        "-n",
        type=str,
        default=None,
        help="Name of the model to delete.",
        required=True,
    )
    @click.option(
        "--version",
        "-v",
        type=str,
        default=None,
        help="Version of the model to delete.",
        required=True,
    )
    @click.pass_obj
    def delete_model_version(
        model_registry: "BaseModelRegistry",
        name: str,
        version: int,
    ) -> None:
        """Delete a model version from the active model registry.

        Args:
            model_registry: The model registry stack component.
            name: Name of the model to delete.
            version: Version of the model to delete.
        """
        # Check if model exists in registry
        if not model_registry.check_model_version_exists(name, version):
            error(
                f"Model with name {name} and version {version} does not exist."
            )
            return
        # Delete model version
        model_registry.delete_model_version(name, version)
        # Declare success
        declare(f"Model {name} version {version} deleted successfully.")

    @models.command(
        "update-version",
        help="Update a model version in the active model registry.",
    )
    @click.option(
        "--name",
        "-n",
        type=str,
        default=None,
        help="Name of the model to update.",
        required=True,
    )
    @click.option(
        "--version",
        "-v",
        type=str,
        default=None,
        help="Version of the model to update.",
        required=True,
    )
    @click.option(
        "--description",
        "-d",
        type=str,
        default=None,
        help="Description of the model to update.",
    )
    @click.option(
        "--tags",
        "-t",
        type=(str, str),
        default=None,
        help="Tags to add to the model. can be used like: --tags key1 value1 key2 value",
        multiple=True,
    )
    @click.option(
        "--stage",
        "-s",
        type=str,
        default=None,
        help="Stage of the model to update.",
    )
    @click.pass_obj
    def update_model_version(
        model_registry: "BaseModelRegistry",
        name: str,
        version: int,
        description: Optional[str],
        tags: Optional[dict],
        stage: Optional[str],
    ) -> None:
        """Update a model version in the active model registry.

        Args:
            model_registry: The model registry stack component.
            name: Name of the model to update.
            version: Version of the model to update.
            description: Description of the model to update.
            tags: Tags to add to the model.
            stage: Stage of the model to update.
        """
        # Set tags to None if empty
        tags = dict(tags) if tags else None
        # Check if model exists in registry
        if not model_registry.check_model_version_exists(name, version):
            error(
                f"Model with name {name} and version {version} does not exist."
            )
            return
        # Update model version
        updated_version = model_registry.update_model_version(
            name=name,
            version=version,
            description=description,
            tags=tags,
            stage=stage,
        )
        # Declare success
        declare(f"Model {name} version {version} updated successfully.")
        # Print model version
        pretty_print_model_version_details(updated_version)

    @models.command(
        "list-versions",
        help="List all model versions in the active model registry.",
    )
    @click.option(
        "--name",
        "-n",
        type=str,
        default=None,
        help="Name of the model to list versions for.",
        required=True,
    )
    @click.option(
        "--model-uri",
        "-m",
        type=str,
        default=None,
        help="Model URI of the model to list versions for.",
    )
    @click.option(
        "--tags",
        "-t",
        type=(str, str),
        default=None,
        help="Tags to filter the model versions by. can be used like: --tags key1 value1 key2 value",
        multiple=True,
    )
    @click.pass_obj
    def list_model_versions(
        model_registry: "BaseModelRegistry",
        name: str,
        model_uri: Optional[str],
        tags: Optional[dict],
    ) -> None:
        """List all model versions in the active model registry.

        Args:
            model_registry: The model registry stack component.
            name: Name of the model to list versions for.
            model_uri: Model URI of the model to list versions for.
            tags: Tags to filter the model versions by.
        """
        # Set tags to None if empty
        tags = dict(tags) if tags else None
        # Get model versions
        model_versions = model_registry.list_model_versions(
            name=name,
            model_source_uri=model_uri,
            tags=tags,
        )
        # Print model versions
        pretty_print_model_version_table(model_versions)

    @models.command(
        "register-version",
        help="Register a model version in the active model registry.",
    )
    @click.option(
        "--name",
        "-n",
        type=str,
        default=None,
        help="Name of the model to register.",
        required=True,
    )
    @click.option(
        "--registered-model-description",
        "-rmd",
        type=str,
        default=None,
        help="Description of the registered model to register.",
    )
    @click.option(
        "--registered-model-tags",
        "-rmt",
        type=(str, str),
        default=None,
        help="Tags to add to the registered model. can be used like: --tags key1 value1 key2 value",
        multiple=True,
    )
    @click.option(
        "--version",
        "-v",
        type=str,
        default=None,
        help="Version of the model to register.",
    )
    @click.option(
        "--model-uri",
        "-m",
        type=str,
        default=None,
        help="Model URI of the model to register.",
        required=True,
    )
    @click.option(
        "--description",
        "-d",
        type=str,
        default=None,
        help="Description of the model to register.",
    )
    @click.option(
        "--tags",
        "-t",
        type=(str, str),
        default=None,
        help="Tags to add to the model. can be used like: --tags key1 value1 key2 value",
        multiple=True,
    )
    @click.option(
        "--registry-metadata",
        "-r",
        type=(str, str),
        default=None,
        help="Registry metadata to add to the model. can be used like: --registry-metadata key1 value1 key2 value",
        multiple=True,
    )
    @click.option(
        "--zenml-version",
        "-z",
        type=str,
        default=None,
        help="ZenML version of the model to register.",
    )
    @click.option(
        "--zenml-pipeline-run-id",
        "-pi",
        type=str,
        default=None,
        help="ZenML pipeline run ID of the model to register.",
    )
    @click.option(
        "zenml-pipeline-run-name",
        "-pn",
        type=str,
        default=None,
        help="ZenML pipeline run name of the model to register.",
    )
    @click.option(
        "zenml-step-name",
        "-sn",
        type=str,
        default=None,
        help="ZenML step name of the model to register.",
    )
    @click.pass_obj
    def register_model_version(
        model_registry: "BaseModelRegistry",
        name: str,
        version: Optional[str],
        model_uri: str,
        description: Optional[str],
        tags: Optional[dict],
        registry_metadata: Optional[dict],
        zenml_version: Optional[str],
        zenml_pipeline_run_id: Optional[str],
        zenml_pipeline_name: Optional[str],
        zenml_step_name: Optional[str],
    ) -> None:
        """Register a model version in the active model registry.

        Args:
            model_registry: The model registry stack component.
            name: Name of the model to register.
            version: Version of the model to register.
            model_uri: Model URI of the model to register.
            description: Description of the model to register.
            tags: Tags to add to the model.
            registry_metadata: Registry metadata to add to the model.
            zenml_version: ZenML version of the model to register.
            zenml_pipeline_run_id: ZenML pipeline run ID of the model to register.
            zenml_pipeline_name: ZenML pipeline run name of the model to register.
            zenml_step_name: ZenML step name of the model to register.
        """
        # Set tags to None if empty
        tags = dict(tags) if tags else None
        registry_metadata = (
            dict(registry_metadata) if registry_metadata else None
        )
        # Register model version
        model_version = model_registry.register_model_version(
            name=name,
            version=version,
            model_source_uri=model_uri,
            description=description,
            tags=tags,
            registry_metadata=registry_metadata,
            zenml_version=zenml_version,
            zenml_pipeline_run_id=zenml_pipeline_run_id,
            zenml_pipeline_name=zenml_pipeline_name,
            zenml_step_name=zenml_step_name,
        )
        # Declare success
        declare(f"Model {name} version {version} registered successfully.")
        # Print model version
        pretty_print_model_version_details(model_version)
