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
"""Harbor BaseEnvironment backed by ZenML's Sandbox stack component."""

import asyncio
import shlex
import tarfile
import tempfile
import uuid
from pathlib import Path

from harbor.environments.base import BaseEnvironment, ExecResult

from zenml.client import Client
from zenml.logger import get_logger
from zenml.sandboxes import BaseSandbox, BaseSandboxSettings, SandboxSession

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

    def _settings_override(
        self, sandbox: BaseSandbox
    ) -> BaseSandboxSettings | None:
        """Translate Harbor's task-level docker_image to a sandbox setting.

        Modal is the only sandbox flavor with an image knob today; switch
        to the active flavor's settings class when another flavor ships
        an image field.

        Args:
            sandbox: The active stack's Sandbox component.

        Returns:
            A Modal-flavor settings override carrying the task's
            docker_image, or None if the task didn't pin one.

        Raises:
            NotImplementedError: If the task pins a docker_image but the
                active sandbox flavor isn't Modal — Modal settings would
                fail confusingly on any other flavor.
        """
        image = self.task_env_config.docker_image
        if image is None:
            return None
        if sandbox.flavor != "modal":
            raise NotImplementedError(
                "Task-level docker_image is currently only supported "
                "with the Modal sandbox flavor (active flavor: "
                f"'{sandbox.flavor}')."
            )
        # Imported lazily so the bridge only needs the modal integration
        # when a task actually pins a docker_image.
        from zenml.integrations.modal.flavors import ModalSandboxSettings

        return ModalSandboxSettings(image=image)

    async def start(self, force_build: bool) -> None:
        """Open a SandboxSession on the active stack's Sandbox component.

        Args:
            force_build: Ignored. The Sandbox component decides whether
                an image needs building based on its own settings.

        Raises:
            RuntimeError: If no Sandbox component is registered on the
                active stack.
            NotImplementedError: If the task requires network isolation
                (allow_internet=false), which the bridge can't enforce.
        """
        sandbox = Client().active_stack.sandbox
        if sandbox is None:
            raise RuntimeError(
                "No Sandbox component is registered on the active stack. "
                "Register one with `zenml sandbox register ...` and add "
                "it to the active stack before running Harbor."
            )
        cfg = self.task_env_config
        if not cfg.allow_internet:
            raise NotImplementedError(
                "This Harbor task sets allow_internet=false, but the "
                "ZenML Sandbox bridge cannot enforce network isolation "
                "yet — refusing to run rather than silently skip it."
            )
        ignored = [
            name
            for name, value in (
                ("cpus", cfg.cpus),
                ("memory_mb", cfg.memory_mb),
                ("gpus", cfg.gpus),
            )
            if value is not None
        ]
        if ignored:
            logger.warning(
                "Harbor task env config sets %s, but the ZenML Sandbox "
                "bridge does not translate resource requests to the "
                "sandbox flavor yet; the values are ignored.",
                ", ".join(ignored),
            )
        settings = self._settings_override(sandbox)
        self._session = await asyncio.to_thread(
            sandbox.create_session, settings=settings
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
        await self.ensure_dirs(dirs)

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
            timeout_sec: Enforced inside the sandbox via coreutils
                ``timeout``, which kills the process and yields a genuine
                return code 124 on expiry.
            user: Not yet plumbed through the Sandbox interface.

        Returns:
            Harbor ExecResult with stdout, stderr, and return code.
        """
        if user is not None:
            logger.warning(
                "ZenMLSandboxEnvironment.exec ignoring user=%r — not "
                "supported by the Sandbox interface yet; the command "
                "runs as the container default user.",
                user,
            )
        merged_env = self._merge_env(env)
        session = self._live_session
        argv = (
            ["timeout", str(timeout_sec), "bash", "-c", command]
            if timeout_sec is not None
            else ["bash", "-c", command]
        )

        def _run() -> ExecResult:
            process = session.exec(argv, cwd=cwd, env=merged_env)
            out = process.collect()
            return ExecResult(
                stdout=out.stdout,
                stderr=out.stderr,
                return_code=out.exit_code,
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

    async def upload_dir(
        self, source_dir: Path | str, target_dir: str
    ) -> None:
        """Upload a directory tree via a single tar archive round-trip.

        Args:
            source_dir: Local directory to upload.
            target_dir: Destination directory inside the sandbox.

        Raises:
            RuntimeError: If extracting the archive inside the sandbox
                fails.
        """
        # SandboxSession only exposes upload_file. Tar locally,
        # upload once, untar in the session — per-file calls would be
        # slow on remote flavors.
        source = Path(source_dir)
        remote_tar = f"/tmp/.hb-{uuid.uuid4().hex}.tar.gz"  # nosec B108
        with tempfile.TemporaryDirectory() as host_tmp:
            archive = Path(host_tmp) / "upload.tar.gz"
            with tarfile.open(archive, "w:gz") as tf:
                tf.add(source, arcname=".")
            await asyncio.to_thread(
                self._live_session.upload_file, str(archive), remote_tar
            )
        q_target = shlex.quote(target_dir)
        q_tar = shlex.quote(remote_tar)
        result = await self.exec(
            f"mkdir -p {q_target} && tar xzf {q_tar} -C {q_target} "
            f"&& rm -f {q_tar}"
        )
        if result.return_code != 0:
            raise RuntimeError(
                f"Failed to extract upload archive: "
                f"{result.stderr or result.stdout}"
            )

    async def download_dir(
        self, source_dir: str, target_dir: Path | str
    ) -> None:
        """Download a directory tree via tar + ``download_file``."""
        await self.download_dir_with_exclusions(
            source_dir=source_dir, target_dir=target_dir, exclude=[]
        )
