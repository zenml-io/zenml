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
# from functools import partial
from typing import Any, Dict, List, Optional

import click

# from uuid import UUID
# import click
from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.client import Client
from zenml.enums import CliCategories, ModelStages
from zenml.exceptions import EntityExistsError
from zenml.logger import get_logger
from zenml.models.model_models import (
    ModelFilterModel,
    ModelRequestModel,
    ModelResponseModel,
    ModelUpdateModel,
    ModelVersionArtifactFilterModel,
    ModelVersionFilterModel,
    ModelVersionPipelineRunFilterModel,
    ModelVersionResponseModel,
    ModelVersionUpdateModel,
)
from zenml.utils.dict_utils import remove_none_values

logger = get_logger(__name__)


def _model_to_print(model: ModelResponseModel) -> Dict[str, Any]:
    return {
        "id": model.id,
        "name": model.name,
        "latest_version": model.latest_version,
        "description": model.description,
        "tags": [t.name for t in model.tags],
        "use_cases": model.use_cases,
        "audience": model.audience,
        "limitations": model.limitations,
        "trade_offs": model.trade_offs,
        "ethics": model.ethics,
        "license": model.license,
        "updated": model.updated.date(),
    }


def _model_version_to_print(
    model_version: ModelVersionResponseModel,
) -> Dict[str, Any]:
    return {
        "id": model_version.id,
        "name": model_version.name,
        "number": model_version.number,
        "description": model_version.description,
        "stage": model_version.stage,
        "artifact_objects_count": len(model_version.artifact_object_ids),
        "model_objects_count": len(model_version.model_object_ids),
        "deployments_count": len(model_version.deployment_ids),
        "pipeline_runs_count": len(model_version.pipeline_run_ids),
        "updated": model_version.updated.date(),
    }


@cli.group(cls=TagGroup, tag=CliCategories.MODEL_CONTROL_PLANE)
def model() -> None:
    """Interact with models and model versions in the Model Control Plane."""


