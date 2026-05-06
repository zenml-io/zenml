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
"""Internal helpers for the producer-side streams API."""

import json
from typing import Any, Dict, NamedTuple, Optional
from uuid import UUID

from zenml.constants import STREAM_EVENT_PAYLOAD_BYTES_MAX


def _check_payload_size(payload: Dict[str, Any]) -> None:
    """Producer-side fast-fail for oversize payloads.

    Lives on the publish path, not the model, so server-side
    deserialization doesn't re-encode every event just to discard the
    result. The authoritative gate is still the wire envelope check on
    the server (`encode_event_for_publish` raises 413).

    Raises:
        ValueError: If the payload isn't JSON-encodable or its encoded
            size exceeds the cap.
    """
    try:
        encoded_size = len(json.dumps(payload, default=str).encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"payload is not JSON-encodable: {exc}")
    if encoded_size > STREAM_EVENT_PAYLOAD_BYTES_MAX:
        raise ValueError(
            f"payload encoded size ({encoded_size} bytes) exceeds the "
            f"cap of {STREAM_EVENT_PAYLOAD_BYTES_MAX} bytes"
        )


class _RunContext(NamedTuple):
    """The run/step to attribute a stream event to."""

    pipeline_run_id: UUID
    step_run_id: Optional[UUID]
    step_name: Optional[str]


def _resolve_run_context() -> Optional[_RunContext]:
    """Identify the run / step to attribute events to, or None."""
    # TODO: decide whether to attribute events to `root_run_id` instead
    # of the immediate `pipeline_run_id`. Using the root would let a
    # consumer attach to a top-level run and receive events from every
    # nested sub-pipeline on the same stream — useful for "watch the
    # whole agent run" UX. Using the immediate run id keeps sub-runs
    # isolated, which is what we want for per-step dashboards. Pick
    # one once we have a concrete use case driving the decision.
    from zenml.execution.pipeline.dynamic.run_context import (
        DynamicPipelineRunContext,
    )
    from zenml.steps.step_context import get_step_context

    try:
        ctx = get_step_context()
    except RuntimeError:
        ctx = None
    if ctx is not None:
        return _RunContext(
            pipeline_run_id=ctx.pipeline_run.id,
            step_run_id=ctx.step_run.id,
            step_name=ctx.step_name,
        )

    dyn = DynamicPipelineRunContext.get()
    if dyn is None:
        return None
    return _RunContext(
        pipeline_run_id=dyn.run.id,
        step_run_id=None,
        step_name=None,
    )
