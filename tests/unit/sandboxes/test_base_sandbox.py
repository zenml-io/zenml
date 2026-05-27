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
"""Unit tests for the Sandbox base abstraction."""

from datetime import datetime
from typing import Dict, Iterator, List, Optional, Type, Union
from uuid import uuid4

import pytest

from zenml.enums import StackComponentType
from zenml.sandboxes import (
    STEP_IMAGE,
    BaseSandbox,
    BaseSandboxConfig,
    BaseSandboxFlavor,
    BaseSandboxSettings,
    BaseSandboxSnapshot,
    SandboxExecError,
    SandboxProcess,
    SandboxSession,
)


class _FakeProcess(SandboxProcess):
    """Minimal SandboxProcess for testing."""

    def __init__(self, code: int = 0) -> None:
        self._code = code

    def stdout(self) -> Iterator[str]:
        yield "line1"
        yield "line2"

    def stderr(self) -> Iterator[str]:
        return iter(())

    def wait(self, timeout: Optional[float] = None) -> int:
        return self._code

    def kill(self) -> None:
        return None

    @property
    def exit_code(self) -> Optional[int]:
        return self._code


class _FakeSession(SandboxSession):
    """Minimal SandboxSession for testing. Only implements `exec` + `close`."""

    def __init__(self, session_id: str = "sess-1") -> None:
        self.id = session_id
        self.closed = False

    def exec(
        self,
        command: Union[str, List[str]],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> SandboxProcess:
        return _FakeProcess()

    def close(self) -> None:
        self.closed = True


class _FakeSandbox(BaseSandbox):
    """Minimal BaseSandbox for testing. `create_session` returns a fake."""

    def create_session(
        self, settings: Optional[BaseSandboxSettings] = None
    ) -> SandboxSession:
        return _FakeSession()


class _FakeSandboxFlavor(BaseSandboxFlavor):
    """Minimal flavor pointing at _FakeSandbox."""

    @property
    def name(self) -> str:
        return "fake"

    @property
    def implementation_class(self) -> Type[BaseSandbox]:
        return _FakeSandbox


def _make_sandbox(flavor: str = "fake") -> _FakeSandbox:
    """Build a _FakeSandbox without going through Stack/Client."""
    return _FakeSandbox(
        name="test-sandbox",
        id=uuid4(),
        config=BaseSandboxConfig(),
        flavor=flavor,
        type=StackComponentType.SANDBOX,
        user=None,
        created=datetime.now(),
        updated=datetime.now(),
    )


class TestStepImageSentinel:
    def test_sentinel_is_a_string(self) -> None:
        assert isinstance(STEP_IMAGE, str)

    def test_sentinel_value_matches_module_export(self) -> None:
        from zenml.sandboxes.base_sandbox import STEP_IMAGE as direct

        assert STEP_IMAGE == direct


class TestFlavor:
    def test_flavor_type_is_sandbox(self) -> None:
        assert _FakeSandboxFlavor().type == StackComponentType.SANDBOX

    def test_default_config_class_is_base(self) -> None:
        assert _FakeSandboxFlavor().config_class is BaseSandboxConfig


class TestConfig:
    def test_is_remote_defaults_false(self) -> None:
        # Sandboxes are called from inside step code; server doesn't need
        # to reach them — unlike orchestrators / step operators.
        assert BaseSandboxConfig().is_remote is False
        assert BaseSandboxConfig().is_local is True


class TestSettings:
    def test_defaults(self) -> None:
        s = BaseSandboxSettings()
        assert s.base_image is None
        assert s.environment == {}
        assert s.copy_local_env is False
        assert s.timeout_seconds is None
        assert s.forward_logs_to_step is None

    def test_step_image_sentinel_accepted(self) -> None:
        s = BaseSandboxSettings(base_image=STEP_IMAGE)
        assert s.base_image == STEP_IMAGE


class TestSnapshotModel:
    def test_round_trip(self) -> None:
        snap = BaseSandboxSnapshot(
            provider="fake",
            ref="snap-123",
            metadata={"size_mb": 42},
        )
        restored = BaseSandboxSnapshot.model_validate_json(
            snap.model_dump_json()
        )
        assert restored == snap

    def test_metadata_defaults_empty(self) -> None:
        snap = BaseSandboxSnapshot(provider="fake", ref="r")
        assert snap.metadata == {}


class TestSessionContextManager:
    def test_with_block_calls_close(self) -> None:
        session = _FakeSession()
        with session as s:
            assert s is session
            assert session.closed is False
        assert session.closed is True


class TestSessionOptionalMethods:
    """Optional methods on SandboxSession raise NotImplementedError by default."""

    def test_aexec_default_raises(self) -> None:
        import asyncio

        session = _FakeSession()
        with pytest.raises(NotImplementedError):
            asyncio.run(session.aexec("echo hi"))

    def test_snapshot_default_raises(self) -> None:
        with pytest.raises(NotImplementedError):
            _FakeSession().snapshot()

    def test_upload_file_default_raises(self) -> None:
        with pytest.raises(NotImplementedError):
            _FakeSession().upload_file("/local", "/remote")

    def test_download_file_default_raises(self) -> None:
        with pytest.raises(NotImplementedError):
            _FakeSession().download_file("/remote", "/local")

    def test_destroy_default_raises(self) -> None:
        with pytest.raises(NotImplementedError):
            _FakeSession().destroy()


class TestSandboxOptionalMethods:
    def test_attach_default_raises(self) -> None:
        with pytest.raises(NotImplementedError):
            _make_sandbox().attach("sess-1")


class TestRestoreProviderGuard:
    def test_restore_rejects_cross_provider_snapshot(self) -> None:
        sandbox = _make_sandbox(flavor="fake")
        wrong_snap = BaseSandboxSnapshot(provider="other", ref="r")
        with pytest.raises(ValueError, match="provider 'other'"):
            sandbox.restore(wrong_snap)

    def test_restore_with_matching_provider_falls_through_to_not_impl(
        self,
    ) -> None:
        sandbox = _make_sandbox(flavor="fake")
        matching_snap = BaseSandboxSnapshot(provider="fake", ref="r")
        # Provider check passes; base then raises NotImplementedError so
        # flavors must explicitly opt in.
        with pytest.raises(NotImplementedError):
            sandbox.restore(matching_snap)


class TestSandboxExecError:
    def test_is_runtime_error_subclass(self) -> None:
        assert issubclass(SandboxExecError, RuntimeError)

    def test_message_passes_through(self) -> None:
        err = SandboxExecError("command not found: foo")
        assert "command not found" in str(err)


class TestCreateSessionIsRequired:
    def test_create_session_returns_session(self) -> None:
        # Sanity: the only abstract method on BaseSandbox is create_session;
        # our fake implements it and returns a working session.
        session = _make_sandbox().create_session()
        assert isinstance(session, SandboxSession)
        assert session.id == "sess-1"
