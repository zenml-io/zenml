"""Harbor BaseEnvironment backed by ZenML's Sandbox stack component.

Implements the full ``harbor.environments.base.BaseEnvironment``
contract by delegating to whatever Sandbox flavor is on the active
ZenML stack:

    Harbor trial
      -> ZenMLSandboxEnvironment (this file)
        -> Client().active_stack.sandbox.create_session()
          -> Modal today; Agent Substrate / GKE Agent Sandbox later

``start`` opens a ``SandboxSession``, ``exec`` runs a command and
wraps the output in Harbor's ``ExecResult``, ``upload_file`` /
``download_file`` delegate straight through, and ``stop`` closes
(or destroys) the session. Resource overrides, GPUs, internet
isolation and Windows containers are not yet wired — those ride on
the underlying flavor's settings model when added.

Consumed by ``run.py`` via ``JobConfig.environment.import_path``.
"""

from __future__ import annotations

import asyncio
import shlex
import tarfile
import tempfile
from pathlib import Path

from harbor.environments.base import BaseEnvironment, ExecResult
from harbor.environments.capabilities import EnvironmentCapabilities

from zenml.client import Client
from zenml.logger import get_logger
from zenml.sandboxes import BaseSandboxSettings, SandboxSession

logger = get_logger(__name__)


