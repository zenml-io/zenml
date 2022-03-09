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

import os
import sys
from typing import Any, Optional, cast

import psutil
from rich import print
from tensorboard import notebook  # type: ignore [import]
from tensorboard.manager import (  # type: ignore [import]
    TensorBoardInfo,
    get_all,
)

from zenml.artifacts.model_artifact import ModelArtifact
from zenml.environment import Environment
from zenml.integrations.tensorflow.services.tensorboard_service import (
    TensorboardService,
    TensorboardServiceConfig,
)
from zenml.logger import get_logger
from zenml.post_execution import StepView
from zenml.repository import Repository
from zenml.visualizers import BaseStepVisualizer

logger = get_logger(__name__)


class TensorboardVisualizer(BaseStepVisualizer):
    """The implementation of a Whylogs Visualizer."""

    @classmethod
    def find_running_tensorboard_server(
        cls, logdir: str
    ) -> Optional[TensorBoardInfo]:
        """Find a local Tensorboard server instance running for the supplied
        logdir location and return its TCP port.

        Returns:
            The TensorBoardInfo describing the running Tensorboard server or
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
        object: StepView,
        *args: Any,
        height: int = 800,
        **kwargs: Any,
    ) -> None:
        """Start a Tensorboard server to visualize all models logged as
        artifacts by the indicated step. The server will monitor and display
        all the models logged by past and future step runs.

        Args:
            object: StepView fetched from run.get_step().
            height: Height of the generated visualization.
        """
        for _, artifact_view in object.outputs.items():
            # filter out anything but model artifacts
            if artifact_view.type == ModelArtifact.TYPE_NAME:
                logdir = os.path.dirname(artifact_view.uri)

                # first check if a Tensorboard server is already running for
                # the same logdir location and use that one
                running_server = self.find_running_tensorboard_server(logdir)
                if running_server:
                    self.visualize_tensorboard(running_server.port, height)
                    return

                if sys.platform == "win32":
                    # Daemon service functionality is currently not supported on Windows
                    print(
                        "You can run:\n"
                        f"[italic green]    tensorboard --logdir {logdir}"
                        "[/italic green]\n"
                        "...to visualize the Tensorboard logs for your trained model."
                    )
                else:
                    # start a new Tensorboard server
                    service = TensorboardService(
                        TensorboardServiceConfig(
                            logdir=logdir,
                        )
                    )
                    service.start(timeout=20)
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
        """Generate a visualization of a Tensorboard.

        Args:
            port: the TCP port where the Tensorboard server is listening for
                requests.
            height: Height of the generated visualization.
            logdir: The logdir location for the Tensorboard server.
        """
        if Environment.in_notebook():

            notebook.display(port, height=height)
            return

        print(
            "You can visit:\n"
            f"[italic green]    http://localhost:{port}/[/italic green]\n"
            "...to visualize the Tensorboard logs for your trained model."
        )

    def stop(
        self,
        object: StepView,
    ) -> None:
        """Stop the Tensorboard server previously started for a pipeline step.

        Args:
            object: StepView fetched from run.get_step().
        """
        for _, artifact_view in object.outputs.items():
            # filter out anything but model artifacts
            if artifact_view.type == ModelArtifact.TYPE_NAME:
                logdir = os.path.dirname(artifact_view.uri)

                # first check if a Tensorboard server is already running for
                # the same logdir location and use that one
                running_server = self.find_running_tensorboard_server(logdir)
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


def get_step(pipeline_name: str, step_name: str) -> StepView:
    """Get the StepView for the specified pipeline and step name.

    Args:
        pipeline_name: The name of the pipeline.
        step_name: The name of the step.

    Returns:
        The StepView for the specified pipeline and step name.
    """
    repo = Repository()
    pipeline = repo.get_pipeline(pipeline_name)
    if pipeline is None:
        raise RuntimeError(f"No pipeline with name `{pipeline_name}` was found")

    last_run = pipeline.runs[-1]
    step = last_run.get_step(name=step_name)
    if step is None:
        raise RuntimeError(
            f"No pipeline step with name `{step_name}` was found in "
            f"pipeline `{pipeline_name}`"
        )
    return cast(StepView, step)


def visualize_tensorboard(pipeline_name: str, step_name: str) -> None:
    """Start a Tensorboard server to visualize all models logged as output by
    the named pipeline step. The server will monitor and display all the models
    logged by past and future step runs.

    Args:
        pipeline_name: the name of the pipeline
        step_name: pipeline step name
    """
    step = get_step(pipeline_name, step_name)
    TensorboardVisualizer().visualize(step)


def stop_tensorboard_server(pipeline_name: str, step_name: str) -> None:
    """Stop the Tensorboard server previously started for a pipeline step.

    Args:
        pipeline_name: the name of the pipeline
        step_name: pipeline step name
    """
    step = get_step(pipeline_name, step_name)
    TensorboardVisualizer().stop(step)
