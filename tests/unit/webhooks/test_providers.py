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

from zenml.enums import WebhookType
from zenml.models import (
    GitHubCommit,
    GitHubMergedPullRequestEvent,
    GitHubPushEvent,
    GitHubSemanticEvent,
    GitHubWebhookTriggerConfiguration,
    PushEvent,
)
from zenml.webhooks import WebhookEvent
from zenml.webhooks.providers import (
    BaseWebhookProvider,
    WebhookAuthenticationError,
    WebhookPayloadError,
    WebhookPreValidationResult,
    WebhookProviderRegistry,
    WebhookTriggerConfiguration,
    get_webhook_provider,
)
from zenml.webhooks.providers.custom import CustomWebhookProvider
from zenml.webhooks.providers.github import GitHubWebhookProvider

pytestmark = pytest.mark.anyio


class _BodyMetadataBearerProvider(BaseWebhookProvider):
    """Test provider with bearer auth and body-derived event metadata."""

    webhook_type = WebhookType.CUSTOM
    configuration_class = WebhookTriggerConfiguration

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

    def validate_configuration(self, configuration):
        return WebhookTriggerConfiguration.model_validate(configuration)

    def match_triggers(self, *, event, candidates):
        return list(candidates)


def test_github_semantic_events_are_public_pydantic_models() -> None:
    """Normalized GitHub events are available through the public models API."""
    event = GitHubPushEvent(
        repo="zenml-io/zenml",
        branch="main",
        actor="octocat",
        commit=GitHubCommit(name="Add webhook triggers", sha="abc123"),
    )

    assert isinstance(event, GitHubSemanticEvent)
    assert event.model_dump() == {
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
        webhook_type=WebhookType.GITHUB,
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

    parsed = GitHubWebhookProvider().parse_semantic_event(event)

    assert isinstance(parsed, GitHubPushEvent)
    assert parsed.commit == GitHubCommit(
        name="Add webhook triggers", sha="abc123"
    )


def test_github_semantic_merged_pr_includes_merge_commit() -> None:
    """Merged-PR parsing includes the PR title and merge commit SHA."""
    event = WebhookEvent(
        project_id=uuid4(),
        webhook_id=uuid4(),
        webhook_type=WebhookType.GITHUB,
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


def _signature(secret: str, body: bytes) -> str:
    return (
        "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    )


@pytest.mark.parametrize(
    "webhook_type, provider_type",
    [
        (WebhookType.GITHUB, GitHubWebhookProvider),
        (WebhookType.CUSTOM, CustomWebhookProvider),
    ],
)
def test_get_webhook_provider_returns_registered_provider(
    webhook_type: WebhookType, provider_type: type
) -> None:
    """The closed resolver returns the provider for each webhook type."""
    provider = get_webhook_provider(webhook_type)

    assert isinstance(provider, provider_type)
    assert provider.webhook_type == webhook_type


def test_webhook_provider_registry_registers_provider_classes() -> None:
    """Provider instances are created only when requested from the registry."""
    created_providers: list[_BodyMetadataBearerProvider] = []

    class _TrackedProvider(_BodyMetadataBearerProvider):
        def __init__(self) -> None:
            created_providers.append(self)

    registry = WebhookProviderRegistry()
    registry.register(_TrackedProvider)

    assert created_providers == []

    first_provider = registry.get(WebhookType.CUSTOM)
    second_provider = registry.get(WebhookType.CUSTOM)

    assert created_providers == [first_provider, second_provider]
    assert first_provider is not second_provider


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"x-github-event": ""},
    ],
)
async def test_github_pre_validation_rejects_missing_or_empty_event_header(
    headers: Mapping[str, str],
) -> None:
    """GitHub pre-validation rejects absent event metadata."""
    provider = GitHubWebhookProvider()

    with pytest.raises(
        WebhookPayloadError,
        match="Missing or empty x-github-event header",
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
        headers={"x-github-event": event_type}
    )

    assert result == WebhookPreValidationResult.IGNORE


@pytest.mark.parametrize(
    "event_type",
    ["pull_request", "workflow_run", "push", "release"],
)
async def test_github_pre_validation_processes_supported_event_type(
    event_type: str,
) -> None:
    """GitHub pre-validation processes every supported raw family."""
    provider = GitHubWebhookProvider()

    result = await provider.pre_validate(
        headers={"x-github-event": event_type}
    )

    assert result == WebhookPreValidationResult.PROCESS


