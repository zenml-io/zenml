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
"""Models for event streaming in pipeline runs."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.constants import STREAM_EVENT_MAX_BATCH_SIZE


class StreamEvent(BaseModel):
    """Stream event."""

    pipeline_run_id: UUID
    step_run_id: Optional[UUID] = None
    step_name: Optional[str] = None
    kind: str
    correlation_id: Optional[str] = None
    index: Optional[int] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class StreamBatchRequest(BaseModel):
    """Stream batch request."""

    events: List[StreamEvent] = Field(max_length=STREAM_EVENT_MAX_BATCH_SIZE)


class StreamBatchResponse(BaseModel):
    """Stream batch response."""

    count: int
    last_id: Optional[str] = None
