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
"""Local subprocess-based Sandbox flavor.

.. warning::
   This flavor provides **no isolation**. Code runs as the same OS user
   that started the step, with full access to the local filesystem,
   network, and any credentials in the environment. It is intended for
   development, quick-start examples, and unit tests — **not for
   running untrusted LLM-generated code in production**.

   For real isolation, use a flavor that boots a container or microVM
   (e.g. ``modal``).

Streams output via ``subprocess.PIPE`` and exposes the same
``BaseSandbox`` / ``SandboxSession`` / ``SandboxProcess`` surface every
other flavor implements, so example code written against the abstraction
works against this flavor without changes.
"""

import os
import shlex
import shutil
import subprocess
import tempfile
import uuid
from typing import Any, Dict, Iterator, List, Optional, Type, Union, cast

from zenml.logger import get_logger
from zenml.sandboxes.base import (
    STEP_IMAGE,
    BaseSandbox,
    BaseSandboxConfig,
    BaseSandboxFlavor,
    BaseSandboxSettings,
)
from zenml.sandboxes.process import SandboxExecError, SandboxProcess
from zenml.sandboxes.session import SandboxSession

logger = get_logger(__name__)

LOCAL_SANDBOX_FLAVOR = "local"

_NO_ISOLATION_WARNING = (
    "LocalSandbox provides NO isolation: LLM-generated code runs as the "
    "current user with full filesystem and network access. Use a "
    "container-backed flavor (e.g. 'modal') for real isolation."
)


class LocalSandboxConfig(BaseSandboxConfig):
    """Configuration for the local subprocess sandbox.

    No fields. Env vars and secrets flow through the standard
    ``StackComponent.environment`` / ``.secrets`` mechanism inherited
    from ``BaseSandboxConfig``.
    """


class LocalSandboxSettings(BaseSandboxSettings):
    """Per-step settings for the local subprocess sandbox.

    Inherits from ``BaseSandboxSettings``. The base ``base_image`` field
    is accepted but ignored — there is no image concept locally; a
    warning is emitted at session creation if a non-None / non-STEP_IMAGE
    value is set.

    Overrides ``copy_local_env`` default to ``True``: LocalSandbox runs
    in the same shell environment as the step (no isolation), so
    propagating PATH and friends matches user expectations. Explicit
    settings still override.
    """

    copy_local_env: bool = True


class LocalSandboxProcess(SandboxProcess):
    """Wraps ``subprocess.Popen`` in the ``SandboxProcess`` interface."""

    def __init__(
        self,
        process: "subprocess.Popen[str]",
        *,
        session: Optional["LocalSandboxSession"] = None,
    ) -> None:
        """Initializes the process wrapper.

        Args:
            process: A live ``subprocess.Popen`` opened with text-mode
                stdout/stderr pipes.
            session: Owning session. When provided, stdout/stderr lines
                are forwarded through ``session._wrap_stream`` so they
                land in the per-session sandbox log source.
        """
        self._process = process
        self._session = session

    def _raw_stdout(self) -> Iterator[str]:
        """Yields stdout one line at a time from the underlying Popen.

        Yields:
            Each line of stdout, including the trailing newline when
            present (matches the base ``SandboxProcess`` contract).
        """
        if self._process.stdout is None:
            return
        for line in self._process.stdout:
            yield line

    def _raw_stderr(self) -> Iterator[str]:
        """Yields stderr one line at a time from the underlying Popen.

        Yields:
            Each line of stderr, including the trailing newline when
            present.
        """
        if self._process.stderr is None:
            return
        for line in self._process.stderr:
            yield line

    def stdout(self) -> Iterator[str]:
        """Returns stdout line iterator, log-wrapped when a session is bound.

        Returns:
            Plain stdout iterator when no session is attached; otherwise
            wrapped via ``session._wrap_stream`` so each line is also
            emitted to the sandbox log source.
        """
        lines = self._raw_stdout()
        if self._session is None:
            return lines
        return self._session._wrap_stream(lines, stream="stdout")

    def stderr(self) -> Iterator[str]:
        """Returns stderr line iterator, log-wrapped when a session is bound.

        Returns:
            Plain stderr iterator when no session is attached; otherwise
            wrapped via ``session._wrap_stream`` so each line is also
            emitted to the sandbox log source at WARNING level.
        """
        lines = self._raw_stderr()
        if self._session is None:
            return lines
        return self._session._wrap_stream(lines, stream="stderr")

    def wait(self, timeout: Optional[float] = None) -> int:
        """Blocks until the subprocess exits.

        Args:
            timeout: Optional seconds to wait before raising
                ``subprocess.TimeoutExpired``.

        Returns:
            The exit code.
        """
        return self._process.wait(timeout=timeout)

    def kill(self) -> None:
        """Sends SIGKILL to the subprocess (no-op if already exited)."""
        try:
            self._process.kill()
        except ProcessLookupError:
            pass
        except Exception as e:
            logger.warning(
                "LocalSandbox kill() failed: %s. Process may still be "
                "running.",
                e,
                exc_info=True,
            )

    @property
    def exit_code(self) -> Optional[int]:
        """Exit code, or ``None`` if the subprocess is still running.

        Returns:
            The exit code or ``None``.
        """
        return self._process.returncode


