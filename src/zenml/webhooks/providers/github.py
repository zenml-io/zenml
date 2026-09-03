#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""GitHub webhook provider and semantic target event catalog."""

import logging
from abc import abstractmethod
from collections.abc import Mapping, Sequence
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    ClassVar,
    Literal,
    TypeAlias,
    cast,
)

from pydantic import BaseModel, Field

from zenml.models.v2.base.filter import StringFilterOption
from zenml.utils.enum_utils import StrEnum
from zenml.webhooks.providers.base import (
    BaseWebhookProvider,
    WebhookConfiguration,
    WebhookPayloadError,
    WebhookPreValidationResult,
    WebhookTargetEvent,
    WebhookTriggerMatch,
    authenticate_hmac_sha256,
    matches_string_collection_filter,
    matches_string_filter,
)
from zenml.webhooks.providers.types import BuiltinWebhookType

if TYPE_CHECKING:
    from zenml.models import WebhookTriggerResponse
    from zenml.webhooks.events import WebhookEvent

logger = logging.getLogger(__name__)

GITHUB_SIGNATURE_HEADER = "x-hub-signature-256"
GITHUB_EVENT_HEADER = "x-github-event"
GITHUB_DELIVERY_HEADER = "x-github-delivery"


class GitHubWebhookEventType(StrEnum):
    """Raw GitHub event families supported by semantic target events."""

    PULL_REQUEST = "pull_request"
    WORKFLOW_RUN = "workflow_run"
    PUSH = "push"
    RELEASE = "release"
    ISSUES = "issues"


class GitHubWebhookEvent(StrEnum):
    """Semantic GitHub events supported by webhook triggers."""

    MERGED_PULL_REQUEST = "merged_pull_request"
    WORKFLOW_RUN_COMPLETED = "workflow_run_completed"
    PUSH = "push"
    RELEASE_PUBLISHED = "release_published"
    ISSUE_OPENED = "issue_opened"


class MergedPullRequest(WebhookTargetEvent):
    """Filters for a merged GitHub pull request."""

    type: Literal[GitHubWebhookEvent.MERGED_PULL_REQUEST] = (
        GitHubWebhookEvent.MERGED_PULL_REQUEST
    )
    repo: StringFilterOption = None
    target_branch: StringFilterOption = None
    source_branch: StringFilterOption = None
    author: StringFilterOption = None


class WorkflowRunCompleted(WebhookTargetEvent):
    """Filters for a completed GitHub workflow run."""

    type: Literal[GitHubWebhookEvent.WORKFLOW_RUN_COMPLETED] = (
        GitHubWebhookEvent.WORKFLOW_RUN_COMPLETED
    )
    workflow: StringFilterOption = None
    conclusion: StringFilterOption = None
    actor: StringFilterOption = None


class PushEvent(WebhookTargetEvent):
    """Filters for a GitHub branch push."""

    type: Literal[GitHubWebhookEvent.PUSH] = GitHubWebhookEvent.PUSH
    repo: StringFilterOption = None
    branch: StringFilterOption = None
    actor: StringFilterOption = None


class ReleasePublished(WebhookTargetEvent):
    """Filters for a published GitHub release."""

    type: Literal[GitHubWebhookEvent.RELEASE_PUBLISHED] = (
        GitHubWebhookEvent.RELEASE_PUBLISHED
    )
    repo: StringFilterOption = None
    tag: StringFilterOption = None
    target_branch: StringFilterOption = None
    actor: StringFilterOption = None


class IssueOpened(WebhookTargetEvent):
    """Filters for a newly opened GitHub issue."""

    type: Literal[GitHubWebhookEvent.ISSUE_OPENED] = (
        GitHubWebhookEvent.ISSUE_OPENED
    )
    repo: StringFilterOption = None
    author: StringFilterOption = None
    author_association: StringFilterOption = None
    labels: StringFilterOption = None
    assignees: StringFilterOption = None
    milestone: StringFilterOption = None


