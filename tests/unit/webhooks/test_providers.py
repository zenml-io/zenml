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
"""Unit tests for stateless webhook providers."""

import hashlib
import hmac
from collections.abc import Mapping
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from zenml.webhooks import WebhookEvent
from zenml.webhooks.providers import (
    BaseWebhookProvider,
    BuiltinWebhookType,
    WebhookAuthenticationError,
    WebhookConfiguration,
    WebhookPayloadError,
    WebhookPreValidationResult,
    WebhookProviderRegistry,
    WebhookTriggerMatch,
    get_webhook_provider,
)
from zenml.webhooks.providers.clickup import (
    CLICKUP_SIGNATURE_HEADER,
    ClickUpSemanticEvent,
    ClickUpTaskStatusUpdatedEvent,
    ClickUpWebhookConfiguration,
    ClickUpWebhookProvider,
    ListCreated,
    TaskCreated,
    TaskStatusUpdated,
)
from zenml.webhooks.providers.custom import (
    CUSTOM_DELIVERY_HEADER,
    CUSTOM_EVENT_HEADER,
    CUSTOM_SIGNATURE_HEADER,
    CustomWebhookConfiguration,
    CustomWebhookProvider,
)
from zenml.webhooks.providers.github import (
    GITHUB_DELIVERY_HEADER,
    GITHUB_EVENT_HEADER,
    GITHUB_SIGNATURE_HEADER,
    GitHubCommit,
    GitHubIssueOpenedEvent,
    GitHubMergedPullRequestEvent,
    GitHubPushEvent,
    GitHubSemanticEvent,
    GitHubWebhookConfiguration,
    GitHubWebhookProvider,
    IssueOpened,
    PushEvent,
)

pytestmark = pytest.mark.anyio


class _BodyMetadataBearerConfiguration(WebhookConfiguration):
    """Configuration for the test-only bearer provider."""


class _BodyMetadataBearerProvider(BaseWebhookProvider):
    """Test provider with bearer auth and body-derived event metadata."""

    webhook_type = "custom"
    configuration_class = _BodyMetadataBearerConfiguration

    def authenticate(
        self, body: bytes, headers: Mapping[str, str], secret: str
    ) -> None:
        if headers.get("authorization") != f"Bearer {secret}":
            raise WebhookAuthenticationError("Invalid bearer token.")

    def get_event_type(self, payload: dict, headers: Mapping[str, str]) -> str:
        event_type = payload.get("type")
        if not isinstance(event_type, str) or not event_type:
            raise WebhookPayloadError("Missing event type in request body.")
        return event_type

    def get_delivery_id(
        self, payload: dict, headers: Mapping[str, str]
    ) -> str | None:
        delivery_id = payload.get("webhookId")
        return delivery_id if isinstance(delivery_id, str) else None

    def match_triggers(self, *, event, candidates):
        return WebhookTriggerMatch(triggers=list(candidates))


def test_github_semantic_events_are_public_pydantic_models() -> None:
    """Normalized GitHub events are available through the public models API."""
    event = GitHubPushEvent(
        repo="zenml-io/zenml",
        branch="main",
        actor="octocat",
        commit=GitHubCommit(name="Add webhook triggers", sha="abc123"),
    )

    assert isinstance(event, GitHubSemanticEvent)
    assert event.event_filter_type is PushEvent
    assert event.model_dump() == {
        "type": "push",
        "repo": "zenml-io/zenml",
        "branch": "main",
        "actor": "octocat",
        "commit": {"name": "Add webhook triggers", "sha": "abc123"},
    }


def test_github_semantic_push_event_includes_head_commit() -> None:
    """Push parsing includes the head commit message and SHA."""
    event = WebhookEvent(
        project_id=uuid4(),
        webhook_id=uuid4(),
        webhook_type="github",
        event_type="push",
        payload={
            "ref": "refs/heads/main",
            "repository": {"full_name": "zenml-io/zenml"},
            "sender": {"login": "octocat"},
            "head_commit": {
                "id": "abc123",
                "message": "Add webhook triggers",
            },
        },
    )

    provider = GitHubWebhookProvider()
    parsed = provider.parse_semantic_event(event)

    assert isinstance(parsed, GitHubPushEvent)
    assert parsed.commit == GitHubCommit(
        name="Add webhook triggers", sha="abc123"
    )


