"""Workload manager interface definition."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from uuid import UUID


class WorkloadManagerInterface(ABC):
    """Workload manager interface."""

    @abstractmethod
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
        """Run a Docker container.

        Args:
            workload_id: Workload ID.
            image: The Docker image to run.
            command: The command to run in the container.
            arguments: The arguments for the command.
            environment: The environment to set in the container.
            sync: If True, will wait until the container finished running before
                returning.
            timeout_in_seconds: Timeout in seconds to wait before cancelling
                the container. If set to 0 the container will run until it
                fails or finishes.
        """
        pass

    @abstractmethod
    def build_and_push_image(
        self,
        workload_id: UUID,
        dockerfile: str,
        image_name: str,
        sync: bool = True,
        timeout_in_seconds: int = 0,
    ) -> str:
        """Build and push a Docker image.

        Args:
            workload_id: Workload ID.
            dockerfile: The dockerfile content to build the image.
            image_name: The image repository and tag.
            sync: If True, will wait until the build finished before returning.
            timeout_in_seconds: Timeout in seconds to wait before cancelling
                the container. If set to 0 the container will run until it
                fails or finishes.

        Returns:
            The full image name including container registry.
        """
        pass

    @abstractmethod
    def delete_workload(self, workload_id: UUID) -> None:
        """Delete a workload.

        Args:
            workload_id: Workload ID.
        """
        pass

    @abstractmethod
    def get_logs(self, workload_id: UUID) -> str:
        """Get logs for a workload.

        Args:
            workload_id: Workload ID.

        Returns:
            The stored logs.
        """
        pass

    @abstractmethod
    def log(self, workload_id: UUID, message: str) -> None:
        """Log a message.

        Args:
            workload_id: Workload ID.
            message: The message to log.
        """
        pass
