#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""GitHub webhook provider and semantic target event catalog."""

import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any, ClassVar, Literal, TypeAlias

from pydantic import (
    Field,
    TypeAdapter,
    ValidationError,
    ValidationInfo,
    field_validator,
)

from zenml.enums import WebhookType
from zenml.models.v2.base.filter import StringFilterOption
from zenml.utils.enum_utils import StrEnum
from zenml.utils.pydantic_utils import YAMLSerializationMixin
from zenml.webhooks.providers.base import (
    BaseWebhookProvider,
    WebhookPayloadError,
    WebhookPreValidationResult,
    WebhookTargetEvent,
    WebhookTriggerConfiguration,
    authenticate_hmac_sha256,
)

if TYPE_CHECKING:
    from zenml.models import WebhookTriggerResponse
    from zenml.webhooks.events import WebhookEvent

logger = logging.getLogger(__name__)


class GitHubWebhookEventType(StrEnum):
    """Raw GitHub event families supported by semantic target events."""

    PULL_REQUEST = "pull_request"
    WORKFLOW_RUN = "workflow_run"
    PUSH = "push"
    RELEASE = "release"


class GitHubWebhookEvent(StrEnum):
    """Semantic GitHub events supported by webhook triggers."""

    MERGED_PULL_REQUEST = "merged_pull_request"
    WORKFLOW_RUN_COMPLETED = "workflow_run_completed"
    PUSH = "push"
    RELEASE_PUBLISHED = "release_published"


def _validate_filter(
    value: StringFilterOption,
    *,
    field_name: str,
    allow_startswith: bool,
) -> StringFilterOption:
    """Validate one semantic string filter."""
    if value is None:
        return None
    allowed = {"oneof"}
    if allow_startswith:
        allowed.add("startswith")
    for item in value if isinstance(value, list) else [value]:
        if not item:
            raise ValueError(f"GitHub event filter '{field_name}' is empty.")
        if ":" not in item:
            continue
        operator, operand = item.split(":", 1)
        if operator not in allowed:
            raise ValueError(
                f"GitHub event filter '{field_name}' does not support the "
                f"'{operator}' operator."
            )
        if not operand:
            raise ValueError(
                f"GitHub event filter '{field_name}' has an empty operand."
            )
        if operator == "oneof":
            try:
                choices = json.loads(operand)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"GitHub event filter '{field_name}' requires a "
                    "JSON-formatted list for 'oneof'."
                ) from error
            if (
                not isinstance(choices, list)
                or not choices
                or not all(
                    isinstance(choice, str) and choice for choice in choices
                )
            ):
                raise ValueError(
                    f"GitHub event filter '{field_name}' requires a non-empty "
                    "JSON list of strings for 'oneof'."
                )
    return value


class MergedPullRequest(WebhookTargetEvent):
    """Filters for a merged GitHub pull request."""

    type: Literal[GitHubWebhookEvent.MERGED_PULL_REQUEST] = (
        GitHubWebhookEvent.MERGED_PULL_REQUEST
    )
    repo: StringFilterOption = None
    target_branch: StringFilterOption = None
    source_branch: StringFilterOption = None
    author: StringFilterOption = None

    @field_validator("repo", "author")
    @classmethod
    def validate_exact(
        cls, value: StringFilterOption, info: ValidationInfo
    ) -> StringFilterOption:
        """Validate an exact-match field."""
        return _validate_filter(
            value,
            field_name=info.field_name or "unknown",
            allow_startswith=False,
        )

    @field_validator("target_branch", "source_branch")
    @classmethod
    def validate_branch(
        cls, value: StringFilterOption, info: ValidationInfo
    ) -> StringFilterOption:
        """Validate a branch field."""
        return _validate_filter(
            value,
            field_name=info.field_name or "unknown",
            allow_startswith=True,
        )


class WorkflowRunCompleted(WebhookTargetEvent):
    """Filters for a completed GitHub workflow run."""

    type: Literal[GitHubWebhookEvent.WORKFLOW_RUN_COMPLETED] = (
        GitHubWebhookEvent.WORKFLOW_RUN_COMPLETED
    )
    workflow: StringFilterOption = None
    conclusion: StringFilterOption = None
    actor: StringFilterOption = None

    @field_validator("workflow", "conclusion", "actor")
    @classmethod
    def validate_exact(
        cls, value: StringFilterOption, info: ValidationInfo
    ) -> StringFilterOption:
        """Validate an exact-match field."""
        return _validate_filter(
            value,
            field_name=info.field_name or "unknown",
            allow_startswith=False,
        )


