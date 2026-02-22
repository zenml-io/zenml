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
"""Tests for base sandbox metadata and cleanup warning behavior."""

from datetime import datetime
from types import SimpleNamespace
from typing import Dict, List, Optional, Set
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from zenml.enums import StackComponentType
from zenml.sandboxes import (
    BaseSandbox,
    BaseSandboxConfig,
    NetworkPolicy,
    SandboxCapability,
    SandboxSession,
    SandboxSessionMetadata,
)


class _MetadataSandbox(BaseSandbox):
    """Minimal sandbox implementation for metadata tests."""

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
        """Creates a sandbox session.

        This test class does not create real sessions.
        """
        raise NotImplementedError


def _create_sandbox(capabilities: Set[SandboxCapability]) -> _MetadataSandbox:
    """Creates a sandbox instance for metadata tests."""
    return _MetadataSandbox(
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


def test_get_step_run_metadata_returns_empty_dict_without_sessions() -> None:
    """Tests that no metadata is emitted when no sessions are tracked."""
    sandbox = _create_sandbox({SandboxCapability.STREAMING_OUTPUT})

    assert sandbox.get_step_run_metadata(info=object()) == {}


def test_get_step_run_metadata_aggregates_multiple_sessions() -> None:
    """Tests multi-session aggregation and serialization behavior."""
    sandbox = _create_sandbox(
        {SandboxCapability.STREAMING_OUTPUT, SandboxCapability.SNAPSHOTS}
    )
    sandbox._track_session(
        SandboxSessionMetadata(
            session_id="session-1",
            provider="dummy",
            duration_seconds=1.5,
            commands_executed=2,
            estimated_cost_usd=1.0,
            extra={"region": "eu-west"},
        )
    )
    sandbox._track_session(
        SandboxSessionMetadata(
            session_id="session-2",
            provider="dummy",
            duration_seconds=2.25,
            commands_executed=3,
            estimated_cost_usd=None,
        )
    )

    metadata = sandbox.get_step_run_metadata(info=object())

    sandbox_info = metadata["sandbox_info"]
    assert sandbox_info["provider"] == "dummy"
    assert sandbox_info["session_count"] == 2
    assert sandbox_info["total_duration_seconds"] == pytest.approx(3.75)
    assert sandbox_info["total_commands_executed"] == 5
    assert sandbox_info["total_estimated_cost_usd"] == pytest.approx(1.0)
    assert sandbox_info["capabilities"] == ["snapshots", "streaming"]


def test_cleanup_step_run_warns_only_for_declared_sandbox_without_sessions(
    monkeypatch,
) -> None:
    """Tests cleanup warnings for declared-but-unused sandboxes."""
    warning_mock = MagicMock()
    monkeypatch.setattr(
        "zenml.sandboxes.base_sandbox.logger.warning", warning_mock
    )

    no_session_sandbox = _create_sandbox({SandboxCapability.STREAMING_OUTPUT})
    info_with_sandbox = SimpleNamespace(
        config=SimpleNamespace(sandbox=True, name="sandbox_step")
    )
    no_session_sandbox.cleanup_step_run(
        info=info_with_sandbox,
        step_failed=False,
    )

    warning_mock.assert_called_once()
    warning_message, step_name = warning_mock.call_args.args
    assert (
        "declared sandbox=True but no sandbox sessions were created"
        in warning_message
    )
    assert step_name == "sandbox_step"

    warning_mock.reset_mock()

    info_without_sandbox = SimpleNamespace(
        config=SimpleNamespace(sandbox=False, name="plain_step")
    )
    no_session_sandbox.cleanup_step_run(
        info=info_without_sandbox,
        step_failed=False,
    )
    warning_mock.assert_not_called()

    warning_mock.reset_mock()

    sandbox_with_session = _create_sandbox(
        {SandboxCapability.STREAMING_OUTPUT}
    )
    sandbox_with_session._track_session(
        SandboxSessionMetadata(
            session_id="session-3",
            provider="dummy",
            duration_seconds=1.0,
        )
    )
    sandbox_with_session.cleanup_step_run(
        info=info_with_sandbox,
        step_failed=False,
    )

    warning_mock.assert_not_called()
