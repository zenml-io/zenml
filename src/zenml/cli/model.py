#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""CLI functionality to interact with Model Control Plane."""

from typing import Any, Dict, List, Optional

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import (
    list_options,
)
from zenml.client import Client
from zenml.console import console
from zenml.enums import CliCategories, ModelStages
from zenml.exceptions import EntityExistsError
from zenml.logger import get_logger
from zenml.models import (
    ModelFilter,
    ModelResponse,
    ModelVersionArtifactFilter,
    ModelVersionArtifactResponse,
    ModelVersionFilter,
    ModelVersionPipelineRunFilter,
    ModelVersionPipelineRunResponse,
    ModelVersionResponse,
)
from zenml.utils.dict_utils import remove_none_values

logger = get_logger(__name__)


def _generate_model_data(model: ModelResponse) -> Dict[str, Any]:
    """Generate additional data for model display.

    Args:
        model: The model response.

    Returns:
        The additional data for the model.
    """
    return {
        "latest_version_name": model.latest_version_name,
        "latest_version_id": model.latest_version_id,
    }


def _generate_model_version_data(
    model_version: ModelVersionResponse, output_format: str
) -> Dict[str, Any]:
    """Generate additional data for model version display.

    Args:
        model_version: The model version response.
        output_format: The output format.

    Returns:
        The additional data for the model version.
    """
    # Get stage value for formatting
    stage_value = (
        str(model_version.stage).lower() if model_version.stage else ""
    )
    model_name = model_version.model.name
    version_name = model_version.name
    stage_display = str(model_version.stage) if model_version.stage else ""

    # Apply stage-based formatting only for table output
    if output_format == "table":
        if stage_value == "production":
            # Format with green dot at beginning, green model name and version
            formatted_model = (
                f"[green]●[/green] [bold green]{model_name}[/bold green]"
            )
            formatted_version = f"[bold green]{version_name}[/bold green]"
            formatted_stage = f"[bold green]{stage_display}[/bold green]"
        elif stage_value == "staging":
            # Format with orange dot at beginning, orange name and version
            formatted_model = f"[bright_yellow]●[/bright_yellow] [bright_yellow]{model_name}[/bright_yellow]"
            formatted_version = (
                f"[bright_yellow]{version_name}[/bright_yellow]"
            )
            formatted_stage = f"[bright_yellow]{stage_display}[/bright_yellow]"
        else:
            # For other stages (development, archived, etc.), keep default format
            formatted_model = model_name
            formatted_version = version_name
            formatted_stage = stage_display
    else:
        # For non-table formats, use plain text
        formatted_model = model_name
        formatted_version = version_name
        formatted_stage = stage_display

    return {
        "model": formatted_model,
        "version": formatted_version,
        "stage": formatted_stage,
        "tags": ", ".join(tag.name for tag in model_version.tags)
        if model_version.tags
        else "",
        "updated": model_version.updated,
    }


def _generate_model_version_artifact_data(
    model_version_artifact: ModelVersionArtifactResponse,
) -> Dict[str, Any]:
    """Generate additional data for model version artifact display.

    Args:
        model_version_artifact: The model version artifact response.

    Returns:
        The additional data for the model version artifact.
    """
    return {
        "artifact_version": model_version_artifact.artifact_version.id,
    }


def _generate_model_version_pipeline_run_data(
    model_version_pipeline_run: ModelVersionPipelineRunResponse,
) -> Dict[str, Any]:
    """Generate additional data for model version pipeline run display.

    Args:
        model_version_pipeline_run: The model version pipeline run response.

    Returns:
        The additional data for the model version pipeline run.
    """
    return {
        "pipeline_run": model_version_pipeline_run.pipeline_run.id,
    }


@cli.group(cls=TagGroup, tag=CliCategories.MODEL_CONTROL_PLANE)
def model() -> None:
    """Interact with models and model versions in the Model Control Plane."""


