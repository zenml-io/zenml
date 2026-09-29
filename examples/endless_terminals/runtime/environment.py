"""Shared terminal and trusted-verifier contract for episode execution."""

from pathlib import Path
from typing import Any, Protocol

MAX_ARCHIVE = 64 * 1024 * 1024


class TerminalEnvironment(Protocol):
    """Execute commands and export task data only after stopping the agent."""

    container_id: str | None
    stopped: bool
    closed: bool
    provenance: dict[str, Any]

    def __enter__(self) -> "TerminalEnvironment":
        """Start the task environment.

        Returns:
            Active environment.
        """
        ...

    def __exit__(self, *_args: Any) -> None:
        """Remove resources created for the episode.

        Args:
            *_args: Context exception details.
        """
        ...

    def execute(self, command: str) -> tuple[bool, str]:
        """Execute a command in the persistent shell.

        Args:
            command: Shell command.

        Returns:
            Success flag and bounded output.
        """
        ...

    def home_snapshot(self) -> bytes:
        """Stop the agent and export its home using a trusted reader.

        Returns:
            Bounded tar archive of the task home.
        """
        ...

    def source_hash(self, path: str) -> str:
        """Hash a regular task input through the trusted reader.

        Args:
            path: Absolute file path inside the task home.

        Returns:
            SHA-256 digest of the file bytes.
        """
        ...

    def verify_snapshot(
        self, archive: bytes, test_path: Path
    ) -> tuple[int, str, bytes]:
        """Run hidden tests in a fresh image containing the validated archive.

        Args:
            archive: Validated task-home archive.
            test_path: Trusted test file, never supplied to the agent.

        Returns:
            Pytest exit code, output, and JUnit XML bytes.
        """
        ...