async def test_custom_pre_validation_always_processes() -> None:
    """Custom deliveries always continue to full intake validation."""
    provider = CustomWebhookProvider()

    result = await provider.pre_validate(headers={})

    assert result == WebhookPreValidationResult.PROCESS


@pytest.mark.parametrize(
    "provider, headers, expected_event_type, expected_delivery_id",
    [
        (
            GitHubWebhookProvider(),
            {
                "x-github-event": "push",
                "x-github-delivery": "github-delivery-id",
            },
            "push",
            "github-delivery-id",
        ),
        (
            CustomWebhookProvider(),
            {
                "x-zenml-event": "pipeline.ready",
                "x-zenml-delivery": "custom-delivery-id",
            },
            "pipeline.ready",
            "custom-delivery-id",
        ),
    ],
)
def test_authenticate_and_parse_return_provider_neutral_event(
    provider: GitHubWebhookProvider | CustomWebhookProvider,
    headers: dict[str, str],
    expected_event_type: str,
    expected_delivery_id: str,
) -> None:
    """Authentication and parsing remain separate provider phases."""
    secret = "webhook-secret"
    body = b'{"repository":"zenml","run_id":42}'
    headers[provider.signature_header] = _signature(secret, body)

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
        webhook_type=WebhookType.GITHUB,
        event_type="pull_request",
        payload={"action": "closed"},
    )

    with pytest.raises(ValidationError):
        event.event_type = "workflow_run"


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
        "x-zenml-event": "pipeline.ready",
        "x-zenml-signature-256": _signature(secret, signed_body),
    }

    with pytest.raises(WebhookAuthenticationError):
        provider.authenticate(
            body=equivalent_body, headers=headers, secret=secret
        )


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"x-zenml-signature-256": "not-prefixed"},
        {"x-zenml-signature-256": "sha256=invalid"},
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
        (b"not-json", {"x-zenml-event": "pipeline.ready"}),
        (b'["not", "an", "object"]', {"x-zenml-event": "pipeline.ready"}),
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
    assert "index 0 (type=unknown)" in message
    assert "index 1 (type=merged_pull_request)" in message


def test_github_configuration_accepts_typed_configuration() -> None:
    """Strict GitHub validation accepts its public typed configuration."""
    provider = GitHubWebhookProvider()
    configuration = GitHubWebhookTriggerConfiguration(
        target_events=[
            PushEvent(repo="zenml-io/zenml", branch="main"),
        ]
    )

    assert provider.validate_configuration(configuration) == (
        WebhookTriggerConfiguration(
            target_events=[
                {
                    "type": "push",
                    "repo": "zenml-io/zenml",
                    "branch": "main",
                    "actor": None,
                }
            ]
        )
    )


def test_custom_configuration_accepts_only_empty_target_events() -> None:
    """Custom V1 configuration remains intentionally unfiltered."""
    provider = CustomWebhookProvider()

    assert provider.validate_configuration({"target_events": []}) == (
        WebhookTriggerConfiguration(target_events=[])
    )
    with pytest.raises(ValueError, match="empty target_events"):
        provider.validate_configuration(
            {"target_events": [{"type": "pipeline.ready"}]}
        )


def test_runtime_matching_skips_stale_github_entries_individually() -> None:
    """One stale stored target does not disable remaining valid targets."""
    provider = GitHubWebhookProvider()
    event = WebhookEvent(
        project_id=uuid4(),
        webhook_id=uuid4(),
        webhook_type=WebhookType.GITHUB,
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

    assert provider.match_triggers(
        event=event, candidates=[partially_stale, entirely_stale]
    ) == [partially_stale]


def test_runtime_empty_target_events_are_unrestricted() -> None:
    """An originally empty target list has unrestricted runtime meaning."""
    provider = GitHubWebhookProvider()
    event = WebhookEvent(
        project_id=uuid4(),
        webhook_id=uuid4(),
        webhook_type=WebhookType.GITHUB,
        event_type="push",
        payload={
            "ref": "refs/heads/develop",
            "repository": {"full_name": "zenml-io/zenml"},
        },
    )
    trigger = SimpleNamespace(id=uuid4(), configuration={"target_events": []})

    assert provider.match_triggers(event=event, candidates=[trigger]) == [
        trigger
    ]
