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

import uuid
from typing import TYPE_CHECKING, cast

import click
from rich.errors import MarkupError

from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import (
    declare,
    error,
    pretty_print_model_deployer,
    print_served_model_configuration,
    warning,
)
from zenml.console import console
from zenml.enums import StackComponentType

if TYPE_CHECKING:
    from zenml.model_deployers import BaseModelDeployer


def register_model_deployer_subcommands() -> None:  # noqa: C901
    """Registers CLI subcommands for the Model Deployer."""
    model_deployer_group = cast(TagGroup, cli.commands.get("model-deployer"))
    if not model_deployer_group:
        return

    @model_deployer_group.group(
        cls=TagGroup,
        help="Commands for interacting with served models.",
    )
    @click.pass_context
    def models(ctx: click.Context) -> None:
        """List and manage served models with the active model deployer.

        Args:
            ctx: The click context.
        """
        from zenml.client import Client
        from zenml.stack.stack_component import StackComponent

        client = Client()
        model_deployer_models = client.active_stack_model.components.get(
            StackComponentType.MODEL_DEPLOYER
        )
        if model_deployer_models is None:
            error(
                "No active model deployer found. Please add a model_deployer "
                "to your stack."
            )
            return
        ctx.obj = StackComponent.from_model(model_deployer_models[0])

    @models.command(
        "list",
        help="Get a list of all served models within the model-deployer stack "
        "component.",
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
        "--pipeline-run-id",
        "-r",
        type=click.STRING,
        default=None,
        help="Show only served models that were deployed by the indicated "
        "pipeline run.",
    )
    @click.option(
        "--pipeline-name",
        "-p",
        type=click.STRING,
        default=None,
        help="Show only served models that were deployed by the indicated "
        "pipeline.",
    )
    @click.option(
        "--model",
        "-m",
        type=click.STRING,
        default=None,
        help="Show only served model versions for the given model name.",
    )
    @click.option(
        "--model-version",
        "-v",
        type=click.STRING,
        default=None,
        help="Show only served model versions for the given model version.",
    )
    @click.option(
        "--flavor",
        "-f",
        type=click.STRING,
        default=None,
        help="Show only served model versions for the given model flavor.",
    )
    @click.option(
        "--running",
        is_flag=True,
        help="Show only model servers that are currently running.",
    )
    @click.pass_obj
    def list_models(
        model_deployer: "BaseModelDeployer",
        step: str | None,
        pipeline_name: str | None,
        pipeline_run_id: str | None,
        model: str | None,
        model_version: str | None,
        flavor: str | None,
        running: bool,
    ) -> None:
        """List of all served models within the model-deployer stack component.

        Args:
            model_deployer: The model-deployer stack component.
            step: Show only served models that were deployed by the indicated
                pipeline step.
            pipeline_run_id: Show only served models that were deployed by the
                indicated pipeline run.
            pipeline_name: Show only served models that were deployed by the
                indicated pipeline.
            model: Show only served model versions for the given model name.
            running: Show only model servers that are currently running.
            model_version: Show only served model versions for the given model
                version.
            flavor: Show only served model versions for the given model flavor.
        """
        services = model_deployer.find_model_server(
            running=running,
            pipeline_name=pipeline_name,
            pipeline_run_id=pipeline_run_id if pipeline_run_id else None,
            pipeline_step_name=step,
            model_name=model,
            model_version=model_version,
            flavor=flavor,
        )
        if services:
            pretty_print_model_deployer(
                services,
                model_deployer,
            )
        else:
            warning("No served models found.")

    @models.command("describe", help="Describe a specified served model.")
    @click.argument("served_model_uuid", type=click.STRING)
    @click.pass_obj
    def describe_model(
        model_deployer: "BaseModelDeployer", served_model_uuid: str
    ) -> None:
        """Describe a specified served model.

        Args:
            model_deployer: The model-deployer stack component.
            served_model_uuid: The UUID of the served model.
        """
        served_models = model_deployer.find_model_server(
            service_uuid=uuid.UUID(served_model_uuid)
        )
        if served_models:
            print_served_model_configuration(served_models[0], model_deployer)
            return
        warning(f"No model with uuid: '{served_model_uuid}' could be found.")
        return

    @models.command(
        "get-url",
        help="Return the prediction URL to a specified model server.",
    )
    @click.argument("served_model_uuid", type=click.STRING)
    @click.pass_obj
    def get_url(
        model_deployer: "BaseModelDeployer", served_model_uuid: str
    ) -> None:
        """Return the prediction URL to a specified model server.

        Args:
            model_deployer: The model-deployer stack component.
            served_model_uuid: The UUID of the served model.
        """
        served_models = model_deployer.find_model_server(
            service_uuid=uuid.UUID(served_model_uuid)
        )
        if served_models:
            try:
                prediction_url = model_deployer.get_model_server_info(
                    served_models[0]
                ).get("PREDICTION_URL")
                prediction_hostname = (
                    model_deployer.get_model_server_info(served_models[0]).get(
                        "PREDICTION_HOSTNAME"
                    )
                    or "No hostname specified for this service"
                )
                prediction_apis_urls = (
                    model_deployer.get_model_server_info(served_models[0]).get(
                        "PREDICTION_APIS_URLS"
                    )
                    or "No prediction APIs URLs specified for this service"
                )
                declare(
                    f"  Prediction URL of Served Model {served_model_uuid} "
                    f"is:\n"
                    f"  {prediction_url}\n"
                    f"  and the hostname is: {prediction_hostname}\n"
                    f"  and the prediction APIs URLs are: {prediction_apis_urls}\n"
                )
            except KeyError:
                warning("The deployed model instance has no 'prediction_url'.")
            return
        warning(f"No model with uuid: '{served_model_uuid}' could be found.")
        return

    @models.command("start", help="Start a specified model server.")
    @click.argument("served_model_uuid", type=click.STRING)
    @click.option(
        "--timeout",
        "-t",
        type=click.INT,
        default=300,
        help="Time in seconds to wait for the model to start. Set to 0 to "
        "return immediately after telling the server to start, without "
        "waiting for it to become fully active (default: 300s).",
    )
    @click.pass_obj
    def start_model_service(
        model_deployer: "BaseModelDeployer",
        served_model_uuid: str,
        timeout: int,
    ) -> None:
        """Start a specified model server.

        Args:
            model_deployer: The model-deployer stack component.
            served_model_uuid: The UUID of the served model.
            timeout: Time in seconds to wait for the model to start.
        """
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

    @models.command("stop", help="Stop a specified model server.")
    @click.argument("served_model_uuid", type=click.STRING)
    @click.option(
        "--timeout",
        "-t",
        type=click.INT,
        default=300,
        help="Time in seconds to wait for the model to start. Set to 0 to "
        "return immediately after telling the server to stop, without "
        "waiting for it to become inactive (default: 300s).",
    )
    @click.option(
        "--yes",
        "-y",
        "force",
        is_flag=True,
        help="Force the model server to stop. This will bypass any graceful "
        "shutdown processes and try to force the model server to stop "
        "immediately, if possible.",
    )
    @click.pass_obj
    def stop_model_service(
        model_deployer: "BaseModelDeployer",
        served_model_uuid: str,
        timeout: int,
        force: bool,
    ) -> None:
        """Stop a specified model server.

        Args:
            model_deployer: The model-deployer stack component.
            served_model_uuid: The UUID of the served model.
            timeout: Time in seconds to wait for the model to stop.
            force: Force the model server to stop.
        """
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

    @models.command("delete", help="Delete a specified model server.")
    @click.argument("served_model_uuid", type=click.STRING)
    @click.option(
        "--timeout",
        "-t",
        type=click.INT,
        default=300,
        help="Time in seconds to wait for the model to be deleted. Set to 0 to "
        "return immediately after stopping and deleting the model server, "
        "without waiting for it to release all allocated resources.",
    )
    @click.option(
        "--yes",
        "-y",
        "force",
        is_flag=True,
        help="Force the model server to stop and delete. This will bypass any "
        "graceful shutdown processes and try to force the model server to "
        "stop and delete immediately, if possible.",
    )
    @click.pass_obj
    def delete_model_service(
        model_deployer: "BaseModelDeployer",
        served_model_uuid: str,
        timeout: int,
        force: bool,
    ) -> None:
        """Delete a specified model server.

        Args:
            model_deployer: The model-deployer stack component.
            served_model_uuid: The UUID of the served model.
            timeout: Time in seconds to wait for the model to be deleted.
            force: Force the model server to stop and delete.
        """
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

    @models.command("logs", help="Show the logs for a model server.")
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
        tail: int | None,
        raw: bool,
    ) -> None:
        """Display the logs for a model server.

        Args:
            model_deployer: The model-deployer stack component.
            served_model_uuid: The UUID of the served model.
            follow: Continue to output new log data as it becomes available.
            tail: Only show the last NUM lines of log output.
            raw: Show raw log contents (don't pretty-print logs).
        """
        served_models = model_deployer.find_model_server(
            service_uuid=uuid.UUID(served_model_uuid)
        )
        if not served_models:
            warning(
                f"No model with uuid: '{served_model_uuid}' could be found."
            )
            return

        model_logs = model_deployer.get_model_server_logs(
            served_models[0].uuid, follow=follow, tail=tail
        )
        if model_logs:
            for line in model_logs:
                # don't pretty-print log lines that are already pretty-printed
                if raw or line.startswith("\x1b["):
                    console.print(line, markup=False)
                else:
                    try:
                        console.print(line)
                    except MarkupError:
                        console.print(line, markup=False)
