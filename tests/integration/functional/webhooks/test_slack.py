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
"""Slack webhook provider and intake endpoint tests."""

import asyncio
import hashlib
import hmac
import json
from collections.abc import Mapping
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from zenml.webhooks import (
    ParsedWebhookDelivery,
    WebhookAuthenticationError,
    WebhookEvent,
    WebhookIntakeResponse,
    WebhookPayloadError,
    WebhookPreValidationResult,
)
from zenml.webhooks.providers import (
    BuiltinWebhookType,
    get_webhook_provider,
)
from zenml.webhooks.providers.slack import (
    SLACK_REQUEST_TIMESTAMP_HEADER,
    SLACK_SIGNATURE_HEADER,
    AppMentionEventFilter,
    FileSharedEventFilter,
    MessageEventFilter,
    MessageMetadataPostedEventFilter,
    MessageMetadataUpdatedEventFilter,
    ReactionAddedEventFilter,
    ReactionRemovedEventFilter,
    SlackAppMentionEvent,
    SlackFileSharedEvent,
    SlackMessageEvent,
    SlackMessageMetadata,
    SlackMessageMetadataPostedEvent,
    SlackMessageMetadataUpdatedEvent,
    SlackReactionAddedEvent,
    SlackReactionItem,
    SlackReactionRemovedEvent,
    SlackWebhookConfiguration,
    SlackWebhookEventType,
    SlackWebhookProvider,
)
from zenml.zen_server.routers import webhook_endpoints as endpoints

SLACK_EVENT_TIME = 1788300000
SLACK_EVENT_TS = "1788300000.000000"


def _slack_signature(secret: str, timestamp: str, body: bytes) -> str:
    signature_base = f"v0:{timestamp}:".encode() + body
    return (
        "v0="
        + hmac.new(secret.encode(), signature_base, hashlib.sha256).hexdigest()
    )


def _slack_headers(
    *,
    body: bytes,
    secret: str = "webhook-secret",
    timestamp: str = "1788300000",
) -> dict[str, str]:
    return {
        SLACK_REQUEST_TIMESTAMP_HEADER: timestamp,
        SLACK_SIGNATURE_HEADER: _slack_signature(secret, timestamp, body),
    }


class _Store:
    def __init__(self) -> None:
        self.records = []
        self.project_id = uuid4()

    def get_webhook_intake_config(self, webhook_id, expected_webhook_type):
        assert expected_webhook_type == "slack"
        return SimpleNamespace(
            webhook_type="slack",
            active=True,
            project_id=self.project_id,
            secret=SecretStr("webhook-secret"),
        )

    def record_webhook_event(self, webhook_id, update):
        self.records.append((webhook_id, update))


def _install_endpoint_dependencies(monkeypatch, store: _Store) -> None:
    monkeypatch.setattr(endpoints, "zen_store", lambda: store)
    monkeypatch.setattr(
        endpoints, "get_webhook_provider", lambda _: SlackWebhookProvider()
    )
    monkeypatch.setattr(
        "zenml.webhooks.providers.slack.time.time", lambda: 1788300000.0
    )


def test_slack_provider_is_registered() -> None:
    """The registry exposes Slack as a built-in provider."""
    provider = get_webhook_provider(BuiltinWebhookType.SLACK)

    assert isinstance(provider, SlackWebhookProvider)
    assert provider.webhook_type == BuiltinWebhookType.SLACK


def test_slack_message_event_types_preserve_wire_and_semantic_names() -> None:
    """Slack intake and ZenML triggers share the Slack message name."""
    assert SlackWebhookEventType.MESSAGE == "message"


def test_slack_pre_validation_always_processes() -> None:
    """Slack leaves authentication metadata checks to authentication."""
    result = asyncio.run(SlackWebhookProvider().pre_validate(headers={}))

    assert result == WebhookPreValidationResult.PROCESS