def test_github_matching_returns_serialized_semantic_event() -> None:
    """GitHub matching returns the event used to match the triggers."""
    provider = GitHubWebhookProvider()
    event = WebhookEvent(
        project_id=uuid4(),
        webhook_id=uuid4(),
        webhook_type="github",
        event_type="push",
        delivery_id="delivery-001",
        payload={
            "ref": "refs/heads/main",
            "repository": {"full_name": "zenml-io/zenml"},
            "sender": {"login": "octocat"},
        },
    )
    trigger = SimpleNamespace(
        id=uuid4(),
        configuration={
            "target_events": [
                {
                    "type": "push",
                    "repo": "zenml-io/zenml",
                    "branch": "main",
                }
            ]
        },
    )

    result = provider.match_triggers(event=event, candidates=[trigger])

    assert result.triggers == [trigger]
    assert result.event == {
        "type": "push",
        "repo": "zenml-io/zenml",
        "branch": "main",
        "actor": "octocat",
        "commit": None,
    }


def test_provider_match_envelope_can_omit_semantic_event() -> None:
    """Providers can match triggers without exposing event metadata."""
    event = WebhookEvent(
        project_id=uuid4(),
        webhook_id=uuid4(),
        webhook_type="custom",
        event_type="monitor.page",
        payload={},
    )
    trigger = SimpleNamespace(id=uuid4())

    result = _BodyMetadataBearerProvider().match_triggers(
        event=event, candidates=[trigger]
    )

    assert result == WebhookTriggerMatch(triggers=[trigger])


def test_github_semantic_merged_pr_includes_merge_commit() -> None:
    """Merged-PR parsing includes the PR title and merge commit SHA."""
    event = WebhookEvent(
        project_id=uuid4(),
        webhook_id=uuid4(),
        webhook_type="github",
        event_type="pull_request",
        payload={
            "action": "closed",
            "repository": {"full_name": "zenml-io/zenml"},
            "pull_request": {
                "merged": True,
                "title": "Add webhook triggers",
                "merge_commit_sha": "def456",
                "base": {"ref": "main"},
                "head": {"ref": "feature/webhook-triggers"},
                "user": {"login": "octocat"},
            },
        },
    )

    parsed = GitHubWebhookProvider().parse_semantic_event(event)

    assert isinstance(parsed, GitHubMergedPullRequestEvent)
    assert parsed.commit == GitHubCommit(
        name="Add webhook triggers", sha="def456"
    )


def test_github_issue_opened_normalizes_and_matches_collections() -> None:
    """Opened issues expose compact metadata and OR-match collections."""
    event = WebhookEvent(
        project_id=uuid4(),
        webhook_id=uuid4(),
        webhook_type="github",
        event_type="issues",
        payload={
            "action": "opened",
            "repository": {"full_name": "zenml-io/zenml"},
            "issue": {
                "number": 42,
                "title": "Support issue webhooks",
                "body": "This intentionally does not enter the event.",
                "user": {"login": "octocat"},
                "author_association": "MEMBER",
                "labels": [{"name": "bug"}, {"name": "priority-high"}],
                "assignees": [
                    {"login": "maintainer"},
                    {"login": "reviewer"},
                ],
                "milestone": {"title": "v1.0"},
                "type": {"name": "Bug"},
            },
        },
    )

    provider = GitHubWebhookProvider()
    parsed = provider.parse_semantic_event(event)

    assert parsed == GitHubIssueOpenedEvent(
        repo="zenml-io/zenml",
        number=42,
        title="Support issue webhooks",
        author="octocat",
        author_association="MEMBER",
        labels=["bug", "priority-high"],
        assignees=["maintainer", "reviewer"],
        milestone="v1.0",
        issue_type="Bug",
    )
    assert parsed.matches(
        IssueOpened(
            repo="zenml-io/zenml",
            author_association='oneof:["OWNER", "MEMBER"]',
            labels='oneof:["feature", "priority-high"]',
            assignees=["nobody", "maintainer"],
            milestone="v1.0",
        )
    )
    assert not parsed.matches(IssueOpened(labels="documentation"))

    trigger = SimpleNamespace(
        id=uuid4(),
        configuration={
            "target_events": [
                {
                    "type": "issue_opened",
                    "repo": "zenml-io/zenml",
                    "labels": 'oneof:["feature", "bug"]',
                }
            ]
        },
    )
    result = provider.match_triggers(event=event, candidates=[trigger])
    assert result.triggers == [trigger]
    assert result.event is not None
    assert result.event["type"] == "issue_opened"
    assert "body" not in result.event


