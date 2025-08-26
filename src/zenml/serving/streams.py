#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Stream management for ZenML pipeline serving with SSE and WebSocket support."""

import asyncio
import json
import threading
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional

import anyio
from anyio.streams.memory import (
    MemoryObjectReceiveStream,
    MemoryObjectSendStream,
)

from zenml.logger import get_logger
from zenml.serving.events import ServingEvent

logger = get_logger(__name__)


class EventStream:
    """Manages event streaming for a specific job with backpressure handling."""

    def __init__(self, job_id: str, buffer_size: int = 100):
        """Initialize event stream for a job.

        Args:
            job_id: Job ID this stream belongs to
            buffer_size: Maximum number of events to buffer
        """
        self.job_id = job_id
        self.buffer_size = buffer_size

        # Create memory object stream for event passing
        self._send_stream: Optional[MemoryObjectSendStream[ServingEvent]] = (
            None
        )
        self._receive_stream: Optional[
            MemoryObjectReceiveStream[ServingEvent]
        ] = None
        self._stream_created = False

        # Track subscribers and stream state
        self._subscribers = 0
        self._closed = False

        logger.debug(
            f"Created EventStream for job {job_id} with buffer size {buffer_size}"
        )

    def _ensure_stream(self) -> None:
        """Ensure the memory object stream is created."""
        if not self._stream_created:
            self._send_stream, self._receive_stream = (
                anyio.create_memory_object_stream(
                    max_buffer_size=self.buffer_size
                )
            )
            self._stream_created = True

    async def send_event(self, event: ServingEvent) -> bool:
        """Send an event to all subscribers.

        Args:
            event: Event to send

        Returns:
            True if event was sent, False if stream is closed or full
        """
        if self._closed:
            return False

        self._ensure_stream()

        try:
            # Non-blocking send with immediate failure if buffer is full
            assert (
                self._send_stream is not None
            )  # _ensure_stream guarantees this
            self._send_stream.send_nowait(event)
            logger.debug(
                f"Sent event {event.event_type} for job {self.job_id}"
            )
            return True

        except anyio.WouldBlock:
            # Buffer is full - drop the event and log warning
            logger.warning(
                f"Event buffer full for job {self.job_id}, dropping event {event.event_type}. "
                f"Consider increasing buffer size or reducing event frequency."
            )
            return False

        except Exception as e:
            logger.error(f"Error sending event for job {self.job_id}: {e}")
            return False

    async def subscribe(self) -> AsyncGenerator[ServingEvent, None]:
        """Subscribe to events from this stream.

        Yields:
            ServingEvent objects as they become available
        """
        if self._closed:
            logger.warning(
                f"Attempted to subscribe to closed stream for job {self.job_id}"
            )
            return

        self._ensure_stream()
        self._subscribers += 1

        try:
            logger.debug(
                f"New subscriber for job {self.job_id} (total: {self._subscribers})"
            )

            assert (
                self._receive_stream is not None
            )  # _ensure_stream guarantees this
            async with self._receive_stream.clone() as stream:
                async for event in stream:
                    if self._closed:
                        break
                    yield event

        except Exception as e:
            logger.error(f"Error in subscription for job {self.job_id}: {e}")

        finally:
            self._subscribers -= 1
            logger.debug(
                f"Subscriber disconnected from job {self.job_id} (remaining: {self._subscribers})"
            )

    def close(self) -> None:
        """Close the stream and stop accepting new events."""
        if self._closed:
            return

        self._closed = True

        if self._send_stream:
            self._send_stream.close()

        logger.debug(f"Closed EventStream for job {self.job_id}")

    @property
    def is_closed(self) -> bool:
        """Check if the stream is closed."""
        return self._closed

    @property
    def subscriber_count(self) -> int:
        """Get the number of active subscribers."""
        return self._subscribers


