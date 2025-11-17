#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""CLI functionality to interact with deployments."""

import json
from typing import Any, List, Optional
from uuid import UUID

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import fetch_snapshot, list_options
from zenml.client import Client
from zenml.console import console
from zenml.deployers.exceptions import DeploymentInvalidParametersError
from zenml.enums import CliCategories
from zenml.logger import get_logger
from zenml.models import (
    DeploymentFilter,
)
from zenml.pipelines.pipeline_definition import Pipeline
from zenml.utils import source_utils
from zenml.utils.dashboard_utils import get_deployment_url

logger = get_logger(__name__)


def _import_pipeline(source: str) -> Pipeline:
    """Import a pipeline.

    Args:
        source: The pipeline source.

    Returns:
        The pipeline.
    """
    try:
        pipeline_instance = source_utils.load(source)
    except ModuleNotFoundError as e:
        source_root = source_utils.get_source_root()
        cli_utils.error(
            f"Unable to import module `{e.name}`. Make sure the source path is "
            f"relative to your source root `{source_root}`."
        )
    except AttributeError as e:
        cli_utils.error("Unable to load attribute from module: " + str(e))

    if not isinstance(pipeline_instance, Pipeline):
        cli_utils.error(
            f"The given source path `{source}` does not resolve to a pipeline "
            "object."
        )

    return pipeline_instance


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def deployment() -> None:
    """Interact with deployments."""


@deployment.command("list", help="List all registered deployments.")
@list_options(DeploymentFilter)
def list_deployments(**kwargs: Any) -> None:
    """List all registered deployments for the filter.

    Args:
        **kwargs: Keyword arguments to filter deployments.
    """
    client = Client()
    try:
        with console.status("Listing deployments...\n"):
            deployments = client.list_deployments(**kwargs)
    except KeyError as err:
        cli_utils.exception(err)
    else:
        if not deployments.items:
            cli_utils.declare("No deployments found for this filter.")
            return

        cli_utils.print_deployment_table(deployments=deployments.items)
        cli_utils.print_page_info(deployments)


@deployment.command("describe", help="Describe a deployment.")
@click.argument("deployment_name_or_id", type=str, required=True)
@click.option(
    "--show-secret",
    "-s",
    is_flag=True,
    help="Show the secret key.",
)
@click.option(
    "--show-metadata",
    "-m",
    is_flag=True,
    help="Show the metadata.",
)
@click.option(
    "--show-schema",
    "-sc",
    is_flag=True,
    help="Show the schema.",
)
@click.option(
    "--no-truncate",
    "-nt",
    is_flag=True,
    help="Don't truncate the metadata.",
)
def describe_deployment(
    deployment_name_or_id: str,
    show_secret: bool = False,
    show_metadata: bool = False,
    no_truncate: bool = False,
    show_schema: bool = False,
) -> None:
    """Describe a deployment.

    Args:
        deployment_name_or_id: The name or ID of the deployment to describe.
        show_secret: If True, show the secret key.
        show_metadata: If True, show the metadata.
        show_schema: If True, show the schema.
        no_truncate: If True, don't truncate the metadata.
    """
    try:
        deployment = Client().get_deployment(
            name_id_or_prefix=deployment_name_or_id,
        )
    except KeyError as e:
        cli_utils.exception(e)
    else:
        cli_utils.pretty_print_deployment(
            deployment,
            show_secret=show_secret,
            show_metadata=show_metadata,
            show_schema=show_schema,
            no_truncate=no_truncate,
        )


