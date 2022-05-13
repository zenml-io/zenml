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
import uuid
from typing import TYPE_CHECKING, Optional

import click

from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import (
    declare,
    error,
    pretty_print_model_deployer,
    print_served_model_configuration,
    warning,
)
from zenml.console import console
from zenml.enums import CliCategories, StackComponentType
from zenml.repository import Repository

if TYPE_CHECKING:
    from zenml.model_deployers import BaseModelDeployer


@cli.group(
    cls=TagGroup,
    tag=CliCategories.MODEL_DEPLOYMENT,
)
@click.pass_context
def served_models(ctx: click.Context) -> None:
    """List and manage served models with the active model
    deployer.
    """
    repo = Repository()
    active_stack = repo.zen_store.get_stack(name=repo.active_stack_name)
    model_deployer_wrapper = active_stack.get_component_wrapper(
        StackComponentType.MODEL_DEPLOYER
    )
    if model_deployer_wrapper is None:
        error(
            "No active model deployer found. Please add a model_deployer to "
            "your stack."
        )
        return
    ctx.obj = model_deployer_wrapper.to_component()


@served_models.command("list")
@click.option(
    "--pipeline",
    "-p",
    type=click.STRING,
    default=None,
    help="Show only served models that were deployed by the indicated "
    "pipeline.",
)
@click.option(
    "--step",
    "-s",
    type=click.STRING,
    default=None,
    help="Show only served models that were deployed by the indicated "
    "pipeline step.",
)
@click.option(
    "--pipeline-run",
    "-r",
    type=click.STRING,
    default=None,
    help="Show only served models that were deployed by the indicated "
    "pipeline run.",
)
@click.option(
    "--model",
    "-m",
    type=click.STRING,
    default=None,
    help="Show only served model versions for the given model name.",
)
@click.option(
    "--running",
    is_flag=True,
    help="Show only model servers that are currently runing.",
)
@click.pass_obj
def list_models(
    model_deployer: "BaseModelDeployer",
    pipeline: Optional[str],
    step: Optional[str],
    pipeline_run: Optional[str],
    model: Optional[str],
    running: bool,
) -> None:
    """Get a list of all served models within the model-deployer stack
    component.
    """
    services = model_deployer.find_model_server(
        running=running,
        pipeline_name=pipeline,
        pipeline_run_id=pipeline_run,
        pipeline_step_name=step,
        model_name=model,
    )
    if services:
        pretty_print_model_deployer(
            services,
            model_deployer,
        )
    else:
        warning("No served models found.")


@served_models.command("describe")
@click.argument("served_model_uuid", type=click.STRING)
@click.pass_obj
def describe_model(
    model_deployer: "BaseModelDeployer", served_model_uuid: str
) -> None:
    """Describe a specified served model."""

    served_models = model_deployer.find_model_server(
        service_uuid=uuid.UUID(served_model_uuid)
    )
    if served_models:
        print_served_model_configuration(served_models[0], model_deployer)
        return
    warning(f"No model with uuid: '{served_model_uuid}' could be found.")
    return


@served_models.command("get-url")
@click.argument("served_model_uuid", type=click.STRING)
@click.pass_obj
def get_url(
    model_deployer: "BaseModelDeployer", served_model_uuid: str
) -> None:
    """Return the prediction URL to a specified model server."""
    served_models = model_deployer.find_model_server(
        service_uuid=uuid.UUID(served_model_uuid)
    )
    if served_models:
        try:
            prediction_url = model_deployer.get_model_server_info(
                served_models[0]
            ).get("PREDICTION_URL")
            declare(
                f"  Prediction URL of Served Model {served_model_uuid} "
                f"is:\n"
                f"  {prediction_url}"
            )
        except KeyError:
            warning("The deployed model instance has no 'prediction_url'.")
        return
    warning(f"No model with uuid: '{served_model_uuid}' could be found.")
    return


@served_models.command("start")
@click.argument("served_model_uuid", type=click.STRING)
@click.option(
    "--timeout",
    "-t",
    type=click.INT,
    default=300,
    help="Time in seconds to wait for the model to start. Set to 0 to return "
    "immediately after telling the server to start, without waiting for it to "
    "become fully active (default: 300s).",
)
@click.pass_obj
def start_model_service(
    model_deployer: "BaseModelDeployer", served_model_uuid: str, timeout: int
) -> None:
    """Start a specified model server."""

    served_models = model_deployer.find_model_server(
        service_uuid=uuid.UUID(served_model_uuid)
    )
    if served_models:
        model_deployer.start_model_server(
            served_models[0].uuid, timeout=timeout
        )
        declare(f"Model server {served_models[0]} was started.")
        return

    warning(f"No model with uuid: '{served_model_uuid}' could be found.")
    return


