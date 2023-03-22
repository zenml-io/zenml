#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""The analytics module of ZenML.

This module is based on the 'analytics-python' package created by Segment.
The base functionalities are adapted to work with the ZenML analytics server.
"""

import atexit
import json
import logging
import numbers
import queue
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Tuple
from uuid import UUID

from six import string_types

from zenml.analytics.consumer import Consumer
from zenml.analytics.request import post
from zenml.constants import IS_DEBUG_ENV

if TYPE_CHECKING:
    from zenml.utils.analytics_utils import AnalyticsEvent

ID_TYPES = (numbers.Number, string_types)

logger = logging.getLogger(__name__)


class AnalyticsEncoder(json.JSONEncoder):
    """Helper encoder class for JSON serialization."""

    def default(self, obj: Any) -> Any:
        """The default method to handle UUID and 'AnalyticsEvent' objects.

        Args:
            obj: The object to encode.

        Returns:
            The encoded object.
        """
        from zenml.utils.analytics_utils import AnalyticsEvent

        # If the object is UUID, we simply return the value of UUID
        if isinstance(obj, UUID):
            return str(obj)

        # If the object is an AnalyticsEvent, return its value
        elif isinstance(obj, AnalyticsEvent):
            return str(obj.value)

        return json.JSONEncoder.default(self, obj)


class Client(object):
    """The client class for ZenML analytics."""

    class DefaultConfig(object):
        """The configuration class for the client.

        Attributes:
            on_error: Function to call if an error occurs.
            debug: Flag to set to switch to the debug mode.
            send: Flag to determine whether to send the message.
            sync_mode: Flag, if set to True, uses the main thread to send
                the messages, and if set to False, creates other threads
                for the analytics.
            max_queue_size: The maximum number of entries a single queue
                can hold.
            timeout: Timeout in seconds.
            max_retries: The number of max tries before failing.
            thread: The number of additional threads to create for the
                analytics if the 'sync_mode' is set to False.
            upload_interval: The upload_interval in seconds if the
                'sync_mode' is set to False.
            upload_size: The maximum size for messages a consumer can send
                if the 'sync_mode' is set to False.
        """

        on_error: Optional[Callable[..., Any]] = None
        debug: bool = False
        send: bool = True
        sync_mode: bool = False
        max_queue_size: int = 10000
        timeout: int = 15
        max_retries: int = 1
        thread: int = 1
        upload_interval: float = 0.5
        upload_size: int = 100

    def __init__(
        self,
        debug: bool = DefaultConfig.debug,
        max_queue_size: int = DefaultConfig.max_queue_size,
        send: bool = DefaultConfig.send,
        on_error: Optional[Callable[..., Any]] = DefaultConfig.on_error,
        max_retries: int = DefaultConfig.max_retries,
        sync_mode: bool = DefaultConfig.sync_mode,
        timeout: int = DefaultConfig.timeout,
        thread: int = DefaultConfig.thread,
        upload_size: int = DefaultConfig.upload_size,
        upload_interval: float = DefaultConfig.upload_interval,
    ) -> None:
        """Initialization of the client.

        Args:
            debug: Flag to set to switch to the debug mode.
            max_queue_size: The maximum number of entries a single queue
                can hold.
            send: Flag to determine whether to send the message.
            on_error: Function to call if an error occurs.
            max_retries: The number of max tries before failing.
            sync_mode: Flag, if set to True, uses the main thread to send
                the messages, and if set to False, creates other threads
                for the analytics.
            timeout: Timeout in seconds.
            thread: The number of additional threads to create for the
                analytics if the 'sync_mode' is set to False.
            upload_size: The maximum size for messages a consumer can send
                if the 'sync_mode' is set to False.
            upload_interval: The upload_interval in seconds if the
                'sync_mode' is set to False.
        """
        self.queue = queue.Queue(max_queue_size)  # type: ignore[var-annotated]
        self.on_error = on_error
        self.debug = debug
        self.send = send
        self.sync_mode = sync_mode
        self.timeout = timeout

        if debug:
            logger.setLevel(logging.DEBUG)

        if sync_mode:
            self.consumers = None
        else:
            # On program exit, allow the consumer thread to exit cleanly.
            # This prevents exceptions and a messy shutdown when the
            # interpreter is destroyed before the daemon thread finishes
            # execution. However, it is *not* the same as flushing the queue!
            # To guarantee all messages have been delivered, you'll still need
            # to call flush().
            if send:
                atexit.register(self.join)
            for _ in range(thread):
                self.consumers = []
                consumer = Consumer(
                    self.queue,
                    on_error=on_error,
                    upload_size=upload_size,
                    upload_interval=upload_interval,
                    retries=max_retries,
                    timeout=timeout,
                )
                self.consumers.append(consumer)

                # if we've disabled sending, just don't start the consumer
                if send:
                    consumer.start()

    def identify(
        self, user_id: UUID, traits: Optional[Dict[Any, Any]]
    ) -> Tuple[bool, str]:
        """Method to identify a user with given traits.

        Args:
            user_id: The user ID.
            traits: The traits for the identification process.

        Returns:
            Tuple (success flag, the original message).
        """
        msg = {
            "user_id": user_id,
            "traits": traits or {},
            "type": "identify",
            "debug": IS_DEBUG_ENV,
        }
        return self._enqueue(json.dumps(msg, cls=AnalyticsEncoder))

    def track(
        self,
        user_id: UUID,
        event: "AnalyticsEvent",
        properties: Optional[Dict[Any, Any]],
    ) -> Tuple[bool, str]:
        """Method to track events.

        Args:
            user_id: The user ID.
            event: The type of the event.
            properties: Dict of additional properties for the event.

        Returns:
            Tuple (success flag, the original message).
        """
        msg = {
            "user_id": user_id,
            "event": event,
            "properties": properties or {},
            "type": "track",
            "debug": IS_DEBUG_ENV,
        }
        return self._enqueue(json.dumps(msg, cls=AnalyticsEncoder))

    def group(
        self, user_id: UUID, group_id: UUID, traits: Optional[Dict[Any, Any]]
    ) -> Tuple[bool, str]:
        """Method to group users.

        Args:
            user_id: The user ID.
            group_id: The group ID.
            traits: Traits to assign to the group.

        Returns:
            Tuple (success flag, the original message).
        """
        msg = {
            "user_id": user_id,
            "group_id": group_id,
            "traits": traits or {},
            "type": "group",
            "debug": IS_DEBUG_ENV,
        }
        return self._enqueue(json.dumps(msg, cls=AnalyticsEncoder))

    def _enqueue(self, msg: str) -> Tuple[bool, str]:
        """Method to queue messages to be sent.

        Args:
            msg: The message to queue.

        Returns:
            Tuple (success flag, the original message).
        """
        # if send is False, return msg as if it was successfully queued
        if not self.send:
            return True, msg

        if self.sync_mode:
            post(timeout=self.timeout, batch=[msg])
            return True, msg

        try:
            self.queue.put(msg, block=False)
            return True, msg
        except queue.Full:
            logger.debug("ZenML analytics-python queue is full")
            return False, msg

    def flush(self) -> None:
        """Method to force a flush from the internal queue to the server."""
        q = self.queue
        size = q.qsize()
        q.join()
        # Note that this message may not be precise, because of threading.
        logger.debug("successfully flushed about %s items.", size)

    def join(self) -> None:
        """Method to end the consumer thread once the queue is empty."""
        for consumer in self.consumers:
            consumer.pause()
            try:
                consumer.join()
            except RuntimeError:
                # consumer thread has not started
                pass

    def shutdown(self) -> None:
        """Method to flush all messages and cleanly shutdown the client."""
        self.flush()
        self.join()