@cli_utils.list_options(ModelFilterModel)
@model.command("list", help="List models with filter.")
def list_models(**kwargs: Any) -> None:
    """List models with filter in the Model Control Plane.

    Args:
        **kwargs: Keyword arguments to filter models.
    """
    models = Client().list_models(ModelFilterModel(**kwargs))

    if not models:
        cli_utils.declare("No models found.")
        return
    to_print = []
    for model in models:
        to_print.append(_model_to_print(model))
    cli_utils.print_table(to_print)


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
    """
    try:
        model = Client().create_model(
            ModelRequestModel(
                name=name,
                license=license,
                description=description,
                audience=audience,
                use_cases=use_cases,
                trade_offs=tradeoffs,
                ethics=ethical,
                limitations=limitations,
                tags=tag,
                user=Client().active_user.id,
                workspace=Client().active_workspace.id,
            )
        )
    except (EntityExistsError, ValueError) as e:
        cli_utils.error(str(e))

    cli_utils.print_table([_model_to_print(model)])


@model.command("update", help="Update an existing model.")
@click.argument("model_name_or_id")
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
def update_model(
    model_name_or_id: str,
    license: Optional[str],
    description: Optional[str],
    audience: Optional[str],
    use_cases: Optional[str],
    tradeoffs: Optional[str],
    ethical: Optional[str],
    limitations: Optional[str],
    tag: Optional[List[str]],
    remove_tag: Optional[List[str]],
) -> None:
    """Register a new model in the Model Control Plane.

    Args:
        model_name_or_id: The name of the model.
        license: The license model created under.
        description: The description of the model.
        audience: The target audience of the model.
        use_cases: The use cases of the model.
        tradeoffs: The tradeoffs of the model.
        ethical: The ethical implications of the model.
        limitations: The know limitations of the model.
        tag: Tags to be added to the model.
        remove_tag: Tags to be removed from the model.
    """
    model_id = Client().get_model(model_name_or_id=model_name_or_id).id
    update_dict = remove_none_values(
        dict(
            license=license,
            description=description,
            audience=audience,
            use_cases=use_cases,
            trade_offs=tradeoffs,
            ethics=ethical,
            limitations=limitations,
            add_tags=tag,
            remove_tags=remove_tag,
            user=Client().active_user.id,
            workspace=Client().active_workspace.id,
        )
    )

    model = Client().update_model(
        model_id=model_id,
        model_update=ModelUpdateModel(**update_dict),
    )
    cli_utils.print_table([_model_to_print(model)])


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
        cli_utils.error(str(e))
    else:
        cli_utils.declare(f"Model '{model_name_or_id}' deleted.")


@model.group()
def version() -> None:
    """Interact with model versions in the Model Control Plane."""


@cli_utils.list_options(ModelVersionFilterModel)
@click.argument("model_name_or_id")
@version.command("list", help="List model versions with filter.")
def list_model_versions(model_name_or_id: str, **kwargs: Any) -> None:
    """List model versions with filter in the Model Control Plane.

    Args:
        model_name_or_id: The ID or name of the model containing version.
        **kwargs: Keyword arguments to filter models.
    """
    model_id = Client().get_model(model_name_or_id=model_name_or_id).id
    model_versions = Client().list_model_versions(
        model_name_or_id=model_id,
        model_version_filter_model=ModelVersionFilterModel(**kwargs),
    )

    if not model_versions:
        cli_utils.declare("No model versions found.")
        return

    to_print = []
    for model_version in model_versions:
        to_print.append(_model_version_to_print(model_version))

    cli_utils.print_table(to_print)


@version.command("update", help="Update an existing model version stage.")
@click.argument("model_name_or_id")
@click.argument("model_version_name_or_number_or_id")
@click.option(
    "--stage",
    "-s",
    type=click.Choice(choices=ModelStages.values()),
    help="The stage of the model version.",
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
    stage: str,
    force: bool = False,
) -> None:
    """Update an existing model version stage in the Model Control Plane.

    Args:
        model_name_or_id: The ID or name of the model containing version.
        model_version_name_or_number_or_id: The ID, number or name of the model version.
        stage: The stage of the model version to be set.
        force: Whether existing model version in target stage should be silently archived.
    """
    model_version = Client().get_model_version(
        model_name_or_id=model_name_or_id,
        model_version_name_or_number_or_id=model_version_name_or_number_or_id,
    )
    try:
        Client().update_model_version(
            model_version_id=model_version.id,
            model_version_update_model=ModelVersionUpdateModel(
                model=model_version.model.id, stage=stage, force=force
            ),
        )
    except RuntimeError:
        if not force:
            cli_utils.print_table(
                [
                    _model_version_to_print(
                        Client().get_model_version(
                            model_name_or_id=model_version.model.id,
                            model_version_name_or_number_or_id=stage,
                        )
                    )
                ]
            )

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
            Client().update_model_version(
                model_version_id=model_version.id,
                model_version_update_model=ModelVersionUpdateModel(
                    model=model_version.model.id, stage=stage, force=True
                ),
            )
    cli_utils.declare(
        f"Model version '{model_version.name}' stage updated to '{stage}'."
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
        Client().delete_model_version(
            model_name_or_id=model_name_or_id,
            model_version_name_or_id=model_version_name_or_number_or_id,
        )
    except (KeyError, ValueError) as e:
        cli_utils.error(str(e))
    else:
        cli_utils.declare(
            f"Model version '{model_version_name_or_number_or_id}' deleted from model '{model_name_or_id}'."
        )


def _print_artifacts_links_generic(
    model_name_or_id: str,
    model_version_name_or_number_or_id: str,
    only_artifact_objects: bool = False,
    only_deployments: bool = False,
    only_model_objects: bool = False,
    **kwargs: Any,
) -> None:
    """Generic method to print artifacts links.

    Args:
        model_name_or_id: The ID or name of the model containing version.
        model_version_name_or_number_or_id: The name, number or ID of the model version.
        only_artifact_objects: If set, only print artifacts.
        only_deployments: If set, only print deployments.
        only_model_objects: If set, only print model objects.
        **kwargs: Keyword arguments to filter models.
    """
    model_version = Client().get_model_version(
        model_name_or_id=model_name_or_id,
        model_version_name_or_number_or_id=ModelStages.LATEST
        if model_version_name_or_number_or_id == "0"
        else model_version_name_or_number_or_id,
    )
    type_ = (
        "artifacts"
        if only_artifact_objects
        else "deployments"
        if only_deployments
        else "model objects"
    )

    if (
        (only_artifact_objects and not model_version.artifact_object_ids)
        or (only_deployments and not model_version.deployment_ids)
        or (only_model_objects and not model_version.model_object_ids)
    ):
        cli_utils.declare(f"No {type_} linked to the model version found.")
        return

    cli_utils.title(
        f"{type_} linked to the model version `{model_version.name}[{model_version.number}]`:"
    )

    links = Client().list_model_version_artifact_links(
        model_name_or_id=model_version.model.id,
        model_version_name_or_number_or_id=model_version.id,
        model_version_artifact_link_filter_model=ModelVersionArtifactFilterModel(
            only_artifacts=only_artifact_objects,
            only_deployments=only_deployments,
            only_model_objects=only_model_objects,
            **kwargs,
        ),
    )

    cli_utils.print_pydantic_models(
        links,
        columns=[
            "pipeline_name",
            "step_name",
            "name",
            "link_version",
            "artifact",
            "created",
        ],
    )


@version.command(
    "artifacts",
    help="List artifacts linked to a model version.",
)
@click.argument("model_name_or_id")
@click.argument("model_version_name_or_number_or_id", default="0")
@cli_utils.list_options(ModelVersionArtifactFilterModel)
def list_model_version_artifacts(
    model_name_or_id: str,
    model_version_name_or_number_or_id: str,
    **kwargs: Any,
) -> None:
    """List artifacts linked to a model version in the Model Control Plane.

    Args:
        model_name_or_id: The ID or name of the model containing version.
        model_version_name_or_number_or_id: The name, number or ID of the model version.
            Or use 0 for the latest version.
        **kwargs: Keyword arguments to filter models.
    """
    _print_artifacts_links_generic(
        model_name_or_id=model_name_or_id,
        model_version_name_or_number_or_id=model_version_name_or_number_or_id,
        only_artifact_objects=True,
        **kwargs,
    )


@version.command(
    "model_objects",
    help="List model objects linked to a model version.",
)
@click.argument("model_name_or_id")
@click.argument("model_version_name_or_number_or_id", default="0")
@cli_utils.list_options(ModelVersionArtifactFilterModel)
def list_model_version_model_objects(
    model_name_or_id: str,
    model_version_name_or_number_or_id: str,
    **kwargs: Any,
) -> None:
    """List model objects linked to a model version in the Model Control Plane.

    Args:
        model_name_or_id: The ID or name of the model containing version.
        model_version_name_or_number_or_id: The name, number or ID of the model version.
            Or use 0 for the latest version.
        **kwargs: Keyword arguments to filter models.
    """
    _print_artifacts_links_generic(
        model_name_or_id=model_name_or_id,
        model_version_name_or_number_or_id=model_version_name_or_number_or_id,
        only_model_objects=True,
        **kwargs,
    )


@version.command(
    "deployments",
    help="List deployments linked to a model version.",
)
@click.argument("model_name_or_id")
@click.argument("model_version_name_or_number_or_id", default="0")
@cli_utils.list_options(ModelVersionArtifactFilterModel)
def list_model_version_deployments(
    model_name_or_id: str,
    model_version_name_or_number_or_id: str,
    **kwargs: Any,
) -> None:
    """List deployments linked to a model version in the Model Control Plane.

    Args:
        model_name_or_id: The ID or name of the model containing version.
        model_version_name_or_number_or_id: The name, number or ID of the model version.
            Or use 0 for the latest version.
        **kwargs: Keyword arguments to filter models.
    """
    _print_artifacts_links_generic(
        model_name_or_id=model_name_or_id,
        model_version_name_or_number_or_id=model_version_name_or_number_or_id,
        only_deployments=True,
        **kwargs,
    )


@version.command(
    "runs",
    help="List pipeline runs of a model version.",
)
@click.argument("model_name_or_id")
@click.argument("model_version_name_or_number_or_id", default="0")
@cli_utils.list_options(ModelVersionPipelineRunFilterModel)
def list_model_version_pipeline_runs(
    model_name_or_id: str,
    model_version_name_or_number_or_id: str,
    **kwargs: Any,
) -> None:
    """List pipeline runs of a model version in the Model Control Plane.

    Args:
        model_name_or_id: The ID or name of the model containing version.
        model_version_name_or_number_or_id: The name, number or ID of the model version.
            Or use 0 for the latest version.
        **kwargs: Keyword arguments to filter models.
    """
    model_version = Client().get_model_version(
        model_name_or_id=model_name_or_id,
        model_version_name_or_number_or_id=ModelStages.LATEST
        if model_version_name_or_number_or_id == "0"
        else model_version_name_or_number_or_id,
    )

    if not model_version.pipeline_run_ids:
        cli_utils.declare("No pipeline runs attached to model version found.")
        return
    cli_utils.title(
        f"Pipeline runs linked to the model version `{model_version.name}[{model_version.number}]`:"
    )

    links = Client().list_model_version_pipeline_run_links(
        model_name_or_id=model_version.model.id,
        model_version_name_or_number_or_id=model_version.id,
        model_version_pipeline_run_link_filter_model=ModelVersionPipelineRunFilterModel(
            **kwargs,
        ),
    )

    cli_utils.print_pydantic_models(
        links,
        columns=[
            "name",
            "pipeline_run",
            "created",
        ],
    )
