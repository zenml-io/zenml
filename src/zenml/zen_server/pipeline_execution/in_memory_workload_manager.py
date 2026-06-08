#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Workload manager interface definition."""

import subprocess
import sys
from typing import Dict, List, Optional
from uuid import UUID

from zenml.logger import get_logger
from zenml.zen_server.pipeline_execution.workload_manager_interface import (
    WorkloadManagerInterface,
    WorkloadType,
)

logger = get_logger(__name__)


class InMemoryWorkloadManager(WorkloadManagerInterface):
    """In-memory workload manager."""

    def run(
        self,
        workload_id: UUID,
        image: str,
        command: List[str],
        arguments: List[str],
        environment: Optional[Dict[str, str]] = None,
        sync: bool = True,
        timeout_in_seconds: int = 0,
    ) -> None:
        """Run a workload.

        Args:
            workload_id: The ID of the workload.
            image: The image to run.
            command: The command to run.
            arguments: The arguments to pass to the command.
            environment: The environment variables to set.
            sync: Whether to wait for the workload to finish.
            timeout_in_seconds: The timeout in seconds.

        Raises:
            RuntimeError: If the workload fails to run.
        """
        command_to_run = [*command, *arguments]
        command_to_run[0] = sys.executable

        if sync:
            result = subprocess.run(
                command_to_run,
                env=environment,
                timeout=timeout_in_seconds or None,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                logger.error(result.stderr)
                raise RuntimeError(
                    f"Workload {workload_id} failed with exit code "
                    f"{result.returncode}."
                )
        else:
            subprocess.Popen(command_to_run, env=environment)

    def build_and_push_image(
        self,
        workload_id: UUID,
        workload_type: WorkloadType,
        dockerfile: str,
        image_name: str,
        sync: bool = True,
        timeout_in_seconds: int = 0,
    ) -> str:
        """Build and push a Docker image.

        Args:
            workload_id: The ID of the workload.
            workload_type: The type of workload.
            dockerfile: The dockerfile to build.
            image_name: The name of the image to push.
            sync: Whether to wait for the build to finish.
            timeout_in_seconds: The timeout in seconds.

        Returns:
            Empty string.
        """
        return ""

    def delete_workload(self, workload_id: UUID) -> None:
        """Delete a workload.

        Args:
            workload_id: The ID of the workload.
        """
        pass

    def get_logs(self, workload_id: UUID) -> str:
        """Get logs for a workload.

        Args:
            workload_id: The ID of the workload.

        Returns:
            The logs for the workload.
        """
        return ""

    def log(self, workload_id: UUID, message: str) -> None:
        """Log a message.

        Args:
            workload_id: The ID of the workload.
            message: The message to log.
        """
        pass