def test_github_issue_reopened_is_not_an_issue_opened_event() -> None:
    """Reopened issues do not produce the opened-issue semantic event."""
    event = WebhookEvent(
        project_id=uuid4(),
        webhook_id=uuid4(),
        webhook_type="github",
        event_type="issues",
        payload={
            "action": "reopened",
            "repository": {"full_name": "zenml-io/zenml"},
            "issue": {"number": 42, "title": "Support issue webhooks"},
        },
    )

    assert GitHubWebhookProvider().parse_semantic_event(event) is None


def _signature(secret: str, body: bytes) -> str:
    return (
        "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    )


@pytest.mark.parametrize(
    "webhook_type, provider_type",
    [
        (BuiltinWebhookType.CLICKUP, ClickUpWebhookProvider),
        (BuiltinWebhookType.GITHUB, GitHubWebhookProvider),
        (BuiltinWebhookType.CUSTOM, CustomWebhookProvider),
    ],
)
def test_get_webhook_provider_returns_registered_provider(
    webhook_type: str, provider_type: type
) -> None:
    """The registry returns the provider for each built-in webhook type."""
    provider = get_webhook_provider(webhook_type)

    assert isinstance(provider, provider_type)
    assert provider.webhook_type == webhook_type


def test_webhook_provider_registry_registers_provider_classes() -> None:
    """Provider instances are created only when requested from the registry."""
    created_providers: list[_BodyMetadataBearerProvider] = []

    class _TrackedProvider(_BodyMetadataBearerProvider):
        webhook_type = "third-party"

        def __init__(self) -> None:
            created_providers.append(self)

    registry = WebhookProviderRegistry()
    registry.register(_TrackedProvider)

    assert created_providers == []

    first_provider = registry.get("third-party")
    second_provider = registry.get("third-party")

    assert created_providers == [first_provider, second_provider]
    assert first_provider is not second_provider


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {GITHUB_EVENT_HEADER: ""},
    ],
)
async def test_github_pre_validation_rejects_missing_or_empty_event_header(
    headers: Mapping[str, str],
) -> None:
    """GitHub pre-validation rejects absent event metadata."""
    provider = GitHubWebhookProvider()

    with pytest.raises(
        WebhookPayloadError,
        match=f"Missing or empty {GITHUB_EVENT_HEADER} header",
    ):
        await provider.pre_validate(headers=headers)


@pytest.mark.parametrize(
    "event_type",
    ["pull request", "pull-request", "PULL_REQUEST"],
)
async def test_github_pre_validation_ignores_unsupported_event_type(
    event_type: str,
) -> None:
    """GitHub pre-validation explicitly ignores unsupported families."""
    provider = GitHubWebhookProvider()

    result = await provider.pre_validate(
        headers={GITHUB_EVENT_HEADER: event_type}
    )

    assert result == WebhookPreValidationResult.IGNORE


@pytest.mark.parametrize(
    "event_type",
    ["pull_request", "workflow_run", "push", "release", "issues"],
)
async def test_github_pre_validation_processes_supported_event_type(
    event_type: str,
) -> None:
    """GitHub pre-validation processes every supported raw family."""
    provider = GitHubWebhookProvider()

    result = await provider.pre_validate(
        headers={GITHUB_EVENT_HEADER: event_type}
    )

    assert result == WebhookPreValidationResult.PROCESS


async def test_custom_pre_validation_always_processes() -> None:
    """Custom deliveries always continue to full intake validation."""
    provider = CustomWebhookProvider()

    result = await provider.pre_validate(headers={})

    assert result == WebhookPreValidationResult.PROCESS


@pytest.mark.parametrize(
    (
        "provider, signature_header, headers, expected_event_type, "
        "expected_delivery_id"
    ),
    [
        (
            GitHubWebhookProvider(),
            GITHUB_SIGNATURE_HEADER,
            {
                GITHUB_EVENT_HEADER: "push",
                GITHUB_DELIVERY_HEADER: "github-delivery-id",
            },
            "push",
            "github-delivery-id",
        ),
        (
            CustomWebhookProvider(),
            CUSTOM_SIGNATURE_HEADER,
            {
                CUSTOM_EVENT_HEADER: "pipeline.ready",
                CUSTOM_DELIVERY_HEADER: "custom-delivery-id",
            },
            "pipeline.ready",
            "custom-delivery-id",
        ),
    ],
)
def test_authenticate_and_parse_return_provider_neutral_event(
    provider: GitHubWebhookProvider | CustomWebhookProvider,
    signature_header: str,
    headers: dict[str, str],
    expected_event_type: str,
    expected_delivery_id: str,
) -> None:
    """Authentication and parsing remain separate provider phases."""
    secret = "webhook-secret"
    body = b'{"repository":"zenml","run_id":42}'
    headers[signature_header] = _signature(secret, body)

    provider.authenticate(body=body, headers=headers, secret=secret)
    event = provider.parse(body=body, headers=headers)

    assert event.event_type == expected_event_type
    assert event.delivery_id == expected_delivery_id
    assert event.payload == {"repository": "zenml", "run_id": 42}