@deployment.command("provision", help="Provision a deployment.")
@click.argument("deployment_name_or_id", type=str, required=True)
@click.option(
    "--snapshot",
    "-s",
    "snapshot_name_or_id",
    type=str,
    required=False,
    help="ID or name of the snapshot to use. If not provided, the current "
    "snapshot configured for the deployment will be used.",
)
@click.option(
    "--pipeline",
    "-p",
    "pipeline_name_or_id",
    type=str,
    required=False,
    help="The name or ID of the pipeline to which the snapshot belongs.",
)
@click.option(
    "--overtake",
    "-o",
    "overtake",
    is_flag=True,
    default=False,
    required=False,
    help="Provision the deployment with the given name even if it is "
    "owned by a different user.",
)
@click.option(
    "--timeout",
    "-t",
    "timeout",
    type=int,
    required=False,
    default=None,
    help="Maximum time in seconds to wait for the deployment to be "
    "provisioned.",
)
def provision_deployment(
    deployment_name_or_id: str,
    snapshot_name_or_id: Optional[str] = None,
    pipeline_name_or_id: Optional[str] = None,
    overtake: bool = False,
    timeout: Optional[int] = None,
) -> None:
    """Provision a deployment.

    Args:
        deployment_name_or_id: The name or ID of the deployment to deploy.
        snapshot_name_or_id: The ID or name of the pipeline snapshot to use.
        pipeline_name_or_id: The name or ID of the pipeline to which the
            snapshot belongs.
        overtake: If True, provision the deployment with the given name
            even if it is owned by a different user.
        timeout: The maximum time in seconds to wait for the deployment
            to be provisioned.
    """
    snapshot_id: Optional[UUID] = None
    if snapshot_name_or_id:
        snapshot = fetch_snapshot(snapshot_name_or_id, pipeline_name_or_id)
        snapshot_id = snapshot.id

    client = Client()
    try:
        deployment = client.get_deployment(deployment_name_or_id)
    except KeyError:
        pass
    else:
        if (
            deployment.user
            and deployment.user.id != client.active_user.id
            and not overtake
        ):
            confirmation = cli_utils.confirmation(
                f"Deployment with name '{deployment.name}' is owned by a "
                f"different user '{deployment.user.name}'.\nDo you want to "
                "continue and provision it "
                "(hint: use the --overtake flag to skip this check)?"
            )
            if not confirmation:
                cli_utils.declare("Deployment provisioning canceled.")
                return

    with console.status(
        f"Provisioning deployment '{deployment_name_or_id}'...\n"
    ):
        try:
            deployment = Client().provision_deployment(
                name_id_or_prefix=deployment_name_or_id,
                snapshot_id=snapshot_id,
                timeout=timeout,
            )
        except KeyError as e:
            cli_utils.exception(e)
        else:
            cli_utils.declare(
                f"Provisioned deployment '{deployment_name_or_id}'."
            )
            cli_utils.pretty_print_deployment(deployment, show_secret=True)

            dashboard_url = get_deployment_url(deployment)
            if dashboard_url:
                cli_utils.declare(
                    f"\nView in ZenML Cloud: [link]{dashboard_url}[/link]"
                )


@deployment.command("deprovision", help="Deprovision a deployment.")
@click.argument("deployment_name_or_id", type=str, required=False)
@click.option(
    "--all",
    "-a",
    is_flag=True,
    default=False,
    help="Deprovision all deployments.",
)
@click.option(
    "--mine",
    "-m",
    is_flag=True,
    default=False,
    help="Deprovision only deployments owned by the current user.",
)
@click.option(
    "--ignore-errors",
    "-i",
    is_flag=True,
    default=False,
    help="Ignore errors when deprovisioning multiple deployments.",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Don't ask for confirmation.",
)
@click.option(
    "--max-count",
    "-c",
    "max_count",
    type=int,
    required=False,
    default=10,
    help="Maximum number of deployments to deprovision in one go.",
)
@click.option(
    "--timeout",
    "-t",
    "timeout",
    type=int,
    required=False,
    default=None,
    help="Maximum time in seconds to wait for the deployment to be "
    "deprovisioned.",
)
def deprovision_deployment(
    deployment_name_or_id: Optional[str] = None,
    all: bool = False,
    mine: bool = False,
    yes: bool = False,
    ignore_errors: bool = False,
    max_count: int = 10,
    timeout: Optional[int] = None,
) -> None:
    """Deprovision a deployment.

    Args:
        deployment_name_or_id: The name or ID of the deployment to deprovision.
        all: If set, deprovision all deployments.
        mine: If set, deprovision only deployments owned by the current user.
        yes: If set, don't ask for confirmation.
        ignore_errors: If set, ignore errors when deprovisioning multiple
            deployments.
        max_count: The maximum number of deployments to deprovision in one go.
        timeout: The maximum time in seconds to wait for the deployment
            to be deprovisioned.
    """
    client = Client()

    if all:
        deployments = client.list_deployments(size=max_count).items
    elif mine:
        deployments = client.list_deployments(
            user=client.active_user.id,
            size=max_count,
        ).items
    elif deployment_name_or_id:
        deployments = [
            client.get_deployment(name_id_or_prefix=deployment_name_or_id)
        ]
    else:
        cli_utils.error(
            "Either a deployment name or ID must be provided or --all or "
            "--mine must be set."
        )

    if len(deployments) == 0:
        cli_utils.error("No deployments found to deprovision.")

    if len(deployments) == 1:
        cli_utils.declare(
            f"The following deployment will be deprovisioned: "
            f"{deployments[0].name}"
        )
    else:
        deployment_names = [deployment.name for deployment in deployments]
        cli_utils.declare(
            f"The following deployments will ALL be deprovisioned: "
            f"{', '.join(deployment_names)}"
        )

    other_deployments = [
        deployment
        for deployment in deployments
        if deployment.user and deployment.user.id != client.active_user.id
    ]

    if other_deployments:
        deployment_names = [
            deployment.name for deployment in other_deployments
        ]
        cli_utils.warning(
            f"The following deployments are not owned by the current "
            f"user: {', '.join(deployment_names)} !"
        )

    if not yes:
        confirmation = cli_utils.confirmation(
            "Are you sure you want to continue?"
        )
        if not confirmation:
            cli_utils.declare("Deployment deprovision canceled.")
            return

    for deployment in deployments:
        with console.status(
            f"Deprovisioning deployment '{deployment.name}'...\n"
        ):
            try:
                client.deprovision_deployment(
                    name_id_or_prefix=deployment.id,
                    timeout=timeout,
                )
                cli_utils.declare(
                    f"Deprovisioned deployment '{deployment.name}'."
                )
                cli_utils.declare(
                    "Hint: to permanently delete the deployment, run `zenml "
                    f"deployment delete {deployment.name}`."
                )
            except KeyError as e:
                error_message = (
                    f"Failed to deprovision deployment '{deployment.name}': "
                    f"{str(e)}"
                )
                if all or mine and ignore_errors:
                    cli_utils.warning(error_message)
                else:
                    cli_utils.error(error_message)