def test_slack_authenticates_exact_raw_body(monkeypatch) -> None:
    """Slack authentication signs the timestamp and exact raw body."""
    provider = SlackWebhookProvider()
    secret = "slack-signing-secret"
    timestamp = "1788300000"
    signed_body = b'{"type":"event_callback"}'
    headers = _slack_headers(
        body=signed_body, secret=secret, timestamp=timestamp
    )
    monkeypatch.setattr(
        "zenml.webhooks.providers.slack.time.time",
        lambda: float(timestamp),
    )

    provider.authenticate(signed_body, headers, secret)

    with pytest.raises(WebhookAuthenticationError):
        provider.authenticate(b'{"type": "event_callback"}', headers, secret)


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {SLACK_REQUEST_TIMESTAMP_HEADER: "1788300000"},
        {
            SLACK_REQUEST_TIMESTAMP_HEADER: "1788300000",
            SLACK_SIGNATURE_HEADER: "sha256=wrong-version",
        },
        {SLACK_SIGNATURE_HEADER: "v0=invalid"},
        {
            SLACK_REQUEST_TIMESTAMP_HEADER: "not-a-timestamp",
            SLACK_SIGNATURE_HEADER: "v0=invalid",
        },
        {
            SLACK_REQUEST_TIMESTAMP_HEADER: "1" * 4301,
            SLACK_SIGNATURE_HEADER: "v0=invalid",
        },
        {
            SLACK_REQUEST_TIMESTAMP_HEADER: "1788300000",
            SLACK_SIGNATURE_HEADER: "v0=invalid",
        },
    ],
)
def test_slack_rejects_invalid_authentication_metadata(
    monkeypatch, headers: Mapping[str, str]
) -> None:
    """Slack authentication rejects missing or malformed metadata."""
    monkeypatch.setattr(
        "zenml.webhooks.providers.slack.time.time", lambda: 1788300000.0
    )

    with pytest.raises(WebhookAuthenticationError):
        SlackWebhookProvider().authenticate(
            b'{"type":"event_callback"}', headers, "secret"
        )


@pytest.mark.parametrize("timestamp", ["1788299699", "1788300301"])
def test_slack_rejects_stale_and_future_timestamps(
    monkeypatch, timestamp: str
) -> None:
    """Slack rejects timestamps outside the five-minute tolerance."""
    body = b'{"type":"event_callback"}'
    secret = "secret"
    monkeypatch.setattr(
        "zenml.webhooks.providers.slack.time.time", lambda: 1788300000.0
    )

    with pytest.raises(WebhookAuthenticationError, match="tolerance"):
        SlackWebhookProvider().authenticate(
            body,
            _slack_headers(body=body, secret=secret, timestamp=timestamp),
            secret,
        )


def test_slack_parses_event_callback() -> None:
    """Slack callbacks preserve the envelope and event identity."""
    payload = {
        "type": "event_callback",
        "team_id": "T123",
        "event_id": "Ev123",
        "event": {"type": "app_mention", "text": "Investigate this"},
    }

    delivery = SlackWebhookProvider().parse_delivery(
        json.dumps(payload).encode(), {}
    )

    assert delivery.event is not None
    assert delivery.event.event_type == "app_mention"
    assert delivery.event.delivery_id == "Ev123"
    assert delivery.event.payload == payload
    assert delivery.response == WebhookIntakeResponse(status_code=200)


@pytest.mark.parametrize(
    "payload",
    [
        {"type": "event_callback"},
        {"type": "event_callback", "event": []},
        {"type": "event_callback", "event": {}},
        {"type": "event_callback", "event": {"type": ""}},
        {"type": "event_callback", "event": {"type": "message"}},
        {
            "type": "event_callback",
            "event": {"type": "message"},
            "event_id": "",
        },
    ],
)
def test_slack_rejects_malformed_event_callback(
    payload: dict[str, object],
) -> None:
    """Slack callbacks require an inner type and delivery ID."""
    with pytest.raises(WebhookPayloadError):
        SlackWebhookProvider().parse_delivery(json.dumps(payload).encode(), {})


@pytest.mark.parametrize("body", [b"not-json", b"[]", b'"scalar"'])
def test_slack_rejects_invalid_json_envelopes(body: bytes) -> None:
    """Slack requires a top-level JSON object."""
    with pytest.raises(WebhookPayloadError):
        SlackWebhookProvider().parse_delivery(body, {})


def test_slack_url_verification_returns_challenge_without_event() -> None:
    """URL verification returns the exact plaintext challenge."""
    delivery = SlackWebhookProvider().parse_delivery(
        b'{"type":"url_verification","challenge":"challenge-value"}', {}
    )

    assert delivery == ParsedWebhookDelivery(
        event=None,
        response=WebhookIntakeResponse(
            status_code=200,
            body="challenge-value",
            media_type="text/plain",
        ),
    )


@pytest.mark.parametrize("challenge", [None, "", 123])
def test_slack_url_verification_rejects_invalid_challenge(
    challenge: object,
) -> None:
    """URL verification requires a non-empty string challenge."""
    body = json.dumps(
        {"type": "url_verification", "challenge": challenge}
    ).encode()

    with pytest.raises(WebhookPayloadError, match="challenge"):
        SlackWebhookProvider().parse_delivery(body, {})