@list_options(
    ModelFilter,
    default_columns=[
        "name",
        "latest_version_name",
        "latest_version_id",
        "updated",
    ],
)
@model.command("list", help="List models with filter.")
def list_models(output_format: str, columns: str, **kwargs: Any) -> None:
    """List models with filter in the Model Control Plane.

    Args:
        output_format: Output format (table, json, yaml, tsv, csv).
        columns: Comma-separated list of columns to display.
        kwargs: Keyword arguments to filter models.
    """
    with console.status("Listing models..."):
        models = Client().list_models(**kwargs)

    cli_utils.render_list_output(
        page=models,
        output_format=output_format,
        columns=columns,
        row_formatter=_generate_model_data,
    )


@model.command("register", help="Register a new model.")
@click.option(
    "--name",
    "-n",
    help="The name of the model.",
    type=str,
    required=True,
)
@click.option(
    "--license",
    "-l",
    help="The license under which the model is created.",
    type=str,
    required=False,
)
@click.option(
    "--description",
    "-d",
    help="The description of the model.",
    type=str,
    required=False,
)
@click.option(
    "--audience",
    "-a",
    help="The target audience for the model.",
    type=str,
    required=False,
)
@click.option(
    "--use-cases",
    "-u",
    help="The use cases of the model.",
    type=str,
    required=False,
)
@click.option(
    "--tradeoffs",
    help="The tradeoffs of the model.",
    type=str,
    required=False,
)
@click.option(
    "--ethical",
    "-e",
    help="The ethical implications of the model.",
    type=str,
    required=False,
)
@click.option(
    "--limitations",
    help="The known limitations of the model.",
    type=str,
    required=False,
)
@click.option(
    "--tag",
    "-t",
    help="Tags associated with the model.",
    type=str,
    required=False,
    multiple=True,
)
@click.option(
    "--save-models-to-registry",
    "-s",
    help="Whether to automatically save model artifacts to the model registry.",
    type=click.BOOL,
    required=False,
    default=True,
)
def register_model(
    name: str,
    license: Optional[str],
    description: Optional[str],
    audience: Optional[str],
    use_cases: Optional[str],
    tradeoffs: Optional[str],
    ethical: Optional[str],
    limitations: Optional[str],
    tag: Optional[List[str]],
    save_models_to_registry: Optional[bool],
) -> None:
    """Register a new model in the Model Control Plane.

    Args:
        name: The name of the model.
        license: The license model created under.
        description: The description of the model.
        audience: The target audience of the model.
        use_cases: The use cases of the model.
        tradeoffs: The tradeoffs of the model.
        ethical: The ethical implications of the model.
        limitations: The know limitations of the model.
        tag: Tags associated with the model.
        save_models_to_registry: Whether to save the model to the
            registry.
    """
    try:
        Client().create_model(
            **remove_none_values(
                dict(
                    name=name,
                    license=license,
                    description=description,
                    audience=audience,
                    use_cases=use_cases,
                    trade_offs=tradeoffs,
                    ethics=ethical,
                    limitations=limitations,
                    tags=tag,
                    save_models_to_registry=save_models_to_registry,
                )
            )
        )
    except (EntityExistsError, ValueError) as e:
        cli_utils.exception(e)


