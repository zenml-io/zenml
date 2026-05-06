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
"""Endpoints for live event streaming on pipeline runs.

Carve-out: these endpoints are async (`async def`). The OSS server is
otherwise sync; SSE / streaming endpoints are an explicit exception
because they hold long-lived connections that would pin a worker thread
and exhaust the pool. See `CLAUDE.md` and
`src/zenml/zen_server/AGENTS.md`.
"""

import asyncio
import json
from typing import AsyncGenerator, List, Optional, Set
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Security, status
from fastapi.responses import StreamingResponse

from zenml.constants import (
    API,
    EVENTS,
    RUNS,
    STREAM,
    VERSION_1,
)
from zenml.logger import get_logger
from zenml.models import EventBatchRequest, EventBatchResponse
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.models import Action
from zenml.zen_server.rbac.utils import verify_permission_for_model
from zenml.zen_server.streaming.broker import StreamTruncatedError
from zenml.zen_server.streaming.encoding import decode, encode
from zenml.zen_server.streaming.hub import EndMarker, GapMarker
from zenml.zen_server.utils import (
    event_broker,
    server_config,
    stream_hub,
    zen_store,
)

logger = get_logger(__name__)

router = APIRouter(
    prefix=API + VERSION_1 + RUNS,
    tags=["run_events"],
    responses={401: error_response, 403: error_response},
)


def _stream_key(pipeline_run_id: UUID) -> str:
    return f"zenml:stream:run:{pipeline_run_id}"


def _ensure_streaming_enabled() -> None:
    if not server_config().streaming_enabled:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Live event streaming is not enabled on this server.",
        )


@router.post(
    "/{pipeline_run_id}" + EVENTS,
    responses={
        401: error_response,
        403: error_response,
        404: error_response,
        422: error_response,
        501: error_response,
    },
)
async def publish_run_events(
    pipeline_run_id: UUID,
    batch: EventBatchRequest,
    _: AuthContext = Security(authorize),
) -> EventBatchResponse:
    """Append a batch of events to a pipeline run's live stream.

    Args:
        pipeline_run_id: ID of the pipeline run that owns the stream.
        batch: Events to publish.

    Returns:
        Count of events published and the broker-assigned id of the last one.
    """
    _ensure_streaming_enabled()

    run = zen_store().get_run(run_id=pipeline_run_id, hydrate=False)
    verify_permission_for_model(model=run, action=Action.UPDATE)

    if not batch.events:
        return EventBatchResponse(count=0, last_id=None)

    # Server stamps the run id from the URL — never trust producer-supplied
    # values to point at a different run.
    payloads: List[bytes] = []
    for event in batch.events:
        event = event.model_copy(update={"pipeline_run_id": pipeline_run_id})
        payloads.append(encode(event))

    try:
        ids = await event_broker().publish(
            _stream_key(pipeline_run_id), payloads
        )
    except Exception as exc:
        logger.exception("Broker publish failed for run %s", pipeline_run_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Broker publish failed: {exc}",
        )

    return EventBatchResponse(count=len(ids), last_id=ids[-1] if ids else None)


def _format_sse(
    event_name: str, data: object, event_id: Optional[str] = None
) -> bytes:
    lines: List[str] = []
    if event_id:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event_name}")
    lines.append(f"data: {json.dumps(data, default=str)}")
    lines.append("")
    lines.append("")
    return "\n".join(lines).encode("utf-8")


@router.get(
    "/{pipeline_run_id}" + EVENTS + STREAM,
    responses={
        401: error_response,
        403: error_response,
        404: error_response,
        501: error_response,
    },
)
async def stream_run_events(
    pipeline_run_id: UUID,
    since: Optional[str] = Query(default=None),
    kinds: Optional[List[str]] = Query(default=None),
    last_event_id: Optional[str] = Header(default=None, alias="Last-Event-ID"),
    _: AuthContext = Security(authorize),
) -> StreamingResponse:
    """Subscribe to a pipeline run's live event stream over SSE."""
    _ensure_streaming_enabled()

    run = zen_store().get_run(run_id=pipeline_run_id, hydrate=False)
    verify_permission_for_model(model=run, action=Action.READ)

    from_id = last_event_id or since
    kind_filter: Optional[Set[str]] = set(kinds) if kinds else None
    heartbeat_seconds = server_config().streaming_heartbeat_seconds

    async def generator() -> AsyncGenerator[bytes, None]:
        hub = stream_hub()
        agen = hub.attach(_stream_key(pipeline_run_id), from_id=from_id)
        try:
            while True:
                try:
                    item = await asyncio.wait_for(
                        agen.__anext__(), timeout=heartbeat_seconds
                    )
                except asyncio.TimeoutError:
                    yield b": ping\n\n"
                    continue
                except StopAsyncIteration:
                    return

                if isinstance(item, EndMarker):
                    yield _format_sse("end", {})
                    return
                if isinstance(item, GapMarker):
                    yield _format_sse("gap", {"reason": item.reason})
                    continue

                # BrokerEvent: decode for kind-filtering and forward as
                # the wire JSON. We send the StreamEvent JSON in `data:`
                # (resolved decision in the plan: full JSON, payload is
                # self-describing for downstream forwarders).
                try:
                    event = decode(item.payload)
                except Exception:
                    logger.exception(
                        "Could not decode event %s on run %s",
                        item.id,
                        pipeline_run_id,
                    )
                    continue
                if kind_filter is not None and event.kind not in kind_filter:
                    continue
                yield _format_sse(
                    event.kind,
                    event.model_dump(mode="json"),
                    event_id=item.id,
                )
        except StreamTruncatedError:
            yield _format_sse("gap", {"reason": "truncated"})
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("SSE stream failed for run %s", pipeline_run_id)
            yield _format_sse("error", {"reason": "stream_failed"})
        finally:
            await agen.aclose()

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",  # disable nginx response buffering
    }
    return StreamingResponse(
        generator(), media_type="text/event-stream", headers=headers
    )
