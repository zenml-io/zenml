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
"""Tests for the implicit model creation used by pipeline and step runs."""

from typing import Any, Dict, List

from pytest_mock import MockerFixture

from zenml.analytics.enums import AnalyticsEvent
from zenml.client import Client
from zenml.models import ModelRequest


def _model_created_events(tracked: Any) -> List[Dict[str, Any]]:
    return [
        call.kwargs["properties"]
        for call in tracked.call_args_list
        if call.kwargs["event"] == AnalyticsEvent.CREATED_MODEL
    ]


def test_get_or_create_model_tracks_only_real_creations(
    clean_client: Client, mocker: MockerFixture
) -> None:
    """An existing model must not emit a failed `Model created` event."""
    store = clean_client.zen_store
    tracked = mocker.patch("zenml.analytics.context.AnalyticsContext.track")
    request = ModelRequest(
        name="implicit_model",
        project=clean_client.active_project.id,
    )

    created, model = store._get_or_create_model(request)

    assert created
    events = _model_created_events(tracked)
    assert len(events) == 1
    assert events[0]["event_success"] is True
    assert events[0]["entity_id"] == model.id

    tracked.reset_mock()
    created_again, existing_model = store._get_or_create_model(request)

    assert not created_again
    assert existing_model.id == model.id
    assert _model_created_events(tracked) == []
