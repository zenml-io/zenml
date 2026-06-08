"""Harbor BaseEnvironment backed by ZenML's Sandbox stack component."""

from __future__ import annotations

import asyncio
import shlex
import tarfile
import tempfile
import uuid
from pathlib import Path

from harbor.environments.base import BaseEnvironment, ExecResult
from harbor.environments.capabilities import EnvironmentCapabilities

from zenml.client import Client
from zenml.integrations.modal.flavors import ModalSandboxSettings
from zenml.logger import get_logger
from zenml.sandboxes import BaseSandboxSettings, SandboxSession

logger = get_logger(__name__)


class ZenMLSandboxEnvironment(BaseEnvironment):
    """A Harbor environment that delegates to the active stack's Sandbox."""

    _session: SandboxSession | None = None

    @property
    def _live_session(self) -> SandboxSession:
        """The open SandboxSession.

        Raises:
            RuntimeError: If the environment has not been started yet
                (or has been stopped).
        """
        if self._session is None:
            raise RuntimeError(
                "ZenMLSandboxEnvironment used before start() (or after "
                "stop()). Call await env.start(...) first."
            )
        return self._session

    @staticmethod
    def type() -> str:
        """The environment identifier surfaced to Harbor."""
        return "zenml-sandbox"

    def _validate_definition(self) -> None:
        """No-op: the Sandbox flavor owns the image, no Dockerfile needed."""

    @property
    def capabilities(self) -> EnvironmentCapabilities:
        """Capabilities reported to Harbor's preflight validators."""
        # Conservative no-GPU default: BaseSandbox doesn't yet expose a
        # supports_gpu capability, and claiming GPU support unconditionally
        # would let Harbor preflight a task that fails deep in the agent run.
        return EnvironmentCapabilities(gpus=False)

    def _settings_override(self) -> BaseSandboxSettings | None:
        """Translate Harbor's task-level docker_image to a sandbox setting.

        Returns:
            A Modal-flavor settings override carrying the task's
            docker_image, or None if the task didn't pin one. Hardcoded to
            Modal because that's the only sandbox flavor with an image
            knob today; switch to the active flavor's settings class when
            another flavor ships an image field.
        """
        image = self.task_env_config.docker_image
        if image is None:
            return None
        return ModalSandboxSettings(image=image)

    async def start(self, force_build: bool) -> None:
        """Open a SandboxSession on the active stack's Sandbox component.

        Args:
            force_build: Ignored. The Sandbox component decides whether
                an image needs building based on its own settings.

        Raises:
            RuntimeError: If no Sandbox component is registered on the
                active stack.
        """
        sandbox = Client().active_stack.sandbox
        if sandbox is None:
            raise RuntimeError(
                "No Sandbox component is registered on the active stack. "
                "Register one with `zenml sandbox register ...` and add "
                "it to the active stack before running Harbor."
            )
        settings = self._settings_override()
        self._session = await asyncio.to_thread(
            lambda: sandbox.create_session(settings=settings).__enter__()
        )
        logger.info(
            "ZenML Sandbox session %s started for Harbor trial %s",
            self._session.id,
            self.session_id,
        )
        try:
            await self._ensure_harbor_log_dirs()
        except Exception:
            # Tear down so a half-started env doesn't leak a paid Modal
            # sandbox up to its TTL.
            await self.stop(delete=True)
            raise

    async def _ensure_harbor_log_dirs(self) -> None:
        """Create the canonical Harbor log dirs the trial harness expects."""
        from harbor.models.trial.paths import EnvironmentPaths

        paths = EnvironmentPaths.for_os(self.task_env_config.os)
        dirs = [
            str(paths.agent_dir),
            str(paths.verifier_dir),
            str(paths.artifacts_dir),
        ]
        joined = " ".join(shlex.quote(d) for d in dirs)
        # chmod 1777 matches /tmp semantics so non-root agent and verifier
        # users can write to /logs/agent and /logs/verifier without one
        # trampling the other.
        await self.exec(f"mkdir -p {joined} && chmod 1777 {joined}")

    async def stop(self, delete: bool) -> None:
        """Close (or destroy) the underlying SandboxSession.

        Args:
            delete: If True, destroy the session so the flavor releases
                provider-side resources. Otherwise just close it.
        """
        if self._session is None:
            return
        session = self._session
        self._session = None
        await asyncio.to_thread(session.destroy if delete else session.close)

    async def exec(
        self,
        command: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout_sec: int | None = None,
        user: str | int | None = None,
    ) -> ExecResult:
        """Run a shell command in the open SandboxSession.

        Args:
            command: Shell string (Harbor uses redirects, subshells,
                pipelines) — wrapped in `bash -c`.
            cwd: Optional working directory inside the sandbox.
            env: Per-call env vars, merged on top of session env.
            timeout_sec: Host-side timeout enforced via asyncio.wait_for.
            user: Not yet plumbed through the Sandbox interface.

        Returns:
            Harbor ExecResult with stdout, stderr, and return code.
        """
        if user is not None:
            logger.debug(
                "ZenMLSandboxEnvironment.exec ignoring user=%r — not "
                "supported by the Sandbox interface yet.",
                user,
            )
        merged_env = self._merge_env(env)
        session = self._live_session

        def _run() -> ExecResult:
            process = session.exec(
                ["bash", "-c", command], cwd=cwd, env=merged_env
            )
            out = process.collect()
            return ExecResult(
                stdout=out.stdout,
                stderr=out.stderr,
                return_code=out.exit_code,
            )

        if timeout_sec is not None:
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(_run), timeout=timeout_sec
                )
            except asyncio.TimeoutError:
                return ExecResult(
                    stdout="",
                    stderr=f"command timed out after {timeout_sec}s",
                    return_code=124,
                )
        return await asyncio.to_thread(_run)

    async def upload_file(
        self, source_path: Path | str, target_path: str
    ) -> None:
        """Stream a local file into the SandboxSession."""
        await asyncio.to_thread(
            self._live_session.upload_file, str(source_path), target_path
        )

    async def download_file(
        self, source_path: str, target_path: Path | str
    ) -> None:
        """Stream a remote file out of the SandboxSession."""
        await asyncio.to_thread(
            self._live_session.download_file, source_path, str(target_path)
        )

    def _remote_tar_path(self, kind: str) -> str:
        """Per-call remote tar path, safe against concurrent calls."""
        # Per-call uuid keeps overlapping upload_dir calls from colliding
        # on the same archive name.
        return f"/tmp/.hb-{kind}-{uuid.uuid4().hex}.tar.gz"

    async def upload_dir(
        self, source_dir: Path | str, target_dir: str
    ) -> None:
        """Upload a directory tree via a single tar archive round-trip."""
        # SandboxSession only exposes upload_file. Tar locally,
        # upload once, untar in the session — per-file calls would be
        # slow on remote flavors.
        source = Path(source_dir)
        remote_tar = self._remote_tar_path("upload")
        with tempfile.TemporaryDirectory() as host_tmp:
            archive = Path(host_tmp) / "upload.tar.gz"
            with tarfile.open(archive, "w:gz") as tf:
                tf.add(source, arcname=".")
            await asyncio.to_thread(
                self._live_session.upload_file, str(archive), remote_tar
            )
        q_target = shlex.quote(target_dir)
        q_tar = shlex.quote(remote_tar)
        # Always remove the tar — failure inside `tar xzf` shouldn't
        # leak the archive into /tmp.
        await self.exec(
            f"mkdir -p {q_target}; "
            f"tar xzf {q_tar} -C {q_target}; "
            f"rc=$?; rm -f {q_tar}; exit $rc"
        )

    async def download_dir(
        self, source_dir: str, target_dir: Path | str
    ) -> None:
        """Download a directory tree via tar + ``download_file``."""
        remote_tar = self._remote_tar_path("download")
        await self.exec(
            f"tar czf {shlex.quote(remote_tar)} -C {shlex.quote(source_dir)} ."
        )
        target = Path(target_dir)
        target.mkdir(parents=True, exist_ok=True)
        try:
            with tempfile.TemporaryDirectory() as host_tmp:
                host_tar = Path(host_tmp) / "download.tar.gz"
                await asyncio.to_thread(
                    self._live_session.download_file,
                    remote_tar,
                    str(host_tar),
                )
                with tarfile.open(host_tar, "r:gz") as tf:
                    # ``filter="data"`` blocks unsafe tar entries
                    # (absolute paths, links escaping target). Requires
                    # Python 3.12+; the surrounding example pins 3.12.
                    tf.extractall(path=target, filter="data")
        finally:
            await self.exec(f"rm -f {shlex.quote(remote_tar)}")
