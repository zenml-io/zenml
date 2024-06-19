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
from rich.markdown import Markdown

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.client import Client
from zenml.console import console
from zenml.enums import CliCategories, ModelStages
from zenml.exceptions import EntityExistsError
from zenml.logger import get_logger
from zenml.model.gen_ai_helper import (
    construct_json_response_of_model_version_stats,
    construct_json_response_of_stack_and_components_from_pipeline_run,
    construct_json_response_of_steps_code_from_pipeline_run,
    get_model_version_latest_run,
    get_pipeline_info,
    get_failing_steps_for_runs,
)
from zenml.model.gen_ai_utils import (
    generate_code_improvement_suggestions,
    generate_log_failure_pattern_suggestions,
    generate_model_report,
    generate_poem,
    generate_stack_improvement_suggestions,
    generate_stats_summary,
    generate_summary_section,
)
from zenml.models import (
    ModelFilter,
    ModelResponse,
    ModelVersionArtifactFilter,
    ModelVersionFilter,
    ModelVersionPipelineRunFilter,
    ModelVersionResponse,
)
from zenml.models.v2.core.model_version import ModelReportType
from zenml.utils.dict_utils import remove_none_values

logger = get_logger(__name__)


def _model_to_print(model: ModelResponse) -> Dict[str, Any]:
    return {
        "id": model.id,
        "name": model.name,
        "latest_version": model.latest_version_name,
        "description": model.description,
        "tags": [t.name for t in model.tags],
        "save_to_registry": ":white_check_mark:"
        if model.save_models_to_registry
        else "",
        "use_cases": model.use_cases,
        "audience": model.audience,
        "limitations": model.limitations,
        "trade_offs": model.trade_offs,
        "ethics": model.ethics,
        "license": model.license,
        "updated": model.updated.date(),
    }


def _model_version_to_print(
    model_version: ModelVersionResponse,
) -> Dict[str, Any]:
    run_metadata = None
    if model_version.run_metadata:
        run_metadata = {
            k: v.value for k, v in model_version.run_metadata.items()
        }
    return {
        "id": model_version.id,
        "model": model_version.model.name,
        "name": model_version.name,
        "number": model_version.number,
        "description": model_version.description,
        "stage": model_version.stage,
        "run_metadata": run_metadata,
        "tags": [t.name for t in model_version.tags],
        "data_artifacts_count": len(model_version.data_artifact_ids),
        "model_artifacts_count": len(model_version.model_artifact_ids),
        "deployment_artifacts_count": len(
            model_version.deployment_artifact_ids
        ),
        "pipeline_runs_count": len(model_version.pipeline_run_ids),
        "updated": model_version.updated.date(),
    }


@cli.group(cls=TagGroup, tag=CliCategories.MODEL_CONTROL_PLANE)
def model() -> None:
    """Interact with models and model versions in the Model Control Plane."""


@cli_utils.list_options(ModelFilter)
@model.command("list", help="List models with filter.")
def list_models(**kwargs: Any) -> None:
    """List models with filter in the Model Control Plane.

    Args:
        **kwargs: Keyword arguments to filter models.
    """
    models = Client().zen_store.list_models(
        model_filter_model=ModelFilter(**kwargs)
    )

    if not models:
        cli_utils.declare("No models found.")
        return
    to_print = []
    for model in models:
        to_print.append(_model_to_print(model))
    cli_utils.print_table(to_print)


