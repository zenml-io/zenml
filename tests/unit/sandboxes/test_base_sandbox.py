#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Tests for base sandbox metadata emission."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from zenml.enums import StackComponentType
from zenml.sandboxes import (
    BaseSandbox,
    BaseSandboxConfig,
    NetworkPolicy,
    SandboxCapability,
    SandboxSession,
    SandboxSessionMetadata,
)


class _DummySandbox(BaseSandbox):
    """Minimal sandbox implementation used to test base metadata behavior."""

    @property
    def capabilities(self):
        """Capabilities supported by this test sandbox."""
        return {SandboxCapability.STREAMING_OUTPUT}

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

        This test implementation does not create sessions.
        """
        raise NotImplementedError


def _create_sandbox() -> _DummySandbox:
    """Creates a sandbox instance for metadata tests."""
    return _DummySandbox(
        name="dummy-sandbox",
        id=uuid4(),
        config=BaseSandboxConfig(),
        flavor="dummy",
        type=StackComponentType.SANDBOX,
        user=None,
        created=datetime.utcnow(),
        updated=datetime.utcnow(),
    )


def test_get_step_run_metadata_returns_structured_dict() -> None:
    """Ensures sandbox metadata is emitted as a structured dict."""
    sandbox = _create_sandbox()
    sandbox._track_session(
        SandboxSessionMetadata(
            session_id="session-1",
            provider="dummy",
            duration_seconds=3.5,
            commands_executed=2,
            extra={"region": "us-east"},
        )
    )

    metadata = sandbox.get_step_run_metadata(info=object())

    assert "sandbox_info" in metadata
    sandbox_info = metadata["sandbox_info"]
    assert isinstance(sandbox_info, dict)
    assert sandbox_info["provider"] == "dummy"
    assert sandbox_info["session_count"] == 1
    assert isinstance(sandbox_info["sessions"], list)
    assert sandbox_info["sessions"][0]["session_id"] == "session-1"
    assert sandbox_info["sessions"][0]["extra"]["region"] == "us-east"
