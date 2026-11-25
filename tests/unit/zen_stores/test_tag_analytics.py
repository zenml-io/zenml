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
"""Tests that creating a tag sends no analytics event."""

from typing import Any, List

import pytest

from zenml.analytics import utils as analytics_utils
from zenml.client import Client
from zenml.models import TagRequest


def test_create_tag_sends_no_analytics_event(
    clean_client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Creating a tag must not make an analytics call.

    The analytics server drops `Tag created`, so sending it only added a
    blocking HTTPS call to every tag creation.

    Args:
        clean_client: A clean ZenML client.
        monkeypatch: The pytest monkeypatch fixture.
    """
    tracked_events: List[Any] = []
    monkeypatch.setattr(
        analytics_utils,
        "track",
        lambda event, *args, **kwargs: tracked_events.append(event),
    )

    clean_client.zen_store.create_tag(TagRequest(name="analytics-free-tag"))

    assert tracked_events == []