def test_slack_accepts_app_rate_limited_without_event() -> None:
    """Rate-limit notifications are successful control deliveries."""
    delivery = SlackWebhookProvider().parse_delivery(
        json.dumps(
            {
                "type": "app_rate_limited",
                "team_id": "T123",
                "api_app_id": "A123",
                "minute_rate_limited": 1788300000,
            }
        ).encode(),
        {},
    )

    assert delivery == ParsedWebhookDelivery(
        event=None,
        response=WebhookIntakeResponse(status_code=200),
    )


@pytest.mark.parametrize(
    "payload",
    [
        {
            "type": "app_rate_limited",
            "api_app_id": "A123",
            "minute_rate_limited": 1788300000,
        },
        {
            "type": "app_rate_limited",
            "team_id": "T123",
            "minute_rate_limited": 1788300000,
        },
        {
            "type": "app_rate_limited",
            "team_id": "T123",
            "api_app_id": "A123",
            "minute_rate_limited": True,
        },
    ],
)
def test_slack_rejects_malformed_rate_limit_deliveries(
    payload: dict[str, object],
) -> None:
    """Rate-limit notifications require their documented identity fields."""
    with pytest.raises(WebhookPayloadError, match="rate-limit"):
        SlackWebhookProvider().parse_delivery(json.dumps(payload).encode(), {})


@pytest.mark.parametrize("delivery_type", [None, "", "future_control"])
def test_slack_rejects_unsupported_delivery_types(
    delivery_type: str | None,
) -> None:
    """Slack accepts only its supported delivery-envelope catalog."""
    with pytest.raises(WebhookPayloadError):
        SlackWebhookProvider().parse_delivery(
            json.dumps({"type": delivery_type}).encode(), {}
        )


def test_slack_configuration_accepts_all_typed_targets() -> None:
    """Slack configuration accepts all targets and ignores removed fields."""
    provider = SlackWebhookProvider()
    configuration = provider.validate_configuration(
        {
            "target_events": [
                {
                    "type": "app_mention",
                    "channel_id": "startswith:C",
                    "user_id": 'oneof:["U123","U456"]',
                    "text": "contains:deploy",
                    "threaded": True,
                },
                {
                    "type": "message",
                    "text": "startswith:deploy ",
                    "channel_type": "channel",
                    "subtype": ["message_changed", "message_deleted"],
                },
                {
                    "type": "reaction_added",
                    "reaction": "notequals:thumbsdown",
                },
                {"type": "reaction_removed", "item_type": "message"},
                {
                    "type": "message_metadata_posted",
                    "metadata_event_type": "startswith:zenml.",
                },
                {
                    "type": "message_metadata_updated",
                    "app_id": "A123",
                },
                {"type": "file_shared", "file_id": "endswith:123"},
            ],
            "removed_provider_option": True,
        }
    )

    assert configuration == SlackWebhookConfiguration(
        target_events=[
            AppMentionEventFilter(
                channel_id="startswith:C",
                user_id='oneof:["U123","U456"]',
                text="contains:deploy",
                threaded=True,
            ),
            MessageEventFilter(
                text="startswith:deploy ",
                channel_type="channel",
                subtype=["message_changed", "message_deleted"],
            ),
            ReactionAddedEventFilter(reaction="notequals:thumbsdown"),
            ReactionRemovedEventFilter(item_type="message"),
            MessageMetadataPostedEventFilter(
                metadata_event_type="startswith:zenml."
            ),
            MessageMetadataUpdatedEventFilter(app_id="A123"),
            FileSharedEventFilter(file_id="endswith:123"),
        ]
    )


@pytest.mark.parametrize(
    "configuration",
    [
        {},
        {"target_events": []},
        {"target_events": [{}]},
        {"target_events": [{"type": "unknown"}]},
        {"target_events": [{"type": "app_mention", "user_id": "oneof:[]"}]},
        {"target_events": [{"type": "app_mention", "workspace_id": "T123"}]},
        {
            "target_events": [
                {
                    "type": "message",
                    "subtype": "message_changed",
                    "include_subtypes": True,
                }
            ]
        },
    ],
)
def test_slack_configuration_rejects_invalid_targets(
    configuration: dict[str, object],
) -> None:
    """Slack target configuration is explicit, non-empty, and strict."""
    with pytest.raises(ValueError):
        SlackWebhookProvider().validate_configuration(configuration)


