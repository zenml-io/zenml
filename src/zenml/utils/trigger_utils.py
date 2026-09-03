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
from collections.abc import Mapping
from typing import Any, overload
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
)
from zenml.models import (
    PipelineRunResponse,
    PlatformEventTriggerResponse,
    WebhookTriggerResponse,
)
from zenml.webhooks import WebhookConfiguration

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


def create_webhook_trigger(
    *,
    name: str,
    webhook: str | UUID,
    configuration: Mapping[str, Any] | WebhookConfiguration,
    project_id: str | UUID | None = None,
    active: bool = True,
    concurrency: TriggerRunConcurrency = TriggerRunConcurrency.SKIP,
) -> WebhookTriggerResponse:
    """Create a webhook trigger owned by a webhook.

    Args:
        name: The trigger name.
        webhook: The owning webhook name, ID, or ID prefix.
        configuration: The complete webhook trigger configuration.
        project_id: The project ID.
        active: Whether the trigger should be active.
        concurrency: The trigger run concurrency behavior.

    Returns:
        The created webhook trigger.
    """
    return Client().create_webhook_trigger(
        name=name,
        webhook=webhook,
        configuration=configuration,
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
    configuration: Mapping[str, Any] | WebhookConfiguration | None = None,
) -> WebhookTriggerResponse:
    """Update a webhook trigger and optionally replace its configuration.

    Args:
        trigger_name_id_or_prefix: The trigger name, ID, or ID prefix.
        name: The new trigger name.
        active: The new active state.
        concurrency: The new trigger run concurrency behavior.
        configuration: Complete replacement configuration. Omitting this
            preserves the existing configuration.

    Returns:
        The updated webhook trigger.
    """
    return Client().update_webhook_trigger(
        trigger_name_id_or_prefix=trigger_name_id_or_prefix,
        name=name,
        active=active,
        concurrency=concurrency,
        configuration=configuration,
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


def get_webhook_upstream_event(
    pipeline_run: PipelineRunResponse | None = None,
) -> dict[str, Any] | None:
    """Get the upstream webhook event for a pipeline run.

    When no run is provided, the current step's pipeline run is used.

    Args:
        pipeline_run: Pipeline run to inspect. If omitted, the current run is
            resolved from the active step context.

    Returns:
        Plain provider-keyed webhook event metadata, or `None` if unavailable.

    Raises:
        RuntimeError: If no run is provided outside a running step.
    """
    if pipeline_run is None:
        from zenml.steps.step_context import get_step_context

        pipeline_run = get_step_context().pipeline_run

    info = pipeline_run.trigger_execution_info
    if info is None or info.webhook_upstream_event is None:
        return None

    return {
        provider: provider_info.model_dump(mode="json")
        for provider, provider_info in info.webhook_upstream_event.items()
    }
