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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Tests for dynamic webhook target filters."""

import pytest
from pydantic import ValidationError

from zenml.webhooks import DynamicWebhookTargetEvent


def test_dynamic_target_matches_event_type_and_body_filters() -> None:
    """Every body filter is required and JSON scalars are canonicalized."""
    target = DynamicWebhookTargetEvent(
        event_type="startswith:pull_",
        filters={
            "action": ["opened", "reopened"],
            "pull_request.merged": "false",
            "pull_request.number": "42",
            "pull_request.milestone": "null",
            'metadata["build.version"]': "equals:v1:beta",
            '["123"].value': "root-key",
            "history_items[0].after.status": "contains:progress",
        },
    )
    payload = {
        "action": "opened",
        "pull_request": {
            "merged": False,
            "number": 42,
            "milestone": None,
        },
        "metadata": {"build.version": "v1:beta"},
        "123": {"value": "root-key"},
        "history_items": [{"after": {"status": "in progress"}}],
    }

    assert target.matches(event_type="pull_request", payload=payload)
    assert not target.matches(event_type="issues", payload=payload)
    assert not target.matches(
        event_type="pull_request", payload={**payload, "action": "closed"}
    )
    assert target.model_dump(mode="json") == {
        "type": "dynamic",
        "event_type": "startswith:pull_",
        "filters": {
            "action": ["opened", "reopened"],
            "pull_request.merged": "false",
            "pull_request.number": "42",
            "pull_request.milestone": "null",
            'metadata["build.version"]': "equals:v1:beta",
            '["123"].value': "root-key",
            "history_items[0].after.status": "contains:progress",
        },
    }


def test_dynamic_target_wildcard_collection_semantics() -> None:
    """Positive predicates use any and negative predicates use all."""
    payload = {
        "labels": [
            {"name": "bug"},
            {"missing": "ignored"},
            {"name": "priority-high"},
        ]
    }

    assert DynamicWebhookTargetEvent(
        event_type="issues", filters={"labels[*].name": "contains:priority"}
    ).matches(event_type="issues", payload=payload)
    assert DynamicWebhookTargetEvent(
        event_type="issues",
        filters={"labels[*].name": "notcontains:documentation"},
    ).matches(event_type="issues", payload=payload)
    assert not DynamicWebhookTargetEvent(
        event_type="issues", filters={"labels[*].name": "notcontains:bug"}
    ).matches(event_type="issues", payload=payload)


def test_dynamic_wildcard_filters_are_independent() -> None:
    """Separate wildcard paths do not require one correlated array item."""
    target = DynamicWebhookTargetEvent(
        event_type="users.changed",
        filters={
            "users[*].role": "admin",
            "users[*].active": "true",
        },
    )

    assert target.matches(
        event_type="users.changed",
        payload={
            "users": [
                {"role": "admin", "active": False},
                {"role": "viewer", "active": True},
            ]
        },
    )


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"items": []},
        {"items": [{"name": "expected"}]},
        {"items": {"0": {"name": "expected"}}},
        {"items": [["expected"]]},
    ],
)
def test_dynamic_target_payload_mismatches_are_silent(
    payload: dict[str, object],
) -> None:
    """Missing, mismatched, and non-scalar terminal values do not match."""
    target = DynamicWebhookTargetEvent(
        event_type="event", filters={"items[1].name": "expected"}
    )

    assert not target.matches(event_type="event", payload=payload)


@pytest.mark.parametrize(
    "path",
    [
        "",
        ".event",
        "event..type",
        "items[-1].name",
        "items.0.name",
        "items[*].children[*].name",
        "a.b.c.d.e.f.g.h.i",
        "a" * 513,
        "metadata['single-quotes']",
        'metadata["unterminated]',
    ],
)
def test_dynamic_target_rejects_invalid_paths(path: str) -> None:
    """Configured paths must follow the constrained path grammar."""
    with pytest.raises(ValidationError):
        DynamicWebhookTargetEvent(event_type="event", filters={path: "value"})


@pytest.mark.parametrize(
    "kwargs",
    [
        {"event_type": None},
        {"event_type": ""},
        {"event_type": []},
        {"event_type": [str(index) for index in range(11)]},
        {"event_type": "x" * 513},
        {"event_type": 'oneof:["0","1","2","3","4","5","6","7","8","9","10"]'},
        {"event_type": "event", "filters": {"key": None}},
        {"event_type": "event", "filters": {"key": []}},
        {
            "event_type": "event",
            "filters": {f"key{index}": "value" for index in range(11)},
        },
    ],
)
def test_dynamic_target_rejects_configuration_over_limits(
    kwargs: dict[str, object],
) -> None:
    """Dynamic target input is bounded independently of payload size."""
    with pytest.raises(ValidationError):
        DynamicWebhookTargetEvent.model_validate(kwargs)


def test_unrecognized_operator_prefix_is_literal_equality() -> None:
    """Colon-containing values are operators only for recognized prefixes."""
    target = DynamicWebhookTargetEvent(
        event_type="event",
        filters={
            "url": "https://example.com/hook",
            "state": "equals:startswith:queued",
        },
    )

    assert target.matches(
        event_type="event",
        payload={
            "url": "https://example.com/hook",
            "state": "startswith:queued",
        },
    )
