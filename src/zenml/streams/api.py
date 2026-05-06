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
"""Public producer API for streaming events from inside a step."""

from typing import Any, Dict, Optional

from zenml.logger import get_logger
from zenml.models import StreamEvent
from zenml.streams.publisher import get_publisher

logger = get_logger(__name__)


def _resolve_step_context() -> Optional[Dict[str, Any]]:
    """Return identifying info for the currently-running step, or None."""
    try:
        from zenml.steps.step_context import get_step_context
    except ImportError:
        return None
    try:
        ctx = get_step_context()
    except RuntimeError:
        return None
    return {
        "pipeline_run_id": ctx.pipeline_run.id,
        "step_run_id": ctx.step_run.id,
        "step_name": ctx.step_name,
    }


def publish(
    payload: Dict[str, Any],
    *,
    kind: str = "event",
    stream_id: Optional[str] = None,
    index: Optional[int] = None,
) -> None:
    """Publish a single event to the current run's live stream.

    Must be called from inside a running step. Calls outside a step
    context are silently dropped (with a debug log).

    Args:
        payload: User-defined event body. Must be JSON-serializable.
        kind: Event kind; well-known values include 'token', 'tool_call',
            'tool_result', 'reasoning', 'status', 'metric'.
        stream_id: Optional sub-stream id (groups tokens of one
            generation, for example).
        index: Optional ordering index within stream_id.
    """
    info = _resolve_step_context()
    if info is None:
        logger.debug(
            "streams.publish() called outside a step context; dropping"
        )
        return

    event = StreamEvent(
        pipeline_run_id=info["pipeline_run_id"],
        step_run_id=info["step_run_id"],
        step_name=info["step_name"],
        kind=kind,
        stream_id=stream_id,
        index=index,
        payload=payload,
    )
    get_publisher().publish(event)


def flush(timeout: float = 2.0) -> None:
    """Block until all queued events have been sent (or timeout)."""
    get_publisher().flush(timeout=timeout)
