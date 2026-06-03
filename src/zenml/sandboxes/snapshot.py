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

from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class BaseSandboxSnapshot(BaseModel):
    """Serializable handle to a captured sandbox session state."""

    @model_validator(mode="before")
    @classmethod
    def _accept_legacy_provider(cls, data: Any) -> Any:
        """Map the pre-rename ``provider`` field to ``sandbox_flavor``.

        Older persisted snapshots (before the field rename) used
        ``provider`` for what is now ``sandbox_flavor``. Accept it
        transparently so loaded artifacts still round-trip.

        Args:
            data: Raw input passed to ``BaseSandboxSnapshot``.

        Returns:
            The same input, with ``provider`` aliased to
            ``sandbox_flavor`` when present.
        """
        if isinstance(data, dict) and "sandbox_flavor" not in data:
            if "provider" in data:
                data = {**data, "sandbox_flavor": data["provider"]}
        return data

    sandbox_flavor: str = Field(
        description="Flavor name that produced this snapshot (e.g. "
        "'modal'). Snapshots cannot be restored across flavors."
    )
    component_id: Optional[UUID] = Field(
        default=None,
        description="UUID of the sandbox stack component that produced "
        "this snapshot. When set, restore is gated to the same "
        "component identity. Useful when one cluster has multiple "
        "sandbox components (different service connectors, namespaces, "
        "regions) where the provider-side `ref` is not portable across "
        "components.",
    )
    ref: str = Field(
        description="Provider-specific reference (e.g. a Modal Image "
        "id, a k8s pod-snapshot resource name). Opaque to ZenML."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional auxiliary fields (created_at, size, cost) "
        "the flavor wants preserved with the snapshot.",
    )
