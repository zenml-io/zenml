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
"""End-of-run broker signal: handler + helpers."""

import asyncio
from uuid import UUID

from zenml.dispatcher import EventHandler
from zenml.logger import get_logger
from zenml.models import PipelineRunResponse
from zenml.utils.time_utils import exponential_backoff_delays
from zenml.zen_server.streaming.broker import StreamBroker
from zenml.zen_server.streaming.wire import EndFrame, encode_frame
from zenml.zen_server.utils import server_config

logger = get_logger(__name__)

# Total publish attempts (the backoff iterator yields N-1 delays
# between N attempts; e.g., 3 attempts → 2 sleeps).
_END_PUBLISH_MAX_ATTEMPTS = 3


def stream_key_for_run(pipeline_run_id: UUID) -> str:
    """Broker stream key for a pipeline run, scoped to this server."""
    return (
        f"zenml:stream:server:{server_config().deployment_id}"
        f":run:{pipeline_run_id}"
    )


class StreamEndEventHandler(EventHandler):
    """Schedules a terminal `EndFrame` publish when a run reaches a terminal state.

    Captures the broker + loop at construction so the dispatcher fire
    (which may be on a worker thread) can hand the publish off to the
    streaming subsystem's loop.
    """

    def __init__(
        self,
        broker: StreamBroker,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        """Capture broker + loop for cross-thread scheduling."""
        self._broker = broker
        self._loop = loop

    def handle_run_status_update(self, run: PipelineRunResponse) -> None:
        """Schedule a stream-end publish if the run is terminal.

        Args:
            run: The run whose status changed.
        """
        if run.in_progress:
            return
        if self._loop.is_closed():
            logger.debug(
                "Skipping stream-end publish for run %s: event loop is closed",
                run.id,
            )
            return
        try:
            asyncio.run_coroutine_threadsafe(
                self._publish_end(run.id), self._loop
            )
        except Exception:
            logger.exception(
                "Failed to schedule stream-end publish for run %s", run.id
            )

    async def _publish_end(self, pipeline_run_id: UUID) -> None:
        payload = encode_frame(EndFrame(pipeline_run_id=pipeline_run_id))
        stream_key = stream_key_for_run(pipeline_run_id)
        delays = exponential_backoff_delays(
            attempts=_END_PUBLISH_MAX_ATTEMPTS - 1,
            initial_delay=0.5,
            max_delay=5.0,
            jitter="full",
        )
        attempt = 0
        while True:
            attempt += 1
            try:
                await self._broker.publish(stream_key, [payload])
                return
            except asyncio.CancelledError:
                return
            except Exception as exc:
                try:
                    delay = next(delays)
                except StopIteration:
                    logger.exception(
                        "Failed to publish stream-end sentinel for run %s "
                        "after %d attempts",
                        pipeline_run_id,
                        attempt,
                    )
                    return
                logger.warning(
                    "Stream-end publish for run %s failed (attempt %d/%d): %s",
                    pipeline_run_id,
                    attempt,
                    _END_PUBLISH_MAX_ATTEMPTS,
                    exc,
                )
                try:
                    await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    return