class PushEvent(WebhookTargetEvent):
    """Filters for a GitHub branch push."""

    type: Literal[GitHubWebhookEvent.PUSH] = GitHubWebhookEvent.PUSH
    repo: StringFilterOption = None
    branch: StringFilterOption = None
    actor: StringFilterOption = None

    @field_validator("repo", "actor")
    @classmethod
    def validate_exact(
        cls, value: StringFilterOption, info: ValidationInfo
    ) -> StringFilterOption:
        """Validate an exact-match field."""
        return _validate_filter(
            value,
            field_name=info.field_name or "unknown",
            allow_startswith=False,
        )

    @field_validator("branch")
    @classmethod
    def validate_branch(
        cls, value: StringFilterOption, info: ValidationInfo
    ) -> StringFilterOption:
        """Validate a branch field."""
        return _validate_filter(
            value,
            field_name=info.field_name or "unknown",
            allow_startswith=True,
        )


class ReleasePublished(WebhookTargetEvent):
    """Filters for a published GitHub release."""

    type: Literal[GitHubWebhookEvent.RELEASE_PUBLISHED] = (
        GitHubWebhookEvent.RELEASE_PUBLISHED
    )
    repo: StringFilterOption = None
    tag: StringFilterOption = None
    target_branch: StringFilterOption = None
    actor: StringFilterOption = None

    @field_validator("repo", "actor")
    @classmethod
    def validate_exact(
        cls, value: StringFilterOption, info: ValidationInfo
    ) -> StringFilterOption:
        """Validate an exact-match field."""
        return _validate_filter(
            value,
            field_name=info.field_name or "unknown",
            allow_startswith=False,
        )

    @field_validator("tag", "target_branch")
    @classmethod
    def validate_ref(
        cls, value: StringFilterOption, info: ValidationInfo
    ) -> StringFilterOption:
        """Validate a tag or target branch field."""
        return _validate_filter(
            value,
            field_name=info.field_name or "unknown",
            allow_startswith=True,
        )


GitHubWebhookTargetEvent: TypeAlias = Annotated[
    MergedPullRequest | WorkflowRunCompleted | PushEvent | ReleasePublished,
    Field(discriminator="type"),
]
GitHubWebhookEventConfiguration = GitHubWebhookTargetEvent


class GitHubWebhookTriggerConfiguration(YAMLSerializationMixin):
    """Typed configuration for a GitHub webhook trigger."""

    target_events: list[GitHubWebhookTargetEvent] = Field(min_length=1)


GitHubWebhookConfiguration = GitHubWebhookTriggerConfiguration


StringFilter = str | list[str] | None


def matches_string_filter(
    *, actual: str | None, configured: StringFilter
) -> bool:
    """Match an extracted value against a supported string filter."""
    if configured is None:
        return True
    if actual is None:
        return False
    for value in configured if isinstance(configured, list) else [configured]:
        if value.startswith("oneof:"):
            if actual in json.loads(value.removeprefix("oneof:")):
                return True
        elif value.startswith("startswith:"):
            if actual.startswith(value.removeprefix("startswith:")):
                return True
        elif actual == value:
            return True
    return False


def _string_at(payload: Mapping[str, Any], *path: str) -> str | None:
    value: Any = payload
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value if isinstance(value, str) and value else None


@dataclass
class _SemanticEvent:
    event_filter_type: ClassVar[type[WebhookTargetEvent]]

    def matches(self, target: GitHubWebhookTargetEvent) -> bool:
        """Return whether the semantic event matches its typed target."""
        raise NotImplementedError


@dataclass
class _MergedPullRequestEvent(_SemanticEvent):
    event_filter_type = MergedPullRequest
    repo: str
    target_branch: str
    source_branch: str | None
    author: str | None

    def matches(self, target: GitHubWebhookTargetEvent) -> bool:
        if not isinstance(target, MergedPullRequest):
            return False
        return all(
            (
                matches_string_filter(
                    actual=self.repo, configured=target.repo
                ),
                matches_string_filter(
                    actual=self.target_branch, configured=target.target_branch
                ),
                matches_string_filter(
                    actual=self.source_branch, configured=target.source_branch
                ),
                matches_string_filter(
                    actual=self.author, configured=target.author
                ),
            )
        )