class StreamManager:
    """Manages event streams for all active jobs."""

    def __init__(
        self, default_buffer_size: int = 100, cleanup_interval: int = 300
    ):
        """Initialize stream manager.

        Args:
            default_buffer_size: Default buffer size for new streams
            cleanup_interval: Interval in seconds to cleanup old streams
        """
        self.default_buffer_size = default_buffer_size
        self.cleanup_interval = cleanup_interval

        self._streams: Dict[str, EventStream] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task[None]] = None
        self._shutdown = False

        # Store reference to main event loop for cross-thread event scheduling
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None
        self._main_loop_lock = threading.Lock()

        logger.info(
            f"StreamManager initialized with buffer size {default_buffer_size}"
        )

    async def start_cleanup_task(self) -> None:
        """Start the background cleanup task."""
        if self._cleanup_task is None:
            # Capture the main event loop reference
            with self._main_loop_lock:
                self._main_loop = asyncio.get_running_loop()

            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Stream cleanup task started")

    async def stop_cleanup_task(self) -> None:
        """Stop the background cleanup task."""
        self._shutdown = True
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Stream cleanup task stopped")

    async def get_stream(self, job_id: str) -> EventStream:
        """Get or create an event stream for a job.

        Args:
            job_id: Job ID to get stream for

        Returns:
            EventStream for the job
        """
        async with self._lock:
            if job_id not in self._streams:
                self._streams[job_id] = EventStream(
                    job_id=job_id, buffer_size=self.default_buffer_size
                )
                logger.debug(f"Created new stream for job {job_id}")

            return self._streams[job_id]

    async def send_event(self, event: ServingEvent) -> bool:
        """Send an event to the appropriate job stream.

        Args:
            event: Event to send

        Returns:
            True if event was sent, False otherwise
        """
        stream = await self.get_stream(event.job_id)
        return await stream.send_event(event)

    def send_event_threadsafe(self, event: ServingEvent) -> None:
        """Send an event from a worker thread to the main event loop.

        This method is thread-safe and can be called from any thread.
        It schedules the event to be sent on the main event loop.

        Args:
            event: Event to send
        """
        with self._main_loop_lock:
            if self._main_loop is None:
                logger.warning(
                    "Main loop not available, cannot send event from worker thread"
                )
                return

            main_loop = self._main_loop

        # Schedule the async send_event on the main loop
        try:
            # Use call_soon_threadsafe to schedule the coroutine
            asyncio.run_coroutine_threadsafe(self.send_event(event), main_loop)
            # Don't wait for result to avoid blocking worker thread
            # The event will be sent asynchronously on the main loop

        except Exception as e:
            logger.warning(f"Failed to schedule event from worker thread: {e}")

    def close_stream_threadsafe(self, job_id: str) -> None:
        """Close a stream from a worker thread to the main event loop.

        This method is thread-safe and can be called from any thread.
        It schedules the stream closure on the main event loop.

        Args:
            job_id: Job ID whose stream should be closed
        """
        with self._main_loop_lock:
            if self._main_loop is None:
                logger.warning(
                    "Main loop not available, cannot close stream from worker thread"
                )
                return

            main_loop = self._main_loop

        # Schedule the async close_stream on the main loop
        try:
            # Use call_soon_threadsafe to schedule the coroutine
            asyncio.run_coroutine_threadsafe(
                self.close_stream(job_id), main_loop
            )
            # Don't wait for result to avoid blocking worker thread
            # The stream will be closed asynchronously on the main loop

        except Exception as e:
            logger.warning(
                f"Failed to schedule stream closure from worker thread: {e}"
            )

    async def subscribe_to_job(
        self, job_id: str
    ) -> AsyncGenerator[ServingEvent, None]:
        """Subscribe to events for a specific job.

        Args:
            job_id: Job ID to subscribe to

        Yields:
            ServingEvent objects for the job
        """
        stream = await self.get_stream(job_id)
        async for event in stream.subscribe():
            yield event

    async def close_stream(self, job_id: str) -> None:
        """Close the stream for a specific job.

        Args:
            job_id: Job ID to close stream for
        """
        async with self._lock:
            if job_id in self._streams:
                stream = self._streams[job_id]
                stream.close()
                del self._streams[job_id]
                logger.debug(f"Closed and removed stream for job {job_id}")

    async def get_stats(self) -> Dict[str, Any]:
        """Get stream manager statistics.

        Returns:
            Dictionary with stream statistics
        """
        async with self._lock:
            total_streams = len(self._streams)
            total_subscribers = sum(
                stream.subscriber_count for stream in self._streams.values()
            )
            active_streams = sum(
                1 for stream in self._streams.values() if not stream.is_closed
            )

        return {
            "total_streams": total_streams,
            "active_streams": active_streams,
            "total_subscribers": total_subscribers,
            "default_buffer_size": self.default_buffer_size,
        }

    async def _cleanup_loop(self) -> None:
        """Background task to periodically clean up old streams."""
        while not self._shutdown:
            try:
                await asyncio.sleep(self.cleanup_interval)
                if not self._shutdown:
                    await self._cleanup_old_streams()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in stream cleanup loop: {e}")

    async def _cleanup_old_streams(self) -> None:
        """Clean up closed streams with no subscribers."""
        async with self._lock:
            streams_to_remove = []

            for job_id, stream in self._streams.items():
                if stream.is_closed and stream.subscriber_count == 0:
                    streams_to_remove.append(job_id)

            for job_id in streams_to_remove:
                del self._streams[job_id]
                logger.debug(f"Cleaned up old stream for job {job_id}")

            if streams_to_remove:
                logger.info(f"Cleaned up {len(streams_to_remove)} old streams")


# Global stream manager instance
_stream_manager: Optional[StreamManager] = None


def get_stream_manager_sync() -> Optional[StreamManager]:
    """Get the global stream manager instance synchronously.

    Returns:
        Global StreamManager instance if available, None otherwise
    """
    global _stream_manager
    return _stream_manager


async def get_stream_manager() -> StreamManager:
    """Get the global stream manager instance.

    Returns:
        Global StreamManager instance
    """
    global _stream_manager
    if _stream_manager is None:
        _stream_manager = StreamManager()
        await _stream_manager.start_cleanup_task()
    return _stream_manager


def set_stream_manager(manager: StreamManager) -> None:
    """Set a custom stream manager (useful for testing).

    Args:
        manager: Custom stream manager instance
    """
    global _stream_manager
    _stream_manager = manager


async def shutdown_stream_manager() -> None:
    """Shutdown the global stream manager."""
    global _stream_manager
    if _stream_manager is not None:
        await _stream_manager.stop_cleanup_task()
        _stream_manager = None


@asynccontextmanager
async def stream_events_as_sse(
    job_id: str,
) -> AsyncGenerator[AsyncGenerator[str, None], None]:
    """Context manager to stream events as Server-Sent Events format.

    Args:
        job_id: Job ID to stream events for

    Yields:
        AsyncGenerator of SSE-formatted strings
    """
    stream_manager = await get_stream_manager()

    async def sse_generator() -> AsyncGenerator[str, None]:
        try:
            async for event in stream_manager.subscribe_to_job(job_id):
                # Format as SSE
                event_data = json.dumps(event.to_dict())
                sse_message = f"data: {event_data}\n\n"
                yield sse_message

        except Exception as e:
            logger.error(f"Error in SSE stream for job {job_id}: {e}")
            # Send error event
            error_event = (
                f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
            )
            yield error_event

    yield sse_generator()