@model.command("update", help="Update an existing model.")
@click.argument("model_name_or_id")
@click.option(
    "--name",
    "-n",
    help="The name of the model.",
    type=str,
    required=False,
)
@click.option(
    "--license",
    "-l",
    help="The license under which the model is created.",
    type=str,
    required=False,
)
@click.option(
    "--description",
    "-d",
    help="The description of the model.",
    type=str,
    required=False,
)
@click.option(
    "--audience",
    "-a",
    help="The target audience for the model.",
    type=str,
    required=False,
)
@click.option(
    "--use-cases",
    "-u",
    help="The use cases of the model.",
    type=str,
    required=False,
)
@click.option(
    "--tradeoffs",
    help="The tradeoffs of the model.",
    type=str,
    required=False,
)
@click.option(
    "--ethical",
    "-e",
    help="The ethical implications of the model.",
    type=str,
    required=False,
)
@click.option(
    "--limitations",
    help="The known limitations of the model.",
    type=str,
    required=False,
)
@click.option(
    "--tag",
    "-t",
    help="Tags to be added to the model.",
    type=str,
    required=False,
    multiple=True,
)
@click.option(
    "--remove-tag",
    "-r",
    help="Tags to be removed from the model.",
    type=str,
    required=False,
    multiple=True,
)
@click.option(
    "--save-models-to-registry",
    "-s",
    help="Whether to automatically save model artifacts to the model registry.",
    type=click.BOOL,
    required=False,
    default=True,
)
def update_model(
    model_name_or_id: str,
    name: Optional[str],
    license: Optional[str],
    description: Optional[str],
    audience: Optional[str],
    use_cases: Optional[str],
    tradeoffs: Optional[str],
    ethical: Optional[str],
    limitations: Optional[str],
    tag: Optional[List[str]],
    remove_tag: Optional[List[str]],
    save_models_to_registry: Optional[bool],
) -> None:
    """Register a new model in the Model Control Plane.

    Args:
        model_name_or_id: The name of the model.
        name: The name of the model.
        license: The license model created under.
        description: The description of the model.
        audience: The target audience of the model.
        use_cases: The use cases of the model.
        tradeoffs: The tradeoffs of the model.
        ethical: The ethical implications of the model.
        limitations: The know limitations of the model.
        tag: Tags to be added to the model.
        remove_tag: Tags to be removed from the model.
        save_models_to_registry: Whether to save the model to the
            registry.
    """
    model_id = Client().get_model(model_name_or_id=model_name_or_id).id
    update_dict = remove_none_values(
        dict(
            name=name,
            license=license,
            description=description,
            audience=audience,
            use_cases=use_cases,
            trade_offs=tradeoffs,
            ethics=ethical,
            limitations=limitations,
            add_tags=tag,
            remove_tags=remove_tag,
            save_models_to_registry=save_models_to_registry,
        )
    )
    Client().update_model(model_name_or_id=model_id, **update_dict)


@model.command("delete", help="Delete an existing model.")
@click.argument("model_name_or_id")
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Don't ask for confirmation.",
)
def delete_model(
    model_name_or_id: str,
    yes: bool = False,
) -> None:
    """Delete an existing model from the Model Control Plane.

    Args:
        model_name_or_id: The ID or name of the model to delete.
        yes: If set, don't ask for confirmation.
    """
    if not yes:
        confirmation = cli_utils.confirmation(
            f"Are you sure you want to delete model '{model_name_or_id}'?"
        )
        if not confirmation:
            cli_utils.declare("Model deletion canceled.")
            return

    try:
        Client().delete_model(
            model_name_or_id=model_name_or_id,
        )
    except (KeyError, ValueError) as e:
        cli_utils.exception(e)
    else:
        cli_utils.declare(f"Model '{model_name_or_id}' deleted.")


@model.group()
def version() -> None:
    """Interact with model versions in the Model Control Plane."""


@list_options(
    ModelVersionFilter,
    default_columns=["model", "version", "stage", "tags", "updated"],
)
@version.command("list", help="List model versions with filter.")
def list_model_versions(
    output_format: str, columns: str, **kwargs: Any
) -> None:
    """List model versions with filter in the Model Control Plane.

    Args:
        output_format: Output format (table, json, yaml, tsv, csv).
        columns: Comma-separated list of columns to display.
        kwargs: Keyword arguments to filter model versions.
    """
    with console.status("Listing model versions..."):
        model_versions = Client().list_model_versions(**kwargs)

    cli_utils.render_list_output(
        page=model_versions,
        output_format=output_format,
        columns=columns,
        row_formatter=_generate_model_version_data,
    )


