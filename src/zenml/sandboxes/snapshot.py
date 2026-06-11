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
"""Sandbox snapshot."""

from typing import Any, Dict
from uuid import UUID

from pydantic import BaseModel, Field


class SandboxSnapshot(BaseModel):
    """Sandbox snapshot."""

    sandbox_id: UUID = Field(
        description="The ID of the sandbox that produced this snapshot."
    )
    ref: str = Field(
        description="Flavor-specific reference to the sandbox session."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional snapshot metadata.",
    )