GitHubWebhookTargetEvent: TypeAlias = Annotated[
    MergedPullRequest
    | WorkflowRunCompleted
    | PushEvent
    | ReleasePublished
    | IssueOpened,
    Field(discriminator="type"),
]


class GitHubWebhookConfiguration(WebhookConfiguration):
    """Typed configuration for a GitHub webhook trigger."""

    target_events: list[GitHubWebhookTargetEvent] = Field(min_length=1)


def _string_at(payload: Mapping[str, Any], *path: str) -> str | None:
    value: Any = payload
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value if isinstance(value, str) and value else None


def _object_strings_at(
    payload: Mapping[str, Any], *path: str, item_field: str
) -> list[str]:
    """Extract non-empty strings from objects in a nested list.

    Args:
        payload: The payload containing the nested list.
        path: Keys identifying the nested list.
        item_field: Field to extract from each object in the list.

    Returns:
        The extracted non-empty string values.
    """
    value: Any = payload
    for key in path:
        if not isinstance(value, Mapping):
            return []
        value = value.get(key)
    if not isinstance(value, list):
        return []
    return [
        item_value
        for item in value
        if isinstance(item, Mapping)
        and (item_value := _string_at(item, item_field)) is not None
    ]


class GitHubSemanticEvent(BaseModel):
    """Provider event normalized for semantic trigger matching."""

    event_filter_type: ClassVar[type[WebhookTargetEvent]]
    type: str

    @abstractmethod
    def matches(self, target: GitHubWebhookTargetEvent) -> bool:
        """Return whether the semantic event matches its typed target.

        Args:
            target: The typed target event configuration.

        Returns:
            Whether the semantic event matches the target.
        """


class GitHubCommit(BaseModel):
    """Commit metadata associated with a GitHub semantic event."""

    name: str | None = None
    sha: str


class GitHubMergedPullRequestEvent(GitHubSemanticEvent):
    """Normalized merged pull request event."""

    event_filter_type = MergedPullRequest
    type: Literal[GitHubWebhookEvent.MERGED_PULL_REQUEST] = (
        GitHubWebhookEvent.MERGED_PULL_REQUEST
    )
    repo: str
    target_branch: str
    source_branch: str | None
    author: str | None
    commit: GitHubCommit | None = None

    def matches(self, target: GitHubWebhookTargetEvent) -> bool:
        """Return whether this event matches a merged-pull-request target.

        Args:
            target: The typed target event configuration.

        Returns:
            Whether this event matches the target.
        """
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


class GitHubWorkflowRunCompletedEvent(GitHubSemanticEvent):
    """Normalized completed workflow run event."""

    event_filter_type = WorkflowRunCompleted
    type: Literal[GitHubWebhookEvent.WORKFLOW_RUN_COMPLETED] = (
        GitHubWebhookEvent.WORKFLOW_RUN_COMPLETED
    )
    workflow: str
    conclusion: str | None
    actor: str | None

    def matches(self, target: GitHubWebhookTargetEvent) -> bool:
        """Return whether this event matches a workflow-run target.

        Args:
            target: The typed target event configuration.

        Returns:
            Whether this event matches the target.
        """
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


class GitHubPushEvent(GitHubSemanticEvent):
    """Normalized branch push event."""

    event_filter_type = PushEvent
    type: Literal[GitHubWebhookEvent.PUSH] = GitHubWebhookEvent.PUSH
    repo: str
    branch: str
    actor: str | None
    commit: GitHubCommit | None = None

    def matches(self, target: GitHubWebhookTargetEvent) -> bool:
        """Return whether this event matches a push target.

        Args:
            target: The typed target event configuration.

        Returns:
            Whether this event matches the target.
        """
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


class GitHubReleasePublishedEvent(GitHubSemanticEvent):
    """Normalized published release event."""

    event_filter_type = ReleasePublished
    type: Literal[GitHubWebhookEvent.RELEASE_PUBLISHED] = (
        GitHubWebhookEvent.RELEASE_PUBLISHED
    )
    repo: str
    tag: str
    target_branch: str | None
    actor: str | None

    def matches(self, target: GitHubWebhookTargetEvent) -> bool:
        """Return whether this event matches a published-release target.

        Args:
            target: The typed target event configuration.

        Returns:
            Whether this event matches the target.
        """
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


