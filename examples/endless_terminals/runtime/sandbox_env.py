"""Run terminal tasks through isolated canonical ZenML sandbox sessions."""

from __future__ import annotations

import hashlib
import io
import re
import shlex
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

from zenml.integrations.kubernetes.sandboxes.kubernetes_sandbox import (
    KubernetesSandbox,
)
from zenml.integrations.modal.sandboxes.modal_sandbox import ModalSandbox
from zenml.sandboxes.base import BaseSandbox
from zenml.sandboxes.process import SandboxOutput
from zenml.sandboxes.session import SandboxSession

from .environment import MAX_ARCHIVE
from .sandbox_shell import SandboxShell
from .sandbox_workspace import SandboxRuntimeConfig as SandboxRuntimeConfig
from .sandbox_workspace import SandboxWorkspace, bounded_call

_ARCHIVE = r"""
import os, stat, tarfile
from pathlib import Path
root = Path(ROOT)
paths = [root]
size = 0
for directory, dirs, files in os.walk(root, followlinks=False):
    for name in dirs + files:
        path = Path(directory) / name
        info = path.lstat()
        if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
            raise ValueError('Workspace contains a non-regular entry')
        size += info.st_size if stat.S_ISREG(info.st_mode) else 0
        if size > 64 * 1024 * 1024 or len(paths) >= 20000:
            raise ValueError('Workspace export limit exceeded')
        paths.append(path)
with tarfile.open('/tmp/endless-home.tar', 'w', dereference=True) as tar:
    for path in paths:
        tar.add(path, arcname='.' if path == root else str(path.relative_to(root)), recursive=False)
if Path('/tmp/endless-home.tar').stat().st_size > 64 * 1024 * 1024:
    raise ValueError('Workspace archive limit exceeded')
"""


