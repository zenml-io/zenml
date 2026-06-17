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
"""Local sandbox flavor."""

import logging
import os
import shlex
import shutil
import subprocess
import tempfile
import time
import uuid
from typing import Dict, Iterator, List, Optional, Type, Union, cast

from pydantic import Field

from zenml.logger import get_logger
from zenml.sandboxes.base import (
    BaseSandbox,
    BaseSandboxConfig,
    BaseSandboxFlavor,
    BaseSandboxSettings,
)
from zenml.sandboxes.process import SandboxExecError, SandboxProcess
from zenml.sandboxes.session import SandboxSession

logger = get_logger(__name__)

LOCAL_SANDBOX_FLAVOR = "local"

# Default set of parent-process variables forwarded into a local session
DEFAULT_FORWARDED_ENV_VARS = [
    "PATH",
    "HOME",
    "LANG",
    "LC_ALL",
    "TMPDIR",
    "TERM",
]

# Variables the host OS needs to launch a child process at all, injected
# beneath the user's `forward_env` selection rather than gated behind it.
# On Windows a child interpreter started without SYSTEMROOT aborts during
# pre-init ("failed to get random numbers to initialize Python"), so a
# curated forward list (which never includes OS plumbing) would otherwise
# break every exec.
_OS_REQUIRED_ENV_VARS = ["SYSTEMROOT"] if os.name == "nt" else []


def _os_required_env() -> Dict[str, str]:
    """Collect the host-OS variables required to launch any subprocess.

    Returns:
        The required OS environment variables present in the parent process.
    """
    return {
        key: os.environ[key]
        for key in _OS_REQUIRED_ENV_VARS
        if key in os.environ
    }


class LocalSandboxSettings(BaseSandboxSettings):
    """Local sandbox settings."""

    forward_env: Union[bool, List[str]] = Field(
        default_factory=lambda: list(DEFAULT_FORWARDED_ENV_VARS),
        description="Selects which parent-process environment variables are "
        "forwarded into local sandbox sessions. True forwards the entire "
        "parent environment, False forwards nothing, and a list forwards "
        "exactly the named variables.",
    )


class LocalSandboxConfig(BaseSandboxConfig, LocalSandboxSettings):
    """Local sandbox configuration."""


class LocalSandboxProcess(SandboxProcess):
    """Local sandbox process wrapping a subprocess."""

    def __init__(
        self,
        process: "subprocess.Popen[str]",
        session: "LocalSandboxSession",
        started_at: float,
    ) -> None:
        """Initialize the local sandbox process.

        Args:
            process: The subprocess handle.
            session: The owning session.
            started_at: The wall-clock time the launch began.
        """
        super().__init__(session=session, started_at=started_at)
        self._process = process

    def stdout(self) -> Iterator[str]:
        """Stdout line iterator.

        Returns:
            Stdout line iterator.
        """

        def _stdout() -> Iterator[str]:
            if self._process.stdout is None:
                return

            for line in self._process.stdout:
                yield line

        return self._session._wrap_stream(_stdout(), log_level=logging.INFO)

    def stderr(self) -> Iterator[str]:
        """Stderr line iterator.

        Returns:
            Stderr line iterator.
        """

        def _stderr() -> Iterator[str]:
            if self._process.stderr is None:
                return

            for line in self._process.stderr:
                yield line

        return self._session._wrap_stream(_stderr(), log_level=logging.ERROR)

    def wait(self, timeout: Optional[float] = None) -> int:
        """Block until the subprocess exits.

        Args:
            timeout: Timeout in seconds to wait.

        Returns:
            The exit code.
        """
        return self._process.wait(timeout=timeout)

    def kill(self) -> None:
        """Kill the subprocess by sending SIGKILL."""
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
        """Exit code, or `None` if the subprocess is still running.

        Returns:
            The exit code or `None`.
        """
        return self._process.returncode

    @staticmethod
    def _release_pipes(process: "subprocess.Popen[str]") -> None:
        """Close the stdout/stderr pipe file objects of a subprocess.

        Without an explicit close, every exec leaks two file descriptors
        until the `Popen` object is GC'd, which exhausts the fd limit in
        long-lived sessions. Closing an already-closed file object is a
        no-op, so this is safe to call repeatedly.

        Args:
            process: The subprocess whose pipes should be released.
        """
        if process.stdout is not None:
            process.stdout.close()
        if process.stderr is not None:
            process.stderr.close()


