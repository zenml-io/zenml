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
"""Shared fixtures for streaming tests."""

import uuid

import pytest

from zenml.models import StreamEvent


@pytest.fixture
def anyio_backend() -> str:
    """Pin async tests to the asyncio backend."""
    return "asyncio"


def make_event(run_id: uuid.UUID, kind: str = "token") -> StreamEvent:
    """Build a `StreamEvent` with a default payload for test use."""
    return StreamEvent(pipeline_run_id=run_id, kind=kind, payload={"v": 1})
