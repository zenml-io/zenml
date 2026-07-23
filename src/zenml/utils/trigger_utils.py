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
"""Utility functions to manage triggers."""

import logging
from collections.abc import Sequence
from typing import Literal, overload
from uuid import UUID

from pydantic import validate_call

from zenml.client import Client
from zenml.enums import (
    PLATFORM_EVENT_REGISTRY,
    PipelineEvent,
    PipelineRunEvent,
    PipelineSnapshotEvent,
    SourceType,
    TriggerRunConcurrency,
    WebhookType,
)
from zenml.models import (
    GitHubWebhookEventConfiguration,
    PipelineRunResponse,
    PlatformEventTriggerResponse,
    WebhookTriggerResponse,
)

logger = logging.getLogger(__name__)


# create pipeline trigger overload
@overload
def create_platform_event_trigger(
    *,
    name: str,
    source_pipeline_id: UUID,
    target_events: list[PipelineEvent],
    active: bool = True,
    concurrency: TriggerRunConcurrency = TriggerRunConcurrency.SKIP,
) -> PlatformEventTriggerResponse:
    pass


# create pipeline run trigger overload
@overload
def create_platform_event_trigger(
    *,
    name: str,
    source_pipeline_run_id: UUID,
    target_events: list[PipelineRunEvent],
    active: bool = True,
    concurrency: TriggerRunConcurrency = TriggerRunConcurrency.SKIP,
) -> PlatformEventTriggerResponse:
    pass


# create pipeline snapshot trigger overload
@overload
def create_platform_event_trigger(
    *,
    name: str,
    source_pipeline_snapshot_id: UUID,
    target_events: list[PipelineSnapshotEvent],
    active: bool = True,
    concurrency: TriggerRunConcurrency = TriggerRunConcurrency.SKIP,
) -> PlatformEventTriggerResponse:
    pass


def create_platform_event_trigger(
    name: str,
    target_events: (
        list[PipelineEvent]
        | list[PipelineRunEvent]
        | list[PipelineSnapshotEvent]
    ),
    source_pipeline_id: UUID | None = None,
    source_pipeline_run_id: UUID | None = None,
    source_pipeline_snapshot_id: UUID | None = None,
    active: bool = True,
    concurrency: TriggerRunConcurrency = TriggerRunConcurrency.SKIP,
) -> PlatformEventTriggerResponse:
    """Utility function to create a Platform Event Trigger.

    Args:
        name: The name of the trigger.
        target_events: A list of target events (events that will cause trigger execution).
        source_pipeline_id: A Pipeline ID (one of the source options).
        source_pipeline_run_id: A Pipeline Run ID (one of the source options).
        source_pipeline_snapshot_id: A Pipeline Snapshot ID (one of the source options).
        active: Flag - whether to activate the trigger on creation.
        concurrency: How to handle concurrent executions (SKIP/SUBMIT etc.).

    Returns:
        The created platform event trigger object response.

    Raises:
        ValueError: If more than one or no source options (e.g. source_pipeline_id) are specified.
    """
    client = Client()

    options = [
        source_pipeline_id,
        source_pipeline_run_id,
        source_pipeline_snapshot_id,
    ]

    if sum(1 if option is not None else 0 for option in options) > 1:
        raise ValueError("You can not provide more than 1 source option")
    elif source_pipeline_id is not None:
        source_type = SourceType.PIPELINE
        source_id = source_pipeline_id
    elif source_pipeline_run_id is not None:
        source_type = SourceType.PIPELINE_RUN
        source_id = source_pipeline_run_id
    elif source_pipeline_snapshot_id is not None:
        source_type = SourceType.PIPELINE_SNAPSHOT
        source_id = source_pipeline_snapshot_id
    else:
        raise ValueError("You must specify at least one source option")

    return client.create_platform_event_trigger(
        name=name,
        source_type=source_type,
        source_id=source_id,
        target_events=[str(t.value) for t in target_events],
        active=active,
        concurrency=concurrency,
    )


