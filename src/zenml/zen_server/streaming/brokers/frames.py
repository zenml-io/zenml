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
"""Frame types stored as payloads in the broker."""

import json
from typing import Annotated, FrozenSet, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from zenml.constants import STREAM_EVENT_PAYLOAD_BYTES_MAX
from zenml.logger import get_logger
from zenml.models import StreamEvent

logger = get_logger(__name__)

_ENVELOPE_OVERHEAD_BYTES: int = 4 * 1024
EVENT_PAYLOAD_BYTES_MAX: int = (
    STREAM_EVENT_PAYLOAD_BYTES_MAX + _ENVELOPE_OVERHEAD_BYTES
)


class EventFrame(BaseModel):
    """Event frame."""

    model_config = ConfigDict(frozen=True)

    type: Literal["event"] = "event"
    event: StreamEvent


class EndFrame(BaseModel):
    """End frame."""

    model_config = ConfigDict(frozen=True)

    type: Literal["end"] = "end"


class UnknownFrame(BaseModel):
    """Unknown frame."""

    model_config = ConfigDict(frozen=True)

    type: str


BrokerFrame = Annotated[
    Union[EventFrame, EndFrame], Field(discriminator="type")
]

_frame_adapter: TypeAdapter[BrokerFrame] = TypeAdapter(BrokerFrame)

DecodedFrame = Union[EventFrame, EndFrame, UnknownFrame]

_KNOWN_FRAME_TYPES: FrozenSet[str] = frozenset({"event", "end"})


def encode_frame(frame: BrokerFrame) -> bytes:
    """Encode a frame as JSON bytes for the broker.

    Args:
        frame: The frame to encode.

    Returns:
        The JSON-encoded payload.
    """
    return _frame_adapter.dump_json(frame)


def decode_frame(payload: bytes) -> DecodedFrame:
    """Decode a broker payload into a frame.

    Args:
        payload: Raw bytes pulled from the broker.

    Returns:
        A parsed frame, or `UnknownFrame` for unknown/corrupt payloads.
    """
    try:
        return _frame_adapter.validate_json(payload)
    except ValidationError:
        pass

    try:
        parsed = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return UnknownFrame(type="?")

    type_value: Optional[object] = (
        parsed.get("type") if isinstance(parsed, dict) else None
    )
    type_str = str(type_value) if type_value else "?"
    if type_str in _KNOWN_FRAME_TYPES:
        # Known type with malformed body = server-side corrupt frame.
        logger.warning("Corrupt %r frame on the broker.", type_str)

    return UnknownFrame(type=type_str)
