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
"""Event handler that emits a terminal frame when a run completes."""

import asyncio
from uuid import UUID

from zenml.dispatcher import EventHandler
from zenml.logger import get_logger
from zenml.models import PipelineRunResponse
from zenml.utils.time_utils import exponential_backoff_delays
from zenml.zen_server.streaming.brokers.base import StreamBroker
from zenml.zen_server.streaming.brokers.frames import EndFrame, encode_frame
from zenml.zen_server.streaming.brokers.utils import stream_key_for_run

logger = get_logger(__name__)

_END_PUBLISH_ATTEMPTS = 3

_END_PUBLISH_GRACE_SECONDS = 1.0


class StreamEndEventHandler(EventHandler):
    """Schedule a terminal `EndFrame` publish when a run becomes terminal."""

    def __init__(
        self,
        broker: StreamBroker,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        """Capture broker + loop for cross-thread scheduling.

        Args:
            broker: The stream broker to publish the EndFrame to.
            loop: Event loop owning the broker. The dispatcher may
                fire on any thread.
        """
        self._broker = broker
        self._loop = loop

    def handle_run_status_update(self, run: PipelineRunResponse) -> None:
        """Schedule a stream-end publish if the run is terminal.

        Args:
            run: The run whose status changed.
        """
        if run.in_progress:
            return

        try:
            asyncio.run_coroutine_threadsafe(
                self._publish_end(run.id), self._loop
            )
        except RuntimeError:
            logger.debug(
                "Skipping stream-end publish for run %s: event loop closed",
                run.id,
            )
        except Exception:
            logger.exception(
                "Failed to schedule stream-end publish for run %s", run.id
            )

    async def _publish_end(self, pipeline_run_id: UUID) -> None:
        """Publish a terminal EndFrame to the run's broker stream.

        Args:
            pipeline_run_id: The pipeline run whose stream to terminate.
        """
        try:
            # Wait for some time to allow clients to flush their buffers before
            # we publish the end frame that would cause all stream consumers
            # to disconnect.
            await asyncio.sleep(_END_PUBLISH_GRACE_SECONDS)
        except asyncio.CancelledError:
            return

        stream_key = stream_key_for_run(pipeline_run_id)
        stream_is_empty = False
        try:
            stream_is_empty = (
                await self._broker.latest_id(stream_key)
            ) is None
        except Exception:
            # Probe failed; default to publishing the EndFrame so a flaky
            # broker can't strand subscribers waiting on a terminal frame.
            stream_is_empty = False

        # Stream empty: no publishes happened, nothing to terminate. An
        # in-progress subscriber attached before the first publish would
        # be left hanging here — the heartbeat-branch TODO in sse.py is
        # the planned backstop.
        if stream_is_empty:
            logger.debug(
                "Skipping stream-end publish for run %s: stream is empty.",
                pipeline_run_id,
            )
            return
        payload = encode_frame(EndFrame())
        delays = exponential_backoff_delays(
            initial_delay=0.5,
            max_delay=5.0,
            jitter="full",
        )
        for attempt in range(1, _END_PUBLISH_ATTEMPTS + 1):
            try:
                await self._broker.publish(stream_key, [payload])
                break
            except asyncio.CancelledError:
                return
            except Exception as exc:
                if attempt >= _END_PUBLISH_ATTEMPTS:
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
                    _END_PUBLISH_ATTEMPTS,
                    exc,
                )
                try:
                    await asyncio.sleep(next(delays))
                except asyncio.CancelledError:
                    return