@deployment.command("delete", help="Delete a deployment.")
@click.argument("deployment_name_or_id", type=str, required=False)
@click.option(
    "--all",
    "-a",
    is_flag=True,
    default=False,
    help="Deprovision all deployments.",
)
@click.option(
    "--mine",
    "-m",
    is_flag=True,
    default=False,
    help="Deprovision only deployments owned by the current user.",
)
@click.option(
    "--ignore-errors",
    "-i",
    is_flag=True,
    default=False,
    help="Ignore errors when deprovisioning multiple deployments.",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Don't ask for confirmation.",
)
@click.option(
    "--timeout",
    "-t",
    "timeout",
    type=int,
    required=False,
    default=None,
    help="Maximum time in seconds to wait for the deployment to be "
    "deprovisioned.",
)
@click.option(
    "--max-count",
    "-c",
    "max_count",
    type=int,
    required=False,
    default=20,
    help="Maximum number of deployments to delete in one go.",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    default=False,
    help="Force the deletion of the deployment if it cannot be deprovisioned.",
)
def delete_deployment(
    deployment_name_or_id: Optional[str] = None,
    all: bool = False,
    mine: bool = False,
    ignore_errors: bool = False,
    yes: bool = False,
    timeout: Optional[int] = None,
    max_count: int = 20,
    force: bool = False,
) -> None:
    """Deprovision and delete a deployment.

    Args:
        deployment_name_or_id: The name or ID of the deployment to delete.
        all: If set, delete all deployments.
        mine: If set, delete only deployments owned by the current user.
        ignore_errors: If set, ignore errors when deleting multiple deployments.
        yes: If set, don't ask for confirmation.
        timeout: The maximum time in seconds to wait for the deployment
            to be deprovisioned.
        max_count: The maximum number of deployments to delete in one go.
        force: If set, force the deletion of the deployment if it cannot
            be deprovisioned.
    """
    client = Client()

    if all:
        deployments = client.list_deployments(size=max_count).items
    elif mine:
        deployments = client.list_deployments(
            user=client.active_user.id,
            size=max_count,
        ).items
    elif deployment_name_or_id:
        deployments = [
            client.get_deployment(name_id_or_prefix=deployment_name_or_id)
        ]
    else:
        cli_utils.error(
            "Either a deployment name or ID must be provided or --all or "
            "--mine must be set."
        )

    if len(deployments) == 0:
        cli_utils.error("No deployments found to delete.")

    if len(deployments) == 1:
        cli_utils.declare(
            f"The following deployment will be deleted: {deployments[0].name}"
        )
    else:
        deployment_names = [deployment.name for deployment in deployments]
        cli_utils.declare(
            f"The following deployments will ALL be deleted: "
            f"{', '.join(deployment_names)}"
        )

    other_deployments = [
        deployment
        for deployment in deployments
        if deployment.user and deployment.user.id != client.active_user.id
    ]

    if other_deployments:
        deployment_names = [
            deployment.name for deployment in other_deployments
        ]
        cli_utils.warning(
            f"The following deployments are not owned by the current "
            f"user: {', '.join(deployment_names)} !"
        )

    if not yes:
        confirmation = cli_utils.confirmation(
            "Are you sure you want to continue?"
        )
        if not confirmation:
            cli_utils.declare("Deployment deletion canceled.")
            return

    for deployment in deployments:
        with console.status(f"Deleting deployment '{deployment.name}'...\n"):
            try:
                Client().delete_deployment(
                    name_id_or_prefix=deployment.id,
                    force=force,
                    timeout=timeout,
                )
                cli_utils.declare(f"Deleted deployment '{deployment.name}'.")
            except KeyError as e:
                error_message = (
                    f"Failed to delete deployment '{deployment.name}': "
                    f"{str(e)}"
                )
                if all or mine and ignore_errors:
                    cli_utils.warning(error_message)
                else:
                    cli_utils.error(error_message)