def _slack_webhook_event(
    *,
    event_type: str = "app_mention",
    event_payload: dict[str, object] | None = None,
) -> WebhookEvent:
    inner_event: dict[str, object] = {
        "type": event_type,
        "channel": "C123",
        "user": "U123",
        "text": "<@APP123> investigate this",
    }
    if event_payload is not None:
        inner_event = dict(event_payload)
    inner_event.setdefault("event_ts", SLACK_EVENT_TS)
    return WebhookEvent(
        project_id=uuid4(),
        webhook_id=uuid4(),
        webhook_type="slack",
        event_type=event_type,
        delivery_id="Ev123",
        payload={
            "type": "event_callback",
            "team_id": "T123",
            "event_id": "Ev123",
            "event_time": SLACK_EVENT_TIME,
            "event": inner_event,
        },
    )


def test_slack_parses_semantic_app_mention() -> None:
    """Semantic parsing extracts stable mention identity fields."""
    event = _slack_webhook_event(
        event_payload={
            "type": "app_mention",
            "channel": "C123",
            "user": "U123",
            "text": "<@APP123> investigate this",
            "ts": "1788300000.000002",
            "thread_ts": "1788300000.000001",
        }
    )

    semantic = SlackWebhookProvider().parse_semantic_event(event)

    assert semantic == SlackAppMentionEvent(
        event_id="Ev123",
        team_id="T123",
        event_time=SLACK_EVENT_TIME,
        event_ts=SLACK_EVENT_TS,
        channel_id="C123",
        user_id="U123",
        text="<@APP123> investigate this",
        message_ts="1788300000.000002",
        thread_ts="1788300000.000001",
    )
    assert semantic.event_filter_type is AppMentionEventFilter
    assert semantic.type == SlackWebhookEventType.APP_MENTION


@pytest.mark.parametrize(
    "missing_field",
    ["event_id", "team_id", "user_id", "event_time", "event_ts"],
)
def test_slack_app_mentions_require_common_and_user_fields(
    missing_field: str,
) -> None:
    """App mentions require common Slack callback and user fields.

    Args:
        missing_field: The required common field to omit.
    """
    event = _slack_webhook_event()
    if missing_field == "event_id":
        event = event.model_copy(update={"delivery_id": None})
    else:
        payload = dict(event.payload)
        if missing_field in {"user_id", "event_ts"}:
            inner_event = dict(payload["event"])
            inner_event.pop(
                "user" if missing_field == "user_id" else missing_field
            )
            payload["event"] = inner_event
        else:
            payload.pop(missing_field)
        event = event.model_copy(update={"payload": payload})

    assert SlackWebhookProvider().parse_semantic_event(event) is None


def test_slack_matches_app_mention_targets() -> None:
    """Targets use OR across entries and AND across populated filters."""
    event = _slack_webhook_event()
    match_all = SimpleNamespace(
        id=uuid4(),
        configuration={"target_events": [{"type": "app_mention"}]},
    )
    matching_filters = SimpleNamespace(
        id=uuid4(),
        configuration={
            "target_events": [
                {
                    "type": "app_mention",
                    "channel_id": ["C999", "C123"],
                    "user_id": 'oneof:["U123","U456"]',
                    "text": "contains:investigate",
                }
            ]
        },
    )
    matching_alternative = SimpleNamespace(
        id=uuid4(),
        configuration={
            "target_events": [
                {"type": "app_mention", "channel_id": "C999"},
                {"type": "app_mention", "user_id": "U123"},
            ]
        },
    )
    wrong_channel = SimpleNamespace(
        id=uuid4(),
        configuration={
            "target_events": [{"type": "app_mention", "channel_id": "C999"}]
        },
    )
    wrong_user = SimpleNamespace(
        id=uuid4(),
        configuration={
            "target_events": [
                {
                    "type": "app_mention",
                    "channel_id": "C123",
                    "user_id": "U999",
                }
            ]
        },
    )
    wrong_text = SimpleNamespace(
        id=uuid4(),
        configuration={
            "target_events": [
                {"type": "app_mention", "text": "notcontains:investigate"}
            ]
        },
    )
    empty_channel_list = SimpleNamespace(
        id=uuid4(),
        configuration={
            "target_events": [{"type": "app_mention", "channel_id": []}]
        },
    )

    matches = SlackWebhookProvider().match_triggers(
        event=event,
        candidates=[
            match_all,
            matching_filters,
            matching_alternative,
            wrong_channel,
            wrong_user,
            wrong_text,
            empty_channel_list,
        ],
    )

    assert matches.triggers == [
        match_all,
        matching_filters,
        matching_alternative,
    ]
    assert matches.event is not None
    assert matches.event["type"] == SlackWebhookEventType.APP_MENTION
    assert matches.event["text"] == "<@APP123> investigate this"


