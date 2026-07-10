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
"""Harbor BaseEnvironment backed by ZenML's Sandbox stack component.

Known limitations, preserved deliberately rather than papered over:
Harbor resource requests (``cpus``/``memory_mb``/``gpus``) are not
translated to sandbox settings; tasks requiring network isolation
(``allow_internet=false``) are refused; ``exec(user=...)`` is ignored;
task-level ``docker_image`` overrides are Modal-only.
"""

import asyncio
import shlex
import tarfile
import tempfile
import uuid
from pathlib import Path
from typing import NamedTuple

from harbor.environments.base import BaseEnvironment, ExecResult

from zenml.client import Client
from zenml.logger import get_logger
from zenml.sandboxes import BaseSandbox, BaseSandboxSettings, SandboxSession

logger = get_logger(__name__)


class SandboxProvenance(NamedTuple):
    """Sandbox facts only the bridge knows at trial runtime."""

    flavor: str
    docker_image: str | None


# Resolved-sandbox facts per environment session, keyed by Harbor's
# session_id (== the trial name for the main trial environment; separate
# verifier environments get a derived id). The bridge is the only party
# that knows which flavor/image actually backed a trial — reconstructing
# the image from the run's stack config gives wrong answers for tasks
# that pin a ``docker_image`` override.
_session_provenance: dict[str, SandboxProvenance] = {}


def drain_session_provenance() -> dict[str, SandboxProvenance]:
    """Take and reset every recorded session provenance entry.

    The shard runner drains once right after ``job.run()`` and joins
    entries to trial results by session id. Draining (rather than
    per-key pops plus a separate clear) hands over the complete snapshot
    and resets the registry in one step, so entries the join never
    touches (e.g. separate verifier sessions) can't accumulate across
    shards in a long-lived process — even if result processing raises.

    Returns:
        The recorded provenance entries, keyed by session id.
    """
    drained = dict(_session_provenance)
    _session_provenance.clear()
    return drained


class ZenMLSandboxEnvironment(BaseEnvironment):
    """A Harbor environment that delegates to the active stack's Sandbox."""

    _session: SandboxSession | None = None
    _start_failure: BaseException | None = None

    @property
    def _live_session(self) -> SandboxSession:
        """The open SandboxSession.

        Returns:
            The open sandbox session.

        Raises:
            RuntimeError: If the environment has not been started yet
                (or has been stopped). If ``start()`` itself failed, the
                message carries that root cause — Harbor's cleanup still
                calls ``exec()``/log download on the never-started
                environment, and those follow-up errors would otherwise
                bury the real failure.
        """
        if self._session is None:
            if self._start_failure is not None:
                raise RuntimeError(
                    "ZenMLSandboxEnvironment has no open session because "
                    f"start() failed ({self._describe_start_failure()}) — "
                    "any further errors from this environment (e.g. "
                    "Harbor's post-failure log download) are fallout of "
                    "that failure."
                ) from self._start_failure
            raise RuntimeError(
                "ZenMLSandboxEnvironment used before start() (or after "
                "stop()). Call await env.start(...) first."
            )
        return self._session

    def _describe_start_failure(self) -> str:
        """One-line root cause of the recorded start failure.

        Returns:
            A human-readable description of the failure.
        """
        failure = self._start_failure
        if isinstance(failure, asyncio.CancelledError):
            # str(CancelledError()) is empty, and cancellation here
            # almost always means Harbor's environment build/start
            # timeout expired.
            return (
                "start() was cancelled, most likely by Harbor's "
                "environment build/start timeout"
            )
        return f"{type(failure).__name__}: {failure}"

    @staticmethod
    def type() -> str:
        """The environment identifier surfaced to Harbor.

        Returns:
            The environment type identifier.
        """
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
            asyncio.CancelledError: Re-raised (after failure bookkeeping)
                when Harbor cancels startup, e.g. on its environment
                build/start timeout.
            Exception: Re-raised from the start implementation — e.g.
                RuntimeError if no Sandbox component is registered on the
                active stack, or NotImplementedError if the task requires
                network isolation (allow_internet=false).
        """
        self._start_failure = None
        try:
            await self._start()
        except (asyncio.CancelledError, Exception) as e:
            # Remembered so that _live_session can point Harbor's
            # post-failure cleanup calls at the root cause.
            # CancelledError is included explicitly: Harbor enforces its
            # environment-build timeout by cancelling this coroutine,
            # and that mode must not stay anonymous.
            self._start_failure = e
            # Retried trials reuse the session id; drop any facts an
            # earlier attempt recorded, or a retry that never opened a
            # sandbox would inherit (and misattribute) them.
            _session_provenance.pop(self.session_id, None)
            raise

    async def _start(self) -> None:
        """Start implementation, separated for failure bookkeeping.

        Raises:
            RuntimeError: If no Sandbox component is registered on the
                active stack.
            NotImplementedError: If the task requires network isolation
                (allow_internet=false), which the bridge can't enforce.
            Exception: Re-raised from preparing the Harbor log dirs after
                the session was torn down again.
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
        _session_provenance[self.session_id] = SandboxProvenance(
            flavor=sandbox.flavor,
            docker_image=cfg.docker_image,
        )
        logger.info(
            "ZenML Sandbox session %s started for Harbor trial %s",
            self._session.id,
            self.session_id,
        )
        try:
            await self._ensure_harbor_log_dirs()
        except Exception:
            # Tear down so a half-started env doesn't leak a paid remote
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
        # _merge_env is a documented hook Harbor's base class provides
        # for combining per-call env vars with the persistent env.
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
            if out.stdout_truncated or out.stderr_truncated:
                logger.warning(
                    "Sandbox command output exceeded the collection cap "
                    "and was truncated (stdout_truncated=%s, "
                    "stderr_truncated=%s): %.200s",
                    out.stdout_truncated,
                    out.stderr_truncated,
                    command,
                )
            return ExecResult(
                stdout=out.stdout,
                stderr=out.stderr,
                return_code=out.exit_code,
            )

        return await asyncio.to_thread(_run)

    async def upload_file(
        self, source_path: Path | str, target_path: str
    ) -> None:
        """Stream a local file into the SandboxSession.

        Args:
            source_path: Local file to upload.
            target_path: Destination path inside the sandbox.
        """
        await asyncio.to_thread(
            self._live_session.upload_file, str(source_path), target_path
        )

    async def download_file(
        self, source_path: str, target_path: Path | str
    ) -> None:
        """Stream a remote file out of the SandboxSession.

        Args:
            source_path: File inside the sandbox to download.
            target_path: Local destination path.
        """
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
        """Download a directory tree via tar + ``download_file``.

        Args:
            source_dir: Directory inside the sandbox to download.
            target_dir: Local destination directory.
        """
        await self.download_dir_with_exclusions(
            source_dir=source_dir, target_dir=target_dir, exclude=[]
        )
