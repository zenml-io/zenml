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
"""Tests for sandbox capability checks and unsupported default methods."""

from datetime import datetime
from typing import Dict, Iterator, List, Optional, Set
from uuid import uuid4

import pytest

from zenml.enums import StackComponentType
from zenml.sandboxes import (
    BaseSandbox,
    BaseSandboxConfig,
    NetworkPolicy,
    SandboxCapability,
    SandboxProcess,
    SandboxSession,
)


class _CapabilitySandbox(BaseSandbox):
    """Minimal concrete sandbox to test capability checks."""

    def __init__(self, capabilities: Set[SandboxCapability], **kwargs) -> None:
        self._capabilities = capabilities
        super().__init__(**kwargs)

    @property
    def capabilities(self) -> Set[SandboxCapability]:
        """Capabilities supported by this test sandbox."""
        return self._capabilities

    def session(
        self,
        *,
        image: Optional[str] = None,
        cpu: Optional[float] = None,
        memory_mb: Optional[int] = None,
        gpu: Optional[str] = None,
        timeout_seconds: int = 300,
        env: Optional[Dict[str, str]] = None,
        secret_refs: Optional[List[str]] = None,
        network_policy: Optional[NetworkPolicy] = None,
        tags: Optional[Dict[str, str]] = None,
        workdir: Optional[str] = None,
    ) -> SandboxSession:
        """Creates a session.

        This test class does not implement concrete sessions.
        """
        raise NotImplementedError


class _StubSession(SandboxSession):
    """Minimal concrete session exposing base default methods."""

    def exec_run(
        self,
        command: List[str],
        *,
        timeout_seconds: Optional[int] = None,
        env: Optional[Dict[str, str]] = None,
        workdir: Optional[str] = None,
        check: Optional[bool] = None,
    ):
        raise NotImplementedError

    def run_code(
        self,
        code: str,
        *,
        language: str = "python",
        inputs: Optional[Dict[str, object]] = None,
        timeout_seconds: Optional[int] = None,
        check: Optional[bool] = None,
    ):
        raise NotImplementedError

    def terminate(self, reason: Optional[str] = None) -> None:
        return None

    def __enter__(self) -> "_StubSession":
        return self

    def __exit__(self, *args) -> None:
        return None


class _StubProcess(SandboxProcess):
    """Minimal concrete process exposing base kill fallback behavior."""

    def stdout_iter(self) -> Iterator[str]:
        return iter(())

    def stderr_iter(self) -> Iterator[str]:
        return iter(())

    def wait(self, timeout_seconds: Optional[int] = None) -> int:
        return 0

    @property
    def exit_code(self) -> Optional[int]:
        return 0


def _create_sandbox(
    capabilities: Set[SandboxCapability],
) -> _CapabilitySandbox:
    """Creates a sandbox instance for unit tests."""
    return _CapabilitySandbox(
        capabilities=capabilities,
        name="dummy-sandbox",
        id=uuid4(),
        config=BaseSandboxConfig(),
        flavor="dummy",
        type=StackComponentType.SANDBOX,
        user=None,
        created=datetime.utcnow(),
        updated=datetime.utcnow(),
    )


def test_base_sandbox_has_capability() -> None:
    """Tests capability membership checks."""
    sandbox = _create_sandbox({SandboxCapability.FILESYSTEM})

    assert sandbox.has_capability(SandboxCapability.FILESYSTEM)
    assert not sandbox.has_capability(SandboxCapability.TUNNELS)


def test_sandbox_session_default_methods_raise_not_implemented() -> None:
    """Tests unsupported default SandboxSession methods."""
    session = _StubSession()

    with pytest.raises(
        NotImplementedError, match="does not support streaming output"
    ):
        session.exec_streaming(["echo", "hello"])

    with pytest.raises(
        NotImplementedError, match="does not support code interpreter mode"
    ):
        session.code_interpreter()

    with pytest.raises(
        NotImplementedError, match="does not support filesystem operations"
    ):
        session.write_file("/tmp/test.txt", "hello")

    with pytest.raises(
        NotImplementedError, match="does not support filesystem operations"
    ):
        session.read_file("/tmp/test.txt")

    with pytest.raises(
        NotImplementedError, match="does not support filesystem operations"
    ):
        session.upload_file("/tmp/local.txt", "/tmp/remote.txt")

    with pytest.raises(
        NotImplementedError, match="does not support filesystem operations"
    ):
        session.download_file("/tmp/remote.txt", "/tmp/local.txt")

    with pytest.raises(
        NotImplementedError, match="does not support snapshots"
    ):
        session.snapshot()

    with pytest.raises(NotImplementedError, match="does not support tunnels"):
        session.open_tunnel(8080)


def test_sandbox_process_kill_default_raises_not_implemented() -> None:
    """Tests kill fallback guidance for process-level cancellation."""
    process = _StubProcess()

    with pytest.raises(
        NotImplementedError, match=r"Use session\.terminate\(\) instead"
    ):
        process.kill()