class LocalSandboxSession(SandboxSession):
    """Subprocess-backed Session.

    Each Session owns a working directory under the system temp dir.
    Files written by exec'd commands persist there for the session
    lifetime; ``close()`` cleans the directory up.
    """

    def __init__(
        self,
        workdir: str,
        env: Dict[str, str],
        *,
        parent: "BaseSandbox",
    ) -> None:
        """Initializes the local Session.

        Args:
            workdir: Path to the per-session working directory.
            env: Resolved env vars to set for every exec'd subprocess.
            parent: The owning ``BaseSandbox`` component.
        """
        super().__init__(
            id=f"local-{uuid.uuid4().hex[:12]}",
            parent=parent,
        )
        self._workdir = workdir
        self._env = env
        self._closed = False

    def exec(
        self,
        command: Union[str, List[str]],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> SandboxProcess:
        """Spawns a subprocess in the Session's working directory.

        Args:
            command: Argv list (no shell escaping needed) or shell string
                (split via ``shlex.split``).
            cwd: Optional working directory override (relative paths are
                resolved against the session workdir).
            env: Optional per-exec env vars layered on top of the
                Session-level env.

        Returns:
            A ``LocalSandboxProcess`` wrapping the live ``subprocess.Popen``.

        Raises:
            SandboxExecError: If ``subprocess.Popen`` fails to launch
                the command (FileNotFoundError, etc.).
        """
        if self._closed:
            raise SandboxExecError(
                "Cannot exec on a closed LocalSandboxSession."
            )

        argv: List[str] = (
            list(command)
            if isinstance(command, list)
            else shlex.split(command)
        )
        # Marker into the sandbox log so the source reads like a shell
        # session: `$ <command>` line followed by its stdout/stderr.
        self._log_command(argv)

        effective_cwd = cwd or self._workdir
        if not os.path.isabs(effective_cwd):
            effective_cwd = os.path.join(self._workdir, effective_cwd)

        effective_env = dict(self._env)
        if env:
            effective_env.update(env)

        try:
            popen: "subprocess.Popen[str]" = subprocess.Popen(
                argv,
                cwd=effective_cwd,
                env=effective_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # line-buffered
            )
        except (FileNotFoundError, OSError) as e:
            raise SandboxExecError(
                f"LocalSandbox exec failed to launch ({type(e).__name__}): {e}"
            ) from e
        return LocalSandboxProcess(popen, session=self)

    def close(self) -> None:
        """Flushes the sandbox log source and removes the workdir.

        Idempotent — safe to call multiple times.
        """
        if self._closed:
            return
        self._closed = True
        self._close_log_origin()
        try:
            shutil.rmtree(self._workdir, ignore_errors=True)
        except Exception as e:
            logger.debug(
                "LocalSandbox workdir cleanup failed: %s",
                e,
            )

    def destroy(self) -> None:
        """Same as ``close()`` for the local flavor.

        There is no separate provider lifetime to terminate; closing
        the local Session already removes its workdir.
        """
        self.close()


class LocalSandbox(BaseSandbox):
    """Subprocess-based Sandbox.

    **Warning:** does NOT isolate code execution. Suitable for examples,
    tests, and development against the Sandbox abstraction; not for
    running untrusted code.
    """

    @property
    def config(self) -> LocalSandboxConfig:
        """Typed config.

        Returns:
            The component's local config.
        """
        return cast(LocalSandboxConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSandboxSettings"]]:
        """Settings class for per-step overrides.

        Returns:
            ``LocalSandboxSettings``.
        """
        return LocalSandboxSettings

    def create_session(
        self, settings: Optional[BaseSandboxSettings] = None
    ) -> SandboxSession:
        """Creates a Session backed by a fresh tmpdir.

        Args:
            settings: Optional per-step ``BaseSandboxSettings`` /
                ``LocalSandboxSettings``.

        Returns:
            A ``LocalSandboxSession`` ready for ``exec()``.
        """
        logger.warning(_NO_ISOLATION_WARNING)

        eff = cast(LocalSandboxSettings, self.effective_settings(settings))
        if eff.base_image not in (None, STEP_IMAGE):
            logger.warning(
                "LocalSandbox ignores base_image=%r — there is no image "
                "concept for the local subprocess flavor.",
                eff.base_image,
            )

        env = self._resolve_session_environment(eff)
        workdir = tempfile.mkdtemp(prefix="zenml-local-sandbox-")

        return LocalSandboxSession(
            workdir=workdir,
            env=env,
            parent=self,
        )


class LocalSandboxFlavor(BaseSandboxFlavor):
    """Local subprocess sandbox flavor."""

    @property
    def name(self) -> str:
        """Flavor name.

        Returns:
            ``"local"``.
        """
        return LOCAL_SANDBOX_FLAVOR

    @property
    def docs_url(self) -> Optional[str]:
        """User-facing docs URL.

        Returns:
            The flavor docs URL.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """SDK docs URL.

        Returns:
            The flavor SDK docs URL.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """Dashboard logo URL.

        Returns:
            The flavor logo URL.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/local.png"

    @property
    def config_class(self) -> Type[LocalSandboxConfig]:
        """Config class.

        Returns:
            ``LocalSandboxConfig``.
        """
        return LocalSandboxConfig

    @property
    def implementation_class(self) -> Type[LocalSandbox]:
        """Implementation class.

        Returns:
            ``LocalSandbox``.
        """
        return LocalSandbox