@overload
def update_platform_event_trigger(
    *,
    trigger_name_id_or_prefix: str | UUID,
    name: str | None = None,
    source_pipeline_id: UUID | None = None,
    target_events: list[PipelineEvent] | None = None,
    active: bool | None = None,
    concurrency: TriggerRunConcurrency | None = None,
) -> PlatformEventTriggerResponse:
    pass


@overload
def update_platform_event_trigger(
    *,
    trigger_name_id_or_prefix: str | UUID,
    name: str | None = None,
    source_pipeline_run_id: UUID | None = None,
    target_events: list[PipelineRunEvent] | None = None,
    active: bool | None = None,
    concurrency: TriggerRunConcurrency | None = None,
) -> PlatformEventTriggerResponse:
    pass


@overload
def update_platform_event_trigger(
    *,
    trigger_name_id_or_prefix: str | UUID,
    name: str | None = None,
    source_pipeline_snapshot_id: UUID | None = None,
    target_events: list[PipelineSnapshotEvent] | None = None,
    active: bool | None = None,
    concurrency: TriggerRunConcurrency | None = None,
) -> PlatformEventTriggerResponse:
    pass


@overload
def update_platform_event_trigger(
    *,
    trigger_name_id_or_prefix: str | UUID,
    name: str | None = None,
    target_events: (
        list[PipelineEvent]
        | list[PipelineRunEvent]
        | list[PipelineSnapshotEvent]
        | None
    ) = None,
    active: bool | None = None,
    concurrency: TriggerRunConcurrency | None = None,
) -> PlatformEventTriggerResponse:
    pass


def update_platform_event_trigger(
    trigger_name_id_or_prefix: str | UUID,
    name: str | None = None,
    target_events: (
        list[PipelineEvent]
        | list[PipelineRunEvent]
        | list[PipelineSnapshotEvent]
        | None
    ) = None,
    source_pipeline_id: UUID | None = None,
    source_pipeline_run_id: UUID | None = None,
    source_pipeline_snapshot_id: UUID | None = None,
    active: bool | None = None,
    concurrency: TriggerRunConcurrency | None = None,
) -> PlatformEventTriggerResponse:
    """Utility function to update a Platform Event Trigger.

    Args:
        trigger_name_id_or_prefix: The name, ID, or ID prefix of the trigger.
        name: The name of the trigger.
        target_events: A list of target events (events that will cause trigger execution).
        source_pipeline_id: A Pipeline ID (one of the source options).
        source_pipeline_run_id: A Pipeline Run ID (one of the source options).
        source_pipeline_snapshot_id: A Pipeline Snapshot ID (one of the source options).
        active: Flag - whether to activate the trigger on creation.
        concurrency: How to handle concurrent executions (SKIP/SUBMIT etc.).

    Returns:
        The updated platform event trigger object response.

    Raises:
        ValueError: If more than one source options (e.g. source_pipeline_id) are specified.
    """
    client = Client()

    options = [
        source_pipeline_id,
        source_pipeline_run_id,
        source_pipeline_snapshot_id,
    ]

    if sum(1 if option is not None else 0 for option in options) > 1:
        raise ValueError("You can not provide more than 1 source option")
    elif source_pipeline_id is not None:
        source_id = source_pipeline_id
        source_type = SourceType.PIPELINE
    elif source_pipeline_run_id is not None:
        source_id = source_pipeline_run_id
        source_type = SourceType.PIPELINE_RUN
    elif source_pipeline_snapshot_id is not None:
        source_id = source_pipeline_snapshot_id
        source_type = SourceType.PIPELINE_SNAPSHOT
    else:
        source_id = None
        source_type = None

    return client.update_platform_event_trigger(
        trigger_name_id_or_prefix=trigger_name_id_or_prefix,
        name=name,
        active=active,
        source_id=source_id,
        source_type=source_type,
        target_events=[str(t.value) for t in target_events]
        if target_events is not None
        else None,
        concurrency=concurrency,
    )


