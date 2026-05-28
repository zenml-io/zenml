"""Harbor BaseEnvironment backed by ZenML's Sandbox stack component.

Implements the full ``harbor.environments.base.BaseEnvironment``
contract by delegating to whatever Sandbox flavor is on the active
ZenML stack:

    Harbor trial
      -> ZenMLSandboxEnvironment (this file)
        -> Client().active_stack.sandbox.create_session()
          -> the Sandbox flavor on your active stack

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
import re
import shlex
import tarfile
import tempfile
import uuid
from pathlib import Path

from harbor.environments.base import BaseEnvironment, ExecResult
from harbor.environments.capabilities import EnvironmentCapabilities

from zenml.client import Client
from zenml.logger import get_logger
from zenml.sandboxes import BaseSandboxSettings, SandboxSession

logger = get_logger(__name__)


def _parse_dockerfile(text: str) -> list[tuple[str, str]]:
    """Parse a Dockerfile into ordered ``(INSTRUCTION, value)`` pairs.

    A deliberately small parser (no ``dockerfile_parse`` dependency): it
    joins ``\\`` line continuations, drops blank lines and comments, and
    splits each logical line into its instruction keyword and remainder.
    Sufficient for the ``FROM`` / ``WORKDIR`` / ``RUN`` / ``COPY``
    instructions the Sandbox bridge replays; richer forms (heredocs,
    parser directives) are out of scope.

    Args:
        text: Raw Dockerfile contents.

    Returns:
        Instructions in file order, keyword upper-cased.
    """
    logical_lines: list[str] = []
    buffer = ""
    for raw in text.splitlines():
        stripped = raw.strip()
        if not buffer and (not stripped or stripped.startswith("#")):
            continue
        buffer = f"{buffer} {stripped}".strip() if buffer else stripped
        if buffer.endswith("\\"):
            buffer = buffer[:-1].rstrip()
        else:
            logical_lines.append(buffer)
            buffer = ""
    if buffer:
        logical_lines.append(buffer)

    instructions: list[tuple[str, str]] = []
    for line in logical_lines:
        keyword, _, value = line.partition(" ")
        instructions.append((keyword.upper(), value.strip()))
    return instructions


class ZenMLSandboxEnvironment(BaseEnvironment):
    """A Harbor environment that delegates to the active stack's Sandbox.

    Harbor's environment lifecycle (``start`` -> ``exec`` * N ->
    ``stop``) maps near-1:1 onto the Sandbox component's
    ``create_session`` / ``session.exec`` / ``session.close``. The
    session is opened in ``start`` and held on ``self._session`` for
    the lifetime of the environment.

    The Sandbox component consumes a prebuilt base image rather than
    building a Dockerfile, so a task's ``environment/Dockerfile`` is
    honored by replaying it at runtime: ``FROM`` selects the base image,
    and ``WORKDIR`` / ``RUN`` / ``COPY`` are applied via ``exec`` /
    uploads right after the session starts (see ``_provision_from_dockerfile``).
    """

    _session: SandboxSession | None = None
    # WORKDIR from the task Dockerfile; used as the default cwd for exec
    # so agent/verifier commands run where the task expects them.
    _workdir: str | None = None

    @staticmethod
    def type() -> str:
        """Returns the environment identifier surfaced to Harbor."""
        return "zenml-sandbox"

    def _validate_definition(self) -> None:
        """No-op: a task Dockerfile is optional, not required.

        Harbor's local backends use this to assert a ``Dockerfile`` /
        ``docker-compose.yaml`` exists next to the task. Here a Dockerfile
        is honored when present (``FROM`` picks the base image,
        ``WORKDIR`` / ``RUN`` / ``COPY`` are replayed in ``start``), but a
        hermetic task with none is equally valid — the flavor's default
        image is used — so there's nothing to require.
        """

    @property
    def capabilities(self) -> EnvironmentCapabilities:
        """Capabilities reported to Harbor's preflight validators.

        Default to no-GPU because the Sandbox interface doesn't yet
        expose a per-flavor capability surface — claiming GPU support
        unconditionally (when Local can't and Modal can) would let
        Harbor preflight a task that fails deep in the agent run.
        Conservative default; revisit when ``BaseSandbox`` grows a
        ``supports_gpu`` property.
        """
        return EnvironmentCapabilities(gpus=False)

    def _dockerfile_path(self) -> Path:
        """Path to the task's environment Dockerfile (may not exist)."""
        return self.environment_dir / "Dockerfile"

    def _base_image(self) -> str | None:
        """Resolve the base image for the sandbox.

        A task may pin a prebuilt image in ``task.toml`` (``docker_image``),
        which wins. Otherwise we read the ``FROM`` line of the task's
        ``environment/Dockerfile`` so the sandbox pulls the same base the
        task was authored against (e.g. ``ubuntu:24.04`` vs the flavor's
        default). Returns None to fall through to the flavor default.
        """
        if self.task_env_config.docker_image:
            return self.task_env_config.docker_image
        dockerfile = self._dockerfile_path()
        if not dockerfile.exists():
            return None
        for instruction, value in _parse_dockerfile(dockerfile.read_text()):
            if instruction == "FROM":
                # Drop a trailing ``as <stage>`` from multi-stage builds.
                return re.split(
                    r"\s+as\s+", value, maxsplit=1, flags=re.IGNORECASE
                )[0].strip()
        return None

    def _settings_override(self) -> BaseSandboxSettings | None:
        """Carry the resolved base image into the Sandbox settings.

        Env vars do NOT ride on the settings: they flow through
        ``exec`` per call so the Sandbox component's own env merge
        (component config + secrets + step-level overrides) stays
        authoritative. The only thing the override needs to carry is
        the base image (from ``task.toml`` or the task's Dockerfile).
        """
        image = self._base_image()
        if image is None:
            return None
        return BaseSandboxSettings(base_image=image)

    async def start(self, force_build: bool) -> None:
        """Open a SandboxSession on the active stack's Sandbox component.

        ``force_build`` is ignored — the Sandbox component decides
        whether an image needs building based on its own settings and
        the active flavor; Harbor's "force rebuild" is meaningless when
        the flavor is consuming a prebuilt registry image.

        Harbor expects ``/logs/{agent,verifier,artifacts}`` to exist
        when the trial starts — its built-in envs either bind-mount
        them (Docker) or create them explicitly after start (Modal).
        We do the latter; if that post-start setup fails the session
        is torn down so we don't leak it.
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
            await self._provision_from_dockerfile()
            await self._ensure_harbor_log_dirs()
        except Exception:
            # Tear down so a half-started env doesn't leak a paid Modal
            # sandbox up to its TTL.
            await self.stop(delete=True)
            raise

    async def _ensure_harbor_log_dirs(self) -> None:
        """Create the canonical Harbor log dirs the trial harness expects.

        Mirrors Harbor's own Modal env, which runs ``ensure_dirs`` on
        the mount targets after ``start``. ``chmod 1777`` matches
        ``/tmp`` semantics — world-writable but sticky — so non-root
        agent and verifier users can write to ``/logs/agent`` and
        ``/logs/verifier`` without one trampling the other.
        """
        from harbor.models.trial.paths import EnvironmentPaths

        paths = EnvironmentPaths.for_os(self.task_env_config.os)
        dirs = [
            str(paths.agent_dir),
            str(paths.verifier_dir),
            str(paths.artifacts_dir),
        ]
        joined = " ".join(shlex.quote(d) for d in dirs)
        await self.exec(f"mkdir -p {joined} && chmod 1777 {joined}")

    async def _provision_from_dockerfile(self) -> None:
        """Replay the task's Dockerfile inside the started sandbox.

        The Sandbox component pulls a prebuilt base image but does not
        build a Dockerfile, so the task's environment setup (working dir
        and starter files created by ``WORKDIR`` / ``RUN`` / ``COPY``)
        would otherwise be missing. We reproduce that state at runtime via
        ``exec`` and file uploads — the same translate-don't-build approach
        Harbor's own remote-sandbox environments (e.g. Novita) take.

        Skipped when the task pins a prebuilt ``docker_image``: that image
        is assumed to already contain the setup, matching Harbor's E2B /
        Novita behavior. ``FROM`` is handled separately via the base image.
        """
        if self.task_env_config.docker_image:
            return
        dockerfile = self._dockerfile_path()
        if not dockerfile.exists():
            return
        for instruction, value in _parse_dockerfile(dockerfile.read_text()):
            if instruction == "WORKDIR":
                # Create the dir before adopting it as the default cwd —
                # otherwise this very mkdir would exec with cwd set to a
                # directory that does not exist yet.
                await self.exec(f"mkdir -p {shlex.quote(value)}")
                self._workdir = value
            elif instruction == "RUN":
                result = await self.exec(value)
                if result.return_code != 0:
                    raise RuntimeError(
                        f"Dockerfile RUN failed ({result.return_code}): "
                        f"{value}\n{result.stderr}"
                    )
            elif instruction == "COPY":
                await self._replay_copy(value)

    async def _replay_copy(self, value: str) -> None:
        """Replay a Dockerfile ``COPY`` by uploading from the build context.

        Build-context sources resolve against ``environment_dir``;
        ``--from=`` (multi-stage) copies are skipped since there is no
        prior build stage to read from. Relative destinations resolve
        against the tracked ``WORKDIR``.
        """
        parts = [p for p in shlex.split(value) if not p.startswith("--")]
        if any(p.startswith("--from=") for p in shlex.split(value)):
            return
        if len(parts) < 2:
            return
        *sources, dest = parts
        if not dest.startswith("/") and self._workdir:
            dest = f"{self._workdir.rstrip('/')}/{dest}"
        for source in sources:
            src_path = self.environment_dir / source
            if src_path.is_dir():
                await self.upload_dir(src_path, dest)
            elif src_path.is_file():
                await self.upload_file(src_path, dest)

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
        self._workdir = None
        await asyncio.to_thread(session.destroy if delete else session.close)

    async def exec(
        self,
        command: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout_sec: int | None = None,
        user: str | int | None = None,
    ) -> ExecResult:
        """Run ``command`` in the open SandboxSession.

        Harbor passes ``command`` as a shell string with redirects,
        subshells, pipelines — so we wrap in ``bash -c`` (argv form,
        not ``shlex.split``-able) and let the session handle env
        injection and workdir natively. When Harbor doesn't pin a cwd we
        fall back to the Dockerfile's ``WORKDIR`` so agent/verifier
        commands run where the task expects (the prebuilt base image
        doesn't carry the Dockerfile's WORKDIR). ``timeout_sec`` is
        enforced host-side via ``asyncio.wait_for`` since Modal doesn't
        take per-exec timeouts. ``user`` is not yet plumbed.
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
        merged_env = self._merge_env(env)
        effective_cwd = cwd or self._workdir

        def _run() -> ExecResult:
            assert self._session is not None
            process = self._session.exec(
                ["bash", "-c", command], cwd=effective_cwd, env=merged_env
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

    def _remote_tar_path(self, kind: str) -> str:
        """Per-call remote tar path, safe against concurrent / repeated calls.

        ``session_id`` alone collides if two ``upload_dir`` calls overlap
        within the same env; a per-call uuid keeps each archive
        independent and lets ``rm -f`` safely race the cleanup.
        """
        return f"/tmp/.hb-{kind}-{uuid.uuid4().hex}.tar.gz"

    async def upload_dir(
        self, source_dir: Path | str, target_dir: str
    ) -> None:
        """Upload a directory tree via a single tar archive round-trip.

        SandboxSession only exposes ``upload_file``; recursive uploads
        would mean a per-file call (slow on remote flavors). We tar
        locally, ``upload_file`` the archive, untar inside the
        session, and remove the archive regardless of extract success.
        """
        if self._session is None:
            raise RuntimeError(
                "ZenMLSandboxEnvironment.upload_dir called before start()."
            )
        source = Path(source_dir)
        remote_tar = self._remote_tar_path("upload")
        with tempfile.TemporaryDirectory() as host_tmp:
            archive = Path(host_tmp) / "upload.tar.gz"
            with tarfile.open(archive, "w:gz") as tf:
                tf.add(source, arcname=".")
            await asyncio.to_thread(
                self._session.upload_file, str(archive), remote_tar
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
        if self._session is None:
            raise RuntimeError(
                "ZenMLSandboxEnvironment.download_dir called before start()."
            )
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
                    self._session.download_file, remote_tar, str(host_tar)
                )
                with tarfile.open(host_tar, "r:gz") as tf:
                    # ``filter="data"`` blocks unsafe tar entries
                    # (absolute paths, links escaping target). Requires
                    # Python 3.12+; the surrounding example pins 3.12.
                    tf.extractall(path=target, filter="data")
        finally:
            await self.exec(f"rm -f {shlex.quote(remote_tar)}")