@dataclass
class _WorkflowRunCompletedEvent(_SemanticEvent):
    event_filter_type = WorkflowRunCompleted
    workflow: str
    conclusion: str | None
    actor: str | None

    def matches(self, target: GitHubWebhookTargetEvent) -> bool:
        if not isinstance(target, WorkflowRunCompleted):
            return False
        return all(
            (
                matches_string_filter(
                    actual=self.workflow, configured=target.workflow
                ),
                matches_string_filter(
                    actual=self.conclusion, configured=target.conclusion
                ),
                matches_string_filter(
                    actual=self.actor, configured=target.actor
                ),
            )
        )


@dataclass
class _PushEvent(_SemanticEvent):
    event_filter_type = PushEvent
    repo: str
    branch: str
    actor: str | None

    def matches(self, target: GitHubWebhookTargetEvent) -> bool:
        if not isinstance(target, PushEvent):
            return False
        return all(
            (
                matches_string_filter(
                    actual=self.repo, configured=target.repo
                ),
                matches_string_filter(
                    actual=self.branch, configured=target.branch
                ),
                matches_string_filter(
                    actual=self.actor, configured=target.actor
                ),
            )
        )


@dataclass
class _ReleasePublishedEvent(_SemanticEvent):
    event_filter_type = ReleasePublished
    repo: str
    tag: str
    target_branch: str | None
    actor: str | None

    def matches(self, target: GitHubWebhookTargetEvent) -> bool:
        if not isinstance(target, ReleasePublished):
            return False
        return all(
            (
                matches_string_filter(
                    actual=self.repo, configured=target.repo
                ),
                matches_string_filter(actual=self.tag, configured=target.tag),
                matches_string_filter(
                    actual=self.target_branch, configured=target.target_branch
                ),
                matches_string_filter(
                    actual=self.actor, configured=target.actor
                ),
            )
        )


