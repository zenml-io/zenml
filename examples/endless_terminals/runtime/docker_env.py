"""Bounded Docker terminal and independent, clean-runtime final-state grading.

The agent runs as root inside a resource-limited, network-disabled container.
This is process isolation, not a security boundary against kernel/Docker exploits.
Only /home/user is transferred to grading; tasks requiring changes elsewhere are
unsupported. Shell protocol tampering is reported as a failed command/deadline.
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import selectors
import shlex
import shutil
import subprocess
import tarfile
import time
import uuid
from pathlib import Path, PurePosixPath

from .docker_command import MAX_OUTPUT, DockerCommand
from .environment import MAX_ARCHIVE


class DockerEnvironment:
    """Preserve Bash state across commands, then grade an isolated home snapshot."""

    def __init__(
        self,
        image_id: str,
        command_timeout: float = 10,
        episode_timeout: float = 1200,
    ) -> None:
        """Configure a bounded terminal using an existing immutable image.

        Args:
            image_id: Immutable local Docker image ID.
            command_timeout: Maximum seconds per command.
            episode_timeout: Maximum seconds for agent interaction.

        Raises:
            ValueError: Image ID or timeouts are invalid.
            RuntimeError: Docker is not available on PATH.
        """
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
            raise ValueError("Use a qualified immutable local image ID")
        if command_timeout <= 0 or episode_timeout <= 0:
            raise ValueError("Timeouts must be positive")
        self.image_id = image_id
        self.provenance = {"backend": "docker", "image_id": image_id}
        self.command_timeout = command_timeout
        self.episode_timeout = episode_timeout
        docker = shutil.which("docker")
        if docker is None:
            raise RuntimeError("Docker CLI is required on PATH")
        self.docker: str = docker
        self.run_docker = DockerCommand(self.docker)
        self.container_id: str | None = None
        self.shell: subprocess.Popen[bytes] | None = None
        self.deadline = 0.0
        self.closed = False
        self.stopped = False
        self._snapshot: bytes | None = None
        self._containers: list[str] = []

    def create_container(self) -> str:
        """Create and start a tracked container with no network or image pull.

        Returns:
            Unique container name registered for cleanup.
        """
        name = "endless-adapter-" + uuid.uuid4().hex
        # Register the name before create so interrupted/ambiguous creates clean up.
        self._containers.append(name)
        self.run_docker(
            [
                "create",
                "--pull=never",
                "--name",
                name,
                "--platform",
                "linux/amd64",
                "--network",
                "none",
                "--cpus",
                "1",
                "--memory",
                "1g",
                "--memory-swap",
                "1g",
                "--pids-limit",
                "128",
                "--cap-drop",
                "ALL",
                "--cap-add",
                "DAC_OVERRIDE",
                "--cap-add",
                "FOWNER",
                "--cap-add",
                "CHOWN",
                "--security-opt",
                "no-new-privileges",
                "--workdir",
                "/home/user",
                "--entrypoint",
                "/bin/sleep",
                self.image_id,
                "infinity",
            ]
        )
        self.run_docker(["start", name])
        return name

    def __enter__(self) -> DockerEnvironment:
        """Start the persistent shell.

        Returns:
            This active environment.

        Raises:
            RuntimeError: Shell initialization or container cleanup fails.
            BaseException: Startup errors or interruptions propagate after cleanup.
        """
        try:
            self.container_id = self.create_container()
            self.deadline = time.monotonic() + self.episode_timeout
            self.shell = subprocess.Popen(
                [
                    self.docker,
                    "exec",
                    "-i",
                    self.container_id,
                    "/bin/bash",
                    "--noprofile",
                    "--norc",
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            ok, output = self.execute(
                "export HOME=/home/user; cd /home/user; set -o pipefail"
            )
            if not ok:
                raise RuntimeError("Shell initialization failed: " + output)
            return self
        except BaseException:
            self.close()
            raise

    def execute(self, command: str) -> tuple[bool, str]:
        """Run a command while retaining shell cwd and variables.

        Args:
            command: Shell command from the model.

        Returns:
            Success flag and bounded terminal output.
        """
        if self.stopped or self.shell is None or self.shell.poll() is not None:
            return False, "Terminal is stopped"
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            self._stop()
            return False, "Episode deadline exceeded"
        if len(command.encode()) > MAX_OUTPUT:
            self._stop()
            return False, "Command size limit exceeded; terminal stopped"
        token = "ENDLESS_" + uuid.uuid4().hex
        marker = re.compile(rb"\x1e" + token.encode() + rb":([0-9]+)\x1f\n")
        script = (
            "eval "
            + shlex.quote(command)
            + "\nbuiltin printf '\\036"
            + token
            + ':%s\\037\\n\' "$?"\n'
        )
        output = bytearray()
        end = time.monotonic() + min(self.command_timeout, remaining)
        try:
            assert (
                self.shell.stdin is not None and self.shell.stdout is not None
            )
            pending = memoryview(script.encode())
            os.set_blocking(self.shell.stdin.fileno(), False)
            with selectors.DefaultSelector() as selector:
                selector.register(self.shell.stdout, selectors.EVENT_READ)
                selector.register(self.shell.stdin, selectors.EVENT_WRITE)
                while time.monotonic() < end:
                    events = selector.select(max(0, end - time.monotonic()))
                    if not events:
                        break
                    if any(
                        key.fileobj is self.shell.stdin for key, _ in events
                    ):
                        written = os.write(
                            self.shell.stdin.fileno(), pending[:4096]
                        )
                        pending = pending[written:]
                        if not pending:
                            selector.unregister(self.shell.stdin)
                    if not any(
                        key.fileobj is self.shell.stdout for key, _ in events
                    ):
                        continue
                    chunk = os.read(self.shell.stdout.fileno(), 65536)
                    if not chunk:
                        self._stop()
                        return False, output.decode(
                            errors="replace"
                        ) + "\nTerminal exited"
                    output.extend(chunk)
                    match = marker.search(output)
                    if match and match.start() <= MAX_OUTPUT:
                        return int(match[1]) == 0, output[
                            : match.start()
                        ].decode(errors="replace")
                    if len(output) > MAX_OUTPUT:
                        self._stop()
                        return False, output[:MAX_OUTPUT].decode(
                            errors="replace"
                        ) + "\nOutput limit exceeded; terminal stopped"
            self._stop()
            return False, output.decode(
                errors="replace"
            ) + "\nCommand or episode deadline exceeded; terminal stopped"
        except (BrokenPipeError, OSError):
            self._stop()
            return False, "Terminal pipe closed"

    def _stop(self) -> None:
        if self.container_id and not self.stopped:
            self.run_docker(["kill", self.container_id], check=False)
            self.run_docker(["stop", "-t", "0", self.container_id])
            self.stopped = True
        if self.shell:
            if self.shell.poll() is None:
                self.shell.kill()
            self.shell.wait(timeout=5)
            for stream in (self.shell.stdin, self.shell.stdout):
                if stream:
                    stream.close()

    def home_snapshot(self) -> bytes:
        """Stop task processes and obtain a bounded home archive.

        Returns:
            Docker archive bytes for the task home directory.

        Raises:
            RuntimeError: No container was started.
        """
        self._stop()
        if self._snapshot is None:
            if not self.container_id:
                raise RuntimeError("Environment has not started")
            self._snapshot = self.run_docker(
                ["cp", f"{self.container_id}:/home/user/.", "-"],
                limit=MAX_ARCHIVE,
            ).stdout
        return self._snapshot

    def source_hash(self, path: str) -> str:
        """Hash source bytes without executing any agent-modifiable program.

        Before grading, copy only this path so obtaining initial hashes does not
        stop the persistent shell. Symlinks and non-regular files are rejected.

        Args:
            path: Absolute protected file path under /home/user.

        Returns:
            SHA-256 of the file bytes.

        Raises:
            ValueError: Path is outside the home or not a regular file.
            RuntimeError: Environment has not started.
        """
        if (
            not path.startswith("/home/user/")
            or ".." in PurePosixPath(path).parts
        ):
            raise ValueError("Protected sources must be inside /home/user")
        if not self.container_id:
            raise RuntimeError("Environment has not started")
        archive = self.run_docker(
            ["cp", f"{self.container_id}:{path}", "-"], limit=MAX_ARCHIVE
        ).stdout
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            members = tar.getmembers()
            if len(members) != 1 or not members[0].isfile():
                raise ValueError("Protected source is not a regular file")
            source = tar.extractfile(members[0])
            assert source is not None
            return hashlib.sha256(source.read()).hexdigest()

    def remove_container(self, name: str) -> None:
        """Forget a successfully removed container.

        Args:
            name: Container previously removed by the verifier.
        """
        self._containers.remove(name)

    def verify_snapshot(
        self, archive: bytes, test_path: Path
    ) -> tuple[int, str, bytes]:
        """Run hidden tests in a fresh container with validated task data.

        Args:
            archive: Validated task-home archive.
            test_path: Trusted verifier source.

        Returns:
            Pytest exit code, output, and JUnit XML bytes.
        """
        from .docker_grading import verify_snapshot

        return verify_snapshot(self, archive, test_path)

    def close(self) -> None:
        """Remove only containers created by this instance, including failed starts.

        Raises:
            RuntimeError: One or more owned containers could not be removed.
        """
        failures = []
        for name in list(self._containers):
            try:
                self.run_docker(["rm", "-f", name])
                self._containers.remove(name)
            except Exception as exc:
                failures.append(str(exc))
        if self.shell:
            if self.shell.poll() is None:
                self.shell.kill()
            self.shell.wait(timeout=5)
            for stream in (self.shell.stdin, self.shell.stdout):
                if stream:
                    stream.close()
        self.closed = not self._containers
        if failures:
            raise RuntimeError(
                "Container cleanup failed: " + "; ".join(failures)
            )

    def __exit__(self, *_args: object) -> None:
        """Remove containers on context exit.

        Args:
            *_args: Context exception details.
        """
        self.close()
