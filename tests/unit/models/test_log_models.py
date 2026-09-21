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
"""Tests for log filter models."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from zenml.enums import LoggingLevels
from zenml.models import LogsEntriesFilter

NOON = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)


@pytest.mark.parametrize("value", [" Error ", "40"])
def test_level_accepts_names_and_numbers(value: str) -> None:
    """Test log level names and numeric values."""
    assert LogsEntriesFilter(level=value).level == LoggingLevels.ERROR


def test_level_rejects_invalid_names() -> None:
    """Test rejection of invalid log levels."""
    with pytest.raises(ValidationError):
        LogsEntriesFilter(level="bogus")


def test_time_bounds_are_made_timezone_aware():
    """Test that naive time bounds are interpreted as UTC."""
    filter_ = LogsEntriesFilter(since=datetime(2026, 1, 1, 12))

    assert filter_.since == NOON


def test_inverted_time_range_is_rejected():
    """Test rejection of inverted time ranges."""
    with pytest.raises(ValidationError, match="must be earlier"):
        LogsEntriesFilter(since=NOON, until=datetime(2026, 1, 1, 11))