@version.command("update", help="Update an existing model version stage.")
@click.argument("model_name_or_id")
@click.argument("model_version_name_or_number_or_id")
@click.option(
    "--stage",
    "-s",
    type=click.Choice(choices=ModelStages.values()),
    required=False,
    help="The stage of the model version.",
)
@click.option(
    "--name",
    "-n",
    type=str,
    required=False,
    help="The name of the model version.",
)
@click.option(
    "--description",
    "-d",
    type=str,
    required=False,
    help="The description of the model version.",
)
@click.option(
    "--tag",
    "-t",
    help="Tags to be added to the model.",
    type=str,
    required=False,
    multiple=True,
)
@click.option(
    "--remove-tag",
    "-r",
    help="Tags to be removed from the model.",
    type=str,
    required=False,
    multiple=True,
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Don't ask for confirmation, if stage already occupied.",
)
def update_model_version(
    model_name_or_id: str,
    model_version_name_or_number_or_id: str,
    stage: Optional[str],
    name: Optional[str],
    description: Optional[str],
    tag: Optional[List[str]],
    remove_tag: Optional[List[str]],
    force: bool = False,
) -> None:
    """Update an existing model version stage in the Model Control Plane.

    Args:
        model_name_or_id: The ID or name of the model containing version.
        model_version_name_or_number_or_id: The ID, number or name of the model version.
        stage: The stage of the model version to be set.
        name: The name of the model version.
        description: The description of the model version.
        tag: Tags to be added to the model version.
        remove_tag: Tags to be removed from the model version.
        force: Whether existing model version in target stage should be silently archived.
    """
    model_version = Client().get_model_version(
        model_name_or_id=model_name_or_id,
        model_version_name_or_number_or_id=model_version_name_or_number_or_id,
    )
    try:
        model_version = Client().update_model_version(
            model_name_or_id=model_name_or_id,
            version_name_or_id=model_version.id,
            stage=stage,
            add_tags=tag,
            remove_tags=remove_tag,
            force=force,
            name=name,
            description=description,
        )
    except RuntimeError:
        if not force:
            confirmation = cli_utils.confirmation(
                "Are you sure you want to change the status of model "
                f"version '{model_version_name_or_number_or_id}' to "
                f"'{stage}'?\nThis stage is already taken by "
                "model version shown above and if you will proceed this "
                "model version will get into archived stage."
            )
            if not confirmation:
                cli_utils.declare("Model version stage update canceled.")
                return
            model_version = Client().update_model_version(
                model_name_or_id=model_version.model.id,
                version_name_or_id=model_version.id,
                stage=stage,
                add_tags=tag,
                remove_tags=remove_tag,
                force=True,
                description=description,
            )


@version.command("delete", help="Delete an existing model version.")
@click.argument("model_name_or_id")
@click.argument("model_version_name_or_number_or_id")
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Don't ask for confirmation.",
)
def delete_model_version(
    model_name_or_id: str,
    model_version_name_or_number_or_id: str,
    yes: bool = False,
) -> None:
    """Delete an existing model version in the Model Control Plane.

    Args:
        model_name_or_id: The ID or name of the model that contains the version.
        model_version_name_or_number_or_id: The ID, number or name of the model version.
        yes: If set, don't ask for confirmation.
    """
    if not yes:
        confirmation = cli_utils.confirmation(
            f"Are you sure you want to delete model version '{model_version_name_or_number_or_id}' from model '{model_name_or_id}'?"
        )
        if not confirmation:
            cli_utils.declare("Model version deletion canceled.")
            return

    try:
        model_version = Client().get_model_version(
            model_name_or_id=model_name_or_id,
            model_version_name_or_number_or_id=model_version_name_or_number_or_id,
        )
        Client().delete_model_version(
            model_version_id=model_version.id,
        )
    except (KeyError, ValueError) as e:
        cli_utils.exception(e)
    else:
        cli_utils.declare(
            f"Model version '{model_version_name_or_number_or_id}' deleted from model '{model_name_or_id}'."
        )


