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
"""Tagged wire envelope for broker payloads.

Producer events and server-emitted control frames share one Redis /
in-memory stream. The envelope keeps the two cleanly separated so
producers can never forge a control frame.
"""

import json
from dataclasses import dataclass
from typing import Annotated, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from zenml.models import StreamEvent


class EventFrame(BaseModel):
    """A producer-published event."""

    type: Literal["event"] = "event"
    event: StreamEvent


class EndFrame(BaseModel):
    """Server-emitted terminal sentinel for a pipeline run's stream."""

    type: Literal["end"] = "end"
    pipeline_run_id: UUID


@dataclass(frozen=True)
class UnknownFrame:
    """Forward-compat sentinel for wire frame types this replica doesn't know.

    Older replicas may read frames a newer replica wrote (rolling
    deploys, mixed clusters). Returning this sentinel keeps the
    consumer's `Last-Event-ID` advancing past the unknown frame
    instead of erroring out and stranding the stream.
    """

    type: str


WireFrame = Annotated[Union[EventFrame, EndFrame], Field(discriminator="type")]

_wire_adapter: TypeAdapter[WireFrame] = TypeAdapter(WireFrame)

DecodedFrame = Union[EventFrame, EndFrame, UnknownFrame]


def encode_frame(frame: WireFrame) -> bytes:
    """Encode a wire frame as JSON bytes for the broker."""
    return _wire_adapter.dump_json(frame)


def decode_frame(payload: bytes) -> DecodedFrame:
    """Decode a broker payload into a wire frame.

    Returns an `UnknownFrame` for payloads whose `type` this replica
    doesn't know. Raises only on JSON-malformed bytes.
    """
    try:
        return _wire_adapter.validate_json(payload)
    except ValidationError:
        try:
            parsed = json.loads(payload)
            type_value: Optional[object] = (
                parsed.get("type") if isinstance(parsed, dict) else None
            )
        except Exception:
            raise
        return UnknownFrame(type=str(type_value) if type_value else "?")