class GitHubIssueOpenedEvent(GitHubSemanticEvent):
    """Normalized newly opened issue event."""

    event_filter_type = IssueOpened
    type: Literal[GitHubWebhookEvent.ISSUE_OPENED] = (
        GitHubWebhookEvent.ISSUE_OPENED
    )
    repo: str
    number: int
    title: str
    author: str | None
    author_association: str | None
    labels: list[str]
    assignees: list[str]
    milestone: str | None
    issue_type: str | None

    def matches(self, target: GitHubWebhookTargetEvent) -> bool:
        """Return whether this event matches an opened-issue target.

        Args:
            target: The typed target event configuration.

        Returns:
            Whether this event matches the target.
        """
        if not isinstance(target, IssueOpened):
            return False
        return all(
            (
                matches_string_filter(
                    actual=self.repo, configured=target.repo
                ),
                matches_string_filter(
                    actual=self.author, configured=target.author
                ),
                matches_string_filter(
                    actual=self.author_association,
                    configured=target.author_association,
                ),
                matches_string_collection_filter(
                    actual=self.labels, configured=target.labels
                ),
                matches_string_collection_filter(
                    actual=self.assignees, configured=target.assignees
                ),
                matches_string_filter(
                    actual=self.milestone, configured=target.milestone
                ),
            )
        )


