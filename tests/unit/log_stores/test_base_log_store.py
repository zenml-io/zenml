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
"""Tests for the pagination helpers shared by all log stores."""

import base64
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

import pytest

from zenml.constants import LOGS_MAX_ENTRIES_PER_REQUEST
from zenml.enums import StackComponentType
from zenml.log_stores.base_log_store import (
    BaseLogStore,
    BaseLogStoreConfig,
)
from zenml.models import (
    LogsEntriesFilter,
    LogsEntriesResponse,
    LogsResponse,
)


class StubLogStore(BaseLogStore):
    """A log store that does nothing but expose the shared helpers."""

    @property
    def default_query_size(self) -> int:
        """A page size small enough to tell apart from any global default.

        Returns:
            The default number of entries per page.
        """
        return 25

    def emit(self, origin, record, metadata=None) -> None:
        """Drop the record.

        Args:
            origin: Ignored.
            record: Ignored.
            metadata: Ignored.
        """

    def _release_origin(self, origin) -> None:
        """Do nothing.

        Args:
            origin: Ignored.
        """

    def flush(self, blocking: bool = True) -> None:
        """Do nothing.

        Args:
            blocking: Ignored.
        """

    def fetch(
        self,
        logs_model: LogsResponse,
        limit: Optional[int] = None,
        before: Optional[str] = None,
        after: Optional[str] = None,
        filter_: Optional[LogsEntriesFilter] = None,
    ) -> LogsEntriesResponse:
        """Not used by these tests.

        Args:
            logs_model: Ignored.
            limit: Ignored.
            before: Ignored.
            after: Ignored.
            filter_: Ignored.

        Returns:
            An empty page.
        """
        return LogsEntriesResponse()


@pytest.fixture
def log_store() -> StubLogStore:
    """A log store with a small page size."""
    return StubLogStore(
        name="stub",
        id=uuid4(),
        config=BaseLogStoreConfig(),
        flavor="stub",
        type=StackComponentType.LOG_STORE,
        user=uuid4(),
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )


def test_cursor_round_trip(log_store):
    """A cursor carries its payload back unchanged."""
    token = log_store.encode_cursor(
        timestamp="2026-01-01T00:00:00Z", ids=["a"]
    )

    assert log_store.decode_cursor(token) == {
        "timestamp": "2026-01-01T00:00:00Z",
        "ids": ["a"],
    }


def test_cursor_is_url_safe(log_store):
    """A cursor is passed around as a query parameter."""
    token = log_store.encode_cursor(cursor="a/b+c=d?e&f")

    assert "/" not in token
    assert "+" not in token


@pytest.mark.parametrize(
    "token",
    [
        "not base64 at all",
        base64.urlsafe_b64encode(b"not json").decode(),
        base64.urlsafe_b64encode(b'"a string"').decode(),
    ],
)
def test_invalid_cursors_are_rejected(log_store, token):
    """A cursor that was not issued by a log store is an error."""
    with pytest.raises(ValueError, match="Invalid pagination cursor"):
        log_store.decode_cursor(token)


def test_limit_defaults_to_the_page_size_of_the_log_store(log_store):
    """A caller that asks for no limit gets the log store's page size."""
    assert log_store.resolve_limit(None) == 25


def test_limit_is_capped(log_store):
    """No single request may ask for an unbounded number of entries."""
    assert (
        log_store.resolve_limit(LOGS_MAX_ENTRIES_PER_REQUEST * 2)
        == LOGS_MAX_ENTRIES_PER_REQUEST
    )


@pytest.mark.parametrize("limit", [0, -1])
def test_non_positive_limits_are_rejected(log_store, limit):
    """A page of zero or fewer entries is meaningless."""
    with pytest.raises(ValueError, match="positive integer"):
        log_store.resolve_limit(limit)
