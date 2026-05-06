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
"""Wire models for live event streaming on pipeline runs."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.utils.time_utils import utc_now


class StreamEvent(BaseModel):
    """A single event published to a pipeline run's live stream.

    Lives only in transit (broker, SSE wire) — never persisted to the
    metadata DB. Consumers attribute events to a step via step_run_id /
    step_name. tokens of a single LLM generation are grouped by stream_id
    with a per-stream_id monotonic index.
    """

    version: Literal[1] = 1
    pipeline_run_id: UUID
    step_run_id: Optional[UUID] = None
    step_name: Optional[str] = None
    kind: str = Field(
        description=(
            "Event kind. Free-form at the protocol layer; well-known kinds "
            "include 'token', 'tool_call', 'tool_result', 'reasoning', "
            "'status', 'overflow', 'end'."
        )
    )
    stream_id: Optional[str] = None
    index: Optional[int] = None
    ts: datetime = Field(default_factory=utc_now)
    payload: Dict[str, Any] = Field(default_factory=dict)


class EventBatchRequest(BaseModel):
    """Producer-side batched ingest body for run events."""

    events: List[StreamEvent]


class EventBatchResponse(BaseModel):
    """Server-side response from the batched ingest endpoint."""

    count: int
    last_id: Optional[str] = None
