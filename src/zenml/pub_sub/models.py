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
"""Models for the pub/sub layer."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

from zenml.utils.enum_utils import StrEnum


class SnapshotExecutionPayload(BaseModel):
    """Payload class for snapshot async execution."""

    snapshot_id: UUID
    trigger_type: Literal["REST", "SCHEDULE", "WEBHOOK"]
    trigger_id: UUID | None = None


class CriticalEventType(StrEnum):
    """Critical event types enum."""

    READ_FAILED = "read_operation_failed"
    ACK_FAILED = "ack_operation_failed"
    ENCODE_FAILED = "encode_operation_failed"
    SEND_FAILED = "send_operation_failed"
    EXECUTE_FAILED = "execute_operation_failed"


class CriticalEvent(BaseModel, arbitrary_types_allowed=True):
    """Class capturing a critical event basic properties."""

    value: CriticalEventType
    description: str
    created_at: datetime
    exception: Exception | None = None


class MessagePayload(BaseModel):
    """Class capturing a message payload basic properties."""

    id: str
    body: SnapshotExecutionPayload | None


class MessageEnvelope(BaseModel):
    """Envelope class for consumer operations (raw payload & de-serialized payload)."""

    payload: MessagePayload
    raw_message: Any

    @property
    def id(self) -> str:
        """Implements the 'id' property.

        Returns:
            The ID of the message payload.
        """
        return self.payload.id