def test_slack_dynamic_target_filters_complete_callback_body() -> None:
    """Dynamic Slack targets use the inner type and complete outer payload."""
    event = _slack_webhook_event(
        event_type="channel_archive",
        event_payload={
            "type": "channel_archive",
            "channel": "C123",
        },
    )
    matching = SimpleNamespace(
        id=uuid4(),
        configuration={
            "target_events": [
                {
                    "type": "dynamic",
                    "event_type": "channel_archive",
                    "filters": {
                        "team_id": "T123",
                        "event.channel": "startswith:C",
                    },
                }
            ]
        },
    )

    result = SlackWebhookProvider().match_triggers(
        event=event, candidates=[matching]
    )

    assert result.triggers == [matching]
    assert result.event is None


def test_slack_parses_and_matches_regular_messages() -> None:
    """Regular root messages and replies support semantic filtering."""
    event = _slack_webhook_event(
        event_type="message",
        event_payload={
            "type": "message",
            "channel": "C123",
            "channel_type": "channel",
            "user": "U123",
            "text": "deploy production",
            "ts": "1788300000.000002",
            "thread_ts": "1788300000.000001",
            "event_ts": "1788300000.000003",
        },
    )

    semantic = SlackWebhookProvider().parse_semantic_event(event)

    assert semantic == SlackMessageEvent(
        event_id="Ev123",
        team_id="T123",
        event_time=SLACK_EVENT_TIME,
        event_ts="1788300000.000003",
        channel_id="C123",
        channel_type="channel",
        user_id="U123",
        text="deploy production",
        subtype=None,
        bot_authored=False,
        message_ts="1788300000.000002",
        thread_ts="1788300000.000001",
    )
    assert semantic.matches(
        MessageEventFilter(
            team_id="T123",
            channel_id="C123",
            channel_type="channel",
            user_id="U123",
            text="startswith:deploy ",
            threaded=True,
        )
    )
    assert semantic.type == SlackWebhookEventType.MESSAGE
    assert not semantic.matches(MessageEventFilter(threaded=False))

    matching = SimpleNamespace(
        id=uuid4(),
        configuration={
            "target_events": [{"type": "message", "text": "deploy production"}]
        },
    )
    wrong_event = SimpleNamespace(
        id=uuid4(),
        configuration={"target_events": [{"type": "app_mention"}]},
    )
    match = SlackWebhookProvider().match_triggers(
        event=event, candidates=[matching, wrong_event]
    )
    assert match.triggers == [matching]
    assert match.event is not None
    assert match.event["type"] == SlackWebhookEventType.MESSAGE


@pytest.mark.parametrize(
    "payload, expected_subtype, expected_bot_authored",
    [
        (
            {
                "type": "message",
                "subtype": "message_changed",
                "channel": "C123",
                "message": {
                    "type": "message",
                    "user": "U123",
                    "text": "updated message",
                    "ts": "1.1",
                },
            },
            "message_changed",
            False,
        ),
        (
            {
                "type": "message",
                "channel": "C123",
                "text": "bot message",
                "ts": "1.1",
                "bot_id": "B123",
            },
            None,
            True,
        ),
        (
            {
                "type": "message",
                "subtype": "bot_message",
                "channel": "C123",
                "text": "bot message",
                "ts": "1.1",
                "bot_profile": {"id": "B123"},
            },
            "bot_message",
            True,
        ),
    ],
    ids=["message-changed", "bot-id", "bot-message-subtype"],
)
def test_slack_message_subtypes_require_explicit_filtering(
    payload: dict[str, object],
    expected_subtype: str | None,
    expected_bot_authored: bool,
) -> None:
    """Subtype and bot messages are normalized but excluded by default."""
    event = _slack_webhook_event(event_type="message", event_payload=payload)
    semantic = SlackWebhookProvider().parse_semantic_event(event)

    assert isinstance(semantic, SlackMessageEvent)
    assert semantic.subtype == expected_subtype
    assert semantic.bot_authored is expected_bot_authored
    assert not semantic.matches(MessageEventFilter())
    assert semantic.matches(MessageEventFilter(include_subtypes=True))
    if expected_subtype is not None:
        assert semantic.matches(MessageEventFilter(subtype=expected_subtype))


def test_slack_matches_multiple_message_subtypes() -> None:
    """Message subtype lists use the shared OR string-filter behavior."""
    event = _slack_webhook_event(
        event_type="message",
        event_payload={
            "type": "message",
            "subtype": "message_deleted",
            "channel": "C123",
            "deleted_ts": "1.1",
        },
    )

    semantic = SlackWebhookProvider().parse_semantic_event(event)

    assert semantic == SlackMessageEvent(
        event_id="Ev123",
        team_id="T123",
        event_time=SLACK_EVENT_TIME,
        event_ts=SLACK_EVENT_TS,
        channel_id="C123",
        subtype="message_deleted",
        bot_authored=False,
        message_ts="1.1",
    )
    assert semantic.matches(
        MessageEventFilter(subtype=["message_changed", "message_deleted"])
    )
    assert semantic.matches(
        MessageEventFilter(
            subtype='oneof:["message_changed","message_deleted"]'
        )
    )
    assert not semantic.matches(MessageEventFilter(subtype="message_changed"))