@cli_utils.list_options(ModelFilter)
@model.command("report", help="Generate a report about a model.")
@click.argument(
    "model_version_id",
)
@click.option(
    "--report-type",
    "-t",
    type=click.Choice(
        ModelReportType.values(),
    ),
    default=ModelReportType.ALL.value,
    help="The type of report to generate.",
)
def generate_model_report_cmd(
    model_version_id: str, report_type: str, **kwargs: Any
) -> None:
    """Generate a report about a model.

    Args:
        model_version_id: The ID of the model version.
        report_type: The type of report to generate.
        **kwargs: Keyword arguments to filter models.
    """
    report = generate_model_report(
        report_type=ModelReportType(report_type),
        model_version_id=model_version_id,
    )

    console.print(report)


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
        model = Client().create_model(
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
        cli_utils.error(str(e))

    cli_utils.print_table([_model_to_print(model)])


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
    model = Client().update_model(model_name_or_id=model_id, **update_dict)

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


@cli_utils.list_options(ModelVersionFilter)
@click.option(
    "--model-name",
    "-n",
    help="The name of the parent model.",
    type=str,
    required=False,
)
@version.command("list", help="List model versions with filter.")
def list_model_versions(model_name: str, **kwargs: Any) -> None:
    """List model versions with filter in the Model Control Plane.

    Args:
        model_name: The name of the parent model.
        **kwargs: Keyword arguments to filter models.
    """
    model_versions = Client().zen_store.list_model_versions(
        model_name_or_id=model_name,
        model_version_filter_model=ModelVersionFilter(**kwargs),
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
            cli_utils.print_table([_model_version_to_print(model_version)])

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
    cli_utils.print_table([_model_version_to_print(model_version)])


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
        cli_utils.error(str(e))
    else:
        cli_utils.declare(
            f"Model version '{model_version_name_or_number_or_id}' deleted from model '{model_name_or_id}'."
        )


def _print_artifacts_links_generic(
    model_name_or_id: str,
    model_version_name_or_number_or_id: Optional[str] = None,
    only_data_artifacts: bool = False,
    only_deployment_artifacts: bool = False,
    only_model_artifacts: bool = False,
    **kwargs: Any,
) -> None:
    """Generic method to print artifacts links.

    Args:
        model_name_or_id: The ID or name of the model containing version.
        model_version_name_or_number_or_id: The name, number or ID of the model version.
        only_data_artifacts: If set, only print data artifacts.
        only_deployment_artifacts: If set, only print deployment artifacts.
        only_model_artifacts: If set, only print model artifacts.
        **kwargs: Keyword arguments to filter models.
    """
    model_version = Client().get_model_version(
        model_name_or_id=model_name_or_id,
        model_version_name_or_number_or_id=model_version_name_or_number_or_id,
    )
    type_ = (
        "data artifacts"
        if only_data_artifacts
        else "deployment artifacts"
        if only_deployment_artifacts
        else "model artifacts"
    )

    if (
        (only_data_artifacts and not model_version.data_artifact_ids)
        or (
            only_deployment_artifacts
            and not model_version.deployment_artifact_ids
        )
        or (only_model_artifacts and not model_version.model_artifact_ids)
    ):
        cli_utils.declare(f"No {type_} linked to the model version found.")
        return

    cli_utils.title(
        f"{type_} linked to the model version `{model_version.name}[{model_version.number}]`:"
    )

    links = Client().list_model_version_artifact_links(
        model_version_id=model_version.id,
        only_data_artifacts=only_data_artifacts,
        only_deployment_artifacts=only_deployment_artifacts,
        only_model_artifacts=only_model_artifacts,
        **kwargs,
    )

    cli_utils.print_pydantic_models(
        links,
        columns=["artifact_version", "created"],
    )


@model.command(
    "data_artifacts",
    help="List data artifacts linked to a model version.",
)
@click.argument("model_name")
@click.option("--model_version", "-v", default=None)
@cli_utils.list_options(ModelVersionArtifactFilter)
def list_model_version_data_artifacts(
    model_name: str,
    model_version: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """List data artifacts linked to a model version in the Model Control Plane.

    Args:
        model_name: The ID or name of the model containing version.
        model_version: The name, number or ID of the model version. If not
            provided, the latest version is used.
        **kwargs: Keyword arguments to filter models.
    """
    _print_artifacts_links_generic(
        model_name_or_id=model_name,
        model_version_name_or_number_or_id=model_version,
        only_data_artifacts=True,
        **kwargs,
    )


@model.command(
    "model_artifacts",
    help="List model artifacts linked to a model version.",
)
@click.argument("model_name")
@click.option("--model_version", "-v", default=None)
@cli_utils.list_options(ModelVersionArtifactFilter)
def list_model_version_model_artifacts(
    model_name: str,
    model_version: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """List model artifacts linked to a model version in the Model Control Plane.

    Args:
        model_name: The ID or name of the model containing version.
        model_version: The name, number or ID of the model version. If not
            provided, the latest version is used.
        **kwargs: Keyword arguments to filter models.
    """
    _print_artifacts_links_generic(
        model_name_or_id=model_name,
        model_version_name_or_number_or_id=model_version,
        only_model_artifacts=True,
        **kwargs,
    )


@model.command(
    "deployment_artifacts",
    help="List deployment artifacts linked to a model version.",
)
@click.argument("model_name")
@click.option("--model_version", "-v", default=None)
@cli_utils.list_options(ModelVersionArtifactFilter)
def list_model_version_deployment_artifacts(
    model_name: str,
    model_version: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """List deployment artifacts linked to a model version in the Model Control Plane.

    Args:
        model_name: The ID or name of the model containing version.
        model_version: The name, number or ID of the model version. If not
            provided, the latest version is used.
        **kwargs: Keyword arguments to filter models.
    """
    _print_artifacts_links_generic(
        model_name_or_id=model_name,
        model_version_name_or_number_or_id=model_version,
        only_deployment_artifacts=True,
        **kwargs,
    )


@model.command(
    "runs",
    help="List pipeline runs of a model version.",
)
@click.argument("model_name")
@click.option("--model_version", "-v", default=None)
@cli_utils.list_options(ModelVersionPipelineRunFilter)
def list_model_version_pipeline_runs(
    model_name: str,
    model_version: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """List pipeline runs of a model version in the Model Control Plane.

    Args:
        model_name: The ID or name of the model containing version.
        model_version: The name, number or ID of the model version. If not
            provided, the latest version is used.
        **kwargs: Keyword arguments to filter models.
    """
    model_version_response_model = Client().get_model_version(
        model_name_or_id=model_name,
        model_version_name_or_number_or_id=model_version,
    )

    if not model_version_response_model.pipeline_run_ids:
        cli_utils.declare("No pipeline runs attached to model version found.")
        return
    cli_utils.title(
        f"Pipeline runs linked to the model version `{model_version_response_model.name}[{model_version_response_model.number}]`:"
    )

    links = Client().list_model_version_pipeline_run_links(
        model_version_id=model_version_response_model.id,
        **kwargs,
    )

    cli_utils.print_pydantic_models(
        links,
        columns=[
            "pipeline_run",
            "created",
        ],
    )