@served_models.command("stop")
@click.argument("served_model_uuid", type=click.STRING)
@click.option(
    "--timeout",
    "-t",
    type=click.INT,
    default=300,
    help="Time in seconds to wait for the model to start. Set to 0 to return "
    "immediately after telling the server to stop, without waiting for it to "
    "become inactive (default: 300s).",
)
@click.option(
    "--yes",
    "-y",
    "force",
    is_flag=True,
    help="Force the model server to stop. This will bypass any graceful "
    "shutdown processes and try to force the model server to stop immediately, "
    "if possible.",
)
@click.option(
    "--force",
    "-f",
    "old_force",
    is_flag=True,
    help="DEPRECATED: Force the model server to stop. This will bypass any graceful "
    "shutdown processes and try to force the model server to stop immediately, "
    "if possible. Use `-y/--yes` instead.",
)
@click.pass_obj
def stop_model_service(
    model_deployer: "BaseModelDeployer",
    served_model_uuid: str,
    timeout: int,
    force: bool,
    old_force: bool,
) -> None:
    """Stop a specified model server."""
    if old_force:
        force = old_force
        warning(
            "The `--force` flag will soon be deprecated. Use `--yes` or `-y` instead."
        )
    served_models = model_deployer.find_model_server(
        service_uuid=uuid.UUID(served_model_uuid)
    )
    if served_models:
        model_deployer.stop_model_server(
            served_models[0].uuid, timeout=timeout, force=force
        )
        declare(f"Model server {served_models[0]} was stopped.")
        return

    warning(f"No model with uuid: '{served_model_uuid}' could be found.")
    return


@served_models.command("delete")
@click.argument("served_model_uuid", type=click.STRING)
@click.option(
    "--timeout",
    "-t",
    type=click.INT,
    default=300,
    help="Time in seconds to wait for the model to be deleted. Set to 0 to "
    "return immediately after stopping and deleting the model server, without "
    "waiting for it to release all allocated resources.",
)
@click.option(
    "--yes",
    "-y",
    "force",
    is_flag=True,
    help="Force the model server to stop and delete. This will bypass any "
    "graceful shutdown processes and try to force the model server to stop and "
    "delete immediately, if possible.",
)
@click.option(
    "--force",
    "-f",
    "old_force",
    is_flag=True,
    help="DEPRECATED: Force the model server to stop and delete. This will bypass any "
    "graceful shutdown processes and try to force the model server to stop and "
    "delete immediately, if possible. Use `-y/--yes` instead.",
)
@click.pass_obj
def delete_model_service(
    model_deployer: "BaseModelDeployer",
    served_model_uuid: str,
    timeout: int,
    force: bool,
    old_force: bool,
) -> None:
    """Delete a specified model server."""
    if old_force:
        force = old_force
        warning(
            "The `--force` flag will soon be deprecated. Use `--yes` or `-y` instead."
        )
    served_models = model_deployer.find_model_server(
        service_uuid=uuid.UUID(served_model_uuid)
    )
    if served_models:
        model_deployer.delete_model_server(
            served_models[0].uuid, timeout=timeout, force=force
        )
        declare(f"Model server {served_models[0]} was deleted.")
        return

    warning(f"No model with uuid: '{served_model_uuid}' could be found.")
    return


@served_models.command("logs")
@click.argument("served_model_uuid", type=click.STRING)
@click.option(
    "--follow",
    "-f",
    is_flag=True,
    help="Continue to output new log data as it becomes available.",
)
@click.option(
    "--tail",
    "-t",
    type=click.INT,
    default=None,
    help="Only show the last NUM lines of log output.",
)
@click.option(
    "--raw",
    "-r",
    is_flag=True,
    help="Show raw log contents (don't pretty-print logs).",
)
@click.pass_obj
def get_model_service_logs(
    model_deployer: "BaseModelDeployer",
    served_model_uuid: str,
    follow: bool,
    tail: Optional[int],
    raw: bool,
) -> None:
    """Display the logs for a model server."""

    served_models = model_deployer.find_model_server(
        service_uuid=uuid.UUID(served_model_uuid)
    )
    if not served_models:
        warning(f"No model with uuid: '{served_model_uuid}' could be found.")
        return

    for line in model_deployer.get_model_server_logs(
        served_models[0].uuid, follow=follow, tail=tail
    ):
        # don't pretty-print log lines that are already pretty-printed
        if raw or line.startswith("\x1b["):
            print(line)
        else:
            console.print(line)
