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
"""Functionality for model deployer CLI subcommands."""

from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional, cast

import click

from zenml import __version__
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
        "--metadata",
        "-m",
        type=(str, str),
        default=None,
        help="Filter models by metadata. can be used like: -m key1 value1 -m key2 value",
        multiple=True,
    )
    @click.pass_obj
    def list_registered_models(
        model_registry: "BaseModelRegistry",
        metadata: Optional[Dict[str, str]],
    ) -> None:
        """List of all registered models within the model registry.

        The list can be filtered by metadata (tags) using the --metadata flag.
        Example: zenml model-registry models list-versions -m key1 value1 -m key2 value2

        Args:
            model_registry: The model registry stack component.
            metadata: Filter models by Metadata (Tags).
        """
        metadata = dict(metadata) if metadata else None
        registered_models = model_registry.list_models(metadata=metadata)
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
        "--metadata",
        "-t",
        type=(str, str),
        default=None,
        help="Metadata or Tags to add to the model. can be used like: -m key1 value1 -m key2 value",
        multiple=True,
    )
    @click.pass_obj
    def register_model(
        model_registry: "BaseModelRegistry",
        name: str,
        description: Optional[str],
        metadata: Optional[Dict[str, str]],
    ) -> None:
        """Register a model with the active model registry.

        Args:
            model_registry: The model registry stack component.
            name: Name of the model to register.
            description: Description of the model to register.
            metadata: Metadata or Tags to add to the registered model.
        """
        try:
            model_registry.get_model(name)
            cli_utils.error(f"Model with name {name} already exists.")
        except KeyError:
            pass
        metadata = dict(metadata) if metadata else None
        model_registry.register_model(
            name=name,
            description=description,
            metadata=metadata,
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
        try:
            model_registry.get_model(name)
        except KeyError:
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
        "--metadata",
        "-t",
        type=(str, str),
        default=None,
        help="Metadata or Tags to add to the model. Can be used like: -m key1 value1 -m key2 value",
        multiple=True,
    )
    @click.pass_obj
    def update_model(
        model_registry: "BaseModelRegistry",
        name: str,
        description: Optional[str],
        metadata: Optional[Dict[str, str]],
    ) -> None:
        """Update a model in the active model registry.

        Args:
            model_registry: The model registry stack component.
            name: Name of the model to update.
            description: Description of the model to update.
            metadata: Metadata or Tags to add to the model.
        """
        try:
            model_registry.get_model(name)
        except KeyError:
            cli_utils.error(f"Model with name {name} does not exist.")
            return
        metadata = dict(metadata) if metadata else None
        model_registry.update_model(
            name=name,
            description=description,
            metadata=metadata,
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
        try:
            model = model_registry.get_model(name)
        except KeyError:
            cli_utils.error(f"Model with name {name} does not exist.")
            return
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
        try:
            model_version = model_registry.get_model_version(name, version)
        except KeyError:
            cli_utils.error(
                f"Model with name {name} and version {version} does not exist."
            )
            return
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
        try:
            model_registry.get_model_version(name, version)
        except KeyError:
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
                cli_utils.declare("Model version deletion canceled.")
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
        "--metadata",
        "-m",
        type=(str, str),
        default=None,
        help="Metadata or Tags to add to the model. can be used like: --m key1 value1 -m key2 value",
        multiple=True,
    )
    @click.option(
        "--stage",
        "-s",
        type=click.Choice(["None", "Staging", "Production", "Archived"]),
        default=None,
        help="Stage of the model to update.",
    )
    @click.option(
        "--remove_metadata",
        "-rm",
        default=None,
        help="Metadata or Tags to remove from the model. Can be used like: -rm key1 -rm key2",
        multiple=True,
    )
    @click.pass_obj
    def update_model_version(
        model_registry: "BaseModelRegistry",
        name: str,
        version: str,
        description: Optional[str],
        metadata: Optional[Dict[str, str]],
        stage: Optional[str],
        remove_metadata: Optional[List[str]],
    ) -> None:
        """Update a model version in the active model registry.

        Args:
            model_registry: The model registry stack component.
            name: Name of the model to update.
            version: Version of the model to update.
            description: Description of the model to update.
            metadata: Metadata to add to the model version.
            stage: Stage of the model to update.
            remove_metadata: Metadata to remove from the model version.
        """
        try:
            model_registry.get_model_version(name, version)
        except KeyError:
            cli_utils.error(
                f"Model with name {name} and version {version} does not exist."
            )
            return
        metadata = dict(metadata) if metadata else {}
        remove_metadata = list(remove_metadata) if remove_metadata else []
        updated_version = model_registry.update_model_version(
            name=name,
            version=version,
            description=description,
            metadata=ModelRegistryModelMetadata(**metadata),
            stage=ModelVersionStage(stage) if stage else None,
            remove_metadata=remove_metadata,
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
        "--metadata",
        "-m",
        type=(str, str),
        default=None,
        help="Metadata or Tags to filter the model versions by. Can be used like: -m key1 value1 -m key2 value",
        multiple=True,
    )
    @click.option(
        "--count",
        "-c",
        type=int,
        help="Number of model versions to list.",
    )
    @click.option(
        "--order-by-date",
        type=click.Choice(["asc", "desc"]),
        default="desc",
        help="Order by date.",
    )
    @click.option(
        "--created-after",
        type=click.DateTime(formats=["%Y-%m-%d"]),
        default=None,
        help="List model versions created after this date.",
    )
    @click.option(
        "--created-before",
        type=click.DateTime(formats=["%Y-%m-%d"]),
        default=None,
        help="List model versions created before this date.",
    )
    @click.pass_obj
    def list_model_versions(
        model_registry: "BaseModelRegistry",
        name: str,
        model_uri: Optional[str],
        count: Optional[int],
        metadata: Optional[Dict[str, str]],
        order_by_date: str,
        created_after: Optional[datetime],
        created_before: Optional[datetime],
    ) -> None:
        """List all model versions in the active model registry.

        Args:
            model_registry: The model registry stack component.
            name: Name of the model to list versions for.
            model_uri: Model URI of the model to list versions for.
            metadata: Metadata or Tags to filter the model versions by.
            count: Number of model versions to list.
            order_by_date: Order by date.
            created_after: List model versions created after this date.
            created_before: List model versions created before this date.
        """
        metadata = dict(metadata) if metadata else {}
        model_versions = model_registry.list_model_versions(
            name=name,
            model_source_uri=model_uri,
            metadata=ModelRegistryModelMetadata(**metadata),
            count=count,
            order_by_date=order_by_date,
            created_after=created_after,
            created_before=created_before,
        )
        if not model_versions:
            cli_utils.declare("No model versions found.")
            return
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
        help="Description of the model version.",
    )
    @click.option(
        "--metadata",
        "-m",
        type=(str, str),
        default=None,
        help="Metadata or Tags to add to the model version. Can be used like: -m key1 value1 -m key2 value",
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
        "--zenml-version",
        type=str,
        default=None,
        help="ZenML version of the model to register.",
    )
    @click.option(
        "--zenml-run-name",
        type=str,
        default=None,
        help="ZenML run name of the model to register.",
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
        metadata: Optional[Dict[str, str]],
        zenml_version: Optional[str],
        zenml_run_name: Optional[str],
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
            metadata: Model version metadata.
            zenml_version: ZenML version of the model to register.
            zenml_run_name: ZenML pipeline run name of the model to register.
            zenml_pipeline_name: ZenML pipeline name of the model to register.
            zenml_step_name: ZenML step name of the model to register.
        """
        # Parse metadata
        metadata = dict(metadata) if metadata else {}
        registered_metadata = ModelRegistryModelMetadata(**dict(metadata))
        registered_metadata.zenml_version = zenml_version or __version__
        registered_metadata.zenml_run_name = zenml_run_name
        registered_metadata.zenml_pipeline_name = zenml_pipeline_name
        registered_metadata.zenml_step_name = zenml_step_name
        model_version = model_registry.register_model_version(
            name=name,
            version=version,
            model_source_uri=model_uri,
            description=description,
            metadata=registered_metadata,
        )
        cli_utils.declare(
            f"Model {name} version {version} registered successfully."
        )
        cli_utils.pretty_print_model_version_details(model_version)