@deployment.command("refresh", help="Refresh the status of a deployment.")
@click.argument("deployment_name_or_id", type=str, required=True)
def refresh_deployment(
    deployment_name_or_id: str,
) -> None:
    """Refresh the status of a deployment.

    Args:
        deployment_name_or_id: The name or ID of the deployment to refresh.
    """
    try:
        deployment = Client().refresh_deployment(
            name_id_or_prefix=deployment_name_or_id
        )

    except KeyError as e:
        cli_utils.exception(e)
    else:
        cli_utils.pretty_print_deployment(deployment, show_secret=True)


@deployment.command(
    "invoke",
    context_settings={"ignore_unknown_options": True},
    help="Invoke a deployment with arguments.",
)
@click.argument("deployment_name_or_id", type=str, required=True)
@click.option(
    "--timeout",
    "-t",
    "timeout",
    type=int,
    required=False,
    default=None,
    help="Maximum time in seconds to wait for the deployment to be invoked.",
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def invoke_deployment(
    deployment_name_or_id: str,
    args: List[str],
    timeout: Optional[int] = None,
) -> None:
    """Call a deployment with arguments.

    Args:
        deployment_name_or_id: The name or ID of the deployment to call.
        args: The arguments to pass to the deployment call.
        timeout: The maximum time in seconds to wait for the deployment
            to be invoked.
    """
    from zenml.deployers.utils import invoke_deployment

    # Parse the given args
    args = list(args)
    args.append(deployment_name_or_id)

    name_or_id, parsed_args = cli_utils.parse_name_and_extra_arguments(
        args,
        expand_args=True,
        name_mandatory=True,
    )
    assert name_or_id is not None

    try:
        response = invoke_deployment(
            deployment_name_or_id=name_or_id,
            timeout=timeout or 300,  # 5 minute timeout
            project=None,
            **parsed_args,
        )
    except DeploymentInvalidParametersError as e:
        cli_utils.error(
            f"Invalid parameters for deployment '{name_or_id}': \n"
            f"{str(e)}\n\n"
            f"Hint: run 'zenml deployment describe --schema {name_or_id}' "
            "to inspect the deployment schema."
        )
    except KeyError as e:
        cli_utils.error(
            str(e)
            + "\n"
            + f"Hint: run [green]`zenml deployment logs {name_or_id}`[/green] "
            "to inspect the deployment logs."
        )
    else:
        cli_utils.declare(f"Invoked deployment '{name_or_id}' with response:")
        print(json.dumps(response, indent=2))
        if isinstance(response, dict) and not response.get("success", True):
            cli_utils.declare(
                f"Hint: run [green]`zenml deployment logs {name_or_id}`[/green] "
                "to inspect the deployment logs."
            )


@deployment.command("logs", help="Get the logs of a deployment.")
@click.argument("deployment_name_or_id", type=str, required=True)
@click.option(
    "--follow",
    "-f",
    is_flag=True,
    default=False,
    help="Follow the logs.",
)
@click.option(
    "--tail",
    "-t",
    type=int,
    default=None,
    help="The number of lines to show from the end of the logs.",
)
def log_deployment(
    deployment_name_or_id: str,
    follow: bool = False,
    tail: Optional[int] = None,
) -> None:
    """Get the logs of a deployment.

    Args:
        deployment_name_or_id: The name or ID of the deployment to get the logs of.
        follow: If True, follow the logs.
        tail: The number of lines to show from the end of the logs. If None,
            show all logs.
    """
    try:
        logs = Client().get_deployment_logs(
            name_id_or_prefix=deployment_name_or_id,
            follow=follow,
            tail=tail,
        )
    except KeyError as e:
        cli_utils.exception(e)
    else:
        for log in logs:
            print(log)