@overload
def create_webhook_trigger(
    *,
    name: str,
    webhook_type: Literal[WebhookType.GITHUB],
    events: Sequence[GitHubWebhookEventConfiguration],
    webhook_integration: str | UUID | None = None,
    project_id: str | UUID | None = None,
    active: bool = True,
    concurrency: TriggerRunConcurrency = TriggerRunConcurrency.SKIP,
) -> WebhookTriggerResponse:
    pass


@overload
def create_webhook_trigger(
    *,
    name: str,
    webhook_type: Literal[WebhookType.CUSTOM],
    webhook_integration: str | UUID | None = None,
    project_id: str | UUID | None = None,
    active: bool = True,
    concurrency: TriggerRunConcurrency = TriggerRunConcurrency.SKIP,
) -> WebhookTriggerResponse:
    pass


def create_webhook_trigger(
    *,
    name: str,
    webhook_type: WebhookType,
    events: Sequence[GitHubWebhookEventConfiguration] | None = None,
    webhook_integration: str | UUID | None = None,
    project_id: str | UUID | None = None,
    active: bool = True,
    concurrency: TriggerRunConcurrency = TriggerRunConcurrency.SKIP,
) -> WebhookTriggerResponse:
    """Create a webhook trigger with provider-specific type guidance.

    Args:
        name: The trigger name.
        webhook_type: The compatible webhook provider type.
        events: GitHub semantic event configurations.
        webhook_integration: Optional integration name, ID, or ID prefix.
        project_id: The project ID.
        active: Whether the trigger should be active.
        concurrency: The trigger run concurrency behavior.

    Returns:
        The created webhook trigger.
    """
    return Client().create_webhook_trigger(
        name=name,
        webhook_type=webhook_type,
        events=events,
        webhook_integration=webhook_integration,
        project_id=project_id,
        active=active,
        concurrency=concurrency,
    )


def update_webhook_trigger(
    *,
    trigger_name_id_or_prefix: str | UUID,
    name: str | None = None,
    active: bool | None = None,
    concurrency: TriggerRunConcurrency | None = None,
    webhook_integration: str | UUID | None = None,
    detach_webhook_integration: bool = False,
    events: Sequence[GitHubWebhookEventConfiguration] | None = None,
) -> WebhookTriggerResponse:
    """Update a webhook trigger and optionally replace its event list.

    Args:
        trigger_name_id_or_prefix: The trigger name, ID, or ID prefix.
        name: The new trigger name.
        active: The new active state.
        concurrency: The new trigger run concurrency behavior.
        webhook_integration: A replacement integration name, ID, or ID prefix.
        detach_webhook_integration: Whether to detach the integration.
        events: Replacement GitHub semantic event configurations. Omitting
            this preserves the existing list.

    Returns:
        The updated webhook trigger.
    """
    return Client().update_webhook_trigger(
        trigger_name_id_or_prefix=trigger_name_id_or_prefix,
        name=name,
        active=active,
        concurrency=concurrency,
        webhook_integration=webhook_integration,
        detach_webhook_integration=detach_webhook_integration,
        events=events,
    )


@validate_call()
def list_supported_events(
    source_type: SourceType,
) -> list[str]:
    """Helper - list supported events for a source type.

    Args:
        source_type: A SourceType value.

    Returns:
        A list of supported events for the source type.
    """
    return PLATFORM_EVENT_REGISTRY[source_type].values()


def get_upstream_run(
    pipeline_run: PipelineRunResponse,
) -> PipelineRunResponse | None:
    """Helper function to resolve upstream runs safely.

    Args:
        pipeline_run: Current pipeline run.

    Returns:
        Upstream run if available, None otherwise.
    """
    info = pipeline_run.trigger_execution_info

    if info is None:
        return None

    if info.upstream_run_id is None:
        return None

    try:
        return Client().get_pipeline_run(
            name_id_or_prefix=info.upstream_run_id
        )
    except Exception as exc:
        logger.error(
            "Failed to get upstream run: %s",
            info.upstream_run_id,
            exc_info=exc,
        )
        return None