def test_parse_supports_body_event_metadata_after_bearer_auth() -> None:
    """Provider parsing can derive neutral metadata from the body."""
    provider = _BodyMetadataBearerProvider()
    body = b'{"type":"monitor.page","webhookId":"delivery-id"}'

    provider.authenticate(
        body=body,
        headers={"authorization": "Bearer webhook-secret"},
        secret="webhook-secret",
    )
    event = provider.parse(
        body=body,
        headers={"authorization": "Bearer webhook-secret"},
    )

    assert event.event_type == "monitor.page"
    assert event.delivery_id == "delivery-id"


def test_trusted_webhook_event_is_immutable() -> None:
    """Trusted webhook event identity cannot change after construction."""
    event = WebhookEvent(
        project_id=uuid4(),
        webhook_id=uuid4(),
        webhook_type="third-party",
        event_type="pull_request",
        payload={"action": "closed"},
    )

    with pytest.raises(ValidationError):
        event.event_type = "workflow_run"

    assert event.webhook_type == "third-party"


def test_parse_rejects_missing_body_event_type() -> None:
    """Provider parsing rejects missing required event metadata."""
    provider = _BodyMetadataBearerProvider()

    with pytest.raises(
        WebhookPayloadError, match="Missing event type in request body"
    ):
        provider.parse(body=b'{"webhookId":"delivery-id"}', headers={})


def test_authentication_uses_exact_raw_body_bytes() -> None:
    """HMAC authentication covers the exact raw request bytes."""
    provider = CustomWebhookProvider()
    secret = "webhook-secret"
    signed_body = b'{"repository":"zenml","run_id":42}'
    equivalent_body = b'{\n  "repository": "zenml",\n  "run_id": 42\n}'
    headers = {
        CUSTOM_EVENT_HEADER: "pipeline.ready",
        CUSTOM_SIGNATURE_HEADER: _signature(secret, signed_body),
    }

    with pytest.raises(WebhookAuthenticationError):
        provider.authenticate(
            body=equivalent_body, headers=headers, secret=secret
        )


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {CUSTOM_SIGNATURE_HEADER: "not-prefixed"},
        {CUSTOM_SIGNATURE_HEADER: "sha256=invalid"},
    ],
)
def test_authentication_rejects_missing_malformed_or_invalid_signature(
    headers: Mapping[str, str],
) -> None:
    """HMAC authentication rejects invalid signature forms."""
    provider = CustomWebhookProvider()

    with pytest.raises(WebhookAuthenticationError):
        provider.authenticate(
            body=b'{"repository":"zenml"}',
            headers=headers,
            secret="webhook-secret",
        )


@pytest.mark.parametrize(
    "body, headers",
    [
        (b'{"repository":"zenml"}', {}),
        (b"not-json", {CUSTOM_EVENT_HEADER: "pipeline.ready"}),
        (b'["not", "an", "object"]', {CUSTOM_EVENT_HEADER: "pipeline.ready"}),
    ],
)
def test_parse_rejects_missing_event_header_or_invalid_payload(
    body: bytes, headers: Mapping[str, str]
) -> None:
    """Custom parsing requires an event header and JSON object body."""
    provider = CustomWebhookProvider()

    with pytest.raises(WebhookPayloadError):
        provider.parse(body=body, headers=headers)


def test_github_configuration_reports_all_invalid_target_events() -> None:
    """Strict GitHub writes report every invalid target entry."""
    provider = GitHubWebhookProvider()

    with pytest.raises(ValueError) as error:
        provider.validate_configuration(
            {
                "target_events": [
                    {"type": "unknown"},
                    {
                        "type": "merged_pull_request",
                        "repo": "startswith:zenml-io/",
                    },
                ]
            }
        )

    message = str(error.value)
    assert "target_events.0" in message
    assert "target_events.1" in message


