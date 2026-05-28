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
"""Snapshot model shared by all sandbox flavors that support restore."""

from typing import Any, Dict

from pydantic import BaseModel, Field


class BaseSandboxSnapshot(BaseModel):
    """Serializable handle to a captured Sandbox Session state.

    Round-trips via ``session.snapshot() → BaseSandboxSnapshot`` and
    ``sandbox.restore(snapshot) → SandboxSession``. Each flavor subclasses
    this model and ships a dedicated materializer for it.

    The ``provider`` field must match the flavor name; ``BaseSandbox.restore``
    rejects cross-flavor snapshots.
    """

    provider: str = Field(
        description="Flavor name that produced this snapshot (e.g. 'modal'). "
        "Snapshots cannot be restored across flavors."
    )
    ref: str = Field(
        description="Provider-specific reference (e.g. a Modal Image id, a "
        "k8s checkpoint resource name). Opaque to ZenML."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional auxiliary fields (created_at, size, cost) the "
        "flavor wants preserved with the snapshot.",
    )