@model.command(
    "data_artifacts",
    help="List data artifacts linked to a model version.",
)
@click.argument("model_name")
@click.option("--model_version", "-v", default=None)
@list_options(ModelVersionArtifactFilter)
def list_model_version_data_artifacts(
    model_name: str,
    output_format: str,
    columns: str,
    model_version: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """List data artifacts linked to a model version in the Model Control Plane.

    Args:
        model_name: The ID or name of the model containing version.
        output_format: Output format (table, json, yaml, tsv, csv).
        columns: Comma-separated list of columns to display.
        model_version: The name, number or ID of the model version. If not
            provided, the latest version is used.
        kwargs: Keyword arguments to filter models.
    """
    model_version_obj = Client().get_model_version(
        model_name_or_id=model_name,
        model_version_name_or_number_or_id=model_version,
    )

    with console.status("Listing data artifacts..."):
        links = Client().list_model_version_artifact_links(
            model_version_id=model_version_obj.id,
            only_data_artifacts=True,
            **kwargs,
        )

    cli_utils.render_list_output(
        page=links,
        output_format=output_format,
        columns=columns,
        row_formatter=_generate_model_version_artifact_data,
    )


@model.command(
    "model_artifacts",
    help="List model artifacts linked to a model version.",
)
@click.argument("model_name")
@click.option("--model_version", "-v", default=None)
@list_options(ModelVersionArtifactFilter)
def list_model_version_model_artifacts(
    model_name: str,
    output_format: str,
    columns: str,
    model_version: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """List model artifacts linked to a model version in the Model Control Plane.

    Args:
        model_name: The ID or name of the model containing version.
        output_format: Output format (table, json, yaml, tsv, csv).
        columns: Comma-separated list of columns to display.
        model_version: The name, number or ID of the model version. If not
            provided, the latest version is used.
        kwargs: Keyword arguments to filter models.
    """
    model_version_obj = Client().get_model_version(
        model_name_or_id=model_name,
        model_version_name_or_number_or_id=model_version,
    )

    with console.status("Listing model artifacts..."):
        links = Client().list_model_version_artifact_links(
            model_version_id=model_version_obj.id,
            only_model_artifacts=True,
            **kwargs,
        )

    cli_utils.render_list_output(
        page=links,
        output_format=output_format,
        columns=columns,
        row_formatter=_generate_model_version_artifact_data,
    )


@model.command(
    "deployment_artifacts",
    help="List deployment artifacts linked to a model version.",
)
@click.argument("model_name")
@click.option("--model_version", "-v", default=None)
@list_options(ModelVersionArtifactFilter)
def list_model_version_deployment_artifacts(
    model_name: str,
    output_format: str,
    columns: str,
    model_version: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """List deployment artifacts linked to a model version in the Model Control Plane.

    Args:
        model_name: The ID or name of the model containing version.
        output_format: Output format (table, json, yaml, tsv, csv).
        columns: Comma-separated list of columns to display.
        model_version: The name, number or ID of the model version. If not
            provided, the latest version is used.
        kwargs: Keyword arguments to filter models.
    """
    model_version_obj = Client().get_model_version(
        model_name_or_id=model_name,
        model_version_name_or_number_or_id=model_version,
    )

    with console.status("Listing deployment artifacts..."):
        links = Client().list_model_version_artifact_links(
            model_version_id=model_version_obj.id,
            only_deployment_artifacts=True,
            **kwargs,
        )

    cli_utils.render_list_output(
        page=links,
        output_format=output_format,
        columns=columns,
        row_formatter=_generate_model_version_artifact_data,
    )


@model.command(
    "runs",
    help="List pipeline runs of a model version.",
)
@click.argument("model_name")
@click.option("--model_version", "-v", default=None)
@list_options(ModelVersionPipelineRunFilter)
def list_model_version_pipeline_runs(
    model_name: str,
    output_format: str,
    columns: str,
    model_version: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """List pipeline runs of a model version in the Model Control Plane.

    Args:
        model_name: The ID or name of the model containing version.
        output_format: Output format (table, json, yaml, tsv, csv).
        columns: Comma-separated list of columns to display.
        model_version: The name, number or ID of the model version. If not
            provided, the latest version is used.
        kwargs: Keyword arguments to filter runs.
    """
    model_version_response_model = Client().get_model_version(
        model_name_or_id=model_name,
        model_version_name_or_number_or_id=model_version,
    )

    with console.status("Listing pipeline runs..."):
        runs = Client().list_model_version_pipeline_run_links(
            model_version_id=model_version_response_model.id,
            **kwargs,
        )

    cli_utils.render_list_output(
        page=runs,
        output_format=output_format,
        columns=columns,
        row_formatter=_generate_model_version_pipeline_run_data,
    )
