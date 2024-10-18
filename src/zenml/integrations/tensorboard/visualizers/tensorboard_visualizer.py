#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Implementation of a TensorBoard visualizer step."""

import os
import sys
from typing import TYPE_CHECKING, Any, Optional

import psutil
from rich import print
from tensorboard import notebook  # type:ignore[import-untyped]
from tensorboard.manager import (  # type:ignore[import-untyped]
    TensorBoardInfo,
    get_all,
)

from zenml.client import Client
from zenml.enums import ArtifactType
from zenml.environment import Environment
from zenml.integrations.tensorboard.services.tensorboard_service import (
    TensorboardService,
    TensorboardServiceConfig,
)
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.models import StepRunResponse

logger = get_logger(__name__)


class TensorboardVisualizer:
    """The implementation of a TensorBoard Visualizer."""

    @classmethod
    def find_running_tensorboard_server(
        cls, logdir: str
    ) -> Optional[TensorBoardInfo]:
        """Find a local TensorBoard server instance.

        Finds when it is running for the supplied logdir location and return its
        TCP port.

        Args:
            logdir: The logdir location where the TensorBoard server is running.

        Returns:
            The TensorBoardInfo describing the running TensorBoard server or
            None if no server is running for the supplied logdir location.
        """
        for server in get_all():
            if (
                server.logdir == logdir
                and server.pid
                and psutil.pid_exists(server.pid)
            ):
                return server
        return None

    def visualize(
        self,
        object: "StepRunResponse",
        height: int = 800,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Start a TensorBoard server.

        Allows for the visualization of all models logged as artifacts by the
        indicated step. The server will monitor and display all the models
        logged by past and future step runs.

        Args:
            object: StepRunResponseModel fetched from get_step().
            height: Height of the generated visualization.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.
        """
        for output in object.outputs.values():
            for artifact_view in output:
                # filter out anything but model artifacts
                if artifact_view.type == ArtifactType.MODEL:
                    logdir = os.path.dirname(artifact_view.uri)

                    # first check if a TensorBoard server is already running for
                    # the same logdir location and use that one
                    running_server = self.find_running_tensorboard_server(
                        logdir
                    )
                    if running_server:
                        self.visualize_tensorboard(running_server.port, height)
                        return

                    if sys.platform == "win32":
                        # Daemon service functionality is currently not supported
                        # on Windows
                        print(
                            "You can run:\n"
                            f"[italic green]    tensorboard --logdir {logdir}"
                            "[/italic green]\n"
                            "...to visualize the TensorBoard logs for your trained model."
                        )
                    else:
                        # start a new TensorBoard server
                        service = TensorboardService(
                            TensorboardServiceConfig(
                                logdir=logdir,
                                name=f"zenml-tensorboard-{logdir}",
                            )
                        )
                        service.start(timeout=60)
                        if service.endpoint.status.port:
                            self.visualize_tensorboard(
                                service.endpoint.status.port, height
                            )
                    return

    def visualize_tensorboard(
        self,
        port: int,
        height: int,
    ) -> None:
        """Generate a visualization of a TensorBoard.

        Args:
            port: the TCP port where the TensorBoard server is listening for
                requests.
            height: Height of the generated visualization.
        """
        if Environment.in_notebook():
            notebook.display(port, height=height)
            return

        print(
            "You can visit:\n"
            f"[italic green]    http://localhost:{port}/[/italic green]\n"
            "...to visualize the TensorBoard logs for your trained model."
        )

    def stop(
        self,
        object: "StepRunResponse",
    ) -> None:
        """Stop the TensorBoard server previously started for a pipeline step.

        Args:
            object: StepRunResponseModel fetched from get_step().
        """
        for output in object.outputs.values():
            for artifact_view in output:
                # filter out anything but model artifacts
                if artifact_view.type == ArtifactType.MODEL:
                    logdir = os.path.dirname(artifact_view.uri)

                    # first check if a TensorBoard server is already running for
                    # the same logdir location and use that one
                    running_server = self.find_running_tensorboard_server(
                        logdir
                    )
                    if not running_server:
                        return

                    logger.debug(
                        "Stopping tensorboard server with PID '%d' ...",
                        running_server.pid,
                    )
                    try:
                        p = psutil.Process(running_server.pid)
                    except psutil.Error:
                        logger.error(
                            "Could not find process for PID '%d' ...",
                            running_server.pid,
                        )
                        continue
                    p.kill()
                    return


def get_step(pipeline_name: str, step_name: str) -> "StepRunResponse":
    """Get the StepRunResponseModel for the specified pipeline and step name.

    Args:
        pipeline_name: The name of the pipeline.
        step_name: The name of the step.

    Returns:
        The StepRunResponseModel for the specified pipeline and step name.

    Raises:
        RuntimeError: If the step is not found.
    """
    runs = Client().list_pipeline_runs(pipeline=pipeline_name)
    if runs.total == 0:
        raise RuntimeError(
            f"No pipeline runs for pipeline `{pipeline_name}` were found"
        )

    last_run = runs[0]
    if step_name not in last_run.steps:
        raise RuntimeError(
            f"No pipeline step with name `{step_name}` was found in "
            f"pipeline `{pipeline_name}`"
        )
    step = last_run.steps[step_name]
    return step


def visualize_tensorboard(pipeline_name: str, step_name: str) -> None:
    """Start a TensorBoard server.

    Allows for the visualization of all models logged as output by the named
    pipeline step. The server will monitor and display all the models logged by
    past and future step runs.

    Args:
        pipeline_name: the name of the pipeline
        step_name: pipeline step name
    """
    step = get_step(pipeline_name, step_name)
    TensorboardVisualizer().visualize(step)


def stop_tensorboard_server(pipeline_name: str, step_name: str) -> None:
    """Stop the TensorBoard server previously started for a pipeline step.

    Args:
        pipeline_name: the name of the pipeline
        step_name: pipeline step name
    """
    step = get_step(pipeline_name, step_name)
    TensorboardVisualizer().stop(step)