class GitHubWebhookProvider(BaseWebhookProvider):
    """Provider for authenticated and semantically matched GitHub webhooks."""

    webhook_type = WebhookType.GITHUB
    configuration_class = GitHubWebhookTriggerConfiguration
    signature_header = "x-hub-signature-256"
    event_header = "x-github-event"
    delivery_header = "x-github-delivery"
    _target_adapter: TypeAdapter[GitHubWebhookTargetEvent] = TypeAdapter(
        GitHubWebhookTargetEvent
    )

    async def pre_validate(
        self, headers: Mapping[str, str]
    ) -> WebhookPreValidationResult:
        """Reject malformed and ignore unsupported GitHub event families."""
        event_type = headers.get(self.event_header)
        if not event_type:
            raise WebhookPayloadError(
                f"Missing or empty {self.event_header} header."
            )
        try:
            GitHubWebhookEventType(event_type)
        except ValueError:
            return WebhookPreValidationResult.IGNORE
        return WebhookPreValidationResult.PROCESS

    def authenticate(
        self, body: bytes, headers: Mapping[str, str], secret: str
    ) -> None:
        """Authenticate a GitHub delivery."""
        authenticate_hmac_sha256(
            body=body,
            headers=headers,
            secret=secret,
            header=self.signature_header,
        )

    def get_event_type(
        self, payload: dict[str, Any], headers: Mapping[str, str]
    ) -> str:
        """Extract the raw GitHub event family."""
        event_type = headers.get(self.event_header)
        if not event_type:
            raise WebhookPayloadError(
                f"Missing required {self.event_header} header."
            )
        return event_type

    def get_delivery_id(
        self, payload: dict[str, Any], headers: Mapping[str, str]
    ) -> str | None:
        """Extract the optional GitHub delivery ID."""
        return headers.get(self.delivery_header)

    def validate_configuration(
        self,
        configuration: WebhookTriggerConfiguration | Mapping[str, Any],
    ) -> WebhookTriggerConfiguration:
        """Validate every GitHub target event and report all failures."""
        generic = WebhookTriggerConfiguration.model_validate(configuration)
        if not generic.target_events:
            raise ValueError(
                "GitHub webhook triggers require at least one target event."
            )
        valid: list[dict[str, Any]] = []
        errors: list[str] = []
        for index, raw_target in enumerate(generic.target_events):
            event_type = (
                raw_target.get("type", "unknown")
                if isinstance(raw_target, Mapping)
                else "unknown"
            )
            try:
                target = self._target_adapter.validate_python(raw_target)
            except ValidationError as error:
                reason = "; ".join(
                    item["msg"] for item in error.errors(include_url=False)
                )
                errors.append(f"index {index} (type={event_type}): {reason}")
            else:
                valid.append(target.model_dump(mode="json"))
        if errors:
            raise ValueError("Invalid target_events: " + "; ".join(errors))
        return WebhookTriggerConfiguration(target_events=valid)

    def _cast_runtime_targets(
        self, trigger: "WebhookTriggerResponse"
    ) -> tuple[bool, list[GitHubWebhookTargetEvent]]:
        try:
            generic = WebhookTriggerConfiguration.model_validate(
                trigger.configuration
            )
        except ValueError:
            logger.exception(
                "Skipping defective webhook trigger configuration %s",
                trigger.id,
            )
            return False, []
        if not generic.target_events:
            return True, []
        valid: list[GitHubWebhookTargetEvent] = []
        for index, raw_target in enumerate(generic.target_events):
            try:
                valid.append(self._target_adapter.validate_python(raw_target))
            except ValidationError:
                logger.exception(
                    "Skipping defective target event %s for trigger %s",
                    index,
                    trigger.id,
                )
        return False, valid

    def match_triggers(
        self,
        *,
        event: "WebhookEvent",
        candidates: Sequence["WebhookTriggerResponse"],
    ) -> list["WebhookTriggerResponse"]:
        """Match GitHub candidates while tolerating stale stored entries."""
        semantic = self._extract_semantic_event(event)
        if semantic is None:
            return []
        matches: list[WebhookTriggerResponse] = []
        for trigger in candidates:
            unrestricted, targets = self._cast_runtime_targets(trigger)
            if unrestricted or any(
                semantic.matches(target) for target in targets
            ):
                matches.append(trigger)
        return matches

    def _extract_semantic_event(
        self, event: "WebhookEvent"
    ) -> _SemanticEvent | None:
        payload = event.payload
        if event.event_type == "pull_request":
            pull_request = payload.get("pull_request")
            if (
                payload.get("action") != "closed"
                or not isinstance(pull_request, Mapping)
                or pull_request.get("merged") is not True
            ):
                return None
            repo = _string_at(payload, "repository", "full_name")
            target = _string_at(payload, "pull_request", "base", "ref")
            if repo is None or target is None:
                return None
            return _MergedPullRequestEvent(
                repo=repo,
                target_branch=target,
                source_branch=_string_at(
                    payload, "pull_request", "head", "ref"
                ),
                author=_string_at(payload, "pull_request", "user", "login"),
            )
        if event.event_type == "workflow_run":
            if payload.get("action") != "completed":
                return None
            workflow = _string_at(payload, "workflow_run", "name")
            if workflow is None:
                return None
            return _WorkflowRunCompletedEvent(
                workflow=workflow,
                conclusion=_string_at(payload, "workflow_run", "conclusion"),
                actor=_string_at(payload, "workflow_run", "actor", "login"),
            )
        if event.event_type == "push":
            ref = _string_at(payload, "ref")
            repo = _string_at(payload, "repository", "full_name")
            prefix = "refs/heads/"
            if ref is None or repo is None or not ref.startswith(prefix):
                return None
            return _PushEvent(
                repo=repo,
                branch=ref.removeprefix(prefix),
                actor=_string_at(payload, "sender", "login"),
            )
        if event.event_type == "release":
            if payload.get("action") != "published":
                return None
            repo = _string_at(payload, "repository", "full_name")
            tag = _string_at(payload, "release", "tag_name")
            if repo is None or tag is None:
                return None
            return _ReleasePublishedEvent(
                repo=repo,
                tag=tag,
                target_branch=_string_at(
                    payload, "release", "target_commitish"
                ),
                actor=_string_at(payload, "release", "author", "login"),
            )
        return None
