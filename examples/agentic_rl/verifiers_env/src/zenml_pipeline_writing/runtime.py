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
"""ZenML Sandbox runtime for verifiers v1.

This file is written to the shape of an upstream contribution to
``verifiers/v1/runtimes/zenml.py`` (mirroring the merged Modal runtime,
PR #1594, and the Daytona vendor contribution, PR #1663). Until that
lands, ``patch.py`` registers it locally by riding the ``docker``
config discriminator — see the module docstring there for why the union
cannot be extended from outside.

The mapping is Runtime -> SandboxSession:

    start()        -> Client().active_stack.sandbox.create_session()
    run(argv, env) -> session.exec(...) -> process.collect()
    read/write     -> session.download_file / upload_file
    stop()/cleanup -> session.destroy()  (idempotent close semantics)

ZenML's session API is synchronous, so every call is bridged with
``asyncio.to_thread``; session creation is bounded by a semaphore so a
large rollout fan-out cannot stampede the sandbox backend into
rate-limiting.
"""

import asyncio
import atexit
import os
import tempfile
import threading
import uuid
import weakref
from typing import Any, ClassVar, Dict, List, Optional

from verifiers.v1.runtimes.base import ProgramResult, Runtime

# Bounded sandbox creation: prime-rl runs many env workers per process,
# and unbounded concurrent session creation trips the sandbox backend's
# rate limits.
_MAX_CONCURRENT_CREATES = int(
    os.environ.get("ZENML_VERIFIERS_MAX_CONCURRENT_CREATES", "4")
)
_create_semaphore = threading.Semaphore(_MAX_CONCURRENT_CREATES)

# atexit backstop registry: sessions whose stop() was cut by a signal
# still get destroyed. Mirrors verifiers' own register()/cleanup
# convention for runtimes.
_live_sessions: "weakref.WeakValueDictionary[str, Any]" = (
    weakref.WeakValueDictionary()
)


def _cleanup_leaked_sessions() -> None:
    """Destroy sessions that were never stopped (atexit backstop)."""
    for session in list(_live_sessions.values()):
        try:
            session.destroy()
        except Exception:
            pass


atexit.register(_cleanup_leaked_sessions)


class ZenMLSandboxRuntime(Runtime):
    """verifiers Runtime executing programs in a ZenML Sandbox session.

    The sandbox provider (docker, kubernetes, modal, ...) is whatever
    the active ZenML stack's Sandbox component is — swapping providers
    is a stack config change, not a code change. The session id is
    recorded on ``info.id`` and therefore lands on ``trace.runtime.id``
    in every rollout record: the reward <-> sandbox join.
    """

    # ZenML sandboxes may be local (docker) or remote (kubernetes,
    # modal) depending on the active stack; declared non-local so
    # host-network shortcuts are never assumed. Correct everywhere,
    # merely slower (tunneling) where a local flavor would not need it.
    is_local: ClassVar[bool] = False

    def __init__(self, config: Any, name: Optional[str] = None) -> None:
        """Initialize the runtime.

        Args:
            config: The runtime config. When selected via the local
                patch this is a verifiers ``DockerConfig``; its
                ``image`` and ``workdir`` fields are honored.
            name: Runtime name — verifiers passes the trace id, which
                makes it the rollout <-> sandbox correlation key.
        """
        super().__init__(name=name or f"zenml-{uuid.uuid4().hex[:8]}")
        self.config = config
        self._session: Optional[Any] = None
        self._workdir: str = getattr(config, "workdir", "/workspace")
        self.info = type(
            "ZenMLRuntimeInfo",
            (),
            {"id": None, "type": "zenml"},
        )()

    async def start(self) -> None:
        """Open a SandboxSession on the active stack's Sandbox component.

        Raises:
            RuntimeError: If the active stack has no Sandbox component.
        """

        def _start() -> Any:
            from zenml.client import Client

            sandbox = Client().active_stack.sandbox
            if sandbox is None:
                raise RuntimeError(
                    "ZenMLSandboxRuntime requires a Sandbox component "
                    "on the active ZenML stack (zenml sandbox register "
                    "...)."
                )
            image = getattr(self.config, "image", None)
            settings = sandbox.image_settings(image) if image else None
            with _create_semaphore:
                return sandbox.create_session(settings=settings)

        self._session = await asyncio.to_thread(_start)
        self.info.id = self._session.id
        _live_sessions[self._session.id] = self._session

    def _require_session(self) -> Any:
        """The open session, or a pointed error.

        Returns:
            The open sandbox session.

        Raises:
            RuntimeError: If the runtime was never started.
        """
        if self._session is None:
            raise RuntimeError(
                "ZenMLSandboxRuntime used before start() (or after stop())."
            )
        return self._session

    async def run(self, argv: List[str], env: Dict[str, str]) -> ProgramResult:
        """Run a program in the sandbox session.

        Args:
            argv: The program argv.
            env: Environment variables for the program.

        Returns:
            The program result with exit code and split streams.
        """
        session = self._require_session()

        def _run() -> ProgramResult:
            process = session.exec(argv, cwd=self._workdir, env=env)
            output = process.collect()
            return ProgramResult(
                exit_code=output.exit_code,
                stdout=output.stdout,
                stderr=output.stderr,
            )

        return await asyncio.to_thread(_run)

    async def read(self, path: str) -> bytes:
        """Read a file from the sandbox.

        Args:
            path: Absolute sandbox path, or relative to the workdir.

        Returns:
            The file contents.
        """
        session = self._require_session()

        def _read() -> bytes:
            with tempfile.NamedTemporaryFile(delete=False) as handle:
                local_path = handle.name
            try:
                session.download_file(path, local_path)
                with open(local_path, "rb") as source:
                    return source.read()
            finally:
                try:
                    os.unlink(local_path)
                except OSError:
                    pass

        return await asyncio.to_thread(_read)

    async def write(self, path: str, data: bytes) -> None:
        """Write a file into the sandbox.

        Args:
            path: Absolute sandbox path, or relative to the workdir.
            data: The file contents.
        """
        session = self._require_session()

        def _write() -> None:
            with tempfile.NamedTemporaryFile(delete=False) as handle:
                handle.write(data)
                local_path = handle.name
            try:
                session.upload_file(local_path, path)
            finally:
                try:
                    os.unlink(local_path)
                except OSError:
                    pass

        await asyncio.to_thread(_write)

    async def stop(self) -> None:
        """Destroy the sandbox session (normal teardown path)."""
        if self._session is None:
            return
        session = self._session
        self._session = None
        _live_sessions.pop(session.id, None)

        def _stop() -> None:
            try:
                session.destroy()
            except Exception:
                # close() is idempotent; destroy failures must not mask
                # the rollout result.
                try:
                    session.close()
                except Exception:
                    pass

        await asyncio.to_thread(_stop)

    def cleanup(self) -> None:
        """Synchronous teardown backstop (atexit / signal-cut stop)."""
        if self._session is None:
            return
        session = self._session
        self._session = None
        _live_sessions.pop(session.id, None)
        try:
            session.destroy()
        except Exception:
            pass