@pytest.mark.parametrize("missing_field", ["channel", "user", "ts"])
def test_slack_ignores_malformed_regular_messages(
    missing_field: str,
) -> None:
    """Regular messages require stable channel, user, and timestamp fields.

    Args:
        missing_field: The required regular-message field to omit.
    """
    payload = {
        "type": "message",
        "channel": "C123",
        "user": "U123",
        "text": "deploy production",
        "ts": "1.1",
    }
    payload.pop(missing_field)
    event = _slack_webhook_event(event_type="message", event_payload=payload)

    assert SlackWebhookProvider().parse_semantic_event(event) is None


@pytest.mark.parametrize(
    "item_payload, expected_item",
    [
        (
            {
                "type": "message",
                "channel": "C123",
                "ts": "1788300000.000001",
            },
            SlackReactionItem(
                type="message",
                id="1788300000.000001",
                channel_id="C123",
            ),
        ),
        (
            {"type": "file", "file": "F123"},
            SlackReactionItem(type="file", id="F123", file_id="F123"),
        ),
        (
            {
                "type": "file_comment",
                "file": "F123",
                "file_comment": "Fc123",
            },
            SlackReactionItem(
                type="file_comment",
                id="Fc123",
                file_id="F123",
            ),
        ),
    ],
    ids=["message", "file", "file-comment"],
)
def test_slack_parses_all_documented_reaction_items(
    item_payload: dict[str, object], expected_item: SlackReactionItem
) -> None:
    """Reaction events normalize message, file, and file-comment items."""
    event = _slack_webhook_event(
        event_type="reaction_added",
        event_payload={
            "type": "reaction_added",
            "user": "U123",
            "reaction": "rocket",
            "item_user": "U456",
            "item": item_payload,
            "event_ts": "1788300000.000002",
        },
    )

    semantic = SlackWebhookProvider().parse_semantic_event(event)

    assert semantic == SlackReactionAddedEvent(
        event_id="Ev123",
        team_id="T123",
        event_time=SLACK_EVENT_TIME,
        channel_id=expected_item.channel_id,
        event_ts="1788300000.000002",
        reaction="rocket",
        user_id="U123",
        item_user_id="U456",
        item=expected_item,
    )
    assert semantic.matches(
        ReactionAddedEventFilter(
            reaction="rocket",
            user_id="U123",
            item_user_id="U456",
            item_type=expected_item.type,
            item_id=expected_item.id,
        )
    )
    assert semantic.type == SlackWebhookEventType.REACTION_ADDED


def test_slack_parses_and_matches_removed_reactions() -> None:
    """Removed reactions match only removed-reaction targets."""
    event = _slack_webhook_event(
        event_type="reaction_removed",
        event_payload={
            "type": "reaction_removed",
            "user": "U123",
            "reaction": "white_check_mark",
            "item": {
                "type": "message",
                "channel": "C123",
                "ts": "1788300000.000001",
            },
        },
    )

    semantic = SlackWebhookProvider().parse_semantic_event(event)

    assert isinstance(semantic, SlackReactionRemovedEvent)
    assert semantic.type == SlackWebhookEventType.REACTION_REMOVED
    assert semantic.matches(
        ReactionRemovedEventFilter(
            channel_id="C123", reaction="white_check_mark"
        )
    )
    assert not semantic.matches(
        ReactionAddedEventFilter(reaction="white_check_mark")
    )


@pytest.mark.parametrize(
    "item_payload",
    [
        {},
        {"type": "unknown", "id": "X123"},
        {"type": "message", "channel": "C123"},
        {"type": "file"},
        {"type": "file_comment", "file": "F123"},
    ],
)
def test_slack_ignores_malformed_reaction_items(
    item_payload: dict[str, object],
) -> None:
    """Unknown or incomplete reaction item shapes launch no trigger."""
    event = _slack_webhook_event(
        event_type="reaction_added",
        event_payload={
            "type": "reaction_added",
            "user": "U123",
            "reaction": "rocket",
            "item": item_payload,
        },
    )

    assert SlackWebhookProvider().parse_semantic_event(event) is None


