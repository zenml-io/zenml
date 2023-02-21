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

from typing import TYPE_CHECKING, Dict, Optional, cast

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.enums import StackComponentType
from zenml.model_registries.base_model_registry import (
    ModelRegistryModelMetadata,
    ModelVersionStage,
)

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
            cli_utils.error(
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
        tags: Optional[Dict[str, str]],
    ) -> None:
        """List of all registered models within the model registry.

        The list can be filtered by tags using the --tags flag.
        Example: zenml model-registry models list-versions --tags key1 value1 key2 value2

        Args:
            model_registry: The model registry stack component.
            tags: Filter models by tags.
        """
        tags = dict(tags) if tags else None
        registered_models = model_registry.list_models(tags=tags)
        # Print registered models if any
        if registered_models:
            cli_utils.pretty_print_registered_model_table(registered_models)
        else:
            cli_utils.declare("No models found.")

    @models.command(
        "register",
        help="Register a model with the active model registry.",
    )
    @click.argument(
        "name",
        type=click.STRING,
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
        tags: Optional[Dict[str, str]],
    ) -> None:
        """Register a model with the active model registry.

        Args:
            model_registry: The model registry stack component.
            name: Name of the model to register.
            description: Description of the model to register.
            tags: Tags to add to the model.
        """
        tags = dict(tags) if tags else None
        if model_registry.check_model_exists(name):
            cli_utils.error(f"Model with name {name} already exists.")
            return
        model_registry.register_model(
            name=name,
            description=description,
            tags=tags,
        )
        cli_utils.declare(f"Model {name} registered successfully.")

    @models.command(
        "delete",
        help="Delete a model from the active model registry.",
    )
    @click.argument(
        "name",
        type=click.STRING,
        required=True,
    )
    @click.option(
        "--yes",
        "-y",
        is_flag=True,
        help="Don't ask for confirmation.",
    )
    @click.pass_obj
    def delete_model(
        model_registry: "BaseModelRegistry",
        name: str,
        yes: bool = False,
    ) -> None:
        """Delete a model from the active model registry.

        Args:
            model_registry: The model registry stack component.
            name: Name of the model to delete.
            yes: If set, don't ask for confirmation.
        """
        if not model_registry.check_model_exists(name):
            cli_utils.error(f"Model with name {name} does not exist.")
            return

        if not yes:
            confirmation = cli_utils.confirmation(
                f"Found Model with name {name}. Do you want to "
                f"delete them?"
            )
            if not confirmation:
                cli_utils.declare("Model deletion canceled.")
                return
        model_registry.delete_model(name)
        cli_utils.declare(f"Model {name} deleted successfully.")

    @models.command(
        "update",
        help="Update a model in the active model registry.",
    )
    @click.argument(
        "name",
        type=click.STRING,
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
        tags: Optional[Dict[str, str]],
    ) -> None:
        """Update a model in the active model registry.

        Args:
            model_registry: The model registry stack component.
            name: Name of the model to update.
            description: Description of the model to update.
            tags: Tags to add to the model.
        """
        tags = dict(tags) if tags else None
        if not model_registry.check_model_exists(name):
            cli_utils.error(f"Model with name {name} does not exist.")
            return
        model_registry.update_model(
            name=name,
            description=description,
            tags=tags,
        )
        cli_utils.declare(f"Model {name} updated successfully.")

    @models.command(
        "get",
        help="Get a model from the active model registry.",
    )
    @click.argument(
        "name",
        type=click.STRING,
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
        if not model_registry.check_model_exists(name):
            cli_utils.error(f"Model with name {name} does not exist.")
            return
        model = model_registry.get_model(name)
        cli_utils.pretty_print_registered_model_table([model])

    @models.command(
        "get-version",
        help="Get a model version from the active model registry.",
    )
    @click.argument(
        "name",
        type=click.STRING,
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
        version: str,
    ) -> None:
        """Get a model version from the active model registry.

        Args:
            model_registry: The model registry stack component.
            name: Name of the model to get.
            version: Version of the model to get.
        """
        if not model_registry.check_model_version_exists(name, version):
            cli_utils.error(
                f"Model with name {name} and version {version} does not exist."
            )
            return
        model_version = model_registry.get_model_version(name, version)
        cli_utils.pretty_print_model_version_details(model_version)

    @models.command(
        "delete-version",
        help="Delete a model version from the active model registry.",
    )
    @click.argument(
        "name",
        type=click.STRING,
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
    @click.option(
        "--yes",
        "-y",
        is_flag=True,
        help="Don't ask for confirmation.",
    )
    @click.pass_obj
    def delete_model_version(
        model_registry: "BaseModelRegistry",
        name: str,
        version: str,
        yes: bool = False,
    ) -> None:
        """Delete a model version from the active model registry.

        Args:
            model_registry: The model registry stack component.
            name: Name of the model to delete.
            version: Version of the model to delete.
            yes: If set, don't ask for confirmation.
        """
        if not model_registry.check_model_version_exists(name, version):
            cli_utils.error(
                f"Model with name {name} and version {version} does not exist."
            )
            return
        if not yes:
            confirmation = cli_utils.confirmation(
                f"Found Model with the name `{name}` and the version `{version}`."
                f"Do you want to delete it?"
            )
            if not confirmation:
                cli_utils.declare("Model Version deletion canceled.")
                return
        model_registry.delete_model_version(name, version)
        cli_utils.declare(
            f"Model {name} version {version} deleted successfully."
        )

    @models.command(
        "update-version",
        help="Update a model version in the active model registry.",
    )
    @click.argument(
        "name",
        type=click.STRING,
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
        type=click.Choice(["None", "Staging", "Production", "Archived"]),
        default=None,
        help="Stage of the model to update.",
    )
    @click.pass_obj
    def update_model_version(
        model_registry: "BaseModelRegistry",
        name: str,
        version: str,
        description: Optional[str],
        tags: Optional[Dict[str, str]],
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
        tags = dict(tags) if tags else None
        if not model_registry.check_model_version_exists(name, version):
            cli_utils.error(
                f"Model with name {name} and version {version} does not exist."
            )
            return
        updated_version = model_registry.update_model_version(
            name=name,
            version=version,
            description=description,
            tags=tags,
            stage=ModelVersionStage(stage),
        )
        cli_utils.declare(
            f"Model {name} version {version} updated successfully."
        )
        cli_utils.pretty_print_model_version_details(updated_version)

    @models.command(
        "list-versions",
        help="List all model versions in the active model registry.",
    )
    @click.argument(
        "name",
        type=click.STRING,
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
        tags: Optional[Dict[str, str]],
    ) -> None:
        """List all model versions in the active model registry.

        Args:
            model_registry: The model registry stack component.
            name: Name of the model to list versions for.
            model_uri: Model URI of the model to list versions for.
            tags: Tags to filter the model versions by.
        """
        tags = dict(tags) if tags else None
        model_versions = model_registry.list_model_versions(
            name=name,
            model_source_uri=model_uri,
            tags=tags,
        )
        cli_utils.pretty_print_model_version_table(model_versions)

    @models.command(
        "register-version",
        help="Register a model version in the active model registry.",
    )
    @click.argument(
        "name",
        type=click.STRING,
        required=True,
    )
    @click.option(
        "--description",
        "-d",
        type=str,
        default=None,
        help="Description of the registered model to register.",
    )
    @click.option(
        "--tags",
        "-t",
        type=(str, str),
        default=None,
        help="Tags to add to the registered model. can be used like: --tags key1 value1 key2 value",
        multiple=True,
    )
    @click.option(
        "--version",
        "-v",
        type=str,
        required=True,
        default=None,
        help="Version of the model to register.",
    )
    @click.option(
        "--model-uri",
        "-u",
        type=str,
        default=None,
        help="Model URI of the model to register.",
        required=True,
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
        type=str,
        default=None,
        help="ZenML version of the model to register.",
    )
    @click.option(
        "--zenml-pipeline-run-id",
        type=str,
        default=None,
        help="ZenML pipeline run ID of the model to register.",
    )
    @click.option(
        "--zenml-pipeline-name",
        type=str,
        default=None,
        help="ZenML pipeline name of the model to register.",
    )
    @click.option(
        "--zenml-step-name",
        type=str,
        default=None,
        help="ZenML step name of the model to register.",
    )
    @click.pass_obj
    def register_model_version(
        model_registry: "BaseModelRegistry",
        name: str,
        version: str,
        model_uri: str,
        description: Optional[str],
        tags: Optional[Dict[str, str]],
        metadata: Optional[Dict[str, str]],
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
            metadata: Registry metadata to add to the model.
            zenml_version: ZenML version of the model to register.
            zenml_pipeline_run_id: ZenML pipeline run ID of the model to register.
            zenml_pipeline_name: ZenML pipeline name of the model to register.
            zenml_step_name: ZenML step name of the model to register.
        """
        tags = dict(tags) if tags else None
        # Parse metadata``
        metadata = dict(metadata) if metadata else {}
        registerted_metadata = ModelRegistryModelMetadata(**dict(metadata))
        registerted_metadata.zenml_version = zenml_version
        registerted_metadata.zenml_pipeline_run_id = zenml_pipeline_run_id
        registerted_metadata.zenml_pipeline_name = zenml_pipeline_name
        registerted_metadata.zenml_step_name = zenml_step_name
        model_version = model_registry.register_model_version(
            name=name,
            version=version,
            model_source_uri=model_uri,
            description=description,
            tags=tags,
            metadata=registerted_metadata,
        )
        cli_utils.declare(
            f"Model {name} version {version} registered successfully."
        )
        cli_utils.pretty_print_model_version_details(model_version)