def test_github_configuration_accepts_typed_configuration() -> None:
    """Strict GitHub validation accepts its public typed configuration."""
    provider = GitHubWebhookProvider()
    configuration = GitHubWebhookConfiguration(
        target_events=[
            PushEvent(repo="zenml-io/zenml", branch="main"),
        ]
    )

    assert provider.validate_configuration(configuration) is configuration


def test_provider_configuration_ignores_removed_fields() -> None:
    """Persisted provider configuration tolerates removed fields."""
    provider = GitHubWebhookProvider()

    configuration = provider.validate_configuration(
        {
            "target_events": [{"type": "push", "branch": "main"}],
            "removed_provider_option": True,
        }
    )

    assert configuration == GitHubWebhookConfiguration(
        target_events=[PushEvent(branch="main")]
    )


def test_custom_configuration_ignores_unknown_fields() -> None:
    """Custom V1 configuration remains intentionally unfiltered."""
    provider = CustomWebhookProvider()

    assert provider.validate_configuration({}) == CustomWebhookConfiguration()
    assert (
        provider.validate_configuration(
            {"target_events": [{"type": "pipeline.ready"}]}
        )
        == CustomWebhookConfiguration()
    )


def test_runtime_matching_rejects_stale_github_configuration() -> None:
    """One stale stored target invalidates the complete configuration."""
    provider = GitHubWebhookProvider()
    event = WebhookEvent(
        project_id=uuid4(),
        webhook_id=uuid4(),
        webhook_type="github",
        event_type="push",
        payload={
            "ref": "refs/heads/develop",
            "repository": {"full_name": "zenml-io/zenml"},
            "sender": {"login": "george"},
        },
    )
    partially_stale = SimpleNamespace(
        id=uuid4(),
        configuration={
            "target_events": [
                {"type": "removed_event"},
                {
                    "type": "push",
                    "repo": "zenml-io/zenml",
                    "branch": "develop",
                },
            ]
        },
    )
    entirely_stale = SimpleNamespace(
        id=uuid4(),
        configuration={"target_events": [{"type": "removed_event"}]},
    )

    assert (
        provider.match_triggers(
            event=event, candidates=[partially_stale, entirely_stale]
        ).triggers
        == []
    )


def test_runtime_empty_target_events_are_rejected() -> None:
    """An empty GitHub target list is invalid at runtime."""
    provider = GitHubWebhookProvider()
    event = WebhookEvent(
        project_id=uuid4(),
        webhook_id=uuid4(),
        webhook_type="github",
        event_type="push",
        payload={
            "ref": "refs/heads/develop",
            "repository": {"full_name": "zenml-io/zenml"},
        },
    )
    trigger = SimpleNamespace(id=uuid4(), configuration={"target_events": []})

    assert (
        provider.match_triggers(event=event, candidates=[trigger]).triggers
        == []
    )


