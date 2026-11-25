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
"""Items the stream broadcaster delivers to subscribers."""

from dataclasses import dataclass
from typing import FrozenSet, Union

from zenml.utils.enum_utils import StrEnum
from zenml.zen_server.streaming.brokers.base import BrokerEntry


class SSEEventName(StrEnum):
    """Reserved SSE `event:` names emitted by the run-events stream.

    These are wire protocol — values are part of the public contract
    with SSE consumers and must not be renamed without a deprecation
    path.
    """

    END = "end"
    GAP = "gap"
    ERROR = "error"
    CURSOR = "cursor"
    SYSTEM = "system"


RESERVED_STREAM_EVENT_KINDS: FrozenSet[str] = frozenset(SSEEventName.values())


class GapReason(StrEnum):
    """Reason a `GapMarker` was emitted."""

    SHUTDOWN = "shutdown"
    """This server replica is shutting down."""

    OUTAGE = "outage"
    """Broker outage."""

    OVERFLOW = "overflow"
    """The subscriber's queue is full and some old events were dropped."""


@dataclass(frozen=True)
class GapMarker:
    """Gap marker."""

    reason: GapReason


@dataclass(frozen=True)
class EndMarker:
    """End marker."""


StreamItem = Union[BrokerEntry, GapMarker, EndMarker]