class GitHubWebhookProvider(BaseWebhookProvider):
    """Provider for authenticated and semantically matched GitHub webhooks."""

    webhook_type = BuiltinWebhookType.GITHUB
    configuration_class = GitHubWebhookConfiguration

    async def pre_validate(
        self, headers: Mapping[str, str]
    ) -> WebhookPreValidationResult:
        """Reject malformed and ignore unsupported GitHub event families.

        Args:
            headers: The untrusted request headers.

        Returns:
            Whether generic intake should process or ignore the delivery.

        Raises:
            WebhookPayloadError: If the GitHub event header is missing.
        """
        event_type = headers.get(GITHUB_EVENT_HEADER)
        if not event_type:
            raise WebhookPayloadError(
                f"Missing or empty {GITHUB_EVENT_HEADER} header."
            )
        try:
            GitHubWebhookEventType(event_type)
        except ValueError:
            return WebhookPreValidationResult.IGNORE
        return WebhookPreValidationResult.PROCESS

    def authenticate(
        self, body: bytes, headers: Mapping[str, str], secret: str
    ) -> None:
        """Authenticate a GitHub delivery.

        Args:
            body: The exact raw request body.
            headers: The request headers.
            secret: The webhook signing secret.
        """
        authenticate_hmac_sha256(
            body=body,
            headers=headers,
            secret=secret,
            header=GITHUB_SIGNATURE_HEADER,
        )

    def get_event_type(
        self, payload: dict[str, Any], headers: Mapping[str, str]
    ) -> str:
        """Extract the raw GitHub event family.

        Args:
            payload: The parsed GitHub payload.
            headers: The request headers.

        Returns:
            The raw GitHub event family.

        Raises:
            WebhookPayloadError: If the GitHub event header is missing.
        """
        event_type = headers.get(GITHUB_EVENT_HEADER)
        if not event_type:
            raise WebhookPayloadError(
                f"Missing required {GITHUB_EVENT_HEADER} header."
            )
        return event_type

    def get_delivery_id(
        self, payload: dict[str, Any], headers: Mapping[str, str]
    ) -> str | None:
        """Extract the optional GitHub delivery ID.

        Args:
            payload: The parsed GitHub payload.
            headers: The request headers.

        Returns:
            The delivery ID, if present.
        """
        return headers.get(GITHUB_DELIVERY_HEADER)

    def _cast_runtime_targets(
        self, trigger: "WebhookTriggerResponse"
    ) -> list[GitHubWebhookTargetEvent]:
        try:
            configuration = self.validate_configuration(trigger.configuration)
        except (TypeError, ValueError):
            logger.exception(
                "Skipping defective webhook trigger configuration %s",
                trigger.id,
            )
            return []
        return cast(GitHubWebhookConfiguration, configuration).target_events

    def match_triggers(
        self,
        *,
        event: "WebhookEvent",
        candidates: Sequence["WebhookTriggerResponse"],
    ) -> "WebhookTriggerMatch[WebhookTriggerResponse]":
        """Match GitHub triggers and return the parsed semantic event.

        Args:
            event: The trusted GitHub webhook event.
            candidates: The candidate webhook triggers.

        Returns:
            Matching triggers and their shared semantic event.
        """
        semantic = self.parse_semantic_event(event)
        if semantic is None:
            return WebhookTriggerMatch(triggers=[])
        matches: list[WebhookTriggerResponse] = []
        for trigger in candidates:
            targets = self._cast_runtime_targets(trigger)
            if any(semantic.matches(target) for target in targets):
                matches.append(trigger)
        return WebhookTriggerMatch(
            triggers=matches,
            event=semantic.model_dump(mode="json"),
        )

    def parse_semantic_event(
        self, event: "WebhookEvent"
    ) -> GitHubSemanticEvent | None:
        """Parse a trusted delivery into a normalized semantic event.

        Args:
            event: The trusted GitHub webhook event.

        Returns:
            The normalized semantic event, or `None` for irrelevant payloads.
        """
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
            merge_commit_sha = _string_at(
                payload, "pull_request", "merge_commit_sha"
            )
            return GitHubMergedPullRequestEvent(
                repo=repo,
                target_branch=target,
                source_branch=_string_at(
                    payload, "pull_request", "head", "ref"
                ),
                author=_string_at(payload, "pull_request", "user", "login"),
                commit=(
                    GitHubCommit(
                        name=_string_at(payload, "pull_request", "title"),
                        sha=merge_commit_sha,
                    )
                    if merge_commit_sha
                    else None
                ),
            )
        if event.event_type == "workflow_run":
            if payload.get("action") != "completed":
                return None
            workflow = _string_at(payload, "workflow_run", "name")
            if workflow is None:
                return None
            return GitHubWorkflowRunCompletedEvent(
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
            head_commit_sha = _string_at(payload, "head_commit", "id")
            return GitHubPushEvent(
                repo=repo,
                branch=ref.removeprefix(prefix),
                actor=_string_at(payload, "sender", "login"),
                commit=(
                    GitHubCommit(
                        name=_string_at(payload, "head_commit", "message"),
                        sha=head_commit_sha,
                    )
                    if head_commit_sha
                    else None
                ),
            )
        if event.event_type == "release":
            if payload.get("action") != "published":
                return None
            repo = _string_at(payload, "repository", "full_name")
            tag = _string_at(payload, "release", "tag_name")
            if repo is None or tag is None:
                return None
            return GitHubReleasePublishedEvent(
                repo=repo,
                tag=tag,
                target_branch=_string_at(
                    payload, "release", "target_commitish"
                ),
                actor=_string_at(payload, "release", "author", "login"),
            )
        if event.event_type == "issues":
            issue = payload.get("issue")
            if payload.get("action") != "opened" or not isinstance(
                issue, Mapping
            ):
                return None
            repo = _string_at(payload, "repository", "full_name")
            title = _string_at(payload, "issue", "title")
            number = issue.get("number")
            if (
                repo is None
                or title is None
                or not isinstance(number, int)
                or isinstance(number, bool)
            ):
                return None
            return GitHubIssueOpenedEvent(
                repo=repo,
                number=number,
                title=title,
                author=_string_at(payload, "issue", "user", "login"),
                author_association=_string_at(
                    payload, "issue", "author_association"
                ),
                labels=_object_strings_at(
                    payload, "issue", "labels", item_field="name"
                ),
                assignees=_object_strings_at(
                    payload, "issue", "assignees", item_field="login"
                ),
                milestone=_string_at(payload, "issue", "milestone", "title"),
                issue_type=_string_at(payload, "issue", "type", "name"),
            )
        return None
