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
"""Encoding for stream events on the broker wire."""

from zenml.models import StreamEvent

# Version byte: lets us swap the body format (msgpack, etc.) without a
# bus-wide migration. Always check on decode.
_VERSION_V1 = 0x01


class EventEncodingError(Exception):
    """Raised when a broker payload cannot be decoded as a StreamEvent."""


def encode(event: StreamEvent) -> bytes:
    """Serialize a StreamEvent for transport on the broker wire."""
    return bytes([_VERSION_V1]) + event.model_dump_json().encode("utf-8")


def decode(data: bytes) -> StreamEvent:
    """Deserialize a broker payload back into a StreamEvent."""
    if not data:
        raise EventEncodingError("Empty event payload")
    version = data[0]
    body = data[1:]
    if version == _VERSION_V1:
        return StreamEvent.model_validate_json(body)
    raise EventEncodingError(f"Unsupported event encoding version: {version}")