def test_slack_parses_and_matches_posted_message_metadata() -> None:
    """Posted structured metadata supports namespaced event filtering."""
    event = _slack_webhook_event(
        event_type="message_metadata_posted",
        event_payload={
            "type": "message_metadata_posted",
            "app_id": "A123",
            "bot_id": "B123",
            "user_id": "U123",
            "channel_id": "C123",
            "message_ts": "1788300000.000001",
            "metadata": {
                "event_type": "zenml.deployment_requested",
                "event_payload": {"snapshot_id": "snapshot-123"},
            },
        },
    )

    semantic = SlackWebhookProvider().parse_semantic_event(event)

    assert semantic == SlackMessageMetadataPostedEvent(
        event_id="Ev123",
        team_id="T123",
        event_time=SLACK_EVENT_TIME,
        event_ts=SLACK_EVENT_TS,
        channel_id="C123",
        app_id="A123",
        bot_id="B123",
        user_id="U123",
        message_ts="1788300000.000001",
        metadata=SlackMessageMetadata(
            event_type="zenml.deployment_requested",
            event_payload={"snapshot_id": "snapshot-123"},
        ),
    )
    assert semantic.matches(
        MessageMetadataPostedEventFilter(
            app_id="A123",
            metadata_event_type="startswith:zenml.",
        )
    )
    assert semantic.type == SlackWebhookEventType.MESSAGE_METADATA_POSTED


def test_slack_parses_and_matches_updated_message_metadata() -> None:
    """Metadata updates retain their previous structured value."""
    event = _slack_webhook_event(
        event_type="message_metadata_updated",
        event_payload={
            "type": "message_metadata_updated",
            "app_id": "A123",
            "user_id": "U123",
            "channel_id": "C123",
            "message_ts": "1788300000.000001",
            "previous_metadata": {
                "event_type": "zenml.approval",
                "event_payload": {"status": "pending"},
            },
            "metadata": {
                "event_type": "zenml.approval",
                "event_payload": {"status": "approved"},
            },
        },
    )

    semantic = SlackWebhookProvider().parse_semantic_event(event)

    assert semantic == SlackMessageMetadataUpdatedEvent(
        event_id="Ev123",
        team_id="T123",
        event_time=SLACK_EVENT_TIME,
        event_ts=SLACK_EVENT_TS,
        channel_id="C123",
        app_id="A123",
        user_id="U123",
        message_ts="1788300000.000001",
        metadata=SlackMessageMetadata(
            event_type="zenml.approval",
            event_payload={"status": "approved"},
        ),
        previous_metadata=SlackMessageMetadata(
            event_type="zenml.approval",
            event_payload={"status": "pending"},
        ),
    )
    assert semantic.matches(
        MessageMetadataUpdatedEventFilter(
            channel_id="C123", metadata_event_type="zenml.approval"
        )
    )
    assert semantic.type == SlackWebhookEventType.MESSAGE_METADATA_UPDATED


@pytest.mark.parametrize(
    "event_type, payload",
    [
        (
            "message_metadata_posted",
            {
                "type": "message_metadata_posted",
                "app_id": "A123",
                "channel_id": "C123",
                "message_ts": "1.1",
                "metadata": {"event_type": "zenml.request"},
            },
        ),
        (
            "message_metadata_updated",
            {
                "type": "message_metadata_updated",
                "app_id": "A123",
                "channel_id": "C123",
                "message_ts": "1.1",
                "metadata": {
                    "event_type": "zenml.request",
                    "event_payload": {},
                },
            },
        ),
    ],
)
def test_slack_ignores_malformed_message_metadata(
    event_type: str, payload: dict[str, object]
) -> None:
    """Metadata callbacks require current and applicable previous values."""
    event = _slack_webhook_event(event_type=event_type, event_payload=payload)

    assert SlackWebhookProvider().parse_semantic_event(event) is None


def test_slack_parses_and_matches_shared_files() -> None:
    """Shared files expose stable Slack identifiers for filtering."""
    event = _slack_webhook_event(
        event_type="file_shared",
        event_payload={
            "type": "file_shared",
            "channel_id": "C123",
            "user_id": "U123",
            "file_id": "F123",
            "event_ts": "1788300000.000001",
        },
    )

    semantic = SlackWebhookProvider().parse_semantic_event(event)

    assert semantic == SlackFileSharedEvent(
        event_id="Ev123",
        team_id="T123",
        event_time=SLACK_EVENT_TIME,
        event_ts="1788300000.000001",
        channel_id="C123",
        user_id="U123",
        file_id="F123",
    )
    assert semantic.matches(
        FileSharedEventFilter(
            team_id="T123", channel_id="C123", file_id="F123"
        )
    )
    assert semantic.type == SlackWebhookEventType.FILE_SHARED
    assert not semantic.matches(FileSharedEventFilter(file_id="F999"))