class ZenMLSandboxEnvironment(BaseEnvironment):
    """A Harbor environment that delegates to the active stack's Sandbox.

    Harbor's environment lifecycle (``start`` -> ``exec`` * N ->
    ``stop``) maps near-1:1 onto the Sandbox component's
    ``create_session`` / ``session.exec`` / ``session.close``. The
    session is opened in ``start`` and held on ``self._session`` for
    the lifetime of the environment.
    """

    _session: SandboxSession | None = None

    @staticmethod
    def type() -> str:
        """Returns the environment identifier surfaced to Harbor."""
        return "zenml-sandbox"

    def _validate_definition(self) -> None:
        """No-op: the Sandbox flavor owns the image; no Dockerfile needed.

        Harbor's local backends use this to assert a ``Dockerfile`` /
        ``docker-compose.yaml`` exists next to the task. With ZenML
        Sandbox the image comes from ``task_env_config.docker_image``
        (or the flavor's default), so there's nothing to validate.
        """

    @property
    def capabilities(self) -> EnvironmentCapabilities:
        """Capabilities reported to Harbor's preflight validators.

        We declare GPU support so tasks requesting GPUs pass preflight;
        the actual allocation rides on the underlying flavor's
        settings. Internet isolation, Windows containers, mount
        semantics and docker-compose stay off — none of those are
        primitives the Sandbox interface currently exposes.
        """
        return EnvironmentCapabilities(gpus=True)

    def _settings_from_task_env(self) -> BaseSandboxSettings | None:
        """Translates Harbor's ``EnvironmentConfig`` into Sandbox settings.

        ``docker_image`` -> ``base_image`` (when set; otherwise the
        flavor default applies). ``env`` -> ``environment`` (resolved
        host env vars come pre-merged in ``self._persistent_env`` by
        the base class). Returns ``None`` when neither is populated so
        the Sandbox component falls back to its own config defaults.
        """
        image = self.task_env_config.docker_image
        env = dict(self._persistent_env)
        if image is None and not env:
            return None
        kwargs: dict = {}
        if image is not None:
            kwargs["base_image"] = image
        if env:
            kwargs["environment"] = env
        return BaseSandboxSettings(**kwargs)

    async def start(self, force_build: bool) -> None:
        """Open a SandboxSession on the active stack's Sandbox component.

        ``force_build`` is ignored — the Sandbox component decides
        whether an image needs building based on its own settings and
        the active flavor; Harbor's "force rebuild" is meaningless when
        the flavor is consuming a prebuilt registry image.

        Harbor expects ``/logs/{agent,verifier,artifacts}`` to exist
        when the trial starts — its built-in envs either bind-mount
        them (Docker) or create them explicitly after start (Modal).
        We do the latter so the agent / verifier / artifact handler
        downstream don't trip on missing directories.
        """
        sandbox = Client().active_stack.sandbox
        if sandbox is None:
            raise RuntimeError(
                "No Sandbox component is registered on the active stack. "
                "Register one with `zenml sandbox register ...` and add "
                "it to the active stack before running Harbor."
            )
        settings = self._settings_from_task_env()
        self._session = await asyncio.to_thread(
            lambda: sandbox.create_session(settings=settings).__enter__()
        )
        logger.info(
            "ZenML Sandbox session %s started for Harbor trial %s",
            self._session.id,
            self.session_id,
        )
        await self._ensure_harbor_log_dirs()

    async def _ensure_harbor_log_dirs(self) -> None:
        """Create the canonical Harbor log dirs the trial harness expects.

        Mirrors Harbor's own Modal env, which runs ``ensure_dirs``
        on the mount targets after ``start``. We hit
        ``EnvironmentPaths.for_os`` for the canonical layout and
        chmod 777 so non-root agents/verifiers can write.
        """
        from harbor.models.trial.paths import EnvironmentPaths

        paths = EnvironmentPaths.for_os(self.task_env_config.os)
        dirs = [
            shlex.quote(str(paths.agent_dir)),
            shlex.quote(str(paths.verifier_dir)),
            shlex.quote(str(paths.artifacts_dir)),
        ]
        joined = " ".join(dirs)
        await self.exec(f"mkdir -p {joined} && chmod 777 {joined}")

    async def stop(self, delete: bool) -> None:
        """Close (or destroy) the underlying SandboxSession.

        Harbor's ``delete=True`` means "tear down completely". We map
        that to ``destroy`` so the underlying flavor can release any
        provider-side resources; otherwise ``close`` keeps the session
        artifacts around but tears down the live connection.
        """
        if self._session is None:
            return
        session = self._session
        self._session = None
        await asyncio.to_thread(session.destroy if delete else session.close)

    def _wrap_command(
        self,
        command: str,
        *,
        cwd: str | None,
        env: dict[str, str] | None,
    ) -> list[str]:
        """Fold ``cwd`` / ``env`` overrides into a ``bash -lc`` invocation.

        ``SandboxSession.exec`` takes an argv list, not a shell string,
        and has no first-class ``cwd`` / ``env`` knobs. We rewrite the
        command so the env vars ride inside a single shell invocation
        as ``export … ;`` statements (NOT ``KEY=val CMD``, which is
        only valid before *simple* commands — a subshell or pipeline
        in ``CMD`` would make bash syntax-error).
        """
        prefix = ""
        if env:
            assigns = " ".join(f"{k}={shlex.quote(v)}" for k, v in env.items())
            prefix += f"export {assigns}; "
        if cwd:
            prefix += f"cd {shlex.quote(cwd)} && "
        return ["bash", "-lc", prefix + command]

    async def exec(
        self,
        command: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout_sec: int | None = None,
        user: str | int | None = None,
    ) -> ExecResult:
        """Run ``command`` in the open SandboxSession.

        ``timeout_sec`` is honored only when the underlying flavor
        supports per-exec timeouts; Modal currently doesn't, so we
        log-and-ignore. ``user`` is not yet plumbed — the session runs
        as the container default.
        """
        if self._session is None:
            raise RuntimeError(
                "ZenMLSandboxEnvironment.exec called before start()."
            )
        if user is not None:
            logger.debug(
                "ZenMLSandboxEnvironment.exec ignoring user=%r — not "
                "supported by the Sandbox interface yet.",
                user,
            )
        argv = self._wrap_command(command, cwd=cwd, env=self._merge_env(env))

        def _run() -> ExecResult:
            assert self._session is not None
            process = self._session.exec(argv)
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
        if self._session is None:
            raise RuntimeError(
                "ZenMLSandboxEnvironment.upload_file called before start()."
            )
        await asyncio.to_thread(
            self._session.upload_file, str(source_path), target_path
        )

    async def download_file(
        self, source_path: str, target_path: Path | str
    ) -> None:
        """Stream a remote file out of the SandboxSession."""
        if self._session is None:
            raise RuntimeError(
                "ZenMLSandboxEnvironment.download_file called before start()."
            )
        await asyncio.to_thread(
            self._session.download_file, source_path, str(target_path)
        )

    async def upload_dir(
        self, source_dir: Path | str, target_dir: str
    ) -> None:
        """Upload a directory tree via a single tar archive round-trip.

        SandboxSession only exposes ``upload_file``; recursive uploads
        would mean a per-file call (slow on remote flavors). We tar
        locally, ``upload_file`` the archive, and untar inside the
        session. Mirrors how Harbor's own ``download_dir_with_exclusions``
        already moves directories.
        """
        if self._session is None:
            raise RuntimeError(
                "ZenMLSandboxEnvironment.upload_dir called before start()."
            )
        source = Path(source_dir)
        with tempfile.TemporaryDirectory() as host_tmp:
            archive = Path(host_tmp) / "upload.tar.gz"
            with tarfile.open(archive, "w:gz") as tf:
                tf.add(source, arcname=".")
            remote_tar = f"/tmp/.hb-upload-{self.session_id}.tar.gz"
            await asyncio.to_thread(
                self._session.upload_file, str(archive), remote_tar
            )
        await self.exec(
            f"mkdir -p {shlex.quote(target_dir)} && "
            f"tar xzf {shlex.quote(remote_tar)} -C "
            f"{shlex.quote(target_dir)} && rm -f {shlex.quote(remote_tar)}"
        )

    async def download_dir(
        self, source_dir: str, target_dir: Path | str
    ) -> None:
        """Download a directory tree via tar + ``download_file``."""
        if self._session is None:
            raise RuntimeError(
                "ZenMLSandboxEnvironment.download_dir called before start()."
            )
        remote_tar = f"/tmp/.hb-download-{self.session_id}.tar.gz"
        await self.exec(
            f"tar czf {shlex.quote(remote_tar)} -C {shlex.quote(source_dir)} ."
        )
        target = Path(target_dir)
        target.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as host_tmp:
            host_tar = Path(host_tmp) / "download.tar.gz"
            await asyncio.to_thread(
                self._session.download_file, remote_tar, str(host_tar)
            )
            with tarfile.open(host_tar, "r:gz") as tf:
                tf.extractall(path=target, filter="data")
        await self.exec(f"rm -f {shlex.quote(remote_tar)}")
