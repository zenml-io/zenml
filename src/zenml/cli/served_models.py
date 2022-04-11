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

import click

from zenml.cli.cli import cli
from zenml.cli.utils import (
    declare,
    error,
    pretty_print_model_deployer,
    print_served_model_configuration,
    warning,
)
from zenml.enums import StackComponentType
from zenml.model_deployers import BaseModelDeployer
from zenml.repository import Repository


@cli.group()
@click.pass_context
def served_models(ctx: click.Context) -> None:
    """Served models that are deployed using the active model deployer in the
    stack

    Args:
        ctx: Click context to pass to all sub-commands
    """
    ctx.obj = Repository().active_stack.components.get(
        StackComponentType.MODEL_DEPLOYER, None
    )
    if ctx.obj is None:
        error(
            "No active model deployer found. Please add a model_deployer to "
            "your stack."
        )


@served_models.command("list")
@click.pass_obj
def list_models(model_deployer: "BaseModelDeployer") -> None:
    """Get a list of all served models within the model-deployer stack
    component.
    Args:
        model_deployer: Stack component that implements the interface to the
            underlying model deployer engine
    """
    pretty_print_model_deployer(model_deployer.find_model_server())


@served_models.command("describe")
@click.argument("served_model_uuid", type=click.STRING)
@click.pass_obj
def describe_model(
    model_deployer: "BaseModelDeployer", served_model_uuid: str
) -> None:
    """Describe a specified served model.

    Args:
        model_deployer: Stack component that implements the interface to the
            underlying model deployer engine
        served_model_uuid: UUID of a served model
    """

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
    """Return the prediction url to a specified served model.
    Args:
        model_deployer: Stack component that implements the interface to the
            underlying model deployer engine
        served_model_uuid: UUID of a served model
    """
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
    """Start a specified served model.
    Args:
        model_deployer: Stack component that implements the interface to the
            underlying model deployer engine
        served_model_uuid: UUID of a served model
    """

    served_models = model_deployer.find_model_server(
        service_uuid=uuid.UUID(served_model_uuid)
    )
    if served_models:
        model_deployer.start_model_server(
            served_models[0].uuid, timeout=timeout
        )
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
    "--force",
    is_flag=True,
    help="Force the model server to stop. This will bypass any graceful "
    "shutdown processes and try to force the model server to stop immediately, "
    "if possible.",
)
@click.pass_obj
def stop_model_service(
    model_deployer: "BaseModelDeployer",
    served_model_uuid: str,
    timeout: int,
    force: bool,
) -> None:
    """Stop a specified served model.
    Args:
        model_deployer: Stack component that implements the interface to the
            underlying model deployer engine
        served_model_uuid: UUID of a served model
    """

    served_models = model_deployer.find_model_server(
        service_uuid=uuid.UUID(served_model_uuid)
    )
    if served_models:
        model_deployer.stop_model_server(
            served_models[0].uuid, timeout=timeout, force=force
        )
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
    "--force",
    is_flag=True,
    help="Force the model server to stop and delete. This will bypass any "
    "graceful shutdown processes and try to force the model server to stop and "
    "delete immediately, if possible.",
)
@click.pass_obj
def delete_model_service(
    model_deployer: "BaseModelDeployer",
    served_model_uuid: str,
    timeout: int,
    force: bool,
) -> None:
    """Delete a specified served model.
    Args:
        model_deployer: Stack component that implements the interface to the
            underlying model deployer engine
        served_model_uuid: UUID of a served model
    """

    served_models = model_deployer.find_model_server(
        service_uuid=uuid.UUID(served_model_uuid)
    )
    if served_models:
        model_deployer.delete_model_server(
            served_models[0].uuid, timeout=timeout, force=force
        )
        return

    warning(f"No model with uuid: '{served_model_uuid}' could be found.")
    return