def _clickup_signature(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_clickup_authentication_uses_raw_hex_signature() -> None:
    """ClickUp HMAC uses a raw hex digest in X-Signature."""
    provider = ClickUpWebhookProvider()
    secret = "clickup-secret"
    body = b'{"event":"taskStatusUpdated","webhook_id":"wh-1","task_id":"abc"}'
    headers = {CLICKUP_SIGNATURE_HEADER: _clickup_signature(secret, body)}

    provider.authenticate(body=body, headers=headers, secret=secret)

    with pytest.raises(WebhookAuthenticationError):
        provider.authenticate(
            body=body,
            headers={
                CLICKUP_SIGNATURE_HEADER: "sha256="
                + headers[CLICKUP_SIGNATURE_HEADER]
            },
            secret=secret,
        )


def test_clickup_parse_extracts_event_and_history_delivery_id() -> None:
    """ClickUp parsing reads event from the body and builds the idempotency key."""
    provider = ClickUpWebhookProvider()
    body = (
        b'{"event":"taskStatusUpdated","webhook_id":"wh-1","task_id":"abc",'
        b'"list_id":"162","history_items":[{"id":"hist-2"},{"id":"hist-1"}]}'
    )

    parsed = provider.parse(body=body, headers={})

    assert parsed.event_type == "taskStatusUpdated"
    assert parsed.delivery_id == "wh-1:hist-1,hist-2"
    assert parsed.payload["task_id"] == "abc"


def test_clickup_parse_rejects_missing_event_or_webhook_id() -> None:
    """ClickUp parsing requires event and webhook_id in the JSON body."""
    provider = ClickUpWebhookProvider()

    with pytest.raises(WebhookPayloadError, match="event"):
        provider.parse(
            body=b'{"webhook_id":"wh-1","task_id":"abc"}', headers={}
        )
    with pytest.raises(WebhookPayloadError, match="webhook_id"):
        provider.parse(
            body=b'{"event":"taskCreated","task_id":"abc"}', headers={}
        )


def test_clickup_semantic_events_are_public_pydantic_models() -> None:
    """Normalized ClickUp events are available through the public models API."""
    event = ClickUpTaskStatusUpdatedEvent(
        task_id="abc",
        list_id="162641285",
        space_id="space-1",
        folder_id=None,
        status="done",
    )

    assert isinstance(event, ClickUpSemanticEvent)
    assert event.event_filter_type is TaskStatusUpdated
    assert event.model_dump() == {
        "type": "taskStatusUpdated",
        "task_id": "abc",
        "list_id": "162641285",
        "space_id": "space-1",
        "folder_id": None,
        "status": "done",
    }


def test_clickup_match_filters_status_and_list() -> None:
    """ClickUp matching uses typed target events and resource filters."""
    provider = ClickUpWebhookProvider()
    event = WebhookEvent(
        project_id=uuid4(),
        webhook_id=uuid4(),
        webhook_type="clickup",
        event_type="taskStatusUpdated",
        payload={
            "event": "taskStatusUpdated",
            "webhook_id": "wh-1",
            "task_id": "abc",
            "list_id": "162641285",
            "history_items": [{"id": "hist-1", "after": "done"}],
        },
    )
    matching = SimpleNamespace(
        id=uuid4(),
        configuration={
            "target_events": [
                {
                    "type": "taskStatusUpdated",
                    "list_id": "162641285",
                    "status": "done",
                }
            ]
        },
    )
    other_list = SimpleNamespace(
        id=uuid4(),
        configuration={
            "target_events": [{"type": "taskStatusUpdated", "list_id": "999"}]
        },
    )
    other_event = SimpleNamespace(
        id=uuid4(),
        configuration={"target_events": [{"type": "taskCreated"}]},
    )

    result = provider.match_triggers(
        event=event, candidates=[matching, other_list, other_event]
    )
    assert result.triggers == [matching]
    assert result.event is not None
    assert result.event["type"] == "taskStatusUpdated"
    assert result.event["list_id"] == "162641285"
    assert result.event["status"] == "done"


def test_clickup_match_filters_list_events() -> None:
    """List events match list filters and ignore task-only targets."""
    provider = ClickUpWebhookProvider()
    event = WebhookEvent(
        project_id=uuid4(),
        webhook_id=uuid4(),
        webhook_type="clickup",
        event_type="listCreated",
        payload={
            "event": "listCreated",
            "webhook_id": "wh-1",
            "list_id": "162641285",
            "space_id": "space-1",
        },
    )
    matching = SimpleNamespace(
        id=uuid4(),
        configuration={
            "target_events": [{"type": "listCreated", "list_id": "162641285"}]
        },
    )
    other_space = SimpleNamespace(
        id=uuid4(),
        configuration={
            "target_events": [{"type": "listCreated", "space_id": "space-9"}]
        },
    )
    task_target = SimpleNamespace(
        id=uuid4(),
        configuration={
            "target_events": [{"type": "taskCreated", "list_id": "162641285"}]
        },
    )

    result = provider.match_triggers(
        event=event, candidates=[matching, other_space, task_target]
    )
    assert result.triggers == [matching]
    assert result.event is not None
    assert result.event["type"] == "listCreated"
    assert result.event["list_id"] == "162641285"


def test_clickup_configuration_accepts_typed_configuration() -> None:
    """Strict ClickUp validation accepts its public typed configuration."""
    provider = ClickUpWebhookProvider()
    configuration = ClickUpWebhookConfiguration(
        target_events=[
            TaskStatusUpdated(
                list_id="162641285",
                status="done",
            ),
            ListCreated(list_id="162641285"),
            TaskCreated(task_id="abc"),
        ]
    )

    assert provider.validate_configuration(configuration) is configuration


def test_clickup_configuration_rejects_filters_for_other_events() -> None:
    """Each ClickUp event type only accepts its own filter fields."""
    provider = ClickUpWebhookProvider()

    with pytest.raises(ValueError):
        provider.validate_configuration(
            {
                "target_events": [
                    {"type": "taskCreated", "status": "done"},
                ]
            }
        )
    with pytest.raises(ValueError):
        provider.validate_configuration(
            {
                "target_events": [
                    {"type": "listCreated", "task_id": "abc"},
                ]
            }
        )
