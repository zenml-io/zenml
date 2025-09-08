#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Capture configuration for ZenML (single, typed)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Capture:
    """Single capture configuration.

    Semantics are derived from context:
    - Batch (orchestrated) runs use blocking publishes.
    - Serving uses async publishes; `memory_only` switches to in-process handoff.

    Only observability toggles are exposed; they never affect dataflow except
    `memory_only`, which is serving-only and ignored elsewhere.
    """

    # Serving-only: run without DB/artifact persistence using in-process handoff
    memory_only: bool = False
    # Observability toggles
    code: bool = True
    logs: bool = True
    metadata: bool = True
    visualizations: bool = True
    metrics: bool = True