@pytest.mark.parametrize(
    "payload",
    [
        {"type": "file_shared", "user_id": "U123", "file_id": "F123"},
        {"type": "file_shared", "channel_id": "C123", "file_id": "F123"},
        {"type": "file_shared", "channel_id": "C123", "user_id": "U123"},
    ],
    ids=["missing-channel", "missing-user", "missing-file"],
)
def test_slack_ignores_malformed_shared_files(
    payload: dict[str, object],
) -> None:
    """File-share callbacks require channel, user, and file identifiers."""
    event = _slack_webhook_event(
        event_type="file_shared", event_payload=payload
    )

    assert SlackWebhookProvider().parse_semantic_event(event) is None


@pytest.mark.parametrize(
    "event",
    [
        _slack_webhook_event(
            event_type="channel_created",
            event_payload={"type": "channel_created"},
        ),
        _slack_webhook_event(
            event_payload={
                "type": "app_mention",
                "user": "U123",
            }
        ),
        _slack_webhook_event(
            event_payload={
                "type": "app_mention",
                "channel": "C123",
            }
        ),
        _slack_webhook_event(
            event_payload={
                "type": "app_mention",
                "channel": "C123",
                "user": "U123",
                "bot_id": "B123",
            }
        ),
        _slack_webhook_event(
            event_payload={
                "type": "app_mention",
                "channel": "C123",
                "user": "U123",
                "subtype": "bot_message",
            }
        ),
    ],
    ids=[
        "unsupported-event",
        "missing-channel",
        "missing-user",
        "bot-id",
        "bot-message-subtype",
    ],
)
def test_slack_ignores_non_matchable_semantic_events(
    event: WebhookEvent,
) -> None:
    """Unsupported, malformed, and bot-authored events launch no trigger."""
    provider = SlackWebhookProvider()
    candidate = SimpleNamespace(
        id=uuid4(),
        configuration={"target_events": [{"type": "app_mention"}]},
    )

    assert provider.parse_semantic_event(event) is None
    match = provider.match_triggers(event=event, candidates=[candidate])
    assert match.triggers == []
    assert match.event is None


def test_slack_runtime_matching_skips_stale_configuration() -> None:
    """Defective stored Slack configuration does not break event handling."""
    provider = SlackWebhookProvider()
    event = _slack_webhook_event()
    stale = SimpleNamespace(
        id=uuid4(),
        configuration={"target_events": [{"type": "removed_event"}]},
    )

    assert (
        provider.match_triggers(event=event, candidates=[stale]).triggers == []
    )


def test_signed_slack_url_verification_is_accepted_without_dispatch(
    monkeypatch,
) -> None:
    """The endpoint authenticates and answers Slack URL verification."""
    webhook_id = uuid4()
    body = b'{"type":"url_verification","challenge":"challenge-value"}'
    store = _Store()
    _install_endpoint_dependencies(monkeypatch, store)

    response = endpoints._receive_webhook_event(
        webhook_type="slack",
        webhook_id=webhook_id,
        body=body,
        headers=_slack_headers(body=body),
    )

    assert response.status_code == 200
    assert response.body == b"challenge-value"
    assert response.media_type == "text/plain"
    assert response.background is None
    assert len(store.records) == 1
    assert store.records[0][1].accepted is True


@pytest.mark.parametrize(
    "body, headers, expected_status, expected_outcome",
    [
        (
            b'{"type":"url_verification","challenge":"value"}',
            {
                SLACK_REQUEST_TIMESTAMP_HEADER: "1788300000",
                SLACK_SIGNATURE_HEADER: "v0=invalid",
            },
            401,
            "auth_failed",
        ),
        (
            b'{"type":"future_control"}',
            _slack_headers(body=b'{"type":"future_control"}'),
            400,
            "invalid_payload",
        ),
    ],
)
def test_slack_endpoint_rejects_untrusted_or_invalid_deliveries(
    monkeypatch,
    body: bytes,
    headers: dict[str, str],
    expected_status: int,
    expected_outcome: str,
) -> None:
    """Slack failures are classified before event dispatch."""
    webhook_id = uuid4()
    store = _Store()
    _install_endpoint_dependencies(monkeypatch, store)

    with pytest.raises(HTTPException) as error:
        endpoints._receive_webhook_event(
            webhook_type="slack",
            webhook_id=webhook_id,
            body=body,
            headers=headers,
        )

    assert error.value.status_code == expected_status
    assert len(store.records) == 1
    assert getattr(store.records[0][1], expected_outcome) is True