class LocalSandboxSession(SandboxSession):
    """Local sandbox session."""

    def __init__(
        self,
        workdir: str,
        env: Dict[str, str],
        *,
        parent: "BaseSandbox",
    ) -> None:
        """Initialize the local sandbox session.

        Args:
            workdir: Absolute path to the working directory for this session.
                This directory is cleaned up when the session is closed.
            env: Environment variables to set for this session.
            parent: The sandbox component that created this session.
        """
        super().__init__(
            id=f"local-{uuid.uuid4().hex[:12]}",
            parent=parent,
        )
        self._workdir = workdir
        self._env = env
        self._processes: List["subprocess.Popen[str]"] = []

    def _exec(
        self,
        command: Union[str, List[str]],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> SandboxProcess:
        """Execute a command in a new subprocess.

        Args:
            command: The command to execute.
            cwd: Optional working directory override. Relative paths
                are resolved against the session workdir. When `None`,
                the session workdir is used.
            env: Environment variables to set in the subprocess environment.

        Raises:
            SandboxExecError: If the subprocess fails to launch.

        Returns:
            Process handle.
        """
        if isinstance(command, str):
            command = shlex.split(command)

        self._log_command(command)

        # Prune exited processes and release their pipe file objects so a
        # long-lived session (e.g. an agent loop issuing many execs) does
        # not accumulate two leaked fds per exec until it hits EMFILE. A
        # caller holding an undrained handle for an exited process across
        # later execs in the same session may find its streams closed;
        # this is acceptable because the alternative is unbounded fd
        # growth, and collect()/stream iteration normally drains before
        # the next exec.
        still_running = []
        for tracked in self._processes:
            if tracked.poll() is None:
                still_running.append(tracked)
            else:
                LocalSandboxProcess._release_pipes(tracked)
        self._processes = still_running

        if cwd is None:
            effective_cwd = self._workdir
        elif os.path.isabs(cwd):
            effective_cwd = cwd
        else:
            effective_cwd = os.path.join(self._workdir, cwd)

        env = {
            **_os_required_env(),
            **self._env,
            **(env or {}),
        }

        started_at = time.time()
        try:
            process = subprocess.Popen(
                command,
                cwd=effective_cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # line-buffered
            )
        except OSError as e:
            raise SandboxExecError(
                f"Local sandbox execution failed to launch: {e}"
            ) from e

        self._processes.append(process)
        return LocalSandboxProcess(
            process=process, session=self, started_at=started_at
        )

    def _close(self) -> None:
        """Terminate running processes and clean up the working directory."""
        for process in self._processes:
            # One misbehaving process must not abort termination of the
            # remaining processes or the workdir removal: close() latches
            # the closed flag, so a retry would be a silent no-op.
            try:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        try:
                            # Reap the killed child so it doesn't linger as a
                            # zombie until the Popen object is GC'd.
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            logger.debug(
                                "Local sandbox child %s survived SIGKILL "
                                "reaping",
                                process.pid,
                            )
                # The session is over, so its streams are over too:
                # release the pipe fds of every tracked process.
                LocalSandboxProcess._release_pipes(process)
            except Exception as e:
                logger.warning(
                    "Failed to clean up local sandbox child %s: %s",
                    process.pid,
                    e,
                )
        self._processes.clear()
        try:
            shutil.rmtree(self._workdir, ignore_errors=True)
        except Exception as e:
            logger.debug(
                "Local sandbox session workdir cleanup failed: %s",
                e,
            )

    def _destroy(self) -> None:
        """Destroy hook; `close()` already performs the full local cleanup."""


class LocalSandbox(BaseSandbox):
    """Local subprocess-based Sandbox.

    **Warning**: This class does NOT provide any isolation and is not suitable
    for running untrusted code.
    """

    @property
    def config(self) -> LocalSandboxConfig:
        """Local sandbox configuration.

        Returns:
            The local sandbox configuration.
        """
        return cast(LocalSandboxConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSandboxSettings"]]:
        """Settings class.

        Returns:
            `LocalSandboxSettings`.
        """
        return LocalSandboxSettings

    def _resolve_session_environment(
        self, settings: BaseSandboxSettings
    ) -> Dict[str, str]:
        """Seed the local subprocess env from the parent process.

        Args:
            settings: Sandbox settings.

        Returns:
            Environment variables.
        """
        env = {}

        if isinstance(settings, LocalSandboxSettings):
            forward_env = settings.forward_env

            if forward_env is True:
                env = dict(os.environ)
            elif isinstance(forward_env, list):
                env = {
                    key: os.environ[key]
                    for key in forward_env
                    if key in os.environ
                }

        env.update(super()._resolve_session_environment(settings))
        return env

    def create_session(
        self, settings: Optional[BaseSandboxSettings] = None
    ) -> SandboxSession:
        """Create a local sandbox session in a clean working directory.

        Args:
            settings: Optional settings overrides.

        Returns:
            A local sandbox session.
        """
        logger.warning(
            "The local sandbox does not provide any isolation. Any code "
            "executed in this sandbox will have full access to the local "
            "filesystem and network."
        )

        settings = cast(LocalSandboxSettings, self.resolve_settings(settings))
        env = self._resolve_session_environment(settings)
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
            The flavor name.
        """
        return LOCAL_SANDBOX_FLAVOR

    @property
    def docs_url(self) -> Optional[str]:
        """Docs URL.

        Returns:
            The docs URL.
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
        return (
            "https://public-flavor-logos.s3.eu-central-1.amazonaws.com"
            "/sandbox/local.png"
        )

    @property
    def config_class(self) -> Type[LocalSandboxConfig]:
        """Config class.

        Returns:
            `LocalSandboxConfig`.
        """
        return LocalSandboxConfig

    @property
    def implementation_class(self) -> Type[LocalSandbox]:
        """Implementation class.

        Returns:
            `LocalSandbox`.
        """
        return LocalSandbox
