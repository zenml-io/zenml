"""Workload manager interface definition."""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Type
from uuid import UUID

from zenml.utils import source_utils
from zenml.zen_server.utils import server_config


class WorkloadManagerInterface(ABC):
    """Workload manager interface."""

    @abstractmethod
    def __init__(self, workload_id: UUID) -> None:
        """Initialize the workload manager.

        Args:
            workload_id: Workload ID.
        """
        pass

    @abstractmethod
    def run(
        self,
        image: str,
        command: List[str],
        arguments: List[str],
        environment: Optional[Dict[str, str]] = None,
        sync: bool = True,
        timeout_in_seconds: int = 0,
    ) -> None:
        """Run a Docker container.

        Args:
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
        dockerfile: str,
        image_name: str,
        sync: bool = True,
        timeout_in_seconds: int = 0,
    ) -> str:
        """Build and push a Docker image.

        Args:
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
    def get_logs(self) -> str:
        """Get logs for the workload ID used to initialize the workload manager.

        Returns:
            The stored logs.
        """
        pass

    @abstractmethod
    def log(self, message: str) -> None:
        """Log a message.

        Args:
            message: The message to log.
        """
        pass


def get_workload_manager(workload_id: UUID) -> WorkloadManagerInterface:
    """Get a workload manager for the given workload ID.

    Args:
        workload_id: The workload ID.

    Raises:
        RuntimeError: If no workload manager is configured.

    Returns:
        The workload manager instance.
    """
    if source := server_config().workload_manager_implementation_source:
        workload_manager_class: Type[
            WorkloadManagerInterface
        ] = source_utils.load_and_validate_class(
            source=source, expected_class=WorkloadManagerInterface
        )
        return workload_manager_class(workload_id=workload_id)
    else:
        raise RuntimeError("Workload manager not enabled.")