class SandboxEnvironment:
    """Separate model execution, persisted home data, and trusted verification."""

    def __init__(
        self,
        image_id: str,
        config: SandboxRuntimeConfig,
        command_timeout: float = 10,
        episode_timeout: float = 180,
        sandbox: KubernetesSandbox | ModalSandbox | None = None,
    ) -> None:
        """Configure a task environment without allocating resources.

        Args:
            image_id: Task image pinned by registry digest.
            config: Workspace and helper-image settings.
            command_timeout: Agent command budget.
            episode_timeout: Agent interaction budget.
            sandbox: Optional injected canonical Kubernetes or Modal sandbox component.

        Raises:
            ValueError: Image or budgets are invalid.
            TypeError: The selected component is not a supported sandbox.
        """
        if not re.fullmatch(r"[^\s]+@sha256:[0-9a-f]{64}", image_id):
            raise ValueError(
                "Task image requires an immutable registry digest"
            )
        if command_timeout <= 0 or episode_timeout <= 0:
            raise ValueError("Episode and command budgets must be positive")
        selected_sandbox: BaseSandbox | None = sandbox
        if selected_sandbox is None:
            from zenml.client import Client

            selected_sandbox = Client().active_stack.sandbox
        if not isinstance(selected_sandbox, (KubernetesSandbox, ModalSandbox)):
            raise TypeError(
                "Select a KubernetesSandbox or ModalSandbox in the active ZenML stack"
            )
        self.image_id = image_id
        self.config = config
        self.command_timeout = command_timeout
        self.episode_timeout = episode_timeout
        from .modal_workspace import ModalWorkspace

        self.workspace: SandboxWorkspace | ModalWorkspace
        if isinstance(selected_sandbox, ModalSandbox):
            self.workspace = ModalWorkspace(selected_sandbox, config)
        else:
            self.workspace = SandboxWorkspace(selected_sandbox, config)
        self.provenance = self.workspace.provenance
        self.container_id: str | None = None
        self.stopped = False
        self.closed = False
        self.agent: SandboxSession | None = None
        self.shell: SandboxShell | None = None
        self.initial: bytes | None = None
        self.final: bytes | None = None

    def _exec(
        self, session: SandboxSession, command: str, timeout: float = 60
    ) -> SandboxOutput:
        try:
            process = bounded_call(
                lambda: session.exec(["sh", "-c", command]), timeout
            )
            return bounded_call(
                lambda: process.collect(max_chars=256 * 1024), timeout
            )
        except BaseException:
            self.workspace.destroy_session(session)
            raise

    def _checked(
        self, session: SandboxSession, command: str, timeout: float = 60
    ) -> str:
        output = self._exec(session, command, timeout)
        if output.exit_code:
            raise RuntimeError(
                f"Trusted sandbox command failed: {output.stderr[:2000]}"
            )
        return output.stdout

    def _python(
        self, session: SandboxSession, source: str, timeout: float = 60
    ) -> str:
        return self._checked(
            session, "python3 -I -c " + shlex.quote(source), timeout
        )

    def _download(
        self, session: SandboxSession, remote: str, limit: int
    ) -> bytes:
        self._python(
            session,
            f"from pathlib import Path; assert Path({remote!r}).stat().st_size <= {limit}",
        )
        with tempfile.TemporaryDirectory() as directory:
            local = Path(directory) / "download"
            try:
                bounded_call(
                    lambda: session.download_file(remote, str(local)), 60
                )
            except BaseException:
                self.workspace.destroy_session(session)
                raise
            data = local.read_bytes()
            if len(data) > limit:
                raise ValueError(
                    "Downloaded sandbox artifact exceeds size limit"
                )
            return data

    def _upload(
        self, session: SandboxSession, data: bytes, remote: str
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            local = Path(directory) / "upload"
            local.write_bytes(data)
            try:
                bounded_call(
                    lambda: session.upload_file(str(local), remote), 60
                )
            except BaseException:
                self.workspace.destroy_session(session)
                raise

    def _archive(self, session: SandboxSession, root: str) -> bytes:
        self._python(session, _ARCHIVE.replace("ROOT", repr(root)))
        return self._download(session, "/tmp/endless-home.tar", MAX_ARCHIVE)

    def _new(
        self, mount: str | None, readonly: bool = False
    ) -> SandboxSession:
        session = self.workspace.create_session(self.image_id, mount, readonly)
        if isinstance(self.workspace, SandboxWorkspace):
            self._python(
                session,
                "from pathlib import Path; "
                "assert all(not(int((p/'flags').read_text(),16)&1) "
                "for p in Path('/sys/class/net').iterdir() if p.name!='lo'), 'Pod networking remains enabled'",
            )
        else:
            self._python(
                session,
                "import socket\n"
                "try:\n"
                "    connection = socket.create_connection(('1.1.1.1', 443), timeout=2)\n"
                "except OSError:\n"
                "    pass\n"
                "else:\n"
                "    connection.close()\n"
                "    raise RuntimeError('Modal task networking remains enabled')\n",
            )
        return session

    def __enter__(self) -> SandboxEnvironment:
        """Seed task data before exposing the volume to the agent.

        Returns:
            Prepared terminal environment.

        Raises:
            BaseException: Setup fails; cleanup is attempted first.
        """
        try:
            self.workspace.create_volume()
            seed = self._new("/workspace")
            self.initial = self._archive(seed, "/home/user")
            self._checked(
                seed,
                "mkdir /workspace/home && cp -a /home/user/. /workspace/home/",
            )
            self.workspace.destroy_session(seed)
            self.agent = self._new("/home/user")
            self.container_id = self.agent.id
            self.shell = SandboxShell(
                self.agent, self.command_timeout, self.episode_timeout
            )
            self.shell.start()
            return self
        except BaseException:
            self.close()
            raise

    def execute(self, command: str) -> tuple[bool, str]:
        """Execute through the persistent public-API shell adapter.

        Args:
            command: Model-supplied command.

        Returns:
            Success flag and bounded terminal output.
        """
        if self.stopped or self.shell is None:
            return False, "Terminal is stopped"
        result = self.shell.execute(command)
        if self.shell.stopped:
            self.stopped = True
            if self.agent:
                self.workspace.destroy_session(self.agent)
                self.agent = None
        return result

    def home_snapshot(self) -> bytes:
        """Terminate agent processes before a trusted container reads the workspace.

        Returns:
            Bounded home-directory archive.
        """
        if self.final is not None:
            return self.final
        if self.shell:
            self.shell.close()
        if self.agent:
            self.workspace.destroy_session(self.agent)
            self.agent = None
        self.stopped = True
        reader = self._new("/workspace", readonly=True)
        try:
            self.final = self._archive(reader, "/workspace/home")
        finally:
            self.workspace.destroy_session(reader)
        return self.final

    def source_hash(self, path: str) -> str:
        """Hash trusted initial or final archive bytes without using agent binaries.

        Args:
            path: Protected file below /home/user.

        Returns:
            SHA-256 of the regular source file.

        Raises:
            ValueError: The source is missing, unsafe, or not a regular file.
        """
        absolute = PurePosixPath(path)
        if not path.startswith("/home/user/") or ".." in absolute.parts:
            raise ValueError("Protected source must be inside /home/user")
        archive = self.home_snapshot() if self.stopped else self.initial
        if archive is None:
            raise ValueError("Environment has not been initialized")
        relative = str(absolute.relative_to("/home/user"))
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            matches = [
                m for m in tar if str(PurePosixPath(m.name)) == relative
            ]
            if len(matches) != 1 or not matches[0].isfile():
                raise ValueError(
                    "Protected source is absent or not a regular file"
                )
            file = tar.extractfile(matches[0])
            assert file is not None
            return hashlib.sha256(file.read()).hexdigest()

    def verify_snapshot(
        self, archive: bytes, test_path: Path
    ) -> tuple[int, str, bytes]:
        """Run trusted tests in a clean image after validating all archive members.

        Args:
            archive: Home archive already audited by the generic grader.
            test_path: Trusted final-state test on the controller.

        Returns:
            Verifier exit code, combined output, and JUnit report bytes.

        Raises:
            ValueError: The archive contains unsafe entries or exceeds limits.
        """
        if len(archive) > MAX_ARCHIVE:
            raise ValueError("Archive exceeds size limit")
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            for member in tar:
                path = PurePosixPath(member.name)
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or not (member.isfile() or member.isdir())
                ):
                    raise ValueError("Unsafe workspace archive member")
        verifier = self._new(None)
        try:
            self._upload(verifier, archive, "/tmp/home.tar")
            self._upload(
                verifier,
                test_path.read_bytes(),
                "/opt/endless-grader/test_final_state.py",
            )
            self._checked(
                verifier,
                "rm -rf /home/user && mkdir -p /home/user && tar -xf /tmp/home.tar -C /home/user",
            )
            result = self._exec(
                verifier,
                "cd /opt/endless-grader && python3 -I -m pytest -q -p no:cacheprovider test_final_state.py --junitxml=/tmp/result.xml",
                120,
            )
            junit = self._download(verifier, "/tmp/result.xml", 1024 * 1024)
            return result.exit_code, result.stdout + result.stderr, junit
        finally:
            self.workspace.destroy_session(verifier)

    def close(self) -> None:
        """Destroy all owned sessions before removing the temporary workspace."""
        try:
            if self.shell:
                self.shell.close()
        finally:
            self.workspace.close()
            self.closed = True
            self.stopped = True

    def __exit__(self, *_args: object) -> None:
        """Clean up this environment on context exit.

        Args:
            _args: Exception type, value, and traceback supplied by the context manager.
        """
        self.close()
